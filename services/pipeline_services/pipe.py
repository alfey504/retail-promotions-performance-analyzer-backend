from  services.pipeline_services.product_pipe import pipe_product
from  services.pipeline_services.skus_pipe import pipe_skus
from  services.pipeline_services.customers_pipe import pipe_customers
from  services.pipeline_services.fulfillment_pipe import pipe_fulfillment
from  services.pipeline_services.promotions_pipe import pipe_promotions
from  services.pipeline_services.sales_pipe import pipe_sales

from services.db_services.sales_db import delete_all_sales
from services.db_services.promotions_db import delete_all_promotions
from services.db_services.fulfillment_db import delete_all_fulfillments
from services.db_services.sku_db import delete_all_skus
from services.db_services.product_db import delete_all_products
from services.db_services.customer_db import delete_all_customers

def load_data():
    _pipe_data()

def reload_data():
    _empty_table()
    _pipe_data()

def _pipe_data():
    pipe_product()
    pipe_customers()
    pipe_skus()
    pipe_fulfillment()
    pipe_promotions()
    pipe_sales()
    
def _empty_table():
    delete_all_sales()
    delete_all_promotions()
    delete_all_fulfillments()
    delete_all_skus()
    delete_all_products()
    delete_all_customers()