from  services.db_services.session import SessionLocal
from  services.db_services.models import Sku

from sqlalchemy import select, text

def add_skus(skus: list[Sku]):
    session = SessionLocal()

    try:
        session.add_all(skus)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

def sku_by_id(sku_id: int) -> Sku:
    session = SessionLocal()
    try:
        statement = select(Sku).where(Sku.sku_id == sku_id)
        sku = session.scalar(statement)
        if sku is None:
            raise Exception(f"unable to find sku with sku_id : {sku_id}")
        return sku
    except Exception as e:
        raise e
    finally:
        session.close()

def delete_all_skus():
    session = SessionLocal() 
    try:
        session.execute(text("TRUNCATE TABLE skus RESTART IDENTITY CASCADE;"))
        session.commit()
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()
    
