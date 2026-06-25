
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Import your models -- adjust the import path to wherever models.py lives.
from services.db_services.models import (
    Bundle,
    BundleSale,
    BundleSku,
    Product,
    Promotion,
    PromotionBundle,
    PromotionSku,
    Sale,
    SalePromotion,
    Sku,
    SkuSale,
)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class UpliftResult:

    product_id: int
    promotion_id: int
    promotion_name: str
    promotion_type: str

    # Promotion window
    promo_start_date: date
    promo_end_date: date

    # Symmetric pre-promo baseline window (same length as promo)
    baseline_start_date: date
    baseline_end_date: date

    # Revenue totals
    promo_revenue: float
    baseline_revenue: float

    # Derived metrics
    incremental_revenue: float          # promo_revenue − baseline_revenue
    promo_units: int
    baseline_units: int
    incremental_units: int              # promo_units − baseline_units

    # Flags
    discount_bleed: bool                # positive unit lift but negative revenue lift


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sku_ids_for_product(session: Session, product_id: int) -> List[int]:
    """Return all sku_ids that belong to the given product_id."""
    rows = session.execute(
        select(Sku.sku_id).where(Sku.product_id == product_id)
    ).scalars().all()
    return list(rows)


def _promo_ids_for_skus(session: Session, sku_ids: List[int]) -> List[int]:
    
    if not sku_ids:
        return []

    # Direct SKU-level promotions
    direct = session.execute(
        select(PromotionSku.promotion_id)
        .where(PromotionSku.sku_id.in_(sku_ids))
        .distinct()
    ).scalars().all()

    # Bundle-level promotions: find bundles containing these SKUs, then their promos
    bundle_ids = session.execute(
        select(BundleSku.bundle_id)
        .where(BundleSku.sku_id.in_(sku_ids))
        .distinct()
    ).scalars().all()

    bundle_promos: List[int] = []
    if bundle_ids:
        bundle_promos = session.execute(
            select(PromotionBundle.promotion_id)
            .where(PromotionBundle.bundle_id.in_(list(bundle_ids)))
            .distinct()
        ).scalars().all()

    return list(set(list(direct) + list(bundle_promos)))


def _revenue_and_units(
    session: Session,
    sku_ids: List[int],
    start: date,
    end: date,
) -> tuple[float, int]:
    
    if not sku_ids:
        return 0.0, 0

    # ---- SKU line-item revenue ----
    sku_rev_row = session.execute(
        select(
            func.coalesce(func.sum(SkuSale.quantity * Sku.price), 0).label("rev"),
            func.coalesce(func.sum(SkuSale.quantity), 0).label("units"),
        )
        .join(Sale, SkuSale.sales_id == Sale.sales_id)
        .join(Sku, SkuSale.sku_id == Sku.sku_id)
        .where(
            SkuSale.sku_id.in_(sku_ids),
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
    ).one()

    sku_revenue = float(sku_rev_row.rev)
    sku_units = int(sku_rev_row.units)

    # ---- Bundle line-item revenue (apportioned) ----
    # Step 1: find bundles that contain at least one of our SKUs
    bundle_ids = session.execute(
        select(BundleSku.bundle_id)
        .where(BundleSku.sku_id.in_(sku_ids))
        .distinct()
    ).scalars().all()

    bundle_revenue = 0.0
    bundle_units = 0

    for bundle_id in bundle_ids:
        # All SKU prices in this bundle (to compute the apportionment ratio)
        all_member_skus = session.execute(
            select(Sku.sku_id, Sku.price)
            .join(BundleSku, BundleSku.sku_id == Sku.sku_id)
            .where(BundleSku.bundle_id == bundle_id)
        ).all()

        total_member_price = sum(float(r.price) for r in all_member_skus)
        our_member_price = sum(
            float(r.price) for r in all_member_skus if r.sku_id in sku_ids
        )

        if total_member_price == 0:
            continue

        ratio = our_member_price / total_member_price

        bundle_obj = session.get(Bundle, bundle_id)
        if bundle_obj is None:
            continue

        # Bundle sales in the window
        bundle_row = session.execute(
            select(
                func.coalesce(func.sum(BundleSale.quantity), 0).label("units"),
            )
            .join(Sale, BundleSale.sales_id == Sale.sales_id)
            .where(
                BundleSale.bundle_id == bundle_id,
                Sale.sale_date >= start,
                Sale.sale_date <= end,
            )
        ).one()

        qty = int(bundle_row.units)
        bundle_revenue += ratio * float(bundle_obj.bundle_price) * qty
        bundle_units += qty

    total_revenue = sku_revenue + bundle_revenue
    total_units = sku_units + bundle_units

    return total_revenue, total_units


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_uplift(session: Session, product_id: int) -> List[UpliftResult]:
    
    sku_ids = _sku_ids_for_product(session, product_id)
    if not sku_ids:
        return []

    promo_ids = _promo_ids_for_skus(session, sku_ids)
    if not promo_ids:
        return []

    promotions = session.execute(
        select(Promotion)
        .where(Promotion.promotion_id.in_(promo_ids))
        .order_by(Promotion.start_date)
    ).scalars().all()

    results: List[UpliftResult] = []

    for promo in promotions:
        promo_start: date = promo.start_date
        promo_end: date = promo.end_date

        promo_length_days = (promo_end - promo_start).days + 1  # inclusive

        # Symmetric baseline: same number of days immediately before promo
        baseline_end: date = promo_start - timedelta(days=1)
        baseline_start: date = baseline_end - timedelta(days=promo_length_days - 1)

        promo_revenue, promo_units = _revenue_and_units(
            session, sku_ids, promo_start, promo_end
        )
        baseline_revenue, baseline_units = _revenue_and_units(
            session, sku_ids, baseline_start, baseline_end
        )

        incremental_revenue = promo_revenue - baseline_revenue
        incremental_units = promo_units - baseline_units

        # Discount bleed: sold more units but made less money
        discount_bleed = (incremental_units > 0) and (incremental_revenue < 0)

        results.append(
            UpliftResult(
                product_id=product_id,
                promotion_id=promo.promotion_id,
                promotion_name=promo.promotion_name,
                promotion_type=promo.promotion_type,
                promo_start_date=promo_start,
                promo_end_date=promo_end,
                baseline_start_date=baseline_start,
                baseline_end_date=baseline_end,
                promo_revenue=round(promo_revenue, 2),
                baseline_revenue=round(baseline_revenue, 2),
                incremental_revenue=round(incremental_revenue, 2),
                promo_units=promo_units,
                baseline_units=baseline_units,
                incremental_units=incremental_units,
                discount_bleed=discount_bleed,
            )
        )

    return results

