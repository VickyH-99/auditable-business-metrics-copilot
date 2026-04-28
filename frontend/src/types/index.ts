export interface MetricDefinition {
  metric_id: string;
  name_zh: string;
  name_en: string;
  description: string;
  table: string;
  time_field: string;
  aggregation: {
    type: string;
    field: string;
  };
  default_filters: Record<string, string>;
  allowed_dimensions: string[];
  formula: string;
  owner: string;
  update_frequency: string;
  aliases: string[];
}

export interface QueryPlanPayload {
  intent: string;
  metric: string;
  time_range: {
    mode: string;
    start_date: string;
    end_date: string;
    label: string;
  };
  comparison: string | null;
  dimensions: string[];
  filters: Record<string, string | string[]>;
  limit: number;
}

export interface ConversationState {
  unresolved_query: unknown;
  last_query_plan: QueryPlanPayload | null;
}

export interface ClarificationResponse {
  type: "clarification";
  message: string;
  options: string[];
  conversation_state: ConversationState;
}

export interface AnswerResponse {
  type: "answer";
  question: string;
  summary: string;
  metric: string;
  metric_name: string;
  current_value: number | null;
  yesterday_value: number | null;
  last_year_value: number | null;
  last_month_value: number | null;
  yoy: number | null;
  mom: number | null;
  dod: number | null;
  mtd_value: number | null;
  anomaly: {
    baseline: number;
    z_score: number;
    is_anomaly: boolean;
    message: string;
  } | null;
  insights: string[];
  query_plan: QueryPlanPayload;
  sql_used: string;
  metric_definition: MetricDefinition;
  chart_data: Array<Record<string, string | number>>;
  table_data: Array<Record<string, string | number | null>>;
  raw_data: Array<Record<string, string | number | null>>;
  raw_data_sql?: string | null;
  attribution?: AttributionPayload | null;
  data_updated_at: string;
  data_source: string;
  conversation_state?: ConversationState;
}

export interface AttributionRow {
  dimension: string;
  dimension_label: string;
  member: string;
  current_value: number | null;
  compare_value: number | null;
  delta: number | null;
  absolute_delta: number | null;
  negative_contribution_pct: number | null;
  positive_offset_pct: number | null;
  net_contribution_pct: number | null;
  direction: "negative_driver" | "positive_offset" | "neutral";
}

export interface AttributionPayload {
  current_total: number | null;
  compare_total: number | null;
  total_delta: number | null;
  drivers: AttributionRow[];
  offsets: AttributionRow[];
  dimension_impact: AttributionRow[];
  negative_drivers?: AttributionRow[];
  positive_offsets?: AttributionRow[];
  neutral_items?: AttributionRow[];
  all_rows?: AttributionRow[];
}

export type ChatResponse = ClarificationResponse | AnswerResponse;

export interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
  response?: ChatResponse;
}

export interface HealthResponse {
  status: string;
  data_source: string;
  database_available: boolean;
  metrics_loaded: number;
  data_updated_at: string | null;
}
