import type { Product } from "./types";

const PRODUCT_QUICK_FILTER_DEFINITIONS = [
  { key: "all", label: "Todos" },
  { key: "needs_review", label: "Revisar" },
  { key: "pending_grades", label: "Grades pendentes" },
  { key: "recent_imports", label: "Importados" },
  { key: "missing_brand", label: "Sem marca" },
  { key: "missing_code", label: "Sem código" },
  { key: "missing_category", label: "Sem categoria" },
  { key: "grade_mismatch", label: "Divergencia" },
] as const;

export type ProductQuickFilter = (typeof PRODUCT_QUICK_FILTER_DEFINITIONS)[number]["key"];

export type ProductQuickFilterOption = {
  key: ProductQuickFilter;
  label: string;
  count: number;
};

export type ProductQuickFilterVisualState = "default" | "active" | "empty";

export type ProductReviewFilter = Exclude<ProductQuickFilter, "all" | "recent_imports" | "needs_review">;

export type ProductReviewBadge = {
  key: ProductReviewFilter;
  filter: ProductReviewFilter;
  label: string;
  tone: "warning" | "error";
};

export type ProductReviewField = "marca" | "codigo" | "categoria";

export type ProductReviewFieldStatus = {
  field: ProductReviewField;
  filter: ProductReviewFilter;
  label: string;
  tone: "warning";
};

export type ProductQuickFilterContextAction = {
  key: "all" | "needs_review";
  label: string;
  targetFilter: ProductQuickFilter;
  tone: "neutral" | "review";
};

export type ProductQuickFilterContext = {
  title: string;
  detail: string;
  tone: "neutral" | "warning" | "review";
  actions: ProductQuickFilterContextAction[];
};

export type ProductQuickFilterEmptyState = {
  title: string;
  detail: string;
  actions: ProductQuickFilterContextAction[];
  searchActive?: boolean;
  searchQuery?: string;
};

const TABLE_LEVEL_REVIEW_BADGE_KEYS = new Set<ProductReviewFilter>([
  "pending_grades",
  "missing_brand",
  "missing_code",
  "missing_category",
]);

function sumSavedGradeValues(product: Pick<Product, "grades">) {
  return (product.grades || []).reduce((sum, item) => sum + (Number(item.quantidade || 0) || 0), 0);
}

function hasAnySavedGrade(product: Pick<Product, "grades">) {
  return (product.grades || []).length > 0 || sumSavedGradeValues(product) > 0;
}

function hasGradeMismatch(product: Product) {
  if (!hasAnySavedGrade(product)) return false;
  return sumSavedGradeValues(product) !== Number(product.quantidade || 0);
}

function isRecentImport(product: Product) {
  return Boolean(product.import_batch_id || product.import_source_name || product.source_type || product.pending_grade_import);
}

function needsReview(product: Product) {
  return buildProductReviewBadges(product).length > 0;
}

export function coerceProductQuickFilter(value: unknown, fallback: ProductQuickFilter = "all"): ProductQuickFilter {
  if (PRODUCT_QUICK_FILTER_DEFINITIONS.some((filter) => filter.key === value)) return value as ProductQuickFilter;
  if (PRODUCT_QUICK_FILTER_DEFINITIONS.some((filter) => filter.key === fallback)) return fallback;
  return "all";
}

export function buildProductReviewBadges(product: Product): ProductReviewBadge[] {
  const badges: ProductReviewBadge[] = [];
  if (product.pending_grade_import) {
    badges.push({ key: "pending_grades", filter: "pending_grades", label: "Grade pendente", tone: "warning" });
  }
  if (!String(product.marca || "").trim()) {
    badges.push({ key: "missing_brand", filter: "missing_brand", label: "Sem marca", tone: "warning" });
  }
  if (!String(product.codigo || "").trim()) {
    badges.push({ key: "missing_code", filter: "missing_code", label: "Sem código", tone: "warning" });
  }
  if (!String(product.categoria || "").trim()) {
    badges.push({ key: "missing_category", filter: "missing_category", label: "Sem categoria", tone: "warning" });
  }
  if (hasGradeMismatch(product)) {
    badges.push({
      key: "grade_mismatch",
      filter: "grade_mismatch",
      label: `Grade ${sumSavedGradeValues(product)}/${Number(product.quantidade || 0)}`,
      tone: "error",
    });
  }
  return badges;
}

