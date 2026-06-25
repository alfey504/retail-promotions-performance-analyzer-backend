from  services.pipeline_services.product_pipe import pipe_product
from  services.pipeline_services.skus_pipe import pipe_skus
from  services.pipeline_services.customers_pipe import pipe_customers
from  services.pipeline_services.bundle_pipe import pipe_bundle
from  services.pipeline_services.fulfillment_pipe import pipe_fulfillment
from  services.pipeline_services.promotions_pipe import pipe_promotions
from  services.pipeline_services.sales_pipe import pipe_sales

def pipe_data():
    pipe_product()
    pipe_skus()
    pipe_customers()
    pipe_bundle()
    pipe_fulfillment()
    pipe_promotions()
    pipe_sales()