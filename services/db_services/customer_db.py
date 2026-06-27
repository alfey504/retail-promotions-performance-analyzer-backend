from  services.db_services.session import SessionLocal
from  services.db_services.models import Customer

from  sqlalchemy import select


def add_customers(customers: list[Customer]):
    session = SessionLocal()

    try:
        session.add_all(customers)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

def customer_by_id(customer_id: int) -> Customer: 
    session = SessionLocal()
    try :
        statement = select(Customer).where(Customer.customer_id == customer_id)
        customer = session.scalar(statement)
        if customer is None:
            raise Exception(f"could'nt find Customer with customer_id : {customer_id}")
        return customer
    except Exception as e:
        raise e
    finally:
        session.close()
