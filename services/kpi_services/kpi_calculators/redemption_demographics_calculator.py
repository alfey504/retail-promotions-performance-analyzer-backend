from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.db_services.models import Sale, Customer, Promotion
from services.db_services.session import SessionLocal
from services.db_services.promotions_db import get_promotion_by_id
from services.kpi_services.kpi_calculators.models import RedemptionDemographics

#function currently only check under 25 as the demographics TODO: Update it to add more demographics
def redemption_demographics_calculator(session: Session, promotion: Promotion) -> RedemptionDemographics :

    promotion_id = promotion.promotion_id
    redemption_count = session.execute(
        select(func.count(Sale.sales_id)).where(Sale.promotion_id == promotion_id)
    ).scalar() or 0

    under_25_count = session.execute(
        select(func.count(Sale.sales_id))
        .join(Customer, Customer.customer_id == Sale.customer_id)
        .where(Sale.promotion_id == promotion_id, Customer.customer_age < 25)
    ).scalar() or 0

    total_customers = session.execute(select(func.count(Customer.customer_id))).scalar() or 0
    under_25_customers = session.execute(
        select(func.count(Customer.customer_id)).where(Customer.customer_age < 25)
    ).scalar() or 0

    under_25_share = (under_25_count / redemption_count) if redemption_count > 0 else None
    customer_base_under_25_share = (
        (under_25_customers / total_customers) if total_customers > 0 else None
    )

    over_indexed_under_25 = (
        under_25_share is not None
        and customer_base_under_25_share is not None
        and (under_25_share - customer_base_under_25_share) >= 0.15
    )

    return RedemptionDemographics(
        promotion_id=promotion_id,
        redemption_count=redemption_count,
        under_25_count=under_25_count,
        under_25_share=under_25_share,
        customer_base_under_25_share=customer_base_under_25_share,
        over_indexed_under_25=over_indexed_under_25,
    )

def get_redemption_demographic(promotion_id: int) -> RedemptionDemographics:
    session = SessionLocal()
    try:
        promotion = get_promotion_by_id(promotion_id)
        post_promo_dip = redemption_demographics_calculator(session, promotion)
        return post_promo_dip
    except Exception as e:
        raise e
    finally:
        session.close()