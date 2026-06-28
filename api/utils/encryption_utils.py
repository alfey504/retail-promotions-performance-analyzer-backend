from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def compare_with_hash(password: str, hash: str) -> bool:
    return pwd_context.verify(password, hash)