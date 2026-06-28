from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.db_services.models import Sale, Promotion
from services.db_services.promotions_db import get_promotion_by_id
from services.db_services.session import SessionLocal
from services.kpi_services.kpi_calculators.models import PostPromoDip

def post_promo_dip_calculator(session: Session, promotion: Promotion) -> PostPromoDip:

    sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]

    promotion_duration = promotion.end_date - promotion.start_date
    baseline_end_date = promotion.start_date - timedelta(days=1)
    baseline_start_date = baseline_end_date - promotion_duration

    post_start_date = promotion.end_date + timedelta(days=1)
    post_end_date = post_start_date + promotion_duration

    baseline_units_sold = session.execute(
        select(func.sum(Sale.quantity)).where(
            Sale.sale_date >= baseline_start_date,
            Sale.sale_date <= baseline_end_date,
            Sale.sku_id.in_(sku_ids),
        )
    ).scalar() or 0

    post_period_units_sold = session.execute(
        select(func.sum(Sale.quantity)).where(
            Sale.sale_date >= post_start_date,
            Sale.sale_date <= post_end_date,
            Sale.sku_id.in_(sku_ids),
        )
    ).scalar() or 0

    if baseline_units_sold > 0:
        post_period_ratio = post_period_units_sold / baseline_units_sold
    else:
        post_period_ratio = None

    pull_forward_dip = post_period_ratio is not None and post_period_ratio < 0.75

    return PostPromoDip(
        promotion_id=promotion.promotion_id,
        baseline_units_sold=baseline_units_sold,
        post_period_units_sold=post_period_units_sold,
        post_period_ratio=post_period_ratio,
        pull_forward_dip=pull_forward_dip,
    )

def get_post_promo_dip(promotion_id: int) -> PostPromoDip:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        post_promo_dip = post_promo_dip_calculator(session, promotion)
        return post_promo_dip
    except Exception as e:
        raise e
    finally:
        session.close()