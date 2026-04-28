import { useMemo, useState } from "react";

import type { AnswerResponse, AttributionRow } from "../types";
import {
  downloadCsv,
  formatMetric,
  formatRatio,
  formatValueWithUnit,
  getMetricUnit,
  prettyJson,
} from "../utils/format";
import { DataTable } from "./DataTable";
import { KpiStrip } from "./KpiStrip";
import { TrendChart } from "./TrendChart";

const TABS = [
  { id: "result", label: "结果" },
  { id: "code", label: "代码" },
  { id: "definition", label: "指标口径" },
  { id: "raw", label: "明细数据" },
] as const;

type TabId = (typeof TABS)[number]["id"];
type AttributionVariant = "negative" | "positive";

interface AssistantAnswerCardProps {
  answer: AnswerResponse;
}

interface AttributionSectionProps {
  rows: AttributionRow[];
  variant: AttributionVariant;
  unitLabel: string;
  overallDelta: number;
}

function getResultTitle(intent: string): string {
  if (intent === "ranking") {
    return "排名结果";
  }
  if (intent === "breakdown") {
    return "拆解结果";
  }
  if (intent === "attribution") {
    return "完整归因表";
  }
  return "结果表";
}

function getContributionLabel(variant: AttributionVariant, overallDelta: number): string {
  if (variant === "negative") {
    return overallDelta > 0 ? "负向拖累" : "负向变化";
  }
  return overallDelta > 0 ? "正向变化" : "正向抵消";
}

function getDirectionVerb(variant: AttributionVariant): string {
  return variant === "negative" ? "下降" : "增长";
}

