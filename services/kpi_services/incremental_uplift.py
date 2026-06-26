from services.db_services.session import SessionLocal
from services.db_services.promotions_db import get_promotion_by_id
from services.db_services.models import Sale
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
        sales_up_revnue_down: bool,
        clean_win: bool,
    ):
        self.baseline_units_sold = baseline_units_sold
        self.promotion_units_sold = promotion_units_sold
        self.baseline_revenue = baseline_revenue
        self.promotion_revenue = promotion_revenue
        self.unit_sales_uplift = unit_sales_uplift
        self.revenue_uplift = revenue_uplift
        self.sales_up_revenue_dow = sales_up_revnue_down
        self.clean_win = clean_win

    def __repr__(self):
        string = "___________UPLIFT_____________\n"
        string += f"Baseline Unit Sales -> {self.baseline_units_sold}\n"
        string += f"Promotion Unit Sales -> {self.promotion_units_sold}\n"
        string += f"Baseline Revenue -> {self.baseline_revenue}\n" 
        string += f"Promotion Revenue -> {self.promotion_revenue}\n"
        string += f"Unit Sales Uplift -> {self.unit_sales_uplift}\n"
        string += f"Revenue Uplift -> {self.revenue_uplift}\n"
        string += f"Sales Up Revenue Down -> {self.sales_up_revenue_dow}\n"
        string += f"sclean win -> {self.clean_win}\n"
        return string
        
def get_incremental_sales_uplift(promotion_id: int) -> Uplift:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        sku_ids = [sku_link.sku_id for sku_link in promotion.sku_links]
        statement = select(func.sum(Sale.quantity), func.sum(Sale.final_price)).where(Sale.promotion_id == promotion_id)
        promotion_units_sold, promotion_revenue = session.execute(statement).tuples().first()
        if (promotion_units_sold in {None, 0}) or (promotion_revenue in {None, 0}):
            raise Exception("prommtion sales query returned None")
        
        promotion_duration = promotion.end_date - promotion.start_date
        baseline_end_date = promotion.start_date - timedelta(days=1)
        baseline_start_date = baseline_end_date - promotion_duration

        statement = select(func.sum(Sale.quantity), func.sum(Sale.final_price)).where(Sale.sale_date >= baseline_start_date, Sale.sale_date <= baseline_end_date, Sale.sku_id.in_(sku_ids))
        baseline_units_sold, baseline_revenue = session.execute(statement).tuples().first()
        if (baseline_units_sold in {None, 0} ) or (baseline_revenue in {None, 0}):
            raise Exception("baseline sales query returned none")
        
        

        unit_sale_uplift = ((promotion_units_sold - baseline_units_sold) / baseline_units_sold) * 100
        revenue_uplift = ((promotion_revenue - baseline_revenue)/ baseline_revenue) * 100

        print(unit_sale_uplift, revenue_uplift)
        sales_up_revenue_down = True if unit_sale_uplift > 0 and revenue_uplift < 0 else False
        clean_win = True if unit_sale_uplift  >0 and revenue_uplift > 0 else False

        return Uplift(
            baseline_units_sold = baseline_units_sold,
            promotion_units_sold = promotion_units_sold,
            baseline_revenue=baseline_revenue,
            promotion_revenue=promotion_revenue,
            unit_sales_uplift=unit_sale_uplift,
            revenue_uplift=revenue_uplift,
            sales_up_revnue_down=sales_up_revenue_down,
            clean_win=clean_win,
        )

    except Exception as e:
        raise e
    finally:
        session.close()

