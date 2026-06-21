"""
SQLAlchemy models for the Retail Promotion Performance Analyzer schema.

The JSON files (`products.json`, `skus.json`, `customers.json`, `promotions.json`,
`bundles.json`, `fulfillment_history.json`, `sales.json`) use embedded arrays for
relationships (`target_sku_ids`, `sku_ids`, `sku_sales`, `bundle_sales`,
`promotion_ids`, ...). A real relational database can't store an array of ids in
an int column, so every embedded relationship below is normalized into a proper
junction table instead:

    JSON (embedded array)                  ->  Relational (junction table)
    ------------------------------------------------------------------------
    bundle.sku_ids[]                       ->  bundle_skus
    promotion.target_sku_ids[]             ->  promotion_skus
    promotion.target_bundle_ids[]          ->  promotion_bundles
    sale.sku_sales[{sku_id, quantity}]     ->  sku_sales            (line items)
    sale.bundle_sales[{bundle_id, qty}]    ->  bundle_sales          (line items)
    sale.promotion_ids[]                   ->  sale_promotions       (junction)

`sku_sales` and `bundle_sales` are technically junction tables too, but since
each row also carries a `quantity`, they're modeled as their own entities
(line items) rather than bare association tables.

Tables: Product, Sku, Customer, Promotion, Bundle, FulfillmentHistory, Sale,
SkuSale, BundleSale, plus junction tables BundleSku, PromotionSku,
PromotionBundle, SalePromotion.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# =============================================================================
# Reference data (sourced from products.json / skus.json / customers.json)
# =============================================================================

class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    product_description: Mapped[Optional[str]] = mapped_column(String(500))
    product_brand: Mapped[str] = mapped_column(String(120), nullable=False)
    product_category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)

    skus: Mapped[List["Sku"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.product_id} name={self.product_name!r}>"


class Sku(Base):
    __tablename__ = "skus"

    sku_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"), nullable=False, index=True)
    sku_name: Mapped[str] = mapped_column(String(160), nullable=False)
    size: Mapped[Optional[str]] = mapped_column(String(30))
    color: Mapped[Optional[str]] = mapped_column(String(60))
    last_fulfillment_date: Mapped[Optional[date]] = mapped_column(Date)
    next_fulfillment_date: Mapped[Optional[date]] = mapped_column(Date)
    in_stock: Mapped[int] = mapped_column(nullable=False, default=0)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="skus")

    bundle_links: Mapped[List["BundleSku"]] = relationship(back_populates="sku")
    promotion_links: Mapped[List["PromotionSku"]] = relationship(back_populates="sku")
    fulfillment_events: Mapped[List["FulfillmentHistory"]] = relationship(back_populates="sku")
    sale_lines: Mapped[List["SkuSale"]] = relationship(back_populates="sku")

    __table_args__ = (
        CheckConstraint("in_stock >= 0", name="ck_sku_in_stock_nonneg"),
        CheckConstraint("price > 0", name="ck_sku_price_positive"),
    )

    def __repr__(self) -> str:
        return f"<Sku id={self.sku_id} name={self.sku_name!r} price={self.price}>"


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    customer_age: Mapped[int] = mapped_column(nullable=False)
    customer_gender: Mapped[Optional[str]] = mapped_column(String(30))
    ethnicity: Mapped[Optional[str]] = mapped_column(String(60))

    sales: Mapped[List["Sale"]] = relationship(back_populates="customer")

    __table_args__ = (
        CheckConstraint("customer_age > 0", name="ck_customer_age_positive"),
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.customer_id} age={self.customer_age}>"


# =============================================================================
# Promotions & bundles (sourced from promotions.json / bundles.json)
# =============================================================================

class Promotion(Base):
    __tablename__ = "promotions"

    promotion_id: Mapped[int] = mapped_column(primary_key=True)
    promotion_name: Mapped[str] = mapped_column(String(160), nullable=False)
    promotion_type: Mapped[str] = mapped_column(String(40), nullable=False)
    discount_percent: Mapped[Optional[int]] = mapped_column()  # null/0 for BOGO-style mechanics
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # was promotion.target_sku_ids[] / target_bundle_ids[] in the JSON -- normalized below
    sku_links: Mapped[List["PromotionSku"]] = relationship(back_populates="promotion")
    bundle_links: Mapped[List["PromotionBundle"]] = relationship(back_populates="promotion")
    sale_links: Mapped[List["SalePromotion"]] = relationship(back_populates="promotion")

    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ck_promotion_end_after_start"),
        CheckConstraint(
            "discount_percent IS NULL OR (discount_percent >= 0 AND discount_percent <= 100)",
            name="ck_promotion_discount_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<Promotion id={self.promotion_id} name={self.promotion_name!r}>"


class Bundle(Base):
    __tablename__ = "bundles"

    bundle_id: Mapped[int] = mapped_column(primary_key=True)
    bundle_name: Mapped[str] = mapped_column(String(160), nullable=False)
    bundle_description: Mapped[Optional[str]] = mapped_column(String(500))
    bundle_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # was bundle.sku_ids[] in the JSON -- normalized below
    sku_links: Mapped[List["BundleSku"]] = relationship(back_populates="bundle")
    promotion_links: Mapped[List["PromotionBundle"]] = relationship(back_populates="bundle")
    sale_lines: Mapped[List["BundleSale"]] = relationship(back_populates="bundle")

    __table_args__ = (
        CheckConstraint("bundle_price > 0", name="ck_bundle_price_positive"),
    )

    def __repr__(self) -> str:
        return f"<Bundle id={self.bundle_id} name={self.bundle_name!r}>"


# -----------------------------------------------------------------------------
# Junction tables: bundle <-> sku, promotion <-> sku, promotion <-> bundle
# -----------------------------------------------------------------------------

class BundleSku(Base):
    """Normalizes bundle.sku_ids[] -- which SKUs make up a bundle."""
    __tablename__ = "bundle_skus"

    bundle_sku_id: Mapped[int] = mapped_column(primary_key=True)
    bundle_id: Mapped[int] = mapped_column(ForeignKey("bundles.bundle_id"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.sku_id"), nullable=False, index=True)

    bundle: Mapped["Bundle"] = relationship(back_populates="sku_links")
    sku: Mapped["Sku"] = relationship(back_populates="bundle_links")

    __table_args__ = (
        UniqueConstraint("bundle_id", "sku_id", name="uq_bundle_sku"),
    )

    def __repr__(self) -> str:
        return f"<BundleSku bundle={self.bundle_id} sku={self.sku_id}>"


class PromotionSku(Base):
    """Normalizes promotion.target_sku_ids[] -- which SKUs a promotion directly targets."""
    __tablename__ = "promotion_skus"

    promo_sku_id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.sku_id"), nullable=False, index=True)

    promotion: Mapped["Promotion"] = relationship(back_populates="sku_links")
    sku: Mapped["Sku"] = relationship(back_populates="promotion_links")

    __table_args__ = (
        UniqueConstraint("promotion_id", "sku_id", name="uq_promotion_sku"),
    )

    def __repr__(self) -> str:
        return f"<PromotionSku promotion={self.promotion_id} sku={self.sku_id}>"


class PromotionBundle(Base):
    """Normalizes promotion.target_bundle_ids[] -- which bundles a promotion targets."""
    __tablename__ = "promotion_bundles"

    promo_bundle_id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), nullable=False, index=True)
    bundle_id: Mapped[int] = mapped_column(ForeignKey("bundles.bundle_id"), nullable=False, index=True)

    promotion: Mapped["Promotion"] = relationship(back_populates="bundle_links")
    bundle: Mapped["Bundle"] = relationship(back_populates="promotion_links")

    __table_args__ = (
        UniqueConstraint("promotion_id", "bundle_id", name="uq_promotion_bundle"),
    )

    def __repr__(self) -> str:
        return f"<PromotionBundle promotion={self.promotion_id} bundle={self.bundle_id}>"


# =============================================================================
# Fulfillment (sourced from fulfillment_history.json)
# =============================================================================

class FulfillmentHistory(Base):
    __tablename__ = "fulfillment_history"

    fulfillment_id: Mapped[int] = mapped_column(primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.sku_id"), nullable=False, index=True)
    fulfillment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity_received: Mapped[int] = mapped_column(nullable=False)

    sku: Mapped["Sku"] = relationship(back_populates="fulfillment_events")

    __table_args__ = (
        CheckConstraint("quantity_received > 0", name="ck_fulfillment_qty_positive"),
    )

    def __repr__(self) -> str:
        return f"<FulfillmentHistory sku={self.sku_id} date={self.fulfillment_date} qty={self.quantity_received}>"


# =============================================================================
# Sales (sourced from sales.json -- transaction header + embedded line items)
# =============================================================================

class Sale(Base):
    """Transaction header. Line items live in SkuSale / BundleSale; the set of
    promotions the cart claims lives in SalePromotion (was sale.promotion_ids[])."""
    __tablename__ = "sales"

    sales_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"), nullable=False, index=True)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    final_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="sales")
    sku_sales: Mapped[List["SkuSale"]] = relationship(back_populates="sale", cascade="all, delete-orphan")
    bundle_sales: Mapped[List["BundleSale"]] = relationship(back_populates="sale", cascade="all, delete-orphan")
    promotion_links: Mapped[List["SalePromotion"]] = relationship(back_populates="sale", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("final_price >= 0", name="ck_sale_final_price_nonneg"),
    )

    def __repr__(self) -> str:
        return f"<Sale id={self.sales_id} date={self.sale_date} total={self.final_price}>"


class SalePromotion(Base):
    """Normalizes sale.promotion_ids[] -- which promotion(s) a cart claims.
    A sale can list zero (no promotion touched the cart), one, or several
    promotion ids (e.g. when line items from two different, concurrently
    running, SKU-disjoint promotions land in the same cart)."""
    __tablename__ = "sale_promotions"

    sale_promotion_id: Mapped[int] = mapped_column(primary_key=True)
    sales_id: Mapped[int] = mapped_column(ForeignKey("sales.sales_id"), nullable=False, index=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), nullable=False, index=True)

    sale: Mapped["Sale"] = relationship(back_populates="promotion_links")
    promotion: Mapped["Promotion"] = relationship(back_populates="sale_links")

    __table_args__ = (
        UniqueConstraint("sales_id", "promotion_id", name="uq_sale_promotion"),
    )

    def __repr__(self) -> str:
        return f"<SalePromotion sale={self.sales_id} promotion={self.promotion_id}>"


class SkuSale(Base):
    """Line item: one SKU + quantity within a sale. Was sale.sku_sales[] in the JSON."""
    __tablename__ = "sku_sales"

    sku_sale_id: Mapped[int] = mapped_column(primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.sku_id"), nullable=False, index=True)
    sales_id: Mapped[int] = mapped_column(ForeignKey("sales.sales_id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(nullable=False)

    sku: Mapped["Sku"] = relationship(back_populates="sale_lines")
    sale: Mapped["Sale"] = relationship(back_populates="sku_sales")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_sku_sale_qty_min1"),
    )

    def __repr__(self) -> str:
        return f"<SkuSale sale={self.sales_id} sku={self.sku_id} qty={self.quantity}>"


class BundleSale(Base):
    """Line item: one bundle + quantity within a sale. Was sale.bundle_sales[] in the JSON."""
    __tablename__ = "bundle_sales"

    bundle_sale_id: Mapped[int] = mapped_column(primary_key=True)
    bundle_id: Mapped[int] = mapped_column(ForeignKey("bundles.bundle_id"), nullable=False, index=True)
    sales_id: Mapped[int] = mapped_column(ForeignKey("sales.sales_id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(nullable=False)

    bundle: Mapped["Bundle"] = relationship(back_populates="sale_lines")
    sale: Mapped["Sale"] = relationship(back_populates="bundle_sales")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_bundle_sale_qty_min1"),
    )

    def __repr__(self) -> str:
        return f"<BundleSale sale={self.sales_id} bundle={self.bundle_id} qty={self.quantity}>"


# =============================================================================
# Convenience: create all tables against a given engine
# =============================================================================

def create_all(engine) -> None:
    """Create every table defined above against the given SQLAlchemy engine.

    Example:
        from sqlalchemy import create_engine
        from models import create_all

        engine = create_engine("sqlite:///promotions.db")
        create_all(engine)
    """
    Base.metadata.create_all(engine)
