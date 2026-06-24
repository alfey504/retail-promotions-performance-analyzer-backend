import httpx
from api_services.model import Sale, PagedAPIResponse
from api_services.api import get_server_uri
from typing import Tuple

def get_sales_by_page(page: int) -> Tuple[int, list[Sale]]:
    try:
        response = httpx.get(get_server_uri(f"/sales?page={page}"))
        json_body = response.json()

        parsed_repsonse = PagedAPIResponse[Sale].model_validate(json_body)
        return parsed_repsonse.max_page, parsed_repsonse.data
    except Exception as e:
        raise e
    
def get_all_sales() -> list[Sale]:
    try:
        max_page, sales = get_sales_by_page(1)
        for i in range(2, max_page+1):
            _, sales_page = get_sales_by_page(i)
            sales.extend(sales_page)
            
        return sales
    except Exception as e:
        raise e