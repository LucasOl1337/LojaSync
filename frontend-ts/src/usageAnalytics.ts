import type { OperationDiaryEntry } from "./uiFormatting";

export type UsageAnalyticsCategoryKey = "product" | "import" | "automation" | "grade" | "other";

export type UsageAnalyticsCategory = {
  key: UsageAnalyticsCategoryKey;
  label: string;
  count: number;
  share: number;
};

export type UsageAnalyticsSummary = {
  eventCount: number;
  successCount: number;
  issueCount: number;
  assistedFlowCount: number;
  healthyRate: number;
  dominantCategory: UsageAnalyticsCategory | null;
  categories: UsageAnalyticsCategory[];
  lastActivity: Pick<OperationDiaryEntry, "title" | "occurredAt"> | null;
};

const CATEGORY_DEFINITIONS: Array<{
  key: UsageAnalyticsCategoryKey;
  label: string;
}> = [
  { key: "product", label: "Produtos" },
  { key: "import", label: "Importações" },
  { key: "automation", label: "Automação" },
  { key: "grade", label: "Grades" },
  { key: "other", label: "Outras" },
];

function normalizeCategory(kind: unknown): UsageAnalyticsCategoryKey {
  const normalized = String(kind || "").trim().toLowerCase();
  return CATEGORY_DEFINITIONS.some((category) => category.key === normalized)
    ? normalized as UsageAnalyticsCategoryKey
    : "other";
}

function getLocalDayBounds(now: number) {
  const date = new Date(now);
  const start = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const endDate = new Date(start);
  endDate.setDate(endDate.getDate() + 1);
  return { start, end: endDate.getTime() };
}

export function buildUsageAnalytics(
  entries: OperationDiaryEntry[],
  now = Date.now(),
): UsageAnalyticsSummary {
  const safeNow = Number.isFinite(now) ? now : Date.now();
  const { start, end } = getLocalDayBounds(safeNow);
  const todayEntries = entries
    .filter((entry) => Number.isFinite(entry.occurredAt) && entry.occurredAt >= start && entry.occurredAt < end)
    .sort((left, right) => right.occurredAt - left.occurredAt);
  const eventCount = todayEntries.length;
  const counts = new Map<UsageAnalyticsCategoryKey, number>();

  todayEntries.forEach((entry) => {
    const category = normalizeCategory(entry.kind);
    counts.set(category, (counts.get(category) || 0) + 1);
  });

  const categories = CATEGORY_DEFINITIONS.map((category) => {
    const count = counts.get(category.key) || 0;
    return {
      ...category,
      count,
      share: eventCount ? Math.round((count / eventCount) * 100) : 0,
    };
  });
  const dominantCategory = eventCount
    ? categories.reduce((dominant, category) => category.count > dominant.count ? category : dominant)
    : null;
  const issueCount = todayEntries.filter((entry) => entry.tone === "error").length;

  return {
    eventCount,
    successCount: todayEntries.filter((entry) => entry.tone === "success").length,
    issueCount,
    assistedFlowCount: todayEntries.filter((entry) => {
      const category = normalizeCategory(entry.kind);
      return category === "import" || category === "automation" || category === "grade";
    }).length,
    healthyRate: eventCount ? Math.round(((eventCount - issueCount) / eventCount) * 100) : 0,
    dominantCategory,
    categories,
    lastActivity: todayEntries[0]
      ? { title: todayEntries[0].title, occurredAt: todayEntries[0].occurredAt }
      : null,
  };
}
