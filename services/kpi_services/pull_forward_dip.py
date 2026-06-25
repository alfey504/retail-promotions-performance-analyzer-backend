from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.db_services.models import (
    Bundle,
    BundleSale,
    BundleSku,
    Promotion,
    PromotionBundle,
    PromotionSku,
    Sale,
    Sku,
    SkuSale,
)
from services.db_services.session import SessionLocal


# ---------------------------------------------------------------------------
# Verdict enum
# ---------------------------------------------------------------------------

class DipVerdict(str, Enum):
    PULL_FORWARD = "PULL_FORWARD"   # post-promo dip — demand was just borrowed
    NEUTRAL      = "NEUTRAL"        # no meaningful timing shift
    HALO         = "HALO"           # promo grew the base; post period is stronger


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class DipResult:
    product_id: int
    promotion_id: int
    promotion_name: str
    promotion_type: str

    # Three equal-length windows
    baseline_start_date: date
    baseline_end_date: date
    promo_start_date: date
    promo_end_date: date
    post_start_date: date
    post_end_date: date
    window_days: int                    # length of each window (N)

    # Revenue per window
    baseline_revenue: float
    promo_revenue: float
    post_revenue: float

    # Units per window
    baseline_units: int
    promo_units: int
    post_units: int

    # Promo lift (vs baseline)
    promo_revenue_delta: float          # promo_revenue - baseline_revenue
    promo_units_delta: int              # promo_units  - baseline_units

    # Post-promo dip (vs baseline)
    post_revenue_delta: float           # post_revenue - baseline_revenue
    post_units_delta: int               # post_units   - baseline_units

    # Severity: (baseline - post) / baseline; >0 means dip
    dip_ratio: float

    # Net demand view
    demand_created: float               # promo lift over baseline
    demand_cannibalized: float          # baseline lost in post window
    net_incremental_revenue: float      # demand_created - demand_cannibalized

    # Verdict
    verdict: DipVerdict
    verdict_note: str                   # human-readable one-liner


# ---------------------------------------------------------------------------
# Neutral band threshold — tweak to taste
# ---------------------------------------------------------------------------

# If |dip_ratio| < NEUTRAL_THRESHOLD, verdict is NEUTRAL
NEUTRAL_THRESHOLD = 0.05   # 5 % swing treated as noise


# ---------------------------------------------------------------------------
# Internal helpers (mirrors uplift_calculator.py pattern)
# ---------------------------------------------------------------------------

def _sku_ids_for_product(session: Session, product_id: int) -> List[int]:
    return list(
        session.execute(
            select(Sku.sku_id).where(Sku.product_id == product_id)
        ).scalars().all()
    )


def _promo_ids_for_skus(session: Session, sku_ids: List[int]) -> List[int]:
    if not sku_ids:
        return []

    direct = session.execute(
        select(PromotionSku.promotion_id)
        .where(PromotionSku.sku_id.in_(sku_ids))
        .distinct()
    ).scalars().all()

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

    # Direct SKU sales
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

    # Bundle sales — apportioned
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


