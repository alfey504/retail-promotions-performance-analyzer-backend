from services.db_services.session import SessionLocal
from services.db_services.promotions_db import get_promotion_by_id
from services.db_services.models import Sale, Promotion
from sqlalchemy import func, select
from datetime import timedelta

class Uplift:
    
    def __init__(
        self,
        baseline_units_sold : int, 
        promotion_units_sold: int, 
        baseline_revenue: float,
        promotion_revenue: float,
        unit_sales_uplift: float,
        revenue_uplift: float,
        sales_up_revenue_down: bool,
        clean_win: bool,
        promotion_id: int,
    ):
        self.promotion_id = promotion_id
        self.baseline_units_sold = baseline_units_sold
        self.promotion_units_sold = promotion_units_sold
        self.baseline_revenue = baseline_revenue
        self.promotion_revenue = promotion_revenue
        self.unit_sales_uplift = unit_sales_uplift
        self.revenue_uplift = revenue_uplift
        self.sales_up_revenue_down = sales_up_revenue_down
        self.clean_win = clean_win

    def __repr__(self):
        string = "___________UPLIFT_____________\n"
        string += f"Baseline Unit Sales -> {self.baseline_units_sold}\n"
        string += f"Promotion Unit Sales -> {self.promotion_units_sold}\n"
        string += f"Baseline Revenue -> {self.baseline_revenue}\n" 
        string += f"Promotion Revenue -> {self.promotion_revenue}\n"
        string += f"Unit Sales Uplift -> {self.unit_sales_uplift}\n"
        string += f"Revenue Uplift -> {self.revenue_uplift}\n"
        string += f"Sales Up Revenue Down -> {self.sales_up_revenue_down}\n"
        string += f"clean win -> {self.clean_win}\n"
        return string

def uplift_calculator(promotion: Promotion) -> Uplift:
    session = SessionLocal()
    try:
        sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]
        statement = select(func.sum(Sale.quantity), func.sum(Sale.final_price)).where(Sale.promotion_id == promotion.promotion_id)
        promotion_units_sold, promotion_revenue = session.execute(statement).tuples().first() or (None, None)
        if ((promotion_units_sold) is None or (promotion_revenue is None)):
            raise Exception("promotion sales query returned None")
        
        promotion_duration = promotion.end_date - promotion.start_date
        baseline_end_date = promotion.start_date - timedelta(days=1)
        baseline_start_date = baseline_end_date - promotion_duration

        statement = select(func.sum(Sale.quantity), func.sum(Sale.final_price)).where(Sale.sale_date >= baseline_start_date, Sale.sale_date <= baseline_end_date, Sale.sku_id.in_(sku_ids))
        baseline_units_sold, baseline_revenue = session.execute(statement).tuples().first() or (None, None)
        if (baseline_units_sold is None ) or (baseline_revenue is None):
            raise Exception("baseline sales query returned none")
        
        

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

    except Exception as e:
        raise e
    finally:
        session.close()

        
def get_incremental_sales_uplift(promotion_id: int) -> Uplift:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        uplift = uplift_calculator(promotion)
        return uplift
    except Exception as e:
        raise e
    finally:
        session.close()
