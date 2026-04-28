import type {
  AnswerResponse,
  AttributionPayload,
  AttributionRow,
  ChatResponse,
  HealthResponse,
  MetricDefinition,
} from "../types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api";
const API_BASE_URLS = Array.from(
  new Set(
    [import.meta.env.VITE_API_BASE_URL, DEFAULT_API_BASE_URL, "http://localhost:8000/api"]
      .filter((value): value is string => Boolean(value))
      .map((value) => value.replace(/\/$/, "")),
  ),
);

const FALLBACK_METRIC_DEFINITION: MetricDefinition = {
  metric_id: "fallback_mock",
  name_zh: "Fallback Mock",
  name_en: "Fallback Mock",
  description: "Client-side fallback response used when the chat API is unavailable.",
  table: "fact_delivery_orders",
  time_field: "statistics_date",
  aggregation: {
    type: "count_distinct",
    field: "order_id",
  },
  default_filters: {},
  allowed_dimensions: [],
  formula: "N/A",
  owner: "frontend",
  update_frequency: "ad hoc",
  aliases: [],
};

function isAnswerResponse(response: ChatResponse): response is AnswerResponse {
  return response.type === "answer";
}

function normalizeAttributionRows(rows: unknown): AttributionRow[] {
  if (!Array.isArray(rows)) {
    return [];
  }

  return rows.map((row) => {
    const item = (row ?? {}) as Partial<AttributionRow>;
    const delta = typeof item.delta === "number" ? item.delta : null;

    return {
      dimension: item.dimension ?? "unknown_dimension",
      dimension_label: item.dimension_label ?? item.dimension ?? "Unknown dimension",
      member: item.member ?? "--",
      current_value: item.current_value ?? null,
      compare_value: item.compare_value ?? null,
      delta,
      absolute_delta: item.absolute_delta ?? (delta === null ? null : Math.abs(delta)),
      negative_contribution_pct: item.negative_contribution_pct ?? null,
      positive_offset_pct: item.positive_offset_pct ?? null,
      net_contribution_pct: item.net_contribution_pct ?? null,
      direction:
        item.direction ??
        (delta === null ? "neutral" : delta < 0 ? "negative_driver" : delta > 0 ? "positive_offset" : "neutral"),
    };
  });
}

function normalizeAttribution(attribution: Partial<AttributionPayload> | null | undefined): AttributionPayload | null {
  if (!attribution) {
    return null;
  }

  const drivers = normalizeAttributionRows(attribution.drivers ?? attribution.positive_offsets);
  const offsets = normalizeAttributionRows(attribution.offsets ?? attribution.negative_drivers);
  const dimensionImpact = normalizeAttributionRows(attribution.dimension_impact ?? attribution.all_rows);

  return {
    current_total: attribution.current_total ?? null,
    compare_total: attribution.compare_total ?? null,
    total_delta: attribution.total_delta ?? null,
    drivers,
    offsets,
    dimension_impact: dimensionImpact,
    negative_drivers: normalizeAttributionRows(attribution.negative_drivers ?? offsets),
    positive_offsets: normalizeAttributionRows(attribution.positive_offsets ?? drivers),
    neutral_items: normalizeAttributionRows(attribution.neutral_items),
    all_rows: normalizeAttributionRows(attribution.all_rows ?? dimensionImpact),
  };
}

function normalizeChatResponse(response: ChatResponse): ChatResponse {
  if (!isAnswerResponse(response)) {
    return response;
  }

  return {
    ...response,
    insights: Array.isArray(response.insights) ? response.insights : [],
    chart_data: Array.isArray(response.chart_data) ? response.chart_data : [],
    table_data: Array.isArray(response.table_data) ? response.table_data : [],
    raw_data: Array.isArray(response.raw_data) ? response.raw_data : [],
    attribution: normalizeAttribution(response.attribution),
  };
}

function inferFallbackIntent(message: string): "summary" | "trend" | "ranking" | "breakdown" | "attribution" {
  const normalized = message.toLowerCase();

  if (/(why|reason|attribution|driver|offset|原因|归因|下滑|下降)/i.test(normalized)) {
    return "attribution";
  }
  if (/(trend|走势|趋势)/i.test(normalized)) {
    return "trend";
  }
  if (/(rank|top|排名)/i.test(normalized)) {
    return "ranking";
  }
  if (/(breakdown|split|按|拆解)/i.test(normalized)) {
    return "breakdown";
  }
  return "summary";
}

function buildFallbackChatResponse(message: string, error: unknown): AnswerResponse {
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const intent = inferFallbackIntent(message);
  const detail = error instanceof Error ? error.message : "Chat API unavailable.";

  return normalizeChatResponse({
    type: "answer",
    question: message,
    summary: `Chat API unavailable, showing fallback_mock so the UI stays usable. ${detail}`,
    metric: "fallback_mock",
    metric_name: "Fallback Mock",
    current_value: null,
    yesterday_value: null,
    last_year_value: null,
    last_month_value: null,
    yoy: null,
    mom: null,
    dod: null,
    mtd_value: null,
    anomaly: null,
    insights: ["This is a client-side fallback response returned because the chat API request failed."],
    query_plan: {
      intent,
      metric: "fallback_mock",
      time_range: {
        mode: "fallback_mock",
        start_date: today,
        end_date: today,
        label: "fallback_mock",
      },
      comparison: null,
      dimensions: [],
      filters: {},
      limit: 10,
    },
    sql_used: "-- fallback_mock: chat API unavailable",
    metric_definition: FALLBACK_METRIC_DEFINITION,
    chart_data: [],
    table_data: [],
    raw_data: [],
    raw_data_sql: "-- fallback_mock: raw data unavailable",
    attribution:
      intent === "attribution"
        ? {
            current_total: null,
            compare_total: null,
            total_delta: null,
            drivers: [],
            offsets: [],
            dimension_impact: [],
          }
        : null,
    data_updated_at: now.toISOString(),
    data_source: "fallback_mock",
    conversation_state: {
      unresolved_query: null,
      last_query_plan: null,
    },
  }) as AnswerResponse;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let lastError: unknown;

  for (const apiBaseUrl of API_BASE_URLS) {
    try {
      const response = await fetch(`${apiBaseUrl}${path}`, {
        headers: {
          "Content-Type": "application/json",
        },
        ...init,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Request failed: ${response.status}`);
      }

      return response.json() as Promise<T>;
    } catch (error) {
      lastError = error;
      const isRetryableNetworkFailure = error instanceof TypeError && apiBaseUrl !== API_BASE_URLS.at(-1);
      if (isRetryableNetworkFailure) {
        continue;
      }
      throw error;
    }
  }

  throw (lastError instanceof Error ? lastError : new Error("Request failed"));
}

export async function postChat(sessionId: string, message: string): Promise<ChatResponse> {
  try {
    const response = await request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        message,
      }),
    });

    return normalizeChatResponse(response);
  } catch (error) {
    return buildFallbackChatResponse(message, error);
  }
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function fetchCatalog(): Promise<MetricDefinition[]> {
  const payload = await request<{ metrics: MetricDefinition[] }>("/metrics/catalog");
  return payload.metrics;
}
