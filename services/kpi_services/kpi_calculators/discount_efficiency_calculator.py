from datetime import timedelta

from sqlalchemy import func, select
from services.db_services.session import SessionLocal
from services.db_services.models import Sale, Promotion
from services.db_services.promotions_db import get_promotion_by_id

class DiscountEfficiency:

    def __init__(
        self,
        promotion_id: int,
        baseline_revenue: float,
        promotion_revenue: float,
        incremental_revenue: float,
        total_discount_given: float,
        discount_efficiency_ratio: float | None,
    ):
        self.promotion_id = promotion_id
        self.baseline_revenue = baseline_revenue
        self.promotion_revenue = promotion_revenue
        self.incremental_revenue = incremental_revenue
        self.total_discount_given = total_discount_given
        self.discount_efficiency_ratio = discount_efficiency_ratio

def discount_efficiency_calculator(promotion: Promotion) -> DiscountEfficiency:
    session = SessionLocal()
    try:
        sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]
        statement = select(
            func.sum(Sale.regular_price), func.sum(Sale.final_price)
        ).where(Sale.promotion_id == promotion.promotion_id)
        total_regular_price, promotion_revenue = session.execute(statement).tuples().first() or (None, None)
        total_regular_price = total_regular_price or 0.0
        promotion_revenue = promotion_revenue or 0.0
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
        ).scalar() or 0.0

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
    finally:
        session.close()

