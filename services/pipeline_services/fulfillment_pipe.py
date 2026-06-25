from  services.api_services.fulfillment_api import get_all_fulfillment_data
from  services.db_services.fulfillment_db import add_fulfillments
from  services.db_services.models import FullfillmentHistory

def pipe_fulfillment():
    try:
        fulfillments = get_all_fulfillment_data()
        fulfillments_db = list[FullfillmentHistory]()
        for fulfillment in fulfillments:
            fulfillment_db = FullfillmentHistory(
                 fulfillment_id = fulfillment.fulfillment_id,
                 sku_id = fulfillment.sku_id,
                 fulfillment_date = fulfillment.fulfillment_date,
                 quantity_received = fulfillment.quantity_received
            )
            fulfillments_db.append(fulfillment_db)
        add_fulfillments(fulfillments_db)
    except Exception as e:
            raise e