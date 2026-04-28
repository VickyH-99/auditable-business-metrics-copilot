import { afterEach, describe, expect, it, vi } from "vitest";

import { postChat } from "./client";

const metricDefinition = {
  metric_id: "car_sales_count",
  name_zh: "Car Sales",
  name_en: "Car Sales",
  description: "Daily delivered car sales",
  table: "fact_delivery_orders",
  time_field: "statistics_date",
  aggregation: {
    type: "count_distinct",
    field: "order_id",
  },
  default_filters: {},
  allowed_dimensions: ["city"],
  formula: "COUNT(DISTINCT order_id)",
  owner: "bi",
  update_frequency: "daily",
  aliases: [],
};

const positiveRow = {
  dimension: "city",
  dimension_label: "City",
  member: "Toronto",
  current_value: 14,
  compare_value: 10,
  delta: 4,
  absolute_delta: 4,
  negative_contribution_pct: null,
  positive_offset_pct: 1,
  net_contribution_pct: 1,
  direction: "positive_offset" as const,
};

const negativeRow = {
  dimension: "city",
  dimension_label: "City",
  member: "Montreal",
  current_value: 6,
  compare_value: 9,
  delta: -3,
  absolute_delta: 3,
  negative_contribution_pct: 1,
  positive_offset_pct: null,
  net_contribution_pct: -0.75,
  direction: "negative_driver" as const,
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("postChat", () => {
  it("normalizes legacy attribution keys into the current UI contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          type: "answer",
          question: "Why did sales change?",
          summary: "Sales increased.",
          metric: "car_sales_count",
          metric_name: "Car Sales",
          current_value: 20,
          yesterday_value: 18,
          last_year_value: 16,
          last_month_value: 17,
          yoy: 0.25,
          mom: 0.18,
          dod: 0.11,
          mtd_value: 240,
          anomaly: null,
          insights: [],
          query_plan: {
            intent: "attribution",
            metric: "car_sales_count",
            time_range: {
              mode: "today",
              start_date: "2026-04-27",
              end_date: "2026-04-27",
              label: "today",
            },
            comparison: "dod",
            dimensions: [],
            filters: {},
            limit: 10,
          },
          sql_used: "select 1",
          metric_definition: metricDefinition,
          chart_data: [],
          table_data: [],
          raw_data: [],
          raw_data_sql: null,
          attribution: {
            current_total: 20,
            compare_total: 17,
            total_delta: 3,
            positive_offsets: [positiveRow],
            negative_drivers: [negativeRow],
            all_rows: [positiveRow, negativeRow],
            neutral_items: [],
          },
          data_updated_at: "2026-04-27T00:00:00",
          data_source: "mock_database",
          conversation_state: {
            unresolved_query: null,
            last_query_plan: null,
          },
        }),
      }),
    );

    const response = await postChat("session-1", "Why did sales change?");

    expect(response.type).toBe("answer");
    if (response.type !== "answer") {
      return;
    }

    expect(response.attribution?.drivers).toEqual([positiveRow]);
    expect(response.attribution?.offsets).toEqual([negativeRow]);
    expect(response.attribution?.dimension_impact).toEqual([positiveRow, negativeRow]);
    expect(response.attribution?.positive_offsets).toEqual([positiveRow]);
    expect(response.attribution?.negative_drivers).toEqual([negativeRow]);
  });

  it("returns a fallback_mock answer when the chat API cannot be reached", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const response = await postChat("session-2", "Why did sales drop?");

    expect(fetchMock).toHaveBeenCalled();
    expect(response.type).toBe("answer");
    if (response.type !== "answer") {
      return;
    }

    expect(response.data_source).toBe("fallback_mock");
    expect(response.summary).toContain("fallback_mock");
    expect(response.query_plan.intent).toBe("attribution");
    expect(response.attribution?.drivers).toEqual([]);
    expect(response.attribution?.offsets).toEqual([]);
    expect(response.attribution?.dimension_impact).toEqual([]);
  });
});
