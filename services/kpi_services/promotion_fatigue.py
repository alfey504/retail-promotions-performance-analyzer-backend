from datetime import timedelta

from sqlalchemy import func, select
from services.db_services.session import SessionLocal
from services.db_services.models import Sale
from services.db_services.promotions_db import get_promotion_by_id


class FatigueInstance:

    def __init__(self, promotion_id: int, unit_sales_uplift_ratio: float | None):
        self.promotion_id = promotion_id
        self.unit_sales_uplift_ratio = unit_sales_uplift_ratio


class PromotionFatigue:

    def __init__(
        self,
        promotion_ids: list[int],
        instances: list[FatigueInstance],
        lift_declining: bool,
    ):
        self.promotion_ids = promotion_ids
        self.instances = instances
        self.lift_declining = lift_declining


def get_promotion_fatigue(promotion_ids: list[int]) -> PromotionFatigue:
    """promotion_ids must already be in chronological order -- the repeated
    instances of the same promotion concept, earliest first."""
    session = SessionLocal()
    try:
        instances = []
        for promotion_id in promotion_ids:
            promotion = get_promotion_by_id(promotion_id)
            sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]

            promotion_units_sold = session.execute(
                select(func.count(Sale.sales_id)).where(Sale.promotion_id == promotion_id)
            ).scalar() or 0

            promotion_duration = promotion.end_date - promotion.start_date
            baseline_end_date = promotion.start_date - timedelta(days=1)
            baseline_start_date = baseline_end_date - promotion_duration

            baseline_units_sold = session.execute(
                select(func.sum(Sale.quantity)).where(
                    Sale.sale_date >= baseline_start_date,
                    Sale.sale_date <= baseline_end_date,
                    Sale.sku_id.in_(sku_ids),
                )
            ).scalar() or 0

            ratio = (promotion_units_sold / baseline_units_sold) if baseline_units_sold > 0 else None
            instances.append(FatigueInstance(promotion_id=promotion_id, unit_sales_uplift_ratio=ratio))

        ratios = [i.unit_sales_uplift_ratio for i in instances if i.unit_sales_uplift_ratio is not None]
        lift_declining = len(ratios) > 1 and all(
            ratios[i] > ratios[i + 1] for i in range(len(ratios) - 1)
        )

        return PromotionFatigue(
            promotion_ids=promotion_ids,
            instances=instances,
            lift_declining=lift_declining,
        )
    finally:
        session.close()