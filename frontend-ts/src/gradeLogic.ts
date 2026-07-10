import type { GradeConfig, GradeItem, Product, TargetPoint, UiGradeFamily } from "./types";
import { normalizeTargetPoint } from "./uiFormatting.js";

const GRADE_SIZE_PRIORITY = [
  "P",
  "M",
  "G",
  "GG",
  "U",
  "PP",
  "P/M",
  "M/G",
  "XG",
  "XXG",
  "XGG",
  "G1",
  "G2",
  "G3",
  "G4",
  "G5",
  "G6",
  "1",
  "2",
  "3",
  "4",
  "6",
  "8",
  "10",
  "12",
  "14",
  "16",
  "18",
  "20",
  "22",
  "3M",
  "6M",
  "9M",
  "12M",
  "18M",
  "34",
  "36",
  "38",
  "40",
  "42",
  "44",
  "46",
  "48",
  "50",
  "52",
  "54",
  "56",
  "58",
  "UN",
];

export const GRADE_UI_VERSION = 2;
export const LAST_ACTIVE_GRADE_FAMILY_KEY = "lojasync:last-active-grade-family";

const GRADE_FAMILY_PRESET = [
  { id: "common", label: "Mais usadas", order: ["P", "M", "G", "GG", "U", "PP", "P/M", "M/G"] },
  { id: "letters", label: "Família letras", order: ["XG", "XXG", "XGG", "G1", "G2", "G3", "G4", "G5", "G6"] },
  { id: "infantil", label: "Família infantil", order: ["1", "2", "3", "4", "6", "8", "10", "12", "14", "16", "18", "20", "22", "3M", "6M", "9M", "12M", "18M"] },
  { id: "adulto", label: "Família adulto", order: ["32", "34", "36", "38", "40", "42", "44", "46", "48", "50", "52", "54", "56", "58"] },
];

export type IncompleteGradeProduct = {
  product: Product;
  total: number;
  expected: number;
};

export type GradeProductStatus = {
  total: number;
  expected: number;
  difference: number;
  complete: boolean;
  hasAny: boolean;
  overflow: boolean;
  pending: boolean;
  status: "empty" | "missing" | "under" | "over" | "complete";
  label: string;
  tone: "neutral" | "warning" | "danger" | "success";
};

export function normalizeGradeSizeLabel(value: string) {
  const label = String(value || "").trim().toUpperCase().replace(/[^A-Z0-9]+/g, "");
  if (!label) return "";
  if (/^\d+$/.test(label)) {
    const number = Number.parseInt(label, 10);
    return Number.isFinite(number) && number > 0 ? String(number) : "";
  }
  return label;
}

function normalizeSizeList(items: unknown) {
  if (!Array.isArray(items)) return [];
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const item of items) {
    const label = normalizeGradeSizeLabel(String(item || ""));
    if (!label || seen.has(label)) continue;
    seen.add(label);
    normalized.push(label);
  }
  return normalized;
}

function normalizePositiveNumber(value: unknown) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function normalizeUiFamiliesState(families: unknown): UiGradeFamily[] {
  if (!Array.isArray(families)) return [];
  return families
    .map((family, index) => {
      const raw = family && typeof family === "object" ? (family as Partial<UiGradeFamily>) : {};
      return {
        id: String(raw.id || `family-${index + 1}`).trim().toLowerCase() || `family-${index + 1}`,
        label: String(raw.label || `Família ${index + 1}`).trim() || `Família ${index + 1}`,
        sizes: normalizeSizeList(raw.sizes || []),
      };
    })
    .filter((family) => family.sizes.length || family.label.trim());
}

export function normalizeGradeConfigState(value?: GradeConfig | null): GradeConfig {
  const rawButtons = value?.buttons && typeof value.buttons === "object" ? value.buttons : {};
  const buttonsEntries = Object.entries(rawButtons)
    .map(([key, point]) => {
      const normalized = normalizeTargetPoint(point);
      return normalized ? ([key, normalized] as const) : null;
    })
    .filter((entry): entry is readonly [string, TargetPoint] => Boolean(entry));
  return {
    ...(value || {}),
    buttons: Object.fromEntries(buttonsEntries),
    first_quant_cell: normalizeTargetPoint(value?.first_quant_cell),
    second_quant_cell: normalizeTargetPoint(value?.second_quant_cell),
    row_height: normalizePositiveNumber(value?.row_height),
    model_index: normalizePositiveNumber(value?.model_index),
    model_hotkey: String(value?.model_hotkey || ""),
    erp_size_order: normalizeSizeList(value?.erp_size_order || []),
    ui_size_order: normalizeSizeList(value?.ui_size_order || []),
    ui_families: normalizeUiFamiliesState(value?.ui_families || []),
    ui_family_version: normalizePositiveNumber(value?.ui_family_version),
  };
}

