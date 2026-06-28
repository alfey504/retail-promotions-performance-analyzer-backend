from api.utils.encryption_utils import hash_password
from services.db_services.user_db import add_user
from services.db_services.models import User

def create_user(username: str, password: str):
    try:
        hashed_password = hash_password(password)
        add_user(username, hashed_password)
    except Exception as e:
        print(e)
        raise e
