import { formatMetric, formatPercent } from "../utils/format";

interface KpiStripProps {
  currentValue: number | null;
  lastYearValue: number | null;
  lastMonthValue: number | null;
  yesterdayValue: number | null;
  yoy: number | null;
  mom: number | null;
  dod: number | null;
  mtdValue: number | null;
}

const items = [
  { key: "current", title: "当前值", valueKey: "currentValue" },
  { key: "yesterday", title: "上个对比周期", valueKey: "yesterdayValue" },
  { key: "lastYear", title: "去年同期", valueKey: "lastYearValue" },
  { key: "lastMonth", title: "上月同期", valueKey: "lastMonthValue" },
  { key: "mtd", title: "本月累计", valueKey: "mtdValue" },
] as const;

export function KpiStrip(props: KpiStripProps) {
  const values = {
    currentValue: props.currentValue,
    yesterdayValue: props.yesterdayValue,
    lastYearValue: props.lastYearValue,
    lastMonthValue: props.lastMonthValue,
    mtdValue: props.mtdValue,
  };

  return (
    <div className="kpi-grid">
      {items.map((item) => (
        <div className="kpi-card" key={item.key}>
          <span className="kpi-label">{item.title}</span>
          <strong className="kpi-value">{formatMetric(values[item.valueKey])}</strong>
        </div>
      ))}
      <div className="kpi-card accent">
        <span className="kpi-label">同比 / 环比 / DOD</span>
        <strong className="kpi-value">
          {formatPercent(props.yoy)} / {formatPercent(props.mom)} / {formatPercent(props.dod)}
        </strong>
      </div>
    </div>
  );
}

