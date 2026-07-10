import { buildProductQuickFilterOptions } from "./productFilters.js";
import type { ProductQuickFilter } from "./productFilters";
import { computeCurrentTotals } from "./productPricing.js";
import type { Product } from "./types";

export type CatalogOverviewIssue = {
  filter: Exclude<ProductQuickFilter, "all" | "recent_imports" | "needs_review">;
  label: string;
  count: number;
  tone: "warning" | "error";
};

export type CatalogOverview = {
  totalProducts: number;
  totalUnits: number;
  costValue: number;
  saleValue: number;
  grossPotential: number;
  grossReturnPercent: number;
  readyCount: number;
  reviewCount: number;
  readinessPercent: number;
  issues: CatalogOverviewIssue[];
};

const ISSUE_FILTERS: CatalogOverviewIssue["filter"][] = [
  "grade_mismatch",
  "pending_grades",
  "missing_code",
  "missing_brand",
  "missing_category",
];

export function buildCatalogOverview(products: Product[], marginPercentual: number): CatalogOverview {
  const totals = computeCurrentTotals(products, marginPercentual);
  const options = buildProductQuickFilterOptions(products);
  const counts = new Map(options.map((option) => [option.key, option.count]));
  const reviewCount = counts.get("needs_review") || 0;
  const grossPotential = Math.max(0, totals.venda - totals.custo);

  const issues = ISSUE_FILTERS
    .map((filter) => ({
      filter,
      label: options.find((option) => option.key === filter)?.label || filter,
      count: counts.get(filter) || 0,
      tone: filter === "grade_mismatch" ? "error" as const : "warning" as const,
    }))
    .filter((issue) => issue.count > 0)
    .sort((left, right) => right.count - left.count);

  return {
    totalProducts: products.length,
    totalUnits: totals.quantidade,
    costValue: totals.custo,
    saleValue: totals.venda,
    grossPotential,
    grossReturnPercent: totals.custo > 0 ? (grossPotential / totals.custo) * 100 : 0,
    readyCount: Math.max(0, products.length - reviewCount),
    reviewCount,
    readinessPercent: products.length > 0
      ? Math.round(((products.length - reviewCount) / products.length) * 100)
      : 0,
    issues,
  };
}
