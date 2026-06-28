from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import Session
from services.kpi_services.kpi_calculators.models import Uplift
from services.db_services.session import SessionLocal
from services.db_services.models import Promotion, Sale, PromotionSku
from pydantic import BaseModel
from typing import Tuple

class HistoricUplift(BaseModel):
    promotion_id: int
    promotion_name: str
    promotion_type: str 

    uplift: Uplift

def historic_uplift() -> list[HistoricUplift]:
    session = SessionLocal()
    try:

        baseline_sales = get_baseline_sales(session)
        promotional_sales = get_promotional_sales(session)
        historic_uplifts: list[HistoricUplift] = []
        for baseline_sale, promotional_sale in zip(baseline_sales, promotional_sales):
            historic_uplift = calculate_uplift(baseline_sale.tuple(), promotional_sale.tuple())  
            historic_uplifts.append(historic_uplift)
        return historic_uplifts
    
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()

def calculate_uplift(
    baseline: Tuple[int, str, str, int, float],
    promotional: Tuple[int, str, str, int, float],
) ->  HistoricUplift:
    (
        baseline_promotion_id, 
        _, 
        _, 
        baseline_total_sales, 
        baseline_total_price
    ) = baseline

    (
        promotional_promotion_id, 
        promotional_promotion_name, 
        promotional_promotion_type, 
        promotional_total_sales, 
        promotional_total_price
    ) = promotional

    if baseline_promotion_id != promotional_promotion_id:
        raise Exception(f"promotion_id does not match baseline : {baseline_promotion_id} promotional : {promotional_promotion_id}")
    
    sales_uplift = ((promotional_total_sales - baseline_total_sales) / baseline_total_sales) * 100
    revenue_uplift = ((promotional_total_price - baseline_total_price)/baseline_total_price) * 100

    sales_uplift, revenue_uplift = float(0) , float(0)
    if (baseline_total_sales !=0 and baseline_total_sales is not None ) or (baseline_total_sales != 0 and baseline_total_sales is not None):
        sales_uplift = ((promotional_total_sales - baseline_total_sales) / baseline_total_sales) * 100 # type: ignore
        revenue_uplift = ((promotional_total_price - baseline_total_price)/ baseline_total_price) * 100 # type: ignore


    print(sales_uplift, revenue_uplift)
    sales_up_revenue_down = True if sales_uplift > 0 and revenue_uplift < 0 else False
    clean_win = True if sales_uplift  >0 and revenue_uplift > 0 else False

    uplift =  Uplift(
        promotion_id= promotional_promotion_id,
        baseline_units_sold = baseline_total_sales,
        promotion_units_sold = promotional_total_sales,
        baseline_revenue= baseline_total_price,
        promotion_revenue= promotional_total_price,
        unit_sales_uplift=sales_uplift,
        revenue_uplift=revenue_uplift,
        sales_up_revenue_down=sales_up_revenue_down,
        clean_win=clean_win,
    )

    return HistoricUplift(
        promotion_id = promotional_promotion_id,
        promotion_name = promotional_promotion_name,
        promotion_type = promotional_promotion_type,
        uplift = uplift
    )

def get_promotional_sales(session: Session): 
    statement = (
        select(
            Promotion.promotion_id,
            Promotion.promotion_name,
            Promotion.promotion_type,
            func.count(Sale.sales_id).label("total_sales"),
            func.sum(Sale.final_price).label("total_revenue"),
        )
        .join(
            Sale,
            and_(
                 Sale.promotion_id == Promotion.promotion_id
            )
        )
        .group_by(
            Promotion.promotion_id,
        )
        .order_by(Promotion.promotion_id.asc())
    )
    results = session.execute(statement).all()
    return results

def get_baseline_sales(session: Session):
    statement = (
        select(
            Promotion.promotion_id,
            Promotion.promotion_name,
            Promotion.promotion_type,
            func.count(Sale.sales_id).label("total_sales"),
            func.sum(Sale.final_price).label("total_revenue"),
        )
        .join(
            PromotionSku,
            PromotionSku.promotion_id == Promotion.promotion_id
        )
        .join(
            Sale,
            and_(
                Sale.sku_id == PromotionSku.sku_id,
                Sale.sale_date >= (
                    Promotion.start_date -
                    text("INTERVAL '30 days'") 
                ),
                Sale.sale_date < Promotion.start_date,
            )
        )
        .group_by(
            Promotion.promotion_id,
            Promotion.promotion_name,
        )
        .order_by(Promotion.promotion_id.asc())
    )
    results = session.execute(statement).all()
    return results