export function buildProductNameReviewBadges(product: Product): ProductReviewBadge[] {
  return buildProductReviewBadges(product).filter((badge) => !TABLE_LEVEL_REVIEW_BADGE_KEYS.has(badge.key));
}

export function buildProductReviewFieldStatus(product: Product, field: ProductReviewField): ProductReviewFieldStatus | null {
  if (String(product[field] || "").trim()) return null;

  if (field === "marca") {
    return { field, filter: "missing_brand", label: "Sem marca", tone: "warning" };
  }

  if (field === "codigo") {
    return { field, filter: "missing_code", label: "Sem código", tone: "warning" };
  }

  return { field, filter: "missing_category", label: "Sem categoria", tone: "warning" };
}

export function productMatchesQuickFilter(product: Product, filter: ProductQuickFilter) {
  switch (filter) {
    case "needs_review":
      return needsReview(product);
    case "pending_grades":
      return Boolean(product.pending_grade_import);
    case "recent_imports":
      return isRecentImport(product);
    case "missing_brand":
      return !String(product.marca || "").trim();
    case "missing_code":
      return !String(product.codigo || "").trim();
    case "missing_category":
      return !String(product.categoria || "").trim();
    case "grade_mismatch":
      return hasGradeMismatch(product);
    case "all":
    default:
      return true;
  }
}

export function filterProductsByQuickFilter(products: Product[], filter: ProductQuickFilter) {
  if (filter === "all") return products;
  return products.filter((product) => productMatchesQuickFilter(product, filter));
}

