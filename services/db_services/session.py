from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from  services.db_services.models import Base
import os 

DATABASE_URL = os.getenv("DB_CONN")
if DATABASE_URL is None:
    raise Exception("DB_CONN is not set on the environment varialbes")

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def init_db():
    Base.metadata.create_all(bind=engine)