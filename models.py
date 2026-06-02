from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base
import enum


class OrderStatus(str, enum.Enum):
    CART = "cart"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    AWAITING_SHIPPING = "awaiting_shipping"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class TransactionType(str, enum.Enum):
    TOPUP = "topup"
    PURCHASE = "purchase"
    REFUND = "refund"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)
    preco = Column(Float, nullable=False)
    categoria = Column(String(100), nullable=False, index=True)
    subcategoria = Column(String(100), nullable=True)
    imagem_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    cor = Column(String(50), nullable=False)
    tamanho = Column(String(20), nullable=False)
    estoque = Column(Integer, default=0)

    product = relationship("Product", back_populates="variants")


class Customer(Base):
    __tablename__ = "customers"

    phone = Column(String(20), primary_key=True)
    nome = Column(String(200), nullable=True)
    endereco = Column(String(300), nullable=True)
    cidade = Column(String(100), nullable=True)
    uf = Column(String(2), nullable=True)
    cep = Column(String(10), nullable=True)
    complemento = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")
    wallet = relationship("Wallet", back_populates="customer", uselist=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), ForeignKey("customers.phone"), nullable=False)
    total = Column(Float, nullable=False, default=0.0)
    frete_valor = Column(Float, nullable=True, default=0.0)
    prazo_entrega = Column(String(50), nullable=True)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.CART, nullable=False)
    pix_qrcode = Column(Text, nullable=True)
    pix_copia_cola = Column(String(500), nullable=True)
    pix_external_id = Column(String(100), nullable=True)
    codigo_rastreio = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class Wallet(Base):
    __tablename__ = "wallets"

    phone = Column(String(20), ForeignKey("customers.phone"), primary_key=True)
    balance = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="wallet")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), ForeignKey("customers.phone"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(SAEnum(TransactionType), nullable=False)
    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.PENDING)
    external_id = Column(String(100), nullable=True, index=True)
    description = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseHistory(Base):
    __tablename__ = "purchase_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), ForeignKey("customers.phone"), nullable=False)
    product_sku = Column(String(50), nullable=False)
    product_nome = Column(String(200), nullable=False)
    quantidade = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
