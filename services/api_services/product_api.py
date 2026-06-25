import httpx
from services.api_services.model import Product, APIResponse
from services.api_services.api import get_server_uri
def get_products() -> list[Product]:
    try:
        uri = get_server_uri("/products")
        response = httpx.get(uri)
        json_body = response.json() 

        parsedResponse = APIResponse[Product].model_validate(json_body)
        return parsedResponse.data
    except Exception as e:
        print(e)
        raise e

  