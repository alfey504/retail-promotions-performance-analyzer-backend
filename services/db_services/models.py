from __future__ import annotations
 
from datetime import date
from typing import List, Optional
 
from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
 
 
class Base(DeclarativeBase):
    pass
 
 
class Product(Base):
    __tablename__ = "products"
 
    product_id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_description: Mapped[Optional[str]] = mapped_column(String(500))
    product_brand: Mapped[str] = mapped_column(String(100), nullable=False)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
 
    skus: Mapped[List["Sku"]] = relationship(back_populates="product")
 
    def __repr__(self) -> str:
        return f"<Product id={self.product_id} name={self.product_name!r}>"


class Sku(Base):
    __tablename__ = "skus"
 
    sku_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), nullable=False, index=True
    )
    sku_name: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[Optional[str]] = mapped_column(String(100))
    color: Mapped[Optional[str]] = mapped_column(String(100))
    last_fulfillment_date: Mapped[Optional[date]] = mapped_column()
    next_fulfillment_date: Mapped[Optional[date]] = mapped_column()
    in_stock: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
 
    product: Mapped["Product"] = relationship(back_populates="skus")
    promotion_links: Mapped[List["PromotionSku"]] = relationship(back_populates="sku")
    fulfillment_events: Mapped[List["FullfillmentHistory"]] = relationship(back_populates="sku")
    sales: Mapped[List["Sale"]] = relationship(back_populates="sku")
 
    def __repr__(self) -> str:
        return f"<Sku id={self.sku_id} name={self.sku_name!r} price={self.price}>"
 
 
class Customer(Base):
    __tablename__ = "customer"
 
    customer_id: Mapped[int] = mapped_column(primary_key=True)
    customer_age: Mapped[int] = mapped_column(nullable=False)
    customer_gender: Mapped[str] = mapped_column(String(20), nullable=False)
    ethnicity: Mapped[str] = mapped_column(String(20), nullable=False)
 
    sales: Mapped[List["Sale"]] = relationship(back_populates="customer")
 
    def __repr__(self) -> str:
        return f"<Customer id={self.customer_id} age={self.customer_age}>"

 
class Promotion(Base):
    __tablename__ = "promotions"
 
    promotion_id: Mapped[int] = mapped_column(primary_key=True)
    promotion_name: Mapped[str] = mapped_column(String(100), nullable=False)
    promotion_description: Mapped[Optional[str]] = mapped_column(String(500))
    promotion_type: Mapped[str] = mapped_column(String(100), nullable=False)
    discount_percent: Mapped[Optional[int]] = mapped_column()
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)
 
    sku_links: Mapped[List["PromotionSku"]] = relationship(back_populates="promotion")
    sales: Mapped[List["Sale"]] = relationship(back_populates="promotion")
 
    def __repr__(self) -> str:
        return f"<Promotion id={self.promotion_id} name={self.promotion_name!r}>"

 
class PromotionSku(Base):
    """Normalizes promotions.target_sku (many-to-many) -- which SKUs a
    promotion targets."""
    __tablename__ = "promotion_sku"
 
    promo_sku_id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("promotions.promotion_id"), nullable=False, index=True
    )
    sku_id: Mapped[int] = mapped_column(
        ForeignKey("skus.sku_id"), nullable=False, index=True
    )
 
    promotion: Mapped["Promotion"] = relationship(back_populates="sku_links")
    sku: Mapped["Sku"] = relationship(back_populates="promotion_links")
 
    __table_args__ = (
        UniqueConstraint("promotion_id", "sku_id", name="uq_promotion_sku"),
    )
 
    def __repr__(self) -> str:
        return f"<PromotionSku promotion={self.promotion_id} sku={self.sku_id}>"
 
 
 
class FullfillmentHistory(Base):
    __tablename__ = "fullfillment_history"
 
    fullfillment_id: Mapped[int] = mapped_column(primary_key=True)
    sku_id: Mapped[int] = mapped_column(
        ForeignKey("skus.sku_id"), nullable=False, index=True
    )
    fullfillment_date: Mapped[date] = mapped_column(nullabe=False)
    quantity_received: Mapped[int] = mapped_column(nullable=False)
 
    sku: Mapped["Sku"] = relationship(back_populates="fulfillment_events")
 
    def __repr__(self) -> str:
        return (
            f"<FullfillmentHistory sku={self.sku_id} "
            f"date={self.fullfillment_date} qty={self.quantity_received}>"
        )
 
class Sale(Base):
    __tablename__ = "sales"
 
    sales_id: Mapped[int] = mapped_column(primary_key=True)
    sku_id: Mapped[int] = mapped_column(
        ForeignKey("skus.sku_id"), nullable=False, index=True
    )
    promotion_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("promotions.promotion_id"), index=True
    )
    regular_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    final_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customer.customer_id"), index=True
    )
    sale_date: Mapped[date] = mapped_column(nullable=False)
 
    sku: Mapped["Sku"] = relationship(back_populates="sales")
    promotion: Mapped[Optional["Promotion"]] = relationship(back_populates="sales")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="sales")
 
    def __repr__(self) -> str:
        return (
            f"<Sale id={self.sales_id} sku={self.sku_id} "
            f"final_price={self.final_price}>"
        )
 