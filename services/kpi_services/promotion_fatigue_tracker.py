# Promotion Fatigue Tracker KPI
# Generated KPI file

from datetime import timedelta
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
def _fetch_promotion(session: Session, promotion_id: int):
    promo = session.get(Promotion, promotion_id)
    if promo is None:
        raise ValueError(f"Promotion {promotion_id} not found")
    return promo

def _fetch_promotion_family(session: Session, promotion_type: str):
    return (
        session.query(Promotion)
        .filter(Promotion.promotion_type == promotion_type)
        .order_by(Promotion.start_date)
        .all()
    )

def _fetch_target_skus(session, promotion_id):
    rows = session.query(PromotionSku).filter(
        PromotionSku.promotion_id == promotion_id
    ).all()
    return {r.sku_id for r in rows}

def _fetch_target_bundles(session, promotion_id):
    rows = session.query(PromotionBundle).filter(
        PromotionBundle.promotion_id == promotion_id
    ).all()
    return {r.bundle_id for r in rows}

def _promotion_revenue(session, promo, sku_ids, bundle_ids):
    sales = (
        session.query(Sale)
        .join(SalePromotion, SalePromotion.sales_id == Sale.sales_id)
        .filter(SalePromotion.promotion_id == promo.promotion_id)
        .all()
    )

    sale_ids = {s.sales_id for s in sales}
    revenue = 0.0

    if sku_ids:
        rows = session.query(SkuSale).filter(
            SkuSale.sales_id.in_(sale_ids),
            SkuSale.sku_id.in_(sku_ids)
        ).all()

        for row in rows:
            sku = session.get(Sku, row.sku_id)
            revenue += float(sku.price) * row.quantity

    if bundle_ids:
        rows = session.query(BundleSale).filter(
            BundleSale.sales_id.in_(sale_ids),
            BundleSale.bundle_id.in_(bundle_ids)
        ).all()

        for row in rows:
            bundle = session.get(Bundle, row.bundle_id)
            revenue += float(bundle.bundle_price) * row.quantity

    return round(revenue, 2)

def _baseline_revenue(session, promo, sku_ids, bundle_ids):
    start = promo.start_date - timedelta(days=30)
    revenue = 0.0

    sales = session.query(Sale).filter(
        Sale.sale_date >= start,
        Sale.sale_date < promo.start_date
    ).all()

    sale_ids = {s.sales_id for s in sales}

    if sku_ids:
        rows = session.query(SkuSale).filter(
            SkuSale.sales_id.in_(sale_ids),
            SkuSale.sku_id.in_(sku_ids)
        ).all()

        for row in rows:
            sku = session.get(Sku, row.sku_id)
            revenue += float(sku.price) * row.quantity

    if bundle_ids:
        rows = session.query(BundleSale).filter(
            BundleSale.sales_id.in_(sale_ids),
            BundleSale.bundle_id.in_(bundle_ids)
        ).all()

        for row in rows:
            bundle = session.get(Bundle, row.bundle_id)
            revenue += float(bundle.bundle_price) * row.quantity

    return round(revenue, 2)

def _uplift_ratio(promo_revenue, baseline_revenue):
    if baseline_revenue <= 0:
        return None
    return round(promo_revenue / baseline_revenue, 2)

def _detect_fatigue(uplift_history):
    if len(uplift_history) < 2:
        return False

    decreases = 0
    for i in range(1, len(uplift_history)):
        if uplift_history[i] < uplift_history[i - 1]:
            decreases += 1

    return decreases == (len(uplift_history) - 1)

def _fatigue_severity(uplift_history):
    if len(uplift_history) < 2:
        return "insufficient-history"

    first = uplift_history[0]
    last = uplift_history[-1]

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

def promotion_fatigue_tracker(session: Session, promotion_id: int):
    current_promo = _fetch_promotion(session, promotion_id)

    family = _fetch_promotion_family(
        session,
        current_promo.promotion_type
    )

    instances = []
    uplift_history = []

    for promo in family:
        sku_ids = _fetch_target_skus(session, promo.promotion_id)
        bundle_ids = _fetch_target_bundles(session, promo.promotion_id)

        promo_rev = _promotion_revenue(
            session,
            promo,
            sku_ids,
            bundle_ids,
        )

        baseline_rev = _baseline_revenue(
            session,
            promo,
            sku_ids,
            bundle_ids,
        )

        uplift = _uplift_ratio(
            promo_rev,
            baseline_rev
        )

        if uplift is not None:
            uplift_history.append(uplift)

        instances.append(
            _build_instance_result(
                promo,
                uplift,
            )
        )

    fatigue_detected = _detect_fatigue(uplift_history)
    severity = _fatigue_severity(uplift_history)

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







    


