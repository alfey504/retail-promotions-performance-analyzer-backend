from api_services.product_api import get_products
from api_services.sku_api import get_skus
from api_services.customer_api import get_customers
from api_services.fulfillment_api import get_fulfillment_by_page, get_all_fulfillment_data
from api_services.bundle_api import get_bundles
from api_services.promotions_api import get_promotions
from api_services.sales_api import get_sales_by_page, get_all_sales
from pipeline_services.product_pipe import pipe_product
from db_services.session import init_db
from db_services.product_db import get_product_by_id

def main():
    # products = get_products()
    # for product in products:
    #     print(product.product_name, "\n")
    
    # skus = get_skus()
    # for sku in skus:
    #     print(sku.sku_name)

    # customers = get_customers()
    # for customer in customers:
    #     print(customer.customer_gender)

    # fulfillment_history = get_all_fulfillment_data()
    # for i, fulfillment in enumerate(fulfillment_history):
    #     print(fulfillment.quantity_received)
    #     if i > 50:
    #         break 

    # bundles = get_bundles()
    # for i, bundle in enumerate(bundles):
    #     print(bundle.bundle_name)
    #     if i > 10:
    #         break

    # promotions = get_promotions()
    # for i, promotion in enumerate(promotions):
    #     print(promotion.promotion_name)
    #     if i > 10:
    #         break

    # sales = get_all_sales()
    # for i, sale in enumerate(sales):
    #     print(sale.sale_date)
    #     if i > 10:
    #         break
    init_db()

    # pipe_product()
    product = get_product_by_id(2)
    print(product.product_name)
    return


if __name__ == "__main__":
    main()

