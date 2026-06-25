
from datetime import timedelta
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

# =========================
# Layer 1 — Fetchers
# =========================

def _fetch_promotion(session, promotion_id):
    promo = session.get(Promotion, promotion_id)

    if promo is None:
        raise ValueError(f"Promotion {promotion_id} not found")

    return promo


def _fetch_target_skus(session, promotion_id):
    rows = (
        session.query(PromotionSku)
        .filter(PromotionSku.promotion_id == promotion_id)
        .all()
    )

    return {r.sku_id for r in rows}


def _fetch_target_bundles(session, promotion_id):
    rows = (
        session.query(PromotionBundle)
        .filter(PromotionBundle.promotion_id == promotion_id)
        .all()
    )

    return {r.bundle_id for r in rows}


def _fetch_promotion_sales(session, promotion_id, start_date, end_date):
    return (
        session.query(Sale)
        .join(
            SalePromotion,
            SalePromotion.sales_id == Sale.sales_id
        )
        .filter(
            SalePromotion.promotion_id == promotion_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        )
        .all()
    )


# =========================
# Layer 2 — Revenue
# =========================

def _calculate_actual_revenue(
    session,
    sale_ids,
    target_skus,
    target_bundles,
):
    revenue = 0.0

    if target_skus:

        sku_rows = (
            session.query(SkuSale)
            .filter(
                SkuSale.sales_id.in_(sale_ids),
                SkuSale.sku_id.in_(target_skus)
            )
            .all()
        )

        for row in sku_rows:
            sku = session.get(Sku, row.sku_id)
            revenue += float(sku.price) * row.quantity

    if target_bundles:

        bundle_rows = (
            session.query(BundleSale)
            .filter(
                BundleSale.sales_id.in_(sale_ids),
                BundleSale.bundle_id.in_(target_bundles)
            )
            .all()
        )

        for row in bundle_rows:
            bundle = session.get(Bundle, row.bundle_id)
            revenue += float(bundle.bundle_price) * row.quantity

    return round(revenue, 2)


def _calculate_expected_revenue(
    session,
    promo,
    target_skus,
    target_bundles,
):
    lookback_start = promo.start_date - timedelta(days=30)

    promo_days = (
        promo.end_date - promo.start_date
    ).days + 1

    revenue = 0.0

    sales = (
        session.query(Sale)
        .filter(
            Sale.sale_date >= lookback_start,
            Sale.sale_date < promo.start_date
        )
        .all()
    )

    sale_ids = {s.sales_id for s in sales}

    if target_skus:

        sku_rows = (
            session.query(SkuSale)
            .filter(
                SkuSale.sales_id.in_(sale_ids),
                SkuSale.sku_id.in_(target_skus)
            )
            .all()
        )

        for row in sku_rows:
            sku = session.get(Sku, row.sku_id)
            revenue += float(sku.price) * row.quantity

    if target_bundles:

        bundle_rows = (
            session.query(BundleSale)
            .filter(
                BundleSale.sales_id.in_(sale_ids),
                BundleSale.bundle_id.in_(target_bundles)
            )
            .all()
        )

        for row in bundle_rows:
            bundle = session.get(Bundle, row.bundle_id)
            revenue += float(bundle.bundle_price) * row.quantity

    avg_daily = revenue / 30

    expected = avg_daily * promo_days

    return round(expected, 2)


def _calculate_discount_cost(
    session,
    sale_ids,
    target_skus,
    target_bundles,
    discount_percent,
):
    cost = 0.0

    if target_skus:

        sku_rows = (
            session.query(SkuSale)
            .filter(
                SkuSale.sales_id.in_(sale_ids),
                SkuSale.sku_id.in_(target_skus)
            )
            .all()
        )

        for row in sku_rows:
            sku = session.get(Sku, row.sku_id)

            unit_discount = (
                float(sku.price)
                * discount_percent
                / 100
            )

            cost += unit_discount * row.quantity

    if target_bundles:

        bundle_rows = (
            session.query(BundleSale)
            .filter(
                BundleSale.sales_id.in_(sale_ids),
                BundleSale.bundle_id.in_(target_bundles)
            )
            .all()
        )

        for row in bundle_rows:

            bundle = session.get(Bundle, row.bundle_id)

            component_value = sum(
                float(link.sku.price)
                for link in bundle.sku_links
            )

            unit_discount = (
                component_value
                - float(bundle.bundle_price)
            )

            cost += unit_discount * row.quantity

    return round(cost, 2)


# =========================
# Layer 3 — KPI Logic
# =========================

def _calculate_incremental_revenue(
    actual_revenue,
    expected_revenue
):
    return round(
        actual_revenue - expected_revenue,
        2
    )


def _calculate_discount_efficiency_ratio(
    incremental_revenue,
    discount_cost
):
    if discount_cost <= 0:
        return None

    return round(
        incremental_revenue / discount_cost,
        2
    )


def _build_verdict(ratio):
    if ratio is None:
        return "No discount cost detected"

    if ratio < 1:
        return "Money-losing promotion"

    if ratio < 1.5:
        return "Marginally profitable"

    if ratio < 3:
        return "Efficient promotion"

    return "Highly efficient promotion"


# =========================
# Public KPI Function
# =========================

def discount_efficiency_ratio(
    session,
    promotion_id,
):
    promo = _fetch_promotion(
        session,
        promotion_id
    )

    target_skus = _fetch_target_skus(
        session,
        promotion_id
    )

    target_bundles = _fetch_target_bundles(
        session,
        promotion_id
    )

    promo_sales = _fetch_promotion_sales(
        session,
        promotion_id,
        promo.start_date,
        promo.end_date,
    )

    sale_ids = {
        s.sales_id
        for s in promo_sales
    }

    actual_revenue = _calculate_actual_revenue(
        session,
        sale_ids,
        target_skus,
        target_bundles,
    )

    expected_revenue = _calculate_expected_revenue(
        session,
        promo,
        target_skus,
        target_bundles,
    )

    incremental_revenue = (
        _calculate_incremental_revenue(
            actual_revenue,
            expected_revenue,
        )
    )

    discount_cost = (
        _calculate_discount_cost(
            session,
            sale_ids,
            target_skus,
            target_bundles,
            promo.discount_percent or 0,
        )
    )

    ratio = (
        _calculate_discount_efficiency_ratio(
            incremental_revenue,
            discount_cost,
        )
    )

    return {
        "promotion_id": promo.promotion_id,
        "promotion_name": promo.promotion_name,
        "promotion_type": promo.promotion_type,
        "discount_percent": promo.discount_percent,
        "actual_revenue": actual_revenue,
        "expected_revenue": expected_revenue,
        "incremental_revenue": incremental_revenue,
        "discount_cost": discount_cost,
        "discount_efficiency_ratio": ratio,
        "verdict": _build_verdict(ratio),
    }
def get_discount_efficiency_ratio(promotion_id: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        result = discount_efficiency_ratio(session, promotion_id)
        return result
    except Exception as e:
        print(f"Error at services/kpi-services/discount_efficiency_ratio function -> get_discount_efficieny_ratio : {e}")
        raise e
    finally:
        session.close()
    


