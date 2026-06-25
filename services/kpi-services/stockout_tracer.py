from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.db_services.models import (
    Bundle,
    BundleSale,
    BundleSku,
    FulfillmentHistory,
    Product,
    Promotion,
    PromotionBundle,
    PromotionSku,
    Sale,
    Sku,
    SkuSale,
)

from services.db_services.session import SessionLocal

# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class DailyStockSnapshot:
    date: date
    units_received: int
    units_sold: int
    closing_stock: int          
    stockout_on_this_day: bool  


@dataclass
class StockoutResult:
    product_id: int
    sku_id: int
    sku_name: str
    promotion_id: int
    promotion_name: str
    promotion_type: str

    promo_start_date: date
    promo_end_date: date

    opening_stock: int              
    units_received_during: int      
    units_sold_during: int          
    closing_stock: int              

    stockout_detected: bool
    stockout_date: Optional[date]   
    days_out_of_stock: int          
    suppressed_demand: int          
    sku_price: float
    potential_revenue_lost: float  

    daily_trace: List[DailyStockSnapshot] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
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


def _daily_sku_sales(
    session: Session, sku_id: int, start: date, end: date
) -> Dict[date, int]:
    """
    Direct SKU sales grouped by day in [start, end].
    Returns {sale_date: total_quantity}.
    """
    rows = session.execute(
        select(Sale.sale_date, func.sum(SkuSale.quantity).label("qty"))
        .join(SkuSale, SkuSale.sales_id == Sale.sales_id)
        .where(
            SkuSale.sku_id == sku_id,
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
        .group_by(Sale.sale_date)
    ).all()
    return {r.sale_date: int(r.qty) for r in rows}


def _daily_bundle_sales_for_sku(
    session: Session, sku_id: int, start: date, end: date
) -> Dict[date, int]:
    """
    Bundle sales that contain this SKU, grouped by day.
    Each bundle unit sold = 1 unit of this SKU consumed (conservative: 1:1 per bundle).
    Returns {sale_date: total_bundle_units_containing_this_sku}.
    """
    bundle_ids = session.execute(
        select(BundleSku.bundle_id).where(BundleSku.sku_id == sku_id)
    ).scalars().all()

    if not bundle_ids:
        return {}

    rows = session.execute(
        select(Sale.sale_date, func.sum(BundleSale.quantity).label("qty"))
        .join(BundleSale, BundleSale.sales_id == Sale.sales_id)
        .where(
            BundleSale.bundle_id.in_(list(bundle_ids)),
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
        .group_by(Sale.sale_date)
    ).all()
    return {r.sale_date: int(r.qty) for r in rows}


def _daily_fulfillments(
    session: Session, sku_id: int, start: date, end: date
) -> Dict[date, int]:
    """Fulfillment receipts grouped by day in [start, end]."""
    rows = session.execute(
        select(
            FulfillmentHistory.fulfillment_date,
            func.sum(FulfillmentHistory.quantity_received).label("qty"),
        )
        .where(
            FulfillmentHistory.sku_id == sku_id,
            FulfillmentHistory.fulfillment_date >= start,
            FulfillmentHistory.fulfillment_date <= end,
        )
        .group_by(FulfillmentHistory.fulfillment_date)
    ).all()
    return {r.fulfillment_date: int(r.qty) for r in rows}


def _reconstruct_opening_stock(
    session: Session, sku: Sku, promo_end: date
) -> int:
    """
    Reconstruct stock at promo START by working backwards from the current
    in_stock snapshot:

        opening_stock = in_stock
                      + units sold STRICTLY AFTER promo_end
                      - units received STRICTLY AFTER promo_end

    This is accurate as long as in_stock reflects the present day and all
    post-promo movements are recorded in sales + fulfillment_history.
    """
    today = date.today()

    # Units sold after promo ended (drew down current stock)
    post_sold_row = session.execute(
        select(func.coalesce(func.sum(SkuSale.quantity), 0).label("qty"))
        .join(Sale, SkuSale.sales_id == Sale.sales_id)
        .where(
            SkuSale.sku_id == sku.sku_id,
            Sale.sale_date > promo_end,
        )
    ).one()
    post_sold = int(post_sold_row.qty)

    # Units received after promo ended (topped up current stock)
    post_received_row = session.execute(
        select(
            func.coalesce(func.sum(FulfillmentHistory.quantity_received), 0).label("qty")
        )
        .where(
            FulfillmentHistory.sku_id == sku.sku_id,
            FulfillmentHistory.fulfillment_date > promo_end,
        )
    ).one()
    post_received = int(post_received_row.qty)

    opening = int(sku.in_stock) + post_sold - post_received
    return max(opening, 0)  # guard against negative if data is sparse


def _build_daily_trace(
    promo_start: date,
    promo_end: date,
    opening_stock: int,
    daily_received: Dict[date, int],
    daily_sold: Dict[date, int],
) -> List[DailyStockSnapshot]:
    
    snapshots: List[DailyStockSnapshot] = []
    running_stock = opening_stock
    current = promo_start

    while current <= promo_end:
        received = daily_received.get(current, 0)
        sold = daily_sold.get(current, 0)
        running_stock = running_stock + received - sold
        snapshots.append(
            DailyStockSnapshot(
                date=current,
                units_received=received,
                units_sold=sold,
                closing_stock=running_stock,
                stockout_on_this_day=running_stock <= 0,
            )
        )
        current += timedelta(days=1)

    return snapshots


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def trace_stockouts(session: Session, product_id: int) -> List[StockoutResult]:
    sku_ids = _sku_ids_for_product(session, product_id)
    if not sku_ids:
        return []

    promo_ids = _promo_ids_for_skus(session, sku_ids)
    if not promo_ids:
        return []

    skus = session.execute(
        select(Sku).where(Sku.sku_id.in_(sku_ids))
    ).scalars().all()

    promotions = session.execute(
        select(Promotion)
        .where(Promotion.promotion_id.in_(promo_ids))
        .order_by(Promotion.start_date)
    ).scalars().all()

    results: List[StockoutResult] = []

    for promo in promotions:
        promo_start: date = promo.start_date
        promo_end: date = promo.end_date

        for sku in skus:
            opening_stock = _reconstruct_opening_stock(session, sku, promo_end)

            daily_sku_sold = _daily_sku_sales(session, sku.sku_id, promo_start, promo_end)
            daily_bundle_sold = _daily_bundle_sales_for_sku(session, sku.sku_id, promo_start, promo_end)

            all_dates = set(daily_sku_sold) | set(daily_bundle_sold)
            daily_sold: Dict[date, int] = {
                d: daily_sku_sold.get(d, 0) + daily_bundle_sold.get(d, 0)
                for d in all_dates
            }

            daily_received = _daily_fulfillments(session, sku.sku_id, promo_start, promo_end)

            units_received_during = sum(daily_received.values())
            units_sold_during = sum(daily_sold.values())

            daily_trace = _build_daily_trace(
                promo_start, promo_end, opening_stock, daily_received, daily_sold
            )

            closing_stock = daily_trace[-1].closing_stock if daily_trace else opening_stock

            stockout_days = [s for s in daily_trace if s.stockout_on_this_day]
            stockout_detected = len(stockout_days) > 0
            stockout_date: Optional[date] = stockout_days[0].date if stockout_days else None
            days_out_of_stock = len(stockout_days)

            suppressed_demand = 0
            prev_closing = opening_stock
            for snap in daily_trace:
                if snap.closing_stock < 0:
                    new_suppressed = max(0, -snap.closing_stock) - max(0, -prev_closing)
                    suppressed_demand += new_suppressed
                prev_closing = snap.closing_stock

            sku_price = float(sku.price)
            potential_revenue_lost = round(suppressed_demand * sku_price, 2)

            results.append(
                StockoutResult(
                    product_id=product_id,
                    sku_id=sku.sku_id,
                    sku_name=sku.sku_name,
                    promotion_id=promo.promotion_id,
                    promotion_name=promo.promotion_name,
                    promotion_type=promo.promotion_type,
                    promo_start_date=promo_start,
                    promo_end_date=promo_end,
                    opening_stock=opening_stock,
                    units_received_during=units_received_during,
                    units_sold_during=units_sold_during,
                    closing_stock=closing_stock,
                    stockout_detected=stockout_detected,
                    stockout_date=stockout_date,
                    days_out_of_stock=days_out_of_stock,
                    suppressed_demand=suppressed_demand,
                    sku_price=sku_price,
                    potential_revenue_lost=potential_revenue_lost,
                    daily_trace=daily_trace,
                )
            )

    # Sort by promo start then sku
    results.sort(key=lambda r: (r.promo_start_date, r.sku_id))
    return results

def get_stockout_trace_for_product(promotion_id: int) -> List[StockoutResult]:
    session = SessionLocal()
    try:
        results = trace_stockouts(session, product_id=promotion_id)
        return results
    except Exception as e:
        print(f"Error tracing stockouts for product {promotion_id}: {e}")
        raise e
    finally:
        session.close()