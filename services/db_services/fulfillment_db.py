from  services.db_services.session import SessionLocal
from  services.db_services.models import FulfillmentHistory

from sqlalchemy import delete

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
        session.execute(delete(FulfillmentHistory))
        session.commit()
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()