export function parseSizeOrderText(value: string) {
  return normalizeSizeList(String(value || "").split(/[\n,;]+/g));
}

const GRADE_SIZE_PRIORITY_INDEX = new Map(GRADE_SIZE_PRIORITY.map((size, index) => [normalizeGradeSizeLabel(size), index]));

export function compareGradeSizeLabels(left: string, right: string) {
  const leftLabel = normalizeGradeSizeLabel(left);
  const rightLabel = normalizeGradeSizeLabel(right);
  const leftRank = GRADE_SIZE_PRIORITY_INDEX.get(leftLabel) ?? Number.POSITIVE_INFINITY;
  const rightRank = GRADE_SIZE_PRIORITY_INDEX.get(rightLabel) ?? Number.POSITIVE_INFINITY;
  if (leftRank !== rightRank) {
    return leftRank - rightRank;
  }
  return leftLabel.localeCompare(rightLabel, "pt-BR");
}

export function gradeItemsToMap(items: GradeItem[] | null | undefined) {
  const map: Record<string, string> = {};
  for (const item of items || []) {
    const label = normalizeGradeSizeLabel(item.tamanho);
    if (!label) continue;
    map[label] = String(item.quantidade ?? 0);
  }
  return map;
}

export function buildGradeItemsFromDraft(draft: Record<string, string>): GradeItem[] {
  const quantitiesBySize = new Map<string, number>();
  for (const [size, rawQuantity] of Object.entries(draft)) {
    const label = normalizeGradeSizeLabel(size);
    const quantity = Number.parseInt(String(rawQuantity || ""), 10) || 0;
    if (!label || quantity <= 0) {
      continue;
    }
    quantitiesBySize.set(label, quantity);
  }
  return Array.from(quantitiesBySize, ([tamanho, quantidade]) => ({ tamanho, quantidade }))
    .sort((left, right) => compareGradeSizeLabels(left.tamanho, right.tamanho));
}

export function hasGradeDraftChanges(
  draft: Record<string, string>,
  baseline: Record<string, string>,
) {
  const currentItems = buildGradeItemsFromDraft(draft);
  const baselineItems = buildGradeItemsFromDraft(baseline);
  if (currentItems.length !== baselineItems.length) {
    return true;
  }
  return currentItems.some((item, index) => {
    const baselineItem = baselineItems[index];
    return item.tamanho !== baselineItem?.tamanho || item.quantidade !== baselineItem?.quantidade;
  });
}

export function sumGradeDraftValues(draft: Record<string, string>) {
  return Object.values(draft).reduce((sum, item) => sum + (Number.parseInt(item, 10) || 0), 0);
}

export function sumSavedGradeValues(product: Product) {
  return (product.grades || []).reduce((sum, item) => sum + (Number(item.quantidade || 0) || 0), 0);
}

export function buildGradeProductStatus(product: Pick<Product, "quantidade" | "grades">, draftTotal?: number | null): GradeProductStatus {
  const expected = Math.max(0, Number(product.quantidade || 0) || 0);
  const total = Math.max(0, Math.floor(Number(draftTotal ?? sumSavedGradeValues(product as Product)) || 0));
  const difference = expected - total;
  const hasAny = total > 0;
  const complete = expected > 0 && total === expected;
  const overflow = total > expected;
  if (expected <= 0) {
    return {
      total,
      expected,
      difference: 0,
      complete: false,
      hasAny,
      overflow: false,
      pending: false,
      status: "empty",
      label: "Sem quantidade",
      tone: "neutral",
    };
  }
  if (complete) {
    return {
      total,
      expected,
      difference: 0,
      complete,
      hasAny,
      overflow,
      pending: false,
      status: "complete",
      label: "Grade fecha",
      tone: "success",
    };
  }
  if (overflow) {
    return {
      total,
      expected,
      difference,
      complete,
      hasAny,
      overflow,
      pending: true,
      status: "over",
      label: `Sobraram ${Math.abs(difference)} peças`,
      tone: "danger",
    };
  }
  return {
    total,
    expected,
    difference,
    complete,
    hasAny,
    overflow,
    pending: true,
    status: hasAny ? "under" : "missing",
    label: `Faltam ${difference} peças`,
    tone: "warning",
  };
}

