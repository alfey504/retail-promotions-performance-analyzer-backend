from fastapi import FastAPI, APIRouter
from api.routes.user_routes import user_router
from api.routes.promotion_routes import promotions_router
from api.routes.conversation_routes import conversation_router
from api.routes.data_routes import data_router


app = FastAPI()

app_v1 = APIRouter(prefix="/api/v1")
app_v1.include_router(user_router)
app_v1.include_router(promotions_router)
app_v1.include_router(conversation_router)
app_v1.include_router(data_router)

app.include_router(app_v1)

@app.get(path="/")
def hello_world():
    return {
        "hello": "world"
    }


def get_app() -> FastAPI:
    return app

