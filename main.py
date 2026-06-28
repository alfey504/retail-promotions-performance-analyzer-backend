from services.db_services.session import init_db
from services.kpi_services.historic_kpi_calculators.historic_uplift import historic_uplift
from api.user_services.create_user import create_user

def main():
    init_db()
    create_user("tempUser", "user@123")


if __name__ == "__main__":
    main()