function AttributionSection({ rows, variant, unitLabel, overallDelta }: AttributionSectionProps) {
  const title = variant === "negative" ? "下滑驱动 Top 5" : "增长抵消 Top 5";
  const contributionLabel = getContributionLabel(variant, overallDelta);
  const emptyText = variant === "negative" ? "当前没有明显的负向驱动。" : "当前没有明显的正向抵消。";

  return (
    <section className="panel attribution-panel">
      <div className="panel-title">{title}</div>
      <p className="panel-subtitle">
        {variant === "negative"
          ? overallDelta > 0
            ? "这些项目对整体增长形成拖累。"
            : "这些项目是整体下滑的主要来源。"
          : overallDelta > 0
            ? "这些项目构成了主要增量。"
            : "这些项目对整体下滑形成了抵消。"}
      </p>

      {!rows.length ? (
        <div className="empty-state">{emptyText}</div>
      ) : (
        <ol className="attribution-list">
          {rows.map((row, index) => {
            const contributionPct =
              variant === "negative" ? row.negative_contribution_pct : row.positive_offset_pct;
            return (
              <li className="attribution-item" key={`${row.dimension}-${row.member}-${index}`}>
                <div className={`attribution-rank ${variant}`}>{index + 1}</div>
                <div className="attribution-body">
                  <div className="attribution-name">
                    {row.dimension_label}：{row.member}
                  </div>
                  <div className="attribution-stats">
                    <span>当前 {formatValueWithUnit(row.current_value, unitLabel)}</span>
                    <span>对比 {formatValueWithUnit(row.compare_value, unitLabel)}</span>
                    <span>
                      {getDirectionVerb(variant)} {formatValueWithUnit(row.absolute_delta, unitLabel)}
                    </span>
                    <span>
                      {contributionLabel} {formatRatio(contributionPct)}
                    </span>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export function AssistantAnswerCard({ answer }: AssistantAnswerCardProps) {
  const [activeTab, setActiveTab] = useState<TabId>("result");
  const metadata = useMemo(
    () => [`数据源 ${answer.data_source}`, `指标 ${answer.metric_name}`, `时间 ${answer.query_plan.time_range.label}`],
    [answer],
  );
  const unitLabel = useMemo(() => getMetricUnit(answer.metric_definition), [answer.metric_definition]);
  const overallDelta = answer.attribution?.total_delta ?? 0;
  const attributionDrivers = useMemo(
    () => answer.attribution?.drivers ?? answer.attribution?.positive_offsets ?? [],
    [answer.attribution],
  );
  const attributionOffsets = useMemo(
    () => answer.attribution?.offsets ?? answer.attribution?.negative_drivers ?? [],
    [answer.attribution],
  );
  const attributionTableRows = useMemo(
    () => (answer.attribution?.dimension_impact ?? answer.attribution?.all_rows ?? []).map((row) => ({ ...row })),
    [answer.attribution],
  );

  return (
    <div className="answer-card">
      <div className="answer-header">
        <div>
          <div className="eyebrow">Auditable Answer</div>
          <h3>{answer.question}</h3>
          <div className="meta-row">
            {metadata.map((item) => (
              <span className="meta-pill" key={item}>
                {item}
              </span>
            ))}
          </div>
        </div>
        <div className="data-freshness">更新于 {answer.data_updated_at}</div>
      </div>

      <div className="tab-row">
        {TABS.map((tab) => (
          <button
            className={tab.id === activeTab ? "tab-button active" : "tab-button"}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "result" ? (
        <div className="tab-panel">
          <p className="summary-text">{answer.summary}</p>
          <KpiStrip
            currentValue={answer.current_value}
            yesterdayValue={answer.yesterday_value}
            lastYearValue={answer.last_year_value}
            lastMonthValue={answer.last_month_value}
            yoy={answer.yoy}
            mom={answer.mom}
            dod={answer.dod}
            mtdValue={answer.mtd_value}
          />

          {answer.anomaly ? (
            <div className={answer.anomaly.is_anomaly ? "anomaly-banner alert" : "anomaly-banner"}>
              <strong>异常检测</strong>
              <span>{answer.anomaly.message}</span>
            </div>
          ) : null}

          {answer.attribution ? (
            <div className="result-stack">
              <section className="panel">
                <div className="panel-title">趋势图</div>
                <TrendChart rows={answer.chart_data} />
              </section>

              <div className="attribution-grid">
                <AttributionSection
                  overallDelta={overallDelta}
                  rows={attributionOffsets}
                  unitLabel={unitLabel}
                  variant="negative"
                />
                <AttributionSection
                  overallDelta={overallDelta}
                  rows={attributionDrivers}
                  unitLabel={unitLabel}
                  variant="positive"
                />
              </div>

              <section className="panel">
                <div className="panel-title">完整归因表</div>
                <DataTable rows={attributionTableRows} />
              </section>
            </div>
          ) : (
            <div className="result-grid">
              <section className="panel">
                <div className="panel-title">趋势图</div>
                <TrendChart rows={answer.chart_data} />
              </section>
              <section className="panel">
                <div className="panel-title">{getResultTitle(answer.query_plan.intent)}</div>
                <DataTable rows={answer.table_data} />
              </section>
            </div>
          )}

          {answer.insights.length ? (
            <section className="panel">
              <div className="panel-title">洞察</div>
              <ul className="insight-list">
                {answer.insights.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}

      {activeTab === "code" ? (
        <div className="tab-panel">
          <div className="code-toolbar">
            <button
              className="secondary-button"
              onClick={() => navigator.clipboard.writeText(answer.sql_used)}
              type="button"
            >
              复制 SQL
            </button>
            <button
              className="secondary-button"
              onClick={() => navigator.clipboard.writeText(prettyJson(answer.query_plan))}
              type="button"
            >
              复制 Query Plan
            </button>
          </div>

          <section className="panel">
            <div className="panel-title">SQL</div>
            <pre className="code-block">{answer.sql_used}</pre>
          </section>

          <section className="panel">
            <div className="panel-title">Query Plan</div>
            <pre className="code-block">{prettyJson(answer.query_plan)}</pre>
          </section>

          <section className="panel">
            <div className="panel-title">Pandas 校验样例</div>
            <pre className="code-block">{`import pandas as pd\n\ndf = pd.DataFrame(raw_data)\nprint(df.head())`}</pre>
          </section>
        </div>
      ) : null}

      {activeTab === "definition" ? (
        <div className="tab-panel">
          <div className="definition-grid">
            <div className="definition-item">
              <span>指标名称</span>
              <strong>{answer.metric_definition.name_zh}</strong>
            </div>
            <div className="definition-item">
              <span>英文名</span>
              <strong>{answer.metric_definition.name_en}</strong>
            </div>
            <div className="definition-item">
              <span>业务含义</span>
              <strong>{answer.metric_definition.description}</strong>
            </div>
            <div className="definition-item">
              <span>公式</span>
              <strong>{answer.metric_definition.formula}</strong>
            </div>
            <div className="definition-item">
              <span>默认时间字段</span>
              <strong>{answer.metric_definition.time_field}</strong>
            </div>
            <div className="definition-item">
              <span>默认过滤</span>
              <strong>{prettyJson(answer.metric_definition.default_filters)}</strong>
            </div>
            <div className="definition-item">
              <span>允许维度</span>
              <strong>{answer.metric_definition.allowed_dimensions.join(", ")}</strong>
            </div>
            <div className="definition-item">
              <span>Owner / 更新频率</span>
              <strong>
                {answer.metric_definition.owner} / {answer.metric_definition.update_frequency}
              </strong>
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === "raw" ? (
        <div className="tab-panel">
          <div className="code-toolbar">
            <button
              className="secondary-button"
              onClick={() => downloadCsv(`${answer.metric}-raw-data.csv`, answer.raw_data)}
              type="button"
            >
              下载 CSV
            </button>
            <span className="raw-counter">返回 {formatMetric(answer.raw_data.length)} 行</span>
          </div>

          {answer.raw_data_sql ? (
            <section className="panel">
              <div className="panel-title">Raw Data SQL</div>
              <pre className="code-block">{answer.raw_data_sql}</pre>
            </section>
          ) : null}
          <section className="panel">
            <div className="panel-title">明细数据</div>
            <DataTable rows={answer.raw_data} />
          </section>
        </div>
      ) : null}
    </div>
  );
}
