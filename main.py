from services.db_services.session import init_db
from services.kpi_services.historic_kpi_calculators.historic_uplift import historic_uplift
def main():
    init_db()
    uplifts = historic_uplift()
    print(uplifts)



if __name__ == "__main__":
    main()

