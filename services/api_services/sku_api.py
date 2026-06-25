import httpx
from services.api_services.model import SKU, APIResponse
from services.api_services.api import get_server_uri

def get_skus() -> list[SKU]:
    try:
        reponse = httpx.get(get_server_uri("/skus"))
        json_body = reponse.json()

        parsedResponse = APIResponse[SKU].model_validate(json_body)
        return parsedResponse.data
    except Exception as e:
        raise e