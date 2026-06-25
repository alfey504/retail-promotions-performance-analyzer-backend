from  services.api_services.sales_api import get_all_sales
from  services.db_services.models import Sale, SkuSale, BundleSale, SalePromotion
from  services.db_services.promotions_db import add_promotions


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
            )
            sales_db.append(sale_db)
            
        add_promotions(sales_db)
    except Exception as e:
            raise e