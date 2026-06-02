import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web
from sqlalchemy import select

from database import init_db, async_session
from models import (
    Product, ProductVariant, Customer, Order, OrderItem,
    Wallet, OrderStatus,
)
import bridge_client
from pix_gateway import create_pix_deposit, generate_external_id
from correios_api import calcular_frete, format_frete_info
from catalog_seeder import seed_database
from payment_poller import PaymentPoller
from admin_handler import is_admin, send_admin_dashboard
import llm_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zapturbo")

BANNER_PATH = os.getenv("BANNER_PATH", "static/banner.jpg")
FREIGHT_FREE_MIN = float(os.getenv("FREIGHT_FREE_MIN", "199.00"))

_conversation_history = {}


async def handle_webhook(request):
    try:
        body = await request.json()
        phone = body.get("phone", "")
        text = body.get("text", "")
        name = body.get("name", "Cliente")

        if not phone or not text:
            return web.json_response({"status": "ok"})

        if text.startswith("/"):
            await handle_command(phone, text, name)
        else:
            await handle_message(phone, text, name)

        return web.json_response({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.json_response({"status": "error"}, status=500)


async def handle_command(phone: str, command: str, push_name: str):
    cmd_parts = command.strip().split()
    cmd = cmd_parts[0].lower()

    if cmd == "/start" or cmd == "/menu":
        await bridge_client.send_text(phone, (
            "🛍️ *Bem-vindo à ZAPTURBO!* 🛍️\n\n"
            "Sou seu atendente virtual de moda masculina.\n"
            "Pode me dizer o que você está procurando ou escolher uma opção:\n\n"
            "• *Ver catálogo* — digite /catalogo\n"
            "• *Meu saldo* — digite /saldo\n"
            "• *Meus pedidos* — digite /pedidos\n"
            "• *Falar com admin* — digite /admin\n\n"
            "Ou simplesmente me pergunte sobre roupas! 😊"
        ))

    elif cmd == "/catalogo":
        async with async_session() as session:
            result = await session.execute(
                select(Product).where(Product.is_active == True)
            )
            products = result.scalars().all()

            if not products:
                await bridge_client.send_text(phone, "📭 Catálogo vazio no momento. Volte em breve!")
                return

            categorias = {}
            for p in products:
                categorias.setdefault(p.categoria, []).append(p)

            msg = "🛍️ *Catálogo ZAPTURBO*\n\n"
            for cat, prods in sorted(categorias.items()):
                msg += f"*{cat.upper()}*\n"
                for p in prods:
                    msg += f"• {p.nome} — *R$ {p.preco:.2f}*\n"
                msg += "\n"

            msg += "Quer ver detalhes de algum? Me fala o nome! 😊"
            await bridge_client.send_text(phone, msg)

    elif cmd == "/saldo":
        async with async_session() as session:
            wallet = await session.get(Wallet, phone)
            balance = wallet.balance if wallet else 0.0
            await bridge_client.send_text(phone, f"💰 *Saldo atual:* R$ {balance:.2f}")

    elif cmd == "/pedidos":
        async with async_session() as session:
            status_labels = {
                OrderStatus.PAID: "✅ Pago (aguardando endereço)",
                OrderStatus.AWAITING_SHIPPING: "📦 Aguardando envio",
                OrderStatus.SHIPPED: "📬 Enviado",
                OrderStatus.DELIVERED: "📬 Entregue",
                OrderStatus.CANCELLED: "❌ Cancelado",
            }

            result = await session.execute(
                select(Order).where(Order.phone == phone).order_by(Order.created_at.desc())
            )
            orders = result.scalars().all()[:5]

            if not orders:
                await bridge_client.send_text(phone, "📋 Nenhum pedido encontrado.")
                return

            msg = "📋 *Seus Pedidos*\n\n"
            for o in orders:
                label = status_labels.get(o.status, o.status.value)
                msg += f"#{o.id} - {label} - R$ {o.total:.2f}\n"
                if o.codigo_rastreio:
                    msg += f"📦 Rastreio: {o.codigo_rastreio}\n"
                msg += "\n"

            await bridge_client.send_text(phone, msg)

    elif cmd == "/admin" and cmd_parts:
        if not is_admin(phone):
            await bridge_client.send_text(phone, "⛔ Comando restrito a administradores.")
            return

        sub = cmd_parts[1] if len(cmd_parts) > 1 else "dashboard"

        if sub == "dashboard":
            async with async_session() as session:
                await send_admin_dashboard(session, phone)
        elif sub == "enviar" and len(cmd_parts) >= 3:
            notify_phone = cmd_parts[2]
            tracking_code = " ".join(cmd_parts[3:]) if len(cmd_parts) > 3 else ""
            await bridge_client.send_text(phone, f"Função de envio em desenvolvimento.")
        else:
            await bridge_client.send_text(phone, (
                "📋 *Comandos Admin:*\n"
                "/admin dashboard — visão geral\n"
                "/admin enviar [telefone] [codigo] — marcar como enviado\n"
                "/admin estornar [telefone] [valor] — estornar saldo"
            ))

    elif cmd == "/ajuda" or cmd == "/help":
        await bridge_client.send_text(phone, (
            "❓ *Ajuda ZAPTURBO*\n\n"
            "• Fale naturalmente sobre o que procura\n"
            "• /catalogo — Ver todos os produtos\n"
            "• /saldo — Seu saldo em carteira\n"
            "• /pedidos — Acompanhar pedidos\n"
            "• /menu — Menu principal\n\n"
            "Estou aqui para ajudar! 😊"
        ))

    else:
        await handle_message(phone, command, push_name)


async def handle_message(phone: str, text: str, push_name: str):
    history = _conversation_history.setdefault(phone, [])

    customer_name = None
    async with async_session() as session:
        customer = await session.get(Customer, phone)
        if customer and customer.nome:
            customer_name = customer.nome

    llm_response = await llm_handler.process_message(text, history, phone, customer_name or push_name)

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": llm_response})
    if len(history) > 20:
        history[:] = history[-20:]

    await _process_llm_actions(phone, text, llm_response)


async def _process_llm_actions(phone: str, user_msg: str, llm_response: str):
    async with async_session() as session:
        customer = await session.get(Customer, phone)
        if not customer:
            customer = Customer(phone=phone)
            session.add(customer)

        user_lower = user_msg.lower()

        if any(p in user_lower for p in ["quero comprar", "comprar", "quero", "pedir", "encomendar"]):
            categoria = _extract_categoria(user_lower)
            result = await session.execute(
                select(Product).where(
                    Product.is_active == True,
                    Product.categoria.ilike(f"%{categoria}%") if categoria else True,
                ).limit(10)
            )
            products = result.scalars().all()
            if products:
                msg = "Aqui estão as opções:\n\n"
                for p in products:
                    variants_result = await session.execute(
                        select(ProductVariant).where(ProductVariant.product_id == p.id)
                    )
                    variants = variants_result.scalars().all()
                    cores = list(set(v.cor for v in variants))
                    tamanhos = list(set(v.tamanho for v in variants))
                    msg += f"🛍️ *{p.nome}*\n"
                    msg += f"💰 R$ {p.preco:.2f}\n"
                    msg += f"🎨 Cores: {', '.join(cores)}\n"
                    msg += f"📏 Tam: {', '.join(tamanhos)}\n\n"

                msg += "Me fala qual te interessou, a cor e o tamanho! 😊"
                await bridge_client.send_text(phone, msg)

        if "cep" in user_lower or "frete" in user_lower:
            cep = _extract_cep(user_msg)
            if cep:
                result = await session.execute(
                    select(Order).where(
                        Order.phone == phone,
                        Order.status == OrderStatus.PAID,
                    ).order_by(Order.created_at.desc())
                )
                order = result.scalar_one_or_none()

                peso = _estimate_weight(order) if order else 0.5
                frete = await calcular_frete(
                    cep_origem="01001000",
                    cep_destino=cep,
                    peso_kg=peso,
                    valor_declarado=order.total if order else 100.0,
                )

                if frete:
                    total_com_frete = (order.total + frete["valor"]) if order else frete["valor"]
                    msg = format_frete_info(frete)
                    if total_com_frete >= FREIGHT_FREE_MIN:
                        msg += "🔥 *Frete grátis* para esta compra!\n"
                    msg += "\nQual seu endereço completo para entrega? (Rua, número, bairro)"
                    await bridge_client.send_text(phone, msg)

        if any(p in user_lower for p in ["endereço", "rua", "avenida", "av.", "travessa"]):
            customer.endereco = user_msg.strip()
            session.add(customer)
            await session.commit()
            await bridge_client.send_text(phone, (
                "📍 Endereço registrado com sucesso!\n\n"
                "Assim que o pagamento for confirmado, já separamos seu pedido! ✅"
            ))

        customer_data = await session.get(Customer, phone)
        if customer_data and not customer_data.nome:
            if "meu nome" in user_lower or "chamo" in user_lower or "me chamo" in user_lower:
                nome = _extract_name(user_msg)
                if nome:
                    customer_data.nome = nome
                    session.add(customer_data)
                    await session.commit()

    await bridge_client.send_text(phone, llm_response)


async def _check_and_start_checkout(phone: str):
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                Order.phone == phone,
                Order.status == OrderStatus.CART,
            ).order_by(Order.created_at.desc())
        )
        order = result.scalar_one_or_none()

        if not order or not order.items:
            return

        total = sum(item.preco_unitario * item.quantidade for item in order.items)

        ext_id = generate_external_id("PEDIDO")
        pix = await create_pix_deposit(total, ext_id)

        if not pix or "qrcode" not in pix:
            return

        order.total = total
        order.status = OrderStatus.AWAITING_PAYMENT
        order.pix_qrcode = pix.get("qrcode", "")
        order.pix_copia_cola = pix.get("copia_e_cola", pix.get("text", ""))
        order.pix_external_id = ext_id
        await session.commit()

        msg = (
            f"🛒 *Resumo do Pedido*\n\n"
            f"{_format_order_items(order)}\n\n"
            f"💰 *Total: R$ {total:.2f}*\n\n"
            f"📱 *PIX (Copia e Cola):*\n"
            f"`{order.pix_copia_cola}`\n\n"
            f"⌛ Prazo para pagamento: 10 minutos\n\n"
            f"Após o pagamento confirmar, peço seu endereço! ✅"
        )
        await bridge_client.send_text(phone, msg)

        if order.pix_qrcode:
            await bridge_client.send_text(phone, f"📱 Ou escaneie o QR Code:\n{order.pix_qrcode}")


