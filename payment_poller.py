import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select

import pix_gateway
import cloud_api

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30
EXPIRATION_MINUTES = 10


class PaymentPoller:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._running = False

    async def start(self):
        self._running = True
        while self._running:
            try:
                await self._check_pending_payments()
            except Exception as e:
                logger.error(f"PaymentPoller error: {e}")
            await asyncio.sleep(POLL_INTERVAL)

    async def stop(self):
        self._running = False

    async def _check_pending_payments(self):
        from models import Order, OrderStatus, Wallet, WalletTransaction, TransactionType, TransactionStatus

        async with self.session_factory() as session:
            result = await session.execute(
                select(Order).where(Order.status == OrderStatus.AWAITING_PAYMENT)
            )
            orders = result.scalars().all()

            for order in orders:
                if not order.pix_external_id:
                    continue

                if order.created_at and datetime.utcnow() - order.created_at > timedelta(minutes=EXPIRATION_MINUTES):
                    order.status = OrderStatus.CANCELLED
                    await session.commit()
                    await cloud_api.send_text(
                        order.phone,
                        f"⏰ O prazo de pagamento do pedido #{order.id} expirou.\n"
                        f"Se ainda quiser, é só pedir um novo PIX! 😊"
                    )
                    continue

                status = await pix_gateway.check_deposit_status(order.pix_external_id)
                if status == "COMPLETED":
                    order.status = OrderStatus.PAID

                    wallet_result = await session.execute(
                        select(Wallet).where(Wallet.phone == order.phone)
                    )
                    wallet = wallet_result.scalar_one_or_none()

                    if wallet:
                        wallet.balance += order.total
                        tx = WalletTransaction(
                            phone=order.phone,
                            amount=order.total,
                            type=TransactionType.TOPUP,
                            status=TransactionStatus.PAID,
                            external_id=order.pix_external_id,
                            description=f"Pagamento pedido #{order.id}",
                        )
                        session.add(tx)

                    await session.commit()

                    await cloud_api.send_text(
                        order.phone,
                        f"✅ *Pagamento confirmado!* Pedido #{order.id} no valor de "
                        f"R$ {order.total:.2f}\n\n"
                        f"Agora preciso do seu *CEP* e *endereço completo* "
                        f"para calcular o frete e finalizar a entrega. 📍"
                    )
