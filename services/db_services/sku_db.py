from  services.db_services.session import SessionLocal
from  services.db_services.models import Sku

def add_skus(skus: list[Sku]):
    session = SessionLocal()

    try:
        session.add_all(skus)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()