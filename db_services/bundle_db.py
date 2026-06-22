from db_services.session import SessionLocal
from db_services.models import Bundle, BundleSku

def add_bundles(bundles: list[Bundle]):
    session = SessionLocal()

    try:
        session.add_all(bundles)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()
