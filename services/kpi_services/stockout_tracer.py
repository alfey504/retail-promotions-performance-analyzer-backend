from datetime import timedelta

from sqlalchemy import func, select
from services.db_services.models import FullfillmentHistory, Sale
from services.db_services.session import SessionLocal
from services.db_services.promotions_db import get_promotion_by_id

class SkuInventoryTrace:

    def __init__(
        self,
        sku_id: int,
        opening_stock: int,
        units_sold: int,
        closing_stock: int,
        stockout: bool,
        stockout_date,
        next_restock_date,
        missed_units_estimate: float,
    ):
        self.sku_id = sku_id
        self.opening_stock = opening_stock
        self.units_sold = units_sold
        self.closing_stock = closing_stock
        self.stockout = stockout
        self.stockout_date = stockout_date
        self.next_restock_date = next_restock_date
        self.missed_units_estimate = missed_units_estimate


class StockoutTrace:

    def __init__(
        self,
        promotion_id: int,
        any_stockout: bool,
        total_missed_units_estimate: float,
        sku_traces: list[SkuInventoryTrace],
    ):
        self.promotion_id = promotion_id
        self.any_stockout = any_stockout
        self.total_missed_units_estimate = total_missed_units_estimate
        self.sku_traces = sku_traces
    


def get_stockout_inventory_trace(promotion_id: int) -> StockoutTrace:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]

        sku_traces = []
        for sku_id in sku_ids:
            received_before = session.execute(
                select(func.sum(FullfillmentHistory.quantity_received)).where(
                    FullfillmentHistory.sku_id == sku_id,
                    FullfillmentHistory.fullfillment_date < promotion.start_date,
                )
            ).scalar() or 0

            sold_before = session.execute(
                select(func.count(Sale.sales_id)).where(
                    Sale.sku_id == sku_id,
                    Sale.sale_date < promotion.start_date,
                )
            ).scalar() or 0

            opening_stock = received_before - sold_before

            sale_dates = session.execute(
                select(Sale.sale_date).where(
                    Sale.sku_id == sku_id,
                    Sale.sale_date >= promotion.start_date,
                    Sale.sale_date <= promotion.end_date,
                ).order_by(Sale.sale_date)
            ).scalars().all()

            running_stock = opening_stock
            stockout_date = None
            for sale_date in sale_dates:
                running_stock -= 1
                if running_stock < 0 and stockout_date is None:
                    stockout_date = sale_date
            closing_stock = running_stock

            missed_units_estimate = 0.0
            if stockout_date is not None:
                pre_stockout_units = sum(1 for d in sale_dates if d < stockout_date)
                pre_stockout_days = max((stockout_date - promotion.start_date).days, 1)
                pre_stockout_rate = pre_stockout_units / pre_stockout_days

                post_stockout_units = sum(1 for d in sale_dates if d >= stockout_date)
                remaining_days = (promotion.end_date - stockout_date).days + 1
                projected_units = pre_stockout_rate * remaining_days
                missed_units_estimate = round(max(0.0, projected_units - post_stockout_units), 1)

            next_restock_date = session.execute(
                select(func.min(FullfillmentHistory.fullfillment_date)).where(
                    FullfillmentHistory.sku_id == sku_id,
                    FullfillmentHistory.fullfillment_date > promotion.end_date,
                )
            ).scalar()

            sku_traces.append(SkuInventoryTrace(
                sku_id=sku_id,
                opening_stock=opening_stock,
                units_sold=len(sale_dates),
                closing_stock=closing_stock,
                stockout=stockout_date is not None,
                stockout_date=stockout_date,
                next_restock_date=next_restock_date,
                missed_units_estimate=missed_units_estimate,
            ))

        return StockoutTrace(
            promotion_id=promotion_id,
            any_stockout=any(t.stockout for t in sku_traces),
            total_missed_units_estimate=round(sum(t.missed_units_estimate for t in sku_traces), 1),
            sku_traces=sku_traces,
        )
    except Exception as e:
        raise e
    finally:
        session.close()