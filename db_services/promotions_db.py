from db_services.session import SessionLocal
from db_services.models import Promotion

def add_promotions(promtions: list[Promotion]):
    session = SessionLocal()

    try:
        session.add_all(promtions)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()
