from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os 

class Base(DeclarativeBase):
    pass

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
    import services.db_services.models
    import services.kpi_services.kpi_db.models

    Base.metadata.create_all(bind=engine)