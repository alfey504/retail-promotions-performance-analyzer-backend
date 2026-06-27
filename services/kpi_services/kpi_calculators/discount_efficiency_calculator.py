from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.db_services.session import SessionLocal
from services.db_services.models import Sale, Promotion
from services.db_services.promotions_db import get_promotion_by_id
from services.kpi_services.kpi_calculators.models import DiscountEfficiency


def discount_efficiency_calculator(session: Session, promotion: Promotion) -> DiscountEfficiency:

    sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]
    statement = select(
        func.sum(Sale.regular_price), func.sum(Sale.final_price)
    ).where(Sale.promotion_id == promotion.promotion_id)
    total_regular_price, promotion_revenue = session.execute(statement).tuples().first() or (0.0, 0.0)
    total_regular_price = float(total_regular_price or 0.0)
    promotion_revenue = float(promotion_revenue or 0.0)
    total_discount_given = total_regular_price - promotion_revenue

    promotion_duration = promotion.end_date - promotion.start_date
    baseline_end_date = promotion.start_date - timedelta(days=1)
    baseline_start_date = baseline_end_date - promotion_duration

    baseline_revenue = session.execute(
        select(func.sum(Sale.final_price)).where(
            Sale.sale_date >= baseline_start_date,
            Sale.sale_date <= baseline_end_date,
            Sale.sku_id.in_(sku_ids),
        )
    ).scalar() 

    baseline_revenue = float(baseline_revenue or 0)

    incremental_revenue = promotion_revenue - baseline_revenue

    if total_discount_given > 0:
        discount_efficiency_ratio = incremental_revenue / total_discount_given
    else:
        discount_efficiency_ratio = None

    return DiscountEfficiency(
        promotion_id=promotion.promotion_id,
        baseline_revenue=baseline_revenue,
        promotion_revenue=promotion_revenue,
        incremental_revenue=incremental_revenue,
        total_discount_given=total_discount_given,
        discount_efficiency_ratio=discount_efficiency_ratio,
    )

def get_discount_efficiency(promotion_id: int) -> DiscountEfficiency:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        return discount_efficiency_calculator(session, promotion)
    except Exception as e:
        raise e
    finally:
        session.close()


