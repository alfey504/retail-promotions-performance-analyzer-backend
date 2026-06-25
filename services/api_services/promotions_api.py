import httpx
from services.api_services.model import Promotion, APIResponse
from services.api_services.api import get_server_uri

def get_promotions() -> list[Promotion]:
    try:
        uri = get_server_uri("/promotions")
        response = httpx.get(uri)
        json_body = response.json() 

        parsedResponse = APIResponse[Promotion].model_validate(json_body)
        return parsedResponse.data
    except Exception as e:
        print(e)
        raise e

  