from  services.api_services.sales_api import get_all_sales
from  services.db_services.models import Sale
from  services.db_services.sales_db import add_sales, delete_all_sales


def pipe_sales():
    try:
        sales = get_all_sales()
        sales_db = list[Sale]()
        for sale in sales:
            sale_db = Sale(
                sales_id = sale.sales_id,
                customer_id = sale.customer_id,
                sale_date = sale.sale_date,
                final_price = sale.final_price,
                promotion_id = sale.promotion_id,
                sku_id = sale.sku_id,
                regular_price = sale.regular_price,
                quantity = sale.quantity,
            )
            sales_db.append(sale_db)
        add_sales(sales_db)
    except Exception as e:
            raise e