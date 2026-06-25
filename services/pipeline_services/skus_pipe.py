from services.api_services.sku_api import get_skus
from services.db_services.product_db import get_product_by_id
from services.db_services.sku_db import add_skus
from services.db_services.models import Sku

def pipe_skus():
    try:
        skus = get_skus()
        skus_db : list[Sku] = []
        for sku in skus:
            sku_db = Sku(
                sku_id = sku.sku_id,
                product_id = sku.product_id,
                sku_name = sku.sku_name,
                size = sku.size,
                color = sku.color,
                last_fulfillment_date = sku.last_fulfillment_date,
                next_fulfillment_date = sku.next_fulfillment_date,
                in_stock = sku.in_stock,
                price = sku.price
            )
            skus_db.append(sku_db)
        add_skus(skus_db)
    except Exception as e:
            raise e