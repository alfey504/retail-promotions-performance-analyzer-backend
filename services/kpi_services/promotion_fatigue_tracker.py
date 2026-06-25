
from datetime import timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from services.db_services.models import (
    Promotion,
    PromotionSku,
    PromotionBundle,
    Sale,
    SalePromotion,
    SkuSale,
    BundleSale,
    Sku,
    Bundle,
)
from services.db_services.session import SessionLocal
from typing import Any

# ---------- Fetchers ----------

def _fetch_promotion(session: Session, promotion_id: int):
    promo = session.get(Promotion, promotion_id)
    if not promo:
        raise ValueError(f"Promotion {promotion_id} not found")
    return promo

def _fetch_promotion_family(session, promotion_type):
    return (
        session.query(Promotion)
        .filter(Promotion.promotion_type == promotion_type)
        .order_by(Promotion.start_date)
        .all()
    )

def _fetch_target_skus(session, promotion_id):
    return {
        r.sku_id
        for r in session.query(PromotionSku)
        .filter(PromotionSku.promotion_id == promotion_id)
        .all()
    }

def _fetch_target_bundles(session, promotion_id):
    return {
        r.bundle_id
        for r in session.query(PromotionBundle)
        .filter(PromotionBundle.promotion_id == promotion_id)
        .all()
    }

# ---------- Revenue ----------

def _promotion_sku_revenue(session, promo, sku_ids):
    if not sku_ids:
        return 0.0

    value = (
        session.query(
            func.coalesce(
                func.sum(SkuSale.quantity * Sku.price),
                0
            )
        )
        .join(Sku, Sku.sku_id == SkuSale.sku_id)
        .join(Sale, Sale.sales_id == SkuSale.sales_id)
        .join(
            SalePromotion,
            SalePromotion.sales_id == Sale.sales_id
        )
        .filter(
            SalePromotion.promotion_id == promo.promotion_id,
            SkuSale.sku_id.in_(sku_ids)
        )
        .scalar()
    )

    return float(value or 0)

def _promotion_bundle_revenue(session, promo, bundle_ids):
    if not bundle_ids:
        return 0.0

    value = (
        session.query(
            func.coalesce(
                func.sum(
                    BundleSale.quantity * Bundle.bundle_price
                ),
                0
            )
        )
        .join(
            Bundle,
            Bundle.bundle_id == BundleSale.bundle_id
        )
        .join(Sale, Sale.sales_id == BundleSale.sales_id)
        .join(
            SalePromotion,
            SalePromotion.sales_id == Sale.sales_id
        )
        .filter(
            SalePromotion.promotion_id == promo.promotion_id,
            BundleSale.bundle_id.in_(bundle_ids)
        )
        .scalar()
    )

    return float(value or 0)

def _baseline_sku_revenue(session, promo, sku_ids):
    if not sku_ids:
        return 0.0

    start = promo.start_date - timedelta(days=30)

    value = (
        session.query(
            func.coalesce(
                func.sum(SkuSale.quantity * Sku.price),
                0
            )
        )
        .join(Sku, Sku.sku_id == SkuSale.sku_id)
        .join(Sale, Sale.sales_id == SkuSale.sales_id)
        .filter(
            Sale.sale_date >= start,
            Sale.sale_date < promo.start_date,
            SkuSale.sku_id.in_(sku_ids)
        )
        .scalar()
    )

    return float(value or 0)

def _baseline_bundle_revenue(session, promo, bundle_ids):
    if not bundle_ids:
        return 0.0

    start = promo.start_date - timedelta(days=30)

    value = (
        session.query(
            func.coalesce(
                func.sum(
                    BundleSale.quantity * Bundle.bundle_price
                ),
                0
            )
        )
        .join(
            Bundle,
            Bundle.bundle_id == BundleSale.bundle_id
        )
        .join(Sale, Sale.sales_id == BundleSale.sales_id)
        .filter(
            Sale.sale_date >= start,
            Sale.sale_date < promo.start_date,
            BundleSale.bundle_id.in_(bundle_ids)
        )
        .scalar()
    )

    return float(value or 0)

# ---------- KPI Logic ----------

def _uplift_ratio(promo_revenue, baseline_revenue):
    if baseline_revenue <= 0:
        return None
    return round(promo_revenue / baseline_revenue, 2)

def _detect_fatigue(history):
    if len(history) < 2:
        return False

    return all(
        history[i] < history[i - 1]
        for i in range(1, len(history))
    )

def _fatigue_severity(history):
    if len(history) < 2:
        return "insufficient-history"

    first = history[0]
    last = history[-1]

    decline_pct = ((first - last) / first) * 100

    if decline_pct >= 50:
        return "severe"
    if decline_pct >= 25:
        return "moderate"
    return "mild"

def _build_instance_result(promo, uplift):
    return {
        "promotion_id": promo.promotion_id,
        "promotion_name": promo.promotion_name,
        "start_date": str(promo.start_date),
        "end_date": str(promo.end_date),
        "uplift_ratio": uplift,
    }

# ---------- Public Function ----------

def promotion_fatigue_tracker(
    session: Session,
    promotion_id: int,
):
    current_promo = _fetch_promotion(
        session,
        promotion_id
    )

    family = _fetch_promotion_family(
        session,
        current_promo.promotion_type
    )

    instances = []
    uplift_history = []

    for promo in family:

        sku_ids = _fetch_target_skus(
            session,
            promo.promotion_id
        )

        bundle_ids = _fetch_target_bundles(
            session,
            promo.promotion_id
        )

        promo_revenue = (
            _promotion_sku_revenue(
                session,
                promo,
                sku_ids
            )
            +
            _promotion_bundle_revenue(
                session,
                promo,
                bundle_ids
            )
        )

        baseline_revenue = (
            _baseline_sku_revenue(
                session,
                promo,
                sku_ids
            )
            +
            _baseline_bundle_revenue(
                session,
                promo,
                bundle_ids
            )
        )

        uplift = _uplift_ratio(
            promo_revenue,
            baseline_revenue
        )

        if uplift is not None:
            uplift_history.append(uplift)

        instances.append(
            _build_instance_result(
                promo,
                uplift
            )
        )

    fatigue_detected = _detect_fatigue(
        uplift_history
    )

    severity = _fatigue_severity(
        uplift_history
    )

    return {
        "promotion_id": current_promo.promotion_id,
        "promotion_name": current_promo.promotion_name,
        "promotion_type": current_promo.promotion_type,
        "promotion_instances": instances,
        "fatigue_analysis": {
            "fatigue_detected": fatigue_detected,
            "severity": severity,
            "uplift_history": uplift_history,
        },
        "agent_verdict": (
            f"Promotion fatigue detected. Uplift trend: {uplift_history}"
            if fatigue_detected
            else f"No fatigue detected. Uplift trend: {uplift_history}"
        )
    }


def get_promotion_fatigue_tracker(promotion_id:int) -> dict[str,Any]:
    session = SessionLocal()
    try:
        result = promotion_fatigue_tracker(session,promotion_id)
        return result
    except Exception as e:
         print(f"Error at services/kpi-services/promotion_fatigue_tracker function -> promotion_fatigue_tracker : {e}")
         raise e
    finally:
        session.close()







    