export function getIncompleteGradeProducts(products: Product[]): IncompleteGradeProduct[] {
  return products
    .map((product) => {
      const status = buildGradeProductStatus(product);
      const hasSavedGrade = (product.grades || []).length > 0 || status.total > 0;
      if (!hasSavedGrade || !status.pending) {
        return null;
      }
      return { product, total: status.total, expected: status.expected };
    })
    .filter((item): item is IncompleteGradeProduct => Boolean(item));
}

export function findNextPendingGradeKey(products: Product[], currentOrderingKey: string | null | undefined, ignoredOrderingKey?: string | null) {
  if (!products.length) return null;
  const currentIndex = products.findIndex((product) => product.ordering_key === currentOrderingKey);
  const startIndex = currentIndex >= 0 ? currentIndex : -1;
  for (let offset = 1; offset <= products.length; offset += 1) {
    const product = products[(startIndex + offset + products.length) % products.length];
    if (!product || product.ordering_key === ignoredOrderingKey) {
      continue;
    }
    if (buildGradeProductStatus(product).pending) {
      return product.ordering_key;
    }
  }
  return null;
}

export function buildVisualSizeOrder(config: GradeConfig | null, catalogSizes: string[], products: Product[]) {
  const merged = new Set<string>();
  for (const size of config?.ui_size_order || []) {
    const label = normalizeGradeSizeLabel(size);
    if (label) merged.add(label);
  }
  for (const size of config?.erp_size_order || []) {
    const label = normalizeGradeSizeLabel(size);
    if (label) merged.add(label);
  }
  for (const size of catalogSizes) {
    const label = normalizeGradeSizeLabel(size);
    if (label) merged.add(label);
  }
  for (const product of products) {
    for (const item of product.grades || []) {
      const label = normalizeGradeSizeLabel(item.tamanho);
      if (label) merged.add(label);
    }
  }
  return Array.from(merged).sort(compareGradeSizeLabels);
}

export function classifyGradeFamily(size: string) {
  const label = normalizeGradeSizeLabel(size);
  const commonAlpha = ["UN", "U", "PP", "P", "M", "G", "GG"];
  if (commonAlpha.includes(label)) {
    return "common";
  }
  if (/^(XG|XXG|G1|G2|G3|G4|EG|EXG|XGG)$/.test(label) || /^[A-Z]+$/.test(label)) {
    return "letters";
  }
  if (/^\d+$/.test(label)) {
    return "numbers";
  }
  return "special";
}

export function buildDefaultUiFamilies(sizes: string[]): UiGradeFamily[] {
  const remaining = [...sizes];
  const takeMatchingSize = (wanted: string) => {
    const wantedLabel = normalizeGradeSizeLabel(wanted);
    const wantedNumeric = /^\d+$/.test(wantedLabel) ? Number.parseInt(wantedLabel, 10) : null;
    const index = remaining.findIndex((candidate) => {
      const normalized = normalizeGradeSizeLabel(candidate);
      if (normalized === wantedLabel) return true;
      if (wantedNumeric !== null && /^\d+$/.test(normalized)) {
        return Number.parseInt(normalized, 10) === wantedNumeric;
      }
      return false;
    });
    if (index < 0) return null;
    const [matched] = remaining.splice(index, 1);
    return matched;
  };

  const families = GRADE_FAMILY_PRESET.map((preset) => ({
    id: preset.id,
    label: preset.label,
    sizes: preset.order.map((item) => takeMatchingSize(item)).filter((item): item is string => Boolean(item)),
  })).filter((family) => family.sizes.length);

  if (remaining.length) {
    families.push({
      id: "extras",
      label: "Extras",
      sizes: remaining,
    });
  }
  return families;
}

export function normalizeUiFamiliesDraft(families: UiGradeFamily[], fallbackSizes: string[]) {
  const seen = new Set<string>();
  const normalizedFamilies = families
    .map((family, index) => {
      const id = String(family.id || `family-${index + 1}`).trim().toLowerCase() || `family-${index + 1}`;
      const label = String(family.label || `Família ${index + 1}`).trim() || `Família ${index + 1}`;
      const sizes: string[] = [];
      for (const size of family.sizes || []) {
        const normalized = normalizeGradeSizeLabel(size);
        if (!normalized || seen.has(normalized)) continue;
        seen.add(normalized);
        sizes.push(normalized);
      }
      return { id, label, sizes };
    })
    .filter((family) => family.sizes.length || family.label.trim());

  const unassigned = fallbackSizes.filter((size) => !seen.has(normalizeGradeSizeLabel(size)));
  if (unassigned.length) {
    const special = normalizedFamilies.find((family) => family.id === "special");
    if (special) {
      special.sizes.push(...unassigned);
    } else {
      normalizedFamilies.push({ id: "special", label: "Especiais", sizes: unassigned });
    }
  }
  return normalizedFamilies;
}
