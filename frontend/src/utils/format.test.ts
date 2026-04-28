import { describe, expect, it } from "vitest";

import { formatMetric, formatPercent, toCsv } from "./format";

describe("format utils", () => {
  it("formats metrics", () => {
    expect(formatMetric(12345.67)).toBe("12,345.67");
  });

  it("formats percentages", () => {
    expect(formatPercent(0.123)).toBe("+12.3%");
  });

  it("converts rows to csv", () => {
    expect(toCsv([{ city: "上海", value: 12 }])).toContain("city,value");
  });
});

