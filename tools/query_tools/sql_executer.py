from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.db_services.database import describe_schema_for_agent, run_sql_query

DISPLAY_LIMIT = 20  # rows actually rendered to the agent, independent of the
                     # database-level max_rows cap inside run_sql_query()


class DescribeSchemaInput(BaseModel):
    """No parameters -- this tool always returns the full current schema."""


@tool("describe_schema_for_agent", args_schema=DescribeSchemaInput)
def describe_schema_tool() -> str:
    """Returns a description of the database schema -- every table, column,
    and foreign key relationship -- along with notes on how revenue and unit
    counts actually work in this schema. Call this once before writing any
    SQL query, so column names and the quantity/price behavior are correct
    rather than guessed."""
    return describe_schema_for_agent()


class ExecuteSqlQueryInput(BaseModel):
    sql: str = Field(
        ...,
        description=(
            "A single read-only SQL statement (SELECT, or WITH ... SELECT). "
            "No INSERT/UPDATE/DELETE/DDL, and no multiple statements in one "
            "call. Call describe_schema_for_agent first if you're unsure of "
            "exact table or column names."
        ),
    )


def _format_query_result(result: dict) -> str:
    if "error" in result:
        return f"Query rejected: {result['error']}"

    columns = result["columns"]
    rows = result["rows"]
    if not rows:
        return f"Query returned 0 rows. Columns: {', '.join(columns)}."

    shown = rows[:DISPLAY_LIMIT]
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join("NULL" if row[c] is None else str(row[c]) for c in columns) + " |"
        for row in shown
    ]
    table = "\n".join([header, divider] + body)

    if len(rows) > DISPLAY_LIMIT:
        note = f" (showing first {DISPLAY_LIMIT} of {len(rows)} returned -- narrow the query for the rest)"
    elif result.get("truncated"):
        note = " (result was truncated at the row limit -- narrow the query for a complete answer)"
    else:
        note = ""

    return f"Query returned {len(rows)} row(s){note}:\n\n{table}"


@tool(
    "execute_sql_query",
    args_schema=ExecuteSqlQueryInput,
    response_format="content_and_artifact",
)
def execute_sql_query_tool(sql: str):
    """Runs a single read-only SQL query against the database and returns the
    result as a table. Use this only for ad-hoc lookups, counts, and filters
    that the dedicated KPI and entity-lookup tools don't cover. Do NOT use
    this for revenue, uplift, or stockout questions -- use the KPI tools
    instead, since they encode discount and baseline logic a hand-written
    query can't reconstruct correctly."""
    result = run_sql_query(sql)
    return _format_query_result(result), result