import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface TrendChartProps {
  rows: Array<Record<string, string | number>>;
}

export function TrendChart({ rows }: TrendChartProps) {
  if (!rows.length || !("statistics_date" in rows[0])) {
    return <div className="empty-state">当前回答没有可绘制的趋势数据</div>;
  }

  return (
    <div className="chart-shell">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="4 4" stroke="rgba(110, 129, 160, 0.2)" />
          <XAxis dataKey="statistics_date" stroke="#61708a" />
          <YAxis stroke="#61708a" />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="metric_value"
            stroke="#f97316"
            strokeWidth={3}
            dot={{ r: 3, strokeWidth: 0, fill: "#0f172a" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

