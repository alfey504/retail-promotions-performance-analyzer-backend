from services.db_services.user_db import get_user_by_username
from services.db_services.models import User
from api.utils.encryption_utils import compare_with_hash

def verify_user(username: str, password: str) -> User | None:
    user = get_user_by_username(username)
    if user is None:
        return None
    if compare_with_hash(password, user.password_hash):
        return user
    return None