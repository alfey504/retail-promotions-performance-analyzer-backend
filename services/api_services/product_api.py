import httpx
from services.api_services.model import Product, APIResponse

def get_products() -> list[Product]:
    try:
        response = httpx.get("http://localhost:8080/api/v1/products")
        json_body = response.json() 

        parsedResponse = APIResponse[Product].model_validate(json_body)
        return parsedResponse.data
    except Exception as e:
        print(e)
        raise e

  