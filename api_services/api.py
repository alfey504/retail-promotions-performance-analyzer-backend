SERVER_URI = "http://localhost:8080/api/v1"

def get_server_uri(route: str) -> str:
     return f"{SERVER_URI.rstrip('/')}/{route.lstrip('/')}"

   