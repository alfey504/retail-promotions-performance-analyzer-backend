from  services.db_services.session import SessionLocal
from  services.db_services.models import Customer

def add_customers(customers: list[Customer]):
    session = SessionLocal()

    try:
        session.add_all(customers)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()