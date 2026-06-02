import os
from typing import Optional
from sqlalchemy import select

import evolution_client

ADMIN_PHONES = [p.strip() for p in os.getenv("ADMIN_PHONES", "").split(",") if p.strip()]


def is_admin(phone: str) -> bool:
    return phone in ADMIN_PHONES


async def notify_new_order(session, order_id: int, phone: str, total: float):
    from models import Order, OrderItem, Customer, Product, ProductVariant

    for admin_phone in ADMIN_PHONES:
        items_result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = items_result.scalars().all()

        msg = f"🛒 *Novo Pedido #{order_id}*\n\n"
        for item in items:
            prod = await session.get(Product, item.product_id)
            var = await session.get(ProductVariant, item.variant_id) if item.variant_id else None
            var_str = f" ({var.cor}/{var.tamanho})" if var else ""
            msg += f"• {prod.nome}{var_str} x{item.quantidade}\n"

        msg += f"\n💰 Total: R$ {total:.2f}"
        msg += f"\n📱 Cliente: {phone}"

        customer_result = await session.execute(select(Customer).where(Customer.phone == phone))
        customer = customer_result.scalar_one_or_none()
        if customer and customer.nome:
            msg += f"\n👤 Nome: {customer.nome}"

        await evolution_client.send_text(admin_phone, msg)


async def notify_status_change(phone: str, order_id: int, new_status: str, tracking: Optional[str] = None):
    status_labels = {
        "paid": "✅ Pago",
        "shipped": "📦 Enviado",
        "delivered": "📬 Entregue",
        "cancelled": "❌ Cancelado",
    }
    label = status_labels.get(new_status, new_status)

    msg = f"📋 *Pedido #{order_id}* — {label}\n\n"
    if new_status == "shipped" and tracking:
        msg += f"📦 Código de rastreio: `{tracking}`\n"
        msg += "Acompanhe pelo site dos Correios."
    elif new_status == "paid":
        msg += "Agora preciso do seu endereço para envio! 📍"

    await evolution_client.send_text(phone, msg)


async def send_admin_dashboard(session, admin_phone: str):
    from models import Order, OrderStatus

    msg = "📊 *Dashboard ZAPTURBO*\n\n"

    for status in OrderStatus:
        result = await session.execute(select(Order).where(Order.status == status))
        count = len(result.scalars().all())

        label = {
            OrderStatus.CART: "🛒 Carrinhos",
            OrderStatus.AWAITING_PAYMENT: "⏳ Aguardando Pagamento",
            OrderStatus.PAID: "✅ Pago - Aguardando Endereço",
            OrderStatus.AWAITING_SHIPPING: "📦 Aguardando Envio",
            OrderStatus.SHIPPED: "📬 Enviados",
            OrderStatus.DELIVERED: "📬 Entregues",
            OrderStatus.CANCELLED: "❌ Cancelados",
        }.get(status, status.value)

        msg += f"{label}: {count}\n"

    await evolution_client.send_text(admin_phone, msg)
