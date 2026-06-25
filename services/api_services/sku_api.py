import httpx
from services.api_services.model import Sku, APIResponse
from services.api_services.api import get_server_uri

def get_skus() -> list[Sku]:
    try:
        reponse = httpx.get(get_server_uri("/skus"))
        json_body = reponse.json()

        parsedResponse = APIResponse[Sku].model_validate(json_body)
        return parsedResponse.data
    except Exception as e:
        raise e