def _make_verdict(dip_ratio: float, net_incremental: float) -> tuple[DipVerdict, str]:

    if dip_ratio > NEUTRAL_THRESHOLD:
        pct = round(dip_ratio * 100, 1)
        verdict = DipVerdict.PULL_FORWARD
        note = (
            f"Post-promo revenue fell {pct}% below baseline — "
            f"promo likely shifted purchase timing rather than creating new demand. "
            f"Net incremental revenue: {net_incremental:+.2f}."
        )
    elif dip_ratio < -NEUTRAL_THRESHOLD:
        pct = round(abs(dip_ratio) * 100, 1)
        verdict = DipVerdict.HALO
        note = (
            f"Post-promo revenue ran {pct}% above baseline — "
            f"promo appears to have built durable new demand (halo effect). "
            f"Net incremental revenue: {net_incremental:+.2f}."
        )
    else:
        verdict = DipVerdict.NEUTRAL
        note = (
            f"Post-promo revenue within ±{int(NEUTRAL_THRESHOLD*100)}% of baseline — "
            f"no significant pull-forward or halo detected. "
            f"Net incremental revenue: {net_incremental:+.2f}."
        )
    return verdict, note


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_pullforward_dip(
    session: Session,
    product_id: int,
    neutral_threshold: Optional[float] = None,
) -> List[DipResult]:

    threshold = neutral_threshold if neutral_threshold is not None else NEUTRAL_THRESHOLD

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

    results: List[DipResult] = []

    for promo in promotions:
        promo_start: date = promo.start_date
        promo_end:   date = promo.end_date

        N = (promo_end - promo_start).days + 1      # promo length (inclusive)

        # Post window: day after promo ends, for N days
        post_start = promo_end + timedelta(days=1)
        post_end   = post_start + timedelta(days=N - 1)

        # Baseline window: N days immediately before promo (no overlap)
        baseline_end   = promo_start - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=N - 1)

        baseline_revenue, baseline_units = _revenue_and_units(
            session, sku_ids, baseline_start, baseline_end
        )
        promo_revenue, promo_units = _revenue_and_units(
            session, sku_ids, promo_start, promo_end
        )
        post_revenue, post_units = _revenue_and_units(
            session, sku_ids, post_start, post_end
        )

        promo_revenue_delta = round(promo_revenue - baseline_revenue, 2)
        promo_units_delta   = promo_units - baseline_units

        post_revenue_delta  = round(post_revenue - baseline_revenue, 2)
        post_units_delta    = post_units - baseline_units

        # dip_ratio: positive = dip below baseline, negative = above baseline
        if baseline_revenue > 0:
            dip_ratio = round((baseline_revenue - post_revenue) / baseline_revenue, 4)
        else:
            # No baseline sales → can't compute a meaningful ratio
            dip_ratio = 0.0

        demand_created      = round(max(promo_revenue - baseline_revenue, 0), 2)
        demand_cannibalized = round(max(baseline_revenue - post_revenue, 0), 2)
        net_incremental     = round(demand_created - demand_cannibalized, 2)

        verdict, verdict_note = _make_verdict(dip_ratio, net_incremental)

        # Override threshold if caller passed a custom one
        if neutral_threshold is not None:
            if dip_ratio > threshold:
                verdict = DipVerdict.PULL_FORWARD
            elif dip_ratio < -threshold:
                verdict = DipVerdict.HALO
            else:
                verdict = DipVerdict.NEUTRAL
            _, verdict_note = _make_verdict(dip_ratio, net_incremental)

        results.append(
            DipResult(
                product_id=product_id,
                promotion_id=promo.promotion_id,
                promotion_name=promo.promotion_name,
                promotion_type=promo.promotion_type,
                baseline_start_date=baseline_start,
                baseline_end_date=baseline_end,
                promo_start_date=promo_start,
                promo_end_date=promo_end,
                post_start_date=post_start,
                post_end_date=post_end,
                window_days=N,
                baseline_revenue=baseline_revenue,
                promo_revenue=promo_revenue,
                post_revenue=post_revenue,
                baseline_units=baseline_units,
                promo_units=promo_units,
                post_units=post_units,
                promo_revenue_delta=promo_revenue_delta,
                promo_units_delta=promo_units_delta,
                post_revenue_delta=post_revenue_delta,
                post_units_delta=post_units_delta,
                dip_ratio=dip_ratio,
                demand_created=demand_created,
                demand_cannibalized=demand_cannibalized,
                net_incremental_revenue=net_incremental,
                verdict=verdict,
                verdict_note=verdict_note,
            )
        )

    return results
def pull_forward_dip_for_product(product_id: int) -> List[DipResult]:
    session = SessionLocal()
    try:
        return detect_pullforward_dip(session, product_id)
    except Exception as e:
        print(f"Error detecting pull-forward dip for product {product_id}: {e}")
        raise
    finally:
        session.close()
