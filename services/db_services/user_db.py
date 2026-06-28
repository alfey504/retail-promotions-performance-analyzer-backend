from services.db_services.models import User
from services.db_services.session import SessionLocal
from sqlalchemy import select
def add_user(username: str, password_hash: str):
    session = SessionLocal()
    try:
        user = User(
            username = username,
            password_hash = password_hash
        )
        session.add(user)
        session.commit()
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()

def get_user_by_username(username: str) -> User | None:
    session = SessionLocal()
    statement = select(User).where(User.username == username)
    user = session.scalar(statement)
    return user

