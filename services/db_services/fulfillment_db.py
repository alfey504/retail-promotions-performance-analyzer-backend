from  services.db_services.session import SessionLocal
from  services.db_services.models import FulfillmentHistory

def add_fulfillments(fulfillments: list[FulfillmentHistory]):
    session = SessionLocal()

    try:
        session.add_all(fulfillments)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

