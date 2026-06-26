from services.rag_services.qdrant_services import search_query
from services.pipeline_services.pipe import pipe_data
from services.db_services.session import init_db
from services.kpi_services.incremental_uplift import get_incremental_sales_uplift
from services.kpi_services.stockout_tracer import get_stockout_inventory_trace

def main():
    uplift = get_stockout_inventory_trace(2)
    print(uplift)

    for sku_invetory_trace in  uplift.sku_traces:
        print(sku_invetory_trace)
  



if __name__ == "__main__":
    main()

