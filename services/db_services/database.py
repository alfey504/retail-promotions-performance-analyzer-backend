from services.db_services.session import engine, SessionLocal
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

def describe_schema_for_agent() -> str:
    insp = inspect(engine)
    lines = []
    for table_name in insp.get_table_names():
        cols = insp.get_columns(table_name)
        fks = insp.get_foreign_keys(table_name)
        fk_by_col = {fk["constrained_columns"][0]: fk for fk in fks if fk["constrained_columns"]}
 
        col_descs = []
        for c in cols:
            piece = f"{c['name']} {c['type']}"
            if c["name"] in fk_by_col:
                fk = fk_by_col[c["name"]]
                piece += f" -> {fk['referred_table']}.{fk['referred_columns'][0]}"
            col_descs.append(piece)
        lines.append(f"{table_name}({', '.join(col_descs)})")
 
    schema_text = "\n".join(lines)
    return (
        "DATABASE SCHEMA:\n" + schema_text + "\n\n"
        "IMPORTANT: sku_sales and bundle_sales store quantity only, not the price "
        "actually paid. Do not compute revenue with a raw SUM(quantity * price) "
        "query -- it ignores promotional discounts entirely and will be wrong for "
        "any promoted period. For anything involving revenue, uplift, stockouts, "
        "or promotion classification, use the dedicated KPI tools instead of "
        "writing SQL directly. This tool is for lookups, counts, and filters only."
    )
 
_ALLOWED_PREFIXES = ("select", "with")
 
def is_read_only(sql: str) -> bool:
    cleaned = sql.strip().rstrip(";").strip().lower()
    if ";" in cleaned:
        return False  # no stacked statements
    return cleaned.startswith(_ALLOWED_PREFIXES)
 
 
def run_sql_query(sql: str, max_rows: int = 200) -> dict:
    session = SessionLocal()
    if not is_read_only(sql):
        return {
            "error": "Only single SELECT (or WITH ... SELECT) statements are "
                      "permitted through this tool.",
            "rejected_sql": sql,
        }
 
    result = session.execute(text(sql))
    columns = list(result.keys())
    rows = result.fetchmany(max_rows)
    return {
        "columns": columns,
        "rows": [dict(zip(columns, row)) for row in rows],
        "truncated": len(rows) == max_rows,
    }


def add_to_db(models : list[DeclarativeBase]):
    session = SessionLocal()
    try:
        session.add_all(models)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()