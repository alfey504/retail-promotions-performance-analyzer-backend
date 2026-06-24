from db_services.session import SessionLocal
from db_services.models import Sale

def add_sales(sales: list[Sale]):
    session = SessionLocal()

    try:
        session.add_all(sales)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()