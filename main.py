from services.db_services.session import init_db
from services.kpi_services.historic_kpi_calculators.historic_uplift import historic_uplift
from api.user_services.create_user import create_user
from api.api import get_app
import uvicorn

def main():
    init_db()
    app = get_app()

    uvicorn.run(app, env_file=".emv")
    


if __name__ == "__main__":
    main()

