import assert from "node:assert/strict";
import test from "node:test";

const analytics = await import(new URL("../.tmp-tests/usageAnalytics.js", import.meta.url));

function entry(overrides = {}) {
  return {
    id: "event",
    occurredAt: new Date(2026, 6, 9, 10, 0).getTime(),
    kind: "product",
    title: "Produto criado",
    detail: "Camiseta",
    tone: "success",
    meta: [],
    ...overrides,
  };
}

test("summarizes only today's operation events", () => {
  const now = new Date(2026, 6, 9, 18, 0).getTime();
  const result = analytics.buildUsageAnalytics([
    entry({ id: "product-1", occurredAt: new Date(2026, 6, 9, 9, 0).getTime() }),
    entry({ id: "product-2", occurredAt: new Date(2026, 6, 9, 11, 0).getTime(), tone: "neutral" }),
    entry({ id: "import", occurredAt: new Date(2026, 6, 9, 12, 0).getTime(), kind: "import" }),
    entry({ id: "automation", occurredAt: new Date(2026, 6, 9, 13, 0).getTime(), kind: "automation", tone: "error" }),
    entry({ id: "yesterday", occurredAt: new Date(2026, 6, 8, 23, 59).getTime() }),
    entry({ id: "tomorrow", occurredAt: new Date(2026, 6, 10, 0, 0).getTime() }),
  ], now);

  assert.deepEqual({
    eventCount: result.eventCount,
    successCount: result.successCount,
    issueCount: result.issueCount,
    assistedFlowCount: result.assistedFlowCount,
    healthyRate: result.healthyRate,
    dominantCategory: result.dominantCategory,
    lastActivity: result.lastActivity,
  }, {
    eventCount: 4,
    successCount: 2,
    issueCount: 1,
    assistedFlowCount: 2,
    healthyRate: 75,
    dominantCategory: { key: "product", label: "Produtos", count: 2, share: 50 },
    lastActivity: {
      title: "Produto criado",
      occurredAt: new Date(2026, 6, 9, 13, 0).getTime(),
    },
  });
});

test("groups unknown kinds and keeps empty days neutral", () => {
  const now = new Date(2026, 6, 9, 18, 0).getTime();
  const grouped = analytics.buildUsageAnalytics([
    entry({ kind: "system" }),
    entry({ id: "grade", kind: "grade", occurredAt: new Date(2026, 6, 9, 10, 1).getTime() }),
  ], now);

  assert.equal(grouped.categories.find((item) => item.key === "other").count, 1);
  assert.equal(grouped.assistedFlowCount, 1);

  const empty = analytics.buildUsageAnalytics([], now);
  assert.equal(empty.eventCount, 0);
  assert.equal(empty.healthyRate, 0);
  assert.equal(empty.dominantCategory, null);
  assert.equal(empty.lastActivity, null);
});
