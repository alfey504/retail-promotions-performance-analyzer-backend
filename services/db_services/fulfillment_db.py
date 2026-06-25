from  services.db_services.session import SessionLocal
from  services.db_services.models import FullfillmentHistory

def add_fulfillments(fulfillments: list[FullfillmentHistory]):
    session = SessionLocal()

    try:
        session.add_all(fulfillments)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()