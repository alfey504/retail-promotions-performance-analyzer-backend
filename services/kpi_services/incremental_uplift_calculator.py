from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.db_services.session import SessionLocal
from services.db_services.models import (
    Bundle,
    BundleSale,
    BundleSku,
    Product,
    Promotion,
    PromotionBundle,
    PromotionSku,
    Sale,
    Sku,
    SkuSale,
)


# ---------------------------------------------------------------------------
# Return type  (same shape as product-level UpliftResult for easy comparison)
# ---------------------------------------------------------------------------

@dataclass
class UpliftResult:
    promotion_id: int
    promotion_name: str
    promotion_type: str
    product_id: int
    product_name: str

    # Windows
    promo_start_date: date
    promo_end_date: date
    baseline_start_date: date
    baseline_end_date: date

    # Revenue
    promo_revenue: float
    baseline_revenue: float
    incremental_revenue: float          
    # Units
    promo_units: int
    baseline_units: int
    incremental_units: int             
    # Flags
    discount_bleed: bool                

# ---------------------------------------------------------------------------
# Step 1 — resolve all product_ids the promotion touches
# ---------------------------------------------------------------------------

def _product_ids_for_promotion(session: Session, promotion_id: int) -> List[int]:
    # Path A
    direct_product_ids = session.execute(
        select(Sku.product_id)
        .join(PromotionSku, PromotionSku.sku_id == Sku.sku_id)
        .where(PromotionSku.promotion_id == promotion_id)
        .distinct()
    ).scalars().all()

    # Path B
    bundle_ids = session.execute(
        select(PromotionBundle.bundle_id)
        .where(PromotionBundle.promotion_id == promotion_id)
        .distinct()
    ).scalars().all()

    bundle_product_ids: List[int] = []
    if bundle_ids:
        bundle_product_ids = session.execute(
            select(Sku.product_id)
            .join(BundleSku, BundleSku.sku_id == Sku.sku_id)
            .where(BundleSku.bundle_id.in_(list(bundle_ids)))
            .distinct()
        ).scalars().all()

    return list(set(list(direct_product_ids) + list(bundle_product_ids)))


# ---------------------------------------------------------------------------
# Step 2 — resolve sku_ids for a product that are IN SCOPE for this promo
#           (only SKUs the promo actually targets, not all SKUs of the product)
# ---------------------------------------------------------------------------

def _scoped_sku_ids(
    session: Session, promotion_id: int, product_id: int
) -> List[int]:
    # Direct
    direct = session.execute(
        select(PromotionSku.sku_id)
        .join(Sku, Sku.sku_id == PromotionSku.sku_id)
        .where(
            PromotionSku.promotion_id == promotion_id,
            Sku.product_id == product_id,
        )
        .distinct()
    ).scalars().all()

    # Via bundle
    bundle_ids = session.execute(
        select(PromotionBundle.bundle_id)
        .where(PromotionBundle.promotion_id == promotion_id)
        .distinct()
    ).scalars().all()

    bundle_skus: List[int] = []
    if bundle_ids:
        bundle_skus = session.execute(
            select(BundleSku.sku_id)
            .join(Sku, Sku.sku_id == BundleSku.sku_id)
            .where(
                BundleSku.bundle_id.in_(list(bundle_ids)),
                Sku.product_id == product_id,
            )
            .distinct()
        ).scalars().all()

    return list(set(list(direct) + list(bundle_skus)))


# ---------------------------------------------------------------------------
# Step 3 — revenue + units for a set of SKUs over a date window
#           (identical apportionment logic as product-level uplift)
# ---------------------------------------------------------------------------