function normalizeProductSearchValue(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function compactProductSearchValue(value: string) {
  return value.replace(/[^a-z0-9]/g, "");
}

function getProductSearchHaystack(product: Product) {
  return normalizeProductSearchValue([
    product.nome,
    product.marca,
    product.codigo,
    product.codigo_original,
    product.categoria,
    product.descricao_completa,
  ].join(" "));
}

function productSearchTermMatches(haystack: string, compactHaystack: string, term: string) {
  if (haystack.includes(term)) return true;

  const compactTerm = compactProductSearchValue(term);
  return Boolean(compactTerm && compactHaystack.includes(compactTerm));
}

export function filterProductsBySearch(products: Product[], query: string) {
  const terms = normalizeProductSearchValue(query).split(/\s+/g).filter(Boolean);
  if (!terms.length) return products;

  return products.filter((product) => {
    const haystack = getProductSearchHaystack(product);
    const compactHaystack = compactProductSearchValue(haystack);
    return terms.every((term) => productSearchTermMatches(haystack, compactHaystack, term));
  });
}

export function buildProductQuickFilterOptions(products: Product[]): ProductQuickFilterOption[] {
  return PRODUCT_QUICK_FILTER_DEFINITIONS.map((filter) => ({
    ...filter,
    count: filter.key === "all" ? products.length : products.filter((product) => productMatchesQuickFilter(product, filter.key)).length,
  }));
}

export function buildProductQuickFilterButtonLabel(option: ProductQuickFilterOption, active: boolean) {
  const countLabel = option.count === 1 ? "1 item" : `${option.count} itens`;
  return `${active ? "Filtro ativo" : "Filtro"}: ${option.label}, ${countLabel}`;
}

export function buildProductQuickFilterLoadingButtonLabel(option: Pick<ProductQuickFilterOption, "label">, active: boolean) {
  return `${active ? "Filtro ativo" : "Filtro"}: ${option.label}, atualizando contagem`;
}

export function getProductQuickFilterVisualState(option: ProductQuickFilterOption, active: boolean): ProductQuickFilterVisualState {
  if (active) return "active";
  if (option.key !== "all" && option.count === 0) return "empty";
  return "default";
}

export function getVisibleProductQuickFilterOptions(
  options: ProductQuickFilterOption[],
  filter: ProductQuickFilter,
): ProductQuickFilterOption[] {
  const activeFilter = coerceProductQuickFilter(filter);
  return options.filter((option) => option.key === "all" || option.count > 0 || option.key === activeFilter);
}

export function resolveStaleProductQuickFilter(
  filter: ProductQuickFilter,
  options: ProductQuickFilterOption[],
  totalCount: number,
): ProductQuickFilter {
  const activeFilter = coerceProductQuickFilter(filter);
  if (activeFilter === "all" || totalCount === 0 || getQuickFilterCount(activeFilter, options) > 0) {
    return activeFilter;
  }

  return getQuickFilterCount("needs_review", options) > 0 ? "needs_review" : "all";
}

function getQuickFilterLabel(filter: ProductQuickFilter, options: ProductQuickFilterOption[]) {
  return options.find((option) => option.key === filter)?.label
    ?? PRODUCT_QUICK_FILTER_DEFINITIONS.find((option) => option.key === filter)?.label
    ?? "Filtro";
}

function getQuickFilterCount(filter: ProductQuickFilter, options: ProductQuickFilterOption[]) {
  return options.find((option) => option.key === filter)?.count ?? 0;
}

function getQuickFilterContextTone(filter: ProductQuickFilter): ProductQuickFilterContext["tone"] {
  if (filter === "needs_review") return "review";
  if (filter === "recent_imports") return "neutral";
  return "warning";
}

function formatCurrentItemsWithoutIssues(totalCount: number) {
  return totalCount === 1
    ? "O item atual não possui pendências deste filtro."
    : `Os ${totalCount} itens atuais não possuem pendências deste filtro.`;
}

function formatItemsOutsideFilter(totalCount: number) {
  return totalCount === 1
    ? "Existe 1 item na lista fora deste recorte."
    : `Existem ${totalCount} itens na lista fora deste recorte.`;
}

export function buildProductQuickFilterContext(
  filter: ProductQuickFilter,
  options: ProductQuickFilterOption[],
  displayedCount: number,
  totalCount: number,
): ProductQuickFilterContext | null {
  const activeFilter = coerceProductQuickFilter(filter);
  if (activeFilter === "all") return null;

  const actions: ProductQuickFilterContextAction[] = [
    { key: "all", label: "Mostrar todos", targetFilter: "all", tone: "neutral" },
  ];
  if (activeFilter !== "needs_review" && getQuickFilterCount("needs_review", options) > 0) {
    actions.push({ key: "needs_review", label: "Voltar para revisar", targetFilter: "needs_review", tone: "review" });
  }

  return {
    title: activeFilter === "needs_review" ? "Revisão ativa" : `Filtro ativo: ${getQuickFilterLabel(activeFilter, options)}`,
    detail: `${displayedCount} de ${totalCount} itens visíveis`,
    tone: getQuickFilterContextTone(activeFilter),
    actions,
  };
}

export function buildProductQuickFilterEmptyState(
  filter: ProductQuickFilter,
  options: ProductQuickFilterOption[],
  displayedCount: number,
  totalCount: number,
): ProductQuickFilterEmptyState {
  const activeFilter = coerceProductQuickFilter(filter);
  if (activeFilter === "all") {
    return {
      title: "Nenhum produto ativo neste momento.",
      detail: "Importe ou cadastre produtos para iniciar a lista.",
      actions: [],
    };
  }

  const context = buildProductQuickFilterContext(activeFilter, options, displayedCount, totalCount);
  const label = getQuickFilterLabel(activeFilter, options);

  return {
    title: activeFilter === "needs_review" ? "Nenhum item para revisar." : `Nenhum item em ${label}.`,
    detail: activeFilter === "needs_review"
      ? formatCurrentItemsWithoutIssues(totalCount)
      : formatItemsOutsideFilter(totalCount),
    actions: context?.actions || [],
  };
}

export function buildProductSearchEmptyState(query: string, searchScopeCount: number): ProductQuickFilterEmptyState {
  const trimmedQuery = query.trim();
  const scopeLabel = searchScopeCount === 1 ? "1 item visível" : `${searchScopeCount} itens visíveis`;

  return {
    title: trimmedQuery ? `Nenhum resultado para ${trimmedQuery}.` : "Nenhum resultado encontrado.",
    detail: `A busca foi aplicada em ${scopeLabel} do recorte atual.`,
    actions: [],
    searchActive: true,
    searchQuery: trimmedQuery,
  };
}
