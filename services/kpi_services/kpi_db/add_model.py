from sqlalchemy.orm import DeclarativeBase
from services.db_services.session import SessionLocal

def add_to_db(models : list[DeclarativeBase]):
    session = SessionLocal()
    try:
        session.add_all(models)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()