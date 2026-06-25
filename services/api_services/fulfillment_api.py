import httpx
from services.api_services.model import FullfillmentHistory, PagedAPIResponse
from services.api_services.api import get_server_uri
from typing import Tuple

def get_fulfillment_by_page(page: int) -> Tuple[int, list[FullfillmentHistory]]:
    try:
        response = httpx.get(get_server_uri(f"/fulfillment-history?page={page}"))
        json_body = response.json()

        parsed_repsonse = PagedAPIResponse[FullfillmentHistory].model_validate(json_body)
        return parsed_repsonse.max_page, parsed_repsonse.data
    except Exception as e:
        raise e
    
def get_all_fulfillment_data() -> list[FullfillmentHistory]:
    try:
        max_page, fulfillment_history = get_fulfillment_by_page(1)
        for i in range(2, max_page+1):
            _, fulfillment_page = get_fulfillment_by_page(i)
            fulfillment_history.extend(fulfillment_page)
            
        return fulfillment_history
    except Exception as e:
        raise e