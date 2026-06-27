from  services.api_services.fulfillment_api import get_all_fulfillment_data
from  services.db_services.fulfillment_db import add_fulfillments
from  services.db_services.models import FulfillmentHistory

def pipe_fulfillment():
    try:
        fulfillments = get_all_fulfillment_data()
        fulfillments_db = list[FulfillmentHistory]()
        for fulfillment in fulfillments:
            fulfillment_db = FulfillmentHistory(
                 fullfillment_id = fulfillment.fullfillment_id,
                 sku_id = fulfillment.sku_id,
                 fullfillment_date = fulfillment.fullfillment_date,
                 quantity_received = fulfillment.quantity_received
            )
            fulfillments_db.append(fulfillment_db)
        add_fulfillments(fulfillments_db)
    except Exception as e:
            raise e