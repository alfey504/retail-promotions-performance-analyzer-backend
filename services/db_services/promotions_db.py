from  services.db_services.session import SessionLocal
from  services.db_services.models import Promotion
from  sqlalchemy import select

def add_promotions(promtions: list[Promotion]):
    session = SessionLocal()

    try:
        session.add_all(promtions)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

def get_promotion_by_id(promotion_id: int) -> Promotion:
    session = SessionLocal()
    try:
        statement = select(Promotion).where(Promotion.promotion_id == promotion_id)
        result = session.scalar(statement)
        if result is None:
            raise Exception(f"could'nt find promotion with promotion_id : {promotion_id}")
        _ = result.sku_links
        return result
    except Exception as e:
        raise e
    finally:
        session.close()

def get_all_promotions() -> list[Promotion]:
    session = SessionLocal()
    try:
        statement = select(Promotion)
        promotion = session.scalars(statement).all()
        return list(promotion)
    except Exception as e:
        raise e