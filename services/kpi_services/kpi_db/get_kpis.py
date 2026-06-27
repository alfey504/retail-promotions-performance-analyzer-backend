from services.kpi_services.kpi_calculators.discount_efficiency_calculator import discount_efficiency_calculator, DiscountEfficiency
from services.kpi_services.kpi_calculators.post_promo_dip_calculator import PostPromoDip, post_promo_dip_calculator
from services.kpi_services.kpi_calculators.redemption_demographics_calculator import RedemptionDemographics, redemption_demographics_calculator
from services.kpi_services.kpi_calculators.stockout_calculator import stockout_inventory_trace_calculator, StockoutTrace
from services.kpi_services.kpi_calculators.uplift_calculator import uplift_calculator, Uplift

from services.db_services.session import SessionLocal
from services.db_services.promotions_db import get_promotion_by_id

def get_discount_efficiency(promotion_id: int) -> DiscountEfficiency:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        discount_efficiency = discount_efficiency_calculator(promotion)
        return discount_efficiency
    finally:
        session.close()


def get_post_promo_dip(promotion_id: int) -> PostPromoDip:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        post_promo_dip = post_promo_dip_calculator(promotion)
        return post_promo_dip
    except Exception as e:
        raise e
    finally:
        session.close()

def get_redemption_demographics(promotion_id: int) -> RedemptionDemographics:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        redemption_demographics = redemption_demographics_calculator(promotion)
        return redemption_demographics
    except Exception as e:
        raise e
    finally:
        session.close()

def get_stockout_inventory_trace(promotion_id: int) -> StockoutTrace:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        stockout_trace = stockout_inventory_trace_calculator(promotion)
        return stockout_trace
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
