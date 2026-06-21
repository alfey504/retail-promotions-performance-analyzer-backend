from api_services.sku_api import get_skus
from db_services.product_db import add_products,get_product_by_id
from db_services.models import Sku

# def pipe_product():
#     try:
#         skus = get_skus()
#         products_db = list[Sku]()
#         for sku in skus:
#             product_db = Sku(
#                 product_id = sku.product_id,
#                 product_name = sku.product_name,
#                 product_description = sku.product_description, 
#                 product_brand = sku.product_brand,
#                 product_category = sku.product_category
#             )
#             products_db.append(product_db)
        
#         add_products(products_db)
#     except Exception as e:
#             raise e