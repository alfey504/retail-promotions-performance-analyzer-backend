from  services.db_services.session import SessionLocal
from  services.db_services.models import FulfillmentHistory

from sqlalchemy import text

def add_fulfillments(fulfillments: list[FulfillmentHistory]):
    session = SessionLocal()

    try:
        session.add_all(fulfillments)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()


def delete_all_fulfillments():
    session = SessionLocal()
    try:
        session.execute(text("TRUNCATE TABLE fulfillment_history RESTART IDENTITY CASCADE;"))
        session.commit()
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()