def _format_order_items(order: Order) -> str:
    lines = []
    for item in order.items:
        nome = item.product.nome if item.product else "Produto"
        var = item.variant
        var_str = f" ({var.cor}/{var.tamanho})" if var else ""
        lines.append(f"• {nome}{var_str} x{item.quantidade} = R$ {item.preco_unitario * item.quantidade:.2f}")
    return "\n".join(lines)


def _extract_categoria(text: str) -> str:
    cats = {
        "camiseta": "Camisetas",
        "camisa": "Camisas",
        "calça": "Calças",
        "bermuda": "Calças",
        "short": "Calças",
        "regata": "Regatas",
        "moletom": "Moletons",
        "conjunto": "Conjuntos",
        "bone": "Acessórios",
        "boné": "Acessórios",
        "touca": "Acessórios",
        "meia": "Acessórios",
    }
    for word, cat in cats.items():
        if word in text:
            return cat
    return ""


def _extract_cep(text: str) -> str:
    import re
    match = re.search(r'\b(\d{5}-?\d{3})\b', text)
    return match.group(1) if match else ""


def _extract_name(text: str) -> str:
    patterns = [
        "meu nome é ", "me chamo ", "sou ", "é ", "chamo ",
    ]
    for p in patterns:
        if p in text.lower():
            return text.lower().split(p)[-1].strip().title()
    return ""


