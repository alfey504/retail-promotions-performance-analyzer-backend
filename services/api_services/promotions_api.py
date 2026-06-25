import httpx
from services.api_services.model import Promotion, APIResponse

def get_promotions() -> list[Promotion]:
    try:
        response = httpx.get("http://localhost:8080/api/v1/promotions")
        json_body = response.json() 

        parsedResponse = APIResponse[Promotion].model_validate(json_body)
        return parsedResponse.data
    except Exception as e:
        print(e)
        raise e

  