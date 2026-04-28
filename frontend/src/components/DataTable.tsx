interface DataTableProps {
  rows: Array<Record<string, unknown>>;
}

export function DataTable({ rows }: DataTableProps) {
  if (!rows.length) {
    return <div className="empty-state">暂无数据</div>;
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((row, index) => (
            <tr key={`${index}-${Object.values(row).join("-")}`}>
              {columns.map((column) => (
                <td key={column}>{String(row[column] ?? "--")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