def _estimate_weight(order: Order) -> float:
    if not order or not order.items:
        return 0.5
    items_weight = sum(item.quantidade * 0.3 for item in order.items)
    return min(items_weight, 10.0)


async def main():
    logger.info("Iniciando ZAPTURBO Bot...")
    await init_db()
    logger.info("Banco de dados inicializado")

    async with async_session() as session:
        await seed_database(session)
    logger.info("Catálogo verificado/populado")

    payment_poller = PaymentPoller(async_session)
    app = web.Application()
    async def health(request):
        return web.json_response({"status": "ok", "service": "zapturbo-bot"})

    async def handle_outbox(request):
        msgs = bridge_client.get_outbox_messages()
        return web.json_response({"messages": msgs})

    async def handle_outbox_sent(request):
        msg_id = request.match_info.get("id", "")
        try:
            bridge_client.mark_message_sent(int(msg_id))
            return web.json_response({"ok": True})
        except (ValueError, IndexError):
            return web.json_response({"ok": False}, status=400)

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/outbox", handle_outbox)
    app.router.add_post("/outbox/{id}/sent", handle_outbox_sent)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Servidor rodando na porta {port}")

    poller_task = asyncio.create_task(payment_poller.start())

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

    logger.info("Desligando...")
    payment_poller.stop()
    poller_task.cancel()
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
