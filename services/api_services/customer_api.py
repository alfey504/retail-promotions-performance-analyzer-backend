import httpx
from services.api_services.model import Customer, APIResponse
from services.api_services.api import get_server_uri

def get_customers() -> list[Customer]:
    try:
        repsonse = httpx.get(get_server_uri("/customers"))
        json_body = repsonse.json()

        parsed_response = APIResponse[Customer].model_validate(json_body)
        return parsed_response.data
    except Exception as e:
        raise e
