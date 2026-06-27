#kpi related tools  
from tools.kpi_tools.discount_efficiency_tool import discount_efficiency_tool
from tools.kpi_tools.incremental_uplift_calculator_tool import incremental_sales_uplift_tool
from tools.kpi_tools.post_promo_dip_tool import post_promo_dip_tool
from tools.kpi_tools.redemption_demographic_tool import redemption_demographics_tool
from tools.kpi_tools.stockout_tracer_tool import stockout_inventory_trace_tool

#query related tools
from tools.query_tools.query_by_id import customer_lookup_tool
from tools.query_tools.query_by_id import sku_lookup_tool
from tools.query_tools.query_by_id import product_lookup_tool
from tools.query_tools.query_by_id import promotion_lookup_tool

from tools.query_tools.sql_executer import describe_schema_tool, execute_sql_query_tool

#rag tools
from tools.rag_tools.rag_tools import semantic_search_tool

kpi_tools = [discount_efficiency_tool, incremental_sales_uplift_tool, post_promo_dip_tool, redemption_demographics_tool, stockout_inventory_trace_tool]
query_tools =  [customer_lookup_tool, sku_lookup_tool, product_lookup_tool, promotion_lookup_tool, describe_schema_tool, execute_sql_query_tool]
rag_tools = [semantic_search_tool]

tools = [*kpi_tools, *query_tools, *rag_tools]