def _revenue_and_units(
    session: Session,
    sku_ids: List[int],
    start: date,
    end: date,
) -> tuple[float, int]:
    if not sku_ids:
        return 0.0, 0

    # Direct SKU line items
    sku_row = session.execute(
        select(
            func.coalesce(func.sum(SkuSale.quantity * Sku.price), 0).label("rev"),
            func.coalesce(func.sum(SkuSale.quantity), 0).label("units"),
        )
        .join(Sale, SkuSale.sales_id == Sale.sales_id)
        .join(Sku,  SkuSale.sku_id   == Sku.sku_id)
        .where(
            SkuSale.sku_id.in_(sku_ids),
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
    ).one()

    sku_revenue = float(sku_row.rev)
    sku_units   = int(sku_row.units)

    # Bundle line items — apportioned share per product
    bundle_ids = session.execute(
        select(BundleSku.bundle_id)
        .where(BundleSku.sku_id.in_(sku_ids))
        .distinct()
    ).scalars().all()

    bundle_revenue = 0.0
    bundle_units   = 0

    for bid in bundle_ids:
        members = session.execute(
            select(Sku.sku_id, Sku.price)
            .join(BundleSku, BundleSku.sku_id == Sku.sku_id)
            .where(BundleSku.bundle_id == bid)
        ).all()

        total_price = sum(float(m.price) for m in members)
        our_price   = sum(float(m.price) for m in members if m.sku_id in sku_ids)

        if total_price == 0:
            continue

        ratio      = our_price / total_price
        bundle_obj = session.get(Bundle, bid)
        if bundle_obj is None:
            continue

        b_row = session.execute(
            select(func.coalesce(func.sum(BundleSale.quantity), 0).label("qty"))
            .join(Sale, BundleSale.sales_id == Sale.sales_id)
            .where(
                BundleSale.bundle_id == bid,
                Sale.sale_date >= start,
                Sale.sale_date <= end,
            )
        ).one()

        qty             = int(b_row.qty)
        bundle_revenue += ratio * float(bundle_obj.bundle_price) * qty
        bundle_units   += qty

    return round(sku_revenue + bundle_revenue, 2), sku_units + bundle_units


# ---------------------------------------------------------------------------
# Public API — session-aware
# ---------------------------------------------------------------------------

def compute_promotion_uplift(
    session: Session, promotion_id: int
) -> List[UpliftResult]:
   
    promo = session.get(Promotion, promotion_id)
    if promo is None:
        return []

    promo_start: date = promo.start_date
    promo_end:   date = promo.end_date
    N = (promo_end - promo_start).days + 1          # window length (inclusive)

    # Symmetric baseline: same N days immediately before the promo
    baseline_end   = promo_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=N - 1)

    product_ids = _product_ids_for_promotion(session, promotion_id)
    if not product_ids:
        return []

    results: List[UpliftResult] = []

    for product_id in sorted(product_ids):
        product = session.get(Product, product_id)
        if product is None:
            continue

        # Only the SKUs of this product that the promo actually targets
        sku_ids = _scoped_sku_ids(session, promotion_id, product_id)
        if not sku_ids:
            continue

        promo_revenue, promo_units = _revenue_and_units(
            session, sku_ids, promo_start, promo_end
        )
        baseline_revenue, baseline_units = _revenue_and_units(
            session, sku_ids, baseline_start, baseline_end
        )

        incremental_revenue = round(promo_revenue - baseline_revenue, 2)
        incremental_units   = promo_units - baseline_units
        discount_bleed      = (incremental_units > 0) and (incremental_revenue < 0)

        results.append(
            UpliftResult(
                promotion_id=promo.promotion_id,
                promotion_name=promo.promotion_name,
                promotion_type=promo.promotion_type,
                product_id=product_id,
                product_name=product.product_name,
                promo_start_date=promo_start,
                promo_end_date=promo_end,
                baseline_start_date=baseline_start,
                baseline_end_date=baseline_end,
                promo_revenue=promo_revenue,
                baseline_revenue=baseline_revenue,
                incremental_revenue=incremental_revenue,
                promo_units=promo_units,
                baseline_units=baseline_units,
                incremental_units=incremental_units,
                discount_bleed=discount_bleed,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Public API — session-managed convenience wrapper (mirrors your existing pattern)
# ---------------------------------------------------------------------------

def get_uplift_for_promotion(promotion_id: int) -> List[UpliftResult]:

    session = SessionLocal()
    try:
        return compute_promotion_uplift(session, promotion_id=promotion_id)
    except Exception as e:
        print(f"Error computing uplift for promotion {promotion_id}: {e}")
        raise
    finally:
        session.close()
