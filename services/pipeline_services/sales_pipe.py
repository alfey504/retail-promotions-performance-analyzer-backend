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
            )
            
            for sku_sale in sale.sku_sales:
                sale_db.sku_sales.append(
                    SkuSale(
                         sku_id=sku_sale.sku_id, 
                         quantity=sku_sale.quantity
                    )
                )
            
            for bundle_sale in sale.bundle_sales:
                sale_db.bundle_sales.append(
                    BundleSale(
                        bundle_id=bundle_sale.bundle_id,
                        quantity = bundle_sale.quantity
                    )
                )
            
            for promotion_id in sale.promotion_ids:
                sale_db.promotion_links.append(
                    SalePromotion(promotion_id = promotion_id)
                )

            sales_db.append(sale_db)
        add_promotions(sales_db)
    except Exception as e:
            raise e