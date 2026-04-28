from __future__ import annotations

from datetime import date

from app.schemas.api import MetricDefinition

DETAIL_COLUMNS = [
    "order_id",
    "statistics_date",
    "delivery_time",
    "channel",
    "region_group",
    "region",
    "city",
    "store_id",
    "store_name",
    "sales_person_id",
    "sales_person_name",
    "business_type",
    "order_status",
    "sales_amount",
    "gross_profit",
    "customer_id",
    "customer_type",
    "created_at",
    "updated_at",
]


def _quote(value: str | int | float | date) -> str:
    if isinstance(value, date):
        return f"'{value.isoformat()}'"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def metric_expression(metric: MetricDefinition) -> str:
    aggregation_type = metric.aggregation.type
    field = metric.aggregation.field
    if aggregation_type == "count_distinct":
        return f"COUNT(DISTINCT {field})"
    if aggregation_type == "sum":
        return f"SUM({field})"
    if aggregation_type == "average_order_value":
        return "SUM(sales_amount) / NULLIF(COUNT(DISTINCT order_id), 0)"
    raise ValueError(f"Unsupported aggregation type: {aggregation_type}")


def merge_filters(metric: MetricDefinition, filters: dict) -> dict:
    merged = dict(metric.default_filters)
    merged.update(filters)
    return merged


def build_where_clause(metric: MetricDefinition, start_date: date, end_date: date, filters: dict) -> str:
    clauses = [
        f"{metric.time_field} BETWEEN {_quote(start_date)} AND {_quote(end_date)}",
    ]
    for field, value in merge_filters(metric, filters).items():
        if isinstance(value, list):
            quoted = ", ".join(_quote(item) for item in value)
            clauses.append(f"{field} IN ({quoted})")
        else:
            clauses.append(f"{field} = {_quote(value)}")
    return " AND\n  ".join(clauses)


def build_aggregate_sql(
    metric: MetricDefinition,
    start_date: date,
    end_date: date,
    filters: dict,
    dimensions: list[str] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
    title: str | None = None,
) -> str:
    dimensions = dimensions or []
    select_dimensions = ",\n    ".join(dimensions)
    group_by_clause = ""
    if dimensions:
        group_by_clause = "\nGROUP BY " + ", ".join(dimensions)
    order_clause = f"\nORDER BY {order_by}" if order_by else ""
    limit_clause = f"\nLIMIT {limit}" if limit else ""
    select_prefix = f"{select_dimensions},\n    " if select_dimensions else ""
    comment = f"-- {title}\n" if title else ""
    return (
        f"{comment}SELECT\n"
        f"    {select_prefix}{metric_expression(metric)} AS metric_value\n"
        f"FROM {metric.table}\n"
        f"WHERE {build_where_clause(metric, start_date, end_date, filters)}"
        f"{group_by_clause}{order_clause}{limit_clause};"
    )


def build_attribution_sql(
    metric: MetricDefinition,
    current_start_date: date,
    current_end_date: date,
    compare_start_date: date,
    compare_end_date: date,
    filters: dict,
    dimension: str,
    title: str | None = None,
) -> str:
    current_where = build_where_clause(metric, current_start_date, current_end_date, filters).replace("\n", "\n        ")
    compare_where = build_where_clause(metric, compare_start_date, compare_end_date, filters).replace("\n", "\n        ")
    expression = metric_expression(metric)
    comment = f"-- {title}\n" if title else ""
    return (
        f"{comment}WITH current_period AS (\n"
        "    SELECT\n"
        f"        {dimension} AS dimension_member,\n"
        f"        {expression} AS current_value\n"
        f"    FROM {metric.table}\n"
        f"    WHERE {current_where}\n"
        f"    GROUP BY {dimension}\n"
        "),\n"
        "compare_period AS (\n"
        "    SELECT\n"
        f"        {dimension} AS dimension_member,\n"
        f"        {expression} AS compare_value\n"
        f"    FROM {metric.table}\n"
        f"    WHERE {compare_where}\n"
        f"    GROUP BY {dimension}\n"
        "),\n"
        "joined AS (\n"
        "    SELECT\n"
        "        current_period.dimension_member,\n"
        "        current_period.current_value,\n"
        "        COALESCE(compare_period.compare_value, 0) AS compare_value\n"
        "    FROM current_period\n"
        "    LEFT JOIN compare_period\n"
        "      ON current_period.dimension_member = compare_period.dimension_member\n"
        "    UNION ALL\n"
        "    SELECT\n"
        "        compare_period.dimension_member,\n"
        "        0 AS current_value,\n"
        "        compare_period.compare_value\n"
        "    FROM compare_period\n"
        "    LEFT JOIN current_period\n"
        "      ON current_period.dimension_member = compare_period.dimension_member\n"
        "    WHERE current_period.dimension_member IS NULL\n"
        ")\n"
        "SELECT\n"
        "    dimension_member,\n"
        "    current_value,\n"
        "    compare_value,\n"
        "    current_value - compare_value AS delta\n"
        "FROM joined\n"
        "ORDER BY ABS(current_value - compare_value) DESC;"
    )


def build_detail_sql(
    metric: MetricDefinition,
    start_date: date,
    end_date: date,
    filters: dict,
    limit: int = 200,
) -> str:
    columns = ",\n    ".join(DETAIL_COLUMNS)
    return (
        "-- 原始明细数据\n"
        "SELECT\n"
        f"    {columns}\n"
        f"FROM {metric.table}\n"
        f"WHERE {build_where_clause(metric, start_date, end_date, filters)}\n"
        "ORDER BY statistics_date DESC, delivery_time DESC\n"
        f"LIMIT {limit};"
    )
