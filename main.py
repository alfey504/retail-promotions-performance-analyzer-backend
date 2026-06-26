from services.rag_services.qdrant_services import search_query
from services.pipeline_services.pipe import pipe_data
from services.db_services.session import init_db
from services.kpi_services.incremental_uplift import get_incremental_sales_uplift
from services.kpi_services.stockout_tracer import get_stockout_inventory_trace
from services.kpi_services.post_promo_dip import get_post_promo_dip
from services.kpi_services.redemption_demographics import get_redemption_demographics
def main():
    uplift = get_redemption_demographics(2)
    print(uplift)

    # for sku_invetory_trace in  uplift.sku_traces:
    #     print(sku_invetory_trace)
  



if __name__ == "__main__":
    main()

