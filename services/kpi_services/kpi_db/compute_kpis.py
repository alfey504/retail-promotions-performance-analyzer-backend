from services.db_services.promotions_db import get_all_promotions
from services.db_services.session import SessionLocal
from services.db_services.database import add_to_db
from sqlalchemy.orm import DeclarativeBase

#kpi calculators
from services.kpi_services.kpi_calculators.uplift_calculator import uplift_calculator
from services.kpi_services.kpi_calculators.discount_efficiency_calculator import discount_efficiency_calculator
from services.kpi_services.kpi_calculators.post_promo_dip_calculator import post_promo_dip_calculator
from services.kpi_services.kpi_calculators.redemption_demographics_calculator import redemption_demographics_calculator
from services.kpi_services.kpi_calculators.stockout_calculator import stockout_inventory_trace_calculator


#orm model adapters
from services.kpi_services.kpi_db.models import (
    uplift_to_orm,
    discount_efficiency_to_orm,
    post_promo_dip_to_orm,
    redemption_demographics_to_orm,
    stockout_trace_to_orm
)

def compute_kpi():
    session = SessionLocal()

    uplifts: list[DeclarativeBase] = []
    discount_efficiencies: list[DeclarativeBase] = []
    post_promo_dips: list[DeclarativeBase] = []
    redemption_demographics: list[DeclarativeBase] = []
    stockout_tracers: list[DeclarativeBase] = []

    try:
        promotions = get_all_promotions()    
        for promotion in promotions:
            uplift = uplift_calculator(promotion)
            uplift_orm = uplift_to_orm (uplift)
            uplifts.append(uplift_orm)

            discount_efficiency = discount_efficiency_calculator(promotion)
            discount_efficiency_orm = discount_efficiency_to_orm(discount_efficiency)
            discount_efficiencies.append(discount_efficiency_orm)

            post_promo_dip = post_promo_dip_calculator(promotion)
            post_promo_dip_orm = post_promo_dip_to_orm(post_promo_dip)
            post_promo_dips.append(post_promo_dip_orm)

            redemption_demographic = redemption_demographics_calculator(promotion)
            redemption_demographic_orm = redemption_demographics_to_orm(redemption_demographic)
            redemption_demographics.append(redemption_demographic_orm)

            stockout_tracer = stockout_inventory_trace_calculator(promotion)
            stockout_tracer_orm = stockout_trace_to_orm(stockout_tracer)
            stockout_tracers.append(stockout_tracer_orm)
        
        add_to_db(uplifts)
        add_to_db(discount_efficiencies)
        add_to_db(post_promo_dips)
        add_to_db(redemption_demographics)
        add_to_db(stockout_tracers)
    except Exception as e:
        raise e
    finally:
        session.close()