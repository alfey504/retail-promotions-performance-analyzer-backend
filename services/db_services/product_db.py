from  services.db_services.session import SessionLocal
from  services.db_services.models import Product
from sqlalchemy import select, delete

def add_product(product: Product):
    session = SessionLocal()

    try:
        session.add(product)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

def add_products(products: list[Product]):
    session = SessionLocal()

    try:
        session.add_all(products)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

def get_product_by_id(product_id: int) -> Product:
    print("get product by id")
    session = SessionLocal()
    try:
        product = session.get(Product, product_id)
        if product is None:
            raise Exception(f"could'nt find product with product_id : {product_id}")
        return product
    except Exception as e:
        raise e
    finally:
        session.close()

def delete_all_products():
    session = SessionLocal()
    try:
        session.execute(delete(Product))
        session.commit()
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()
