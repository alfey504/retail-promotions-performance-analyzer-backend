from services.db_services.session import SessionLocal
from services.db_services.promotions_db import get_promotion_by_id
from services.db_services.models import Sale, Promotion
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from datetime import timedelta
from pydantic import BaseModel
from services.kpi_services.kpi_calculators.models import Uplift

def uplift_calculator(session: Session, promotion: Promotion) -> Uplift:
 
    sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]
    statement = select(func.sum(Sale.quantity), func.sum(Sale.final_price)).where(Sale.promotion_id == promotion.promotion_id)
    promotion_units_sold, promotion_revenue = session.execute(statement).tuples().first() or (None, None)
    promotion_units_sold = int(promotion_units_sold or 0)
    promotion_revenue = float(promotion_revenue or 0)
    
    promotion_duration = promotion.end_date - promotion.start_date
    baseline_end_date = promotion.start_date - timedelta(days=1)
    baseline_start_date = baseline_end_date - promotion_duration

    statement = select(func.sum(Sale.quantity), func.sum(Sale.final_price)).where(Sale.sale_date >= baseline_start_date, Sale.sale_date <= baseline_end_date, Sale.sku_id.in_(sku_ids))
    baseline_units_sold, baseline_revenue = session.execute(statement).tuples().first() or (None, None)
    baseline_units_sold = int(baseline_units_sold or 0)
    baseline_revenue = float(baseline_revenue or 0)
    # if (baseline_units_sold is None ) or (baseline_revenue is None):
    #     raise Exception("baseline sales query returned none")
    
    
    unit_sale_uplift, revenue_uplift = float(0) , float(0)
    if (baseline_units_sold !=0 and baseline_units_sold is not None ) or (baseline_revenue != 0 and baseline_revenue is not None):
        unit_sale_uplift = ((promotion_units_sold - baseline_units_sold) / baseline_units_sold) * 100 # type: ignore
        revenue_uplift = ((promotion_revenue - baseline_revenue)/ baseline_revenue) * 100 # type: ignore


    print(unit_sale_uplift, revenue_uplift)
    sales_up_revenue_down = True if unit_sale_uplift > 0 and revenue_uplift < 0 else False
    clean_win = True if unit_sale_uplift  >0 and revenue_uplift > 0 else False

    return Uplift(
        promotion_id=promotion.promotion_id,
        baseline_units_sold = baseline_units_sold,
        promotion_units_sold = promotion_units_sold,
        baseline_revenue=baseline_revenue,
        promotion_revenue=promotion_revenue,
        unit_sales_uplift=unit_sale_uplift,
        revenue_uplift=revenue_uplift,
        sales_up_revenue_down=sales_up_revenue_down,
        clean_win=clean_win,
    )


def get_incremental_uplift(promotion_id: int) -> Uplift:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        post_promo_dip = uplift_calculator(session, promotion)
        return post_promo_dip
    except Exception as e:
        raise e
    finally:
        session.close()