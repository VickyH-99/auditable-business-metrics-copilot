export function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)}%`;
}

export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function getMetricUnit(metricDefinition: { aggregation: { type: string } }): string {
  if (metricDefinition.aggregation.type === "count_distinct") {
    return "台";
  }
  if (metricDefinition.aggregation.type === "sum" || metricDefinition.aggregation.type === "average_order_value") {
    return "元";
  }
  return "";
}

export function formatValueWithUnit(value: number | null | undefined, unit = ""): string {
  const formatted = formatMetric(value);
  if (formatted === "--") {
    return formatted;
  }
  return `${formatted}${unit}`;
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function toCsv(rows: Array<Record<string, unknown>>): string {
  if (!rows.length) {
    return "";
  }
  const columns = Object.keys(rows[0]);
  const lines = [
    columns.join(","),
    ...rows.map((row) =>
      columns
        .map((column) => {
          const cell = `${row[column] ?? ""}`.replace(/"/g, '""');
          return `"${cell}"`;
        })
        .join(","),
    ),
  ];
  return lines.join("\n");
}

export function downloadCsv(filename: string, rows: Array<Record<string, unknown>>) {
  const blob = new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
