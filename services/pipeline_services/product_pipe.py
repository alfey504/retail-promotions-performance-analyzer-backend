from  services.api_services.product_api import get_products
from  services.db_services.product_db import add_products, delete_all_products
from  services.db_services.models import Product


def pipe_product():
    try:
        products = get_products()
        products_db = list[Product]()
        for product in products:
            product_db = Product(
                product_id = product.product_id,
                product_name = product.product_name,
                product_description = product.product_description, 
                product_brand = product.product_brand,
                product_category = product.product_category
            )
            products_db.append(product_db)
        
        add_products(products_db)
    except Exception as e:
            print(e)
            raise e