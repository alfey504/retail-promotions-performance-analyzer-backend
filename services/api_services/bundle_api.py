import httpx
from api_services.model import Bundle, APIResponse
from api_services.api import get_server_uri

def get_bundles() -> list[Bundle]:
    try:
        repsonse = httpx.get(get_server_uri("/bundles"))
        json_body = repsonse.json()

        parsed_response = APIResponse[Bundle].model_validate(json_body)
        return parsed_response.data
    except Exception as e:
        raise e