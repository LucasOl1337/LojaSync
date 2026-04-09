import { startTransition, useEffect, useMemo, useRef, useState } from "react";

import {
  addBrand,
  applyBrand,
  applyCategory,
  applyMargin,
  buildWsUrl,
  captureAutomationTarget,
  clearProducts,
  createProduct,
  createSet,
  deleteProduct,
  executeGradesProducts,
  fetchAutomationTargets,
  fetchAutomationStatus,
  fetchBrands,
  fetchByteEmpresaContext,
  fetchCatalogSizes,
  fetchGradeConfig,
  fetchImportResult,
  fetchImportStatus,
  fetchMargin,
  fetchProducts,
  fetchTotals,
  formatCodes,
  improveDescriptions,
  importRomaneio,
  joinDuplicates,
  joinGrades,
  patchProduct,
  reorderProducts,
  restoreOriginalCodes,
  restoreSnapshot,
  saveAutomationTargets,
  saveGradeConfig,
  saveMargin,
  startAutomationCatalog,
  startAutomationComplete,
  prepareByteEmpresa,
  stopAutomation,
  stopGradesExecution,
} from "./api";
import type { AutomationStatus, AutomationTargets, GradeConfig, GradeItem, ImportResult, ImportStatus, Product, ProductPayload, TargetPoint, UiEvent, UiGradeFamily } from "./types";

const CATEGORIES = ["Masculino", "Feminino", "Infantil", "Acessorios"];
const MAX_UNDO_HISTORY = 10;
const AUTOMATION_TARGET_FIELDS = [
  { key: "byte_empresa_posicao", label: "Posicao Byte Empresa" },
  { key: "campo_descricao", label: "Campo Descricao" },
  { key: "tres_pontinhos", label: "Botao 3 pontinhos" },
  { key: "cadastro_completo_passo_1", label: "Cadastro completo passo 1" },
  { key: "cadastro_completo_passo_2", label: "Cadastro completo passo 2" },
  { key: "cadastro_completo_passo_3", label: "Cadastro completo passo 3" },
  { key: "cadastro_completo_passo_4", label: "Cadastro completo passo 4" },
] as const;
const GRADE_CAPTURE_FIELDS = [
  { key: "focus_app", label: "Focar aplicativo" },
  { key: "alterar_grade", label: "Botao Alterar/Definir Grade" },
  { key: "modelos", label: "Botao Modelos" },
  { key: "model_select", label: "Linha do modelo" },
  { key: "model_ok", label: "Botao OK do modelo" },
  { key: "confirm_sim", label: "Botao Sim da confirmacao" },
  { key: "close_after_import", label: "Fechar intermediario" },
  { key: "save_grade", label: "Salvar grade" },
  { key: "close_grade", label: "Fechar grade" },
] as const;

type Scope = "products" | "totals" | "brands" | "margin" | "automation";
type EditableField = "nome" | "marca" | "codigo" | "quantidade" | "preco" | "preco_final" | "categoria";
type ProductFormField = "nome" | "codigo" | "quantidade" | "preco";
type EditingCellState = { orderingKey: string; field: EditableField; value: string };
type AutomationTargetKey = typeof AUTOMATION_TARGET_FIELDS[number]["key"];
type GradeCaptureKey = typeof GRADE_CAPTURE_FIELDS[number]["key"];

type LoadState = {
  products: Product[];
  brands: string[];
  totalsText: {
    atualCusto: string;
    atualVenda: string;
    historicoCusto: string;
    historicoVenda: string;
    tempo: string;
  };
  totalsRaw: {
    atualQuantidade: number;
    historicoQuantidade: number;
    caracteres: number;
  };
  marginPercentual: number;
  automation: AutomationStatus;
};

const initialState: LoadState = {
  products: [],
  brands: [],
  totalsText: {
    atualCusto: "R$ 0,00",
    atualVenda: "R$ 0,00",
    historicoCusto: "R$ 0,00",
    historicoVenda: "R$ 0,00",
    tempo: "0s",
  },
  totalsRaw: {
    atualQuantidade: 0,
    historicoQuantidade: 0,
    caracteres: 0,
  },
  marginPercentual: 0,
  automation: {},
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value || 0);
}

function formatDuration(seconds: number) {
  if (!seconds) return "0s";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  const parts: string[] = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}min`);
  if (remaining || !parts.length) parts.push(`${remaining}s`);
  return parts.join(" ");
}

function formatTimestamp(value?: number | null) {
  if (!value) return "agora";
  return new Date(value * 1000).toLocaleTimeString("pt-BR");
}

function parsePromptInteger(raw: string | null) {
  if (!raw || !raw.trim()) return null;
  const value = Number.parseInt(raw.trim(), 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}

function cloneSnapshotProducts(items: Product[]) {
  return JSON.parse(JSON.stringify(items || [])) as Product[];
}

function formatTargetPoint(point?: TargetPoint | null) {
  if (!point) return "Nao calibrado";
  return `X: ${point.x} | Y: ${point.y}`;
}

function normalizeTargetPoint(value: unknown): TargetPoint | null {
  if (value && typeof value === "object" && "x" in (value as Record<string, unknown>) && "y" in (value as Record<string, unknown>)) {
    return {
      x: Number((value as Record<string, unknown>).x) || 0,
      y: Number((value as Record<string, unknown>).y) || 0,
    };
  }
  return null;
}

function normalizeGradeConfigState(value?: GradeConfig | null): GradeConfig {
  const buttonsEntries = Object.entries(value?.buttons || {})
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
    row_height: Number(value?.row_height || 0) || null,
    model_index: Number(value?.model_index || 0) || null,
    model_hotkey: value?.model_hotkey || "",
    erp_size_order: Array.isArray(value?.erp_size_order) ? value?.erp_size_order.map((item) => String(item).trim()).filter(Boolean) : [],
    ui_size_order: Array.isArray(value?.ui_size_order) ? value?.ui_size_order.map((item) => String(item).trim()).filter(Boolean) : [],
    ui_families: Array.isArray(value?.ui_families) ? value.ui_families : [],
    ui_family_version: Number(value?.ui_family_version || 0) || null,
  };
}

function formatJsonBlock(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function parseSizeOrderText(value: string) {
  return value
    .split(/[\n,;]+/g)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
}

function parsePriceInput(value: string | null | undefined) {
  if (!value) return null;
  const text = String(value).trim().replace("R$", "").replace(/\s+/g, "").replace(/\u00a0/g, "");
  if (!text) return null;
  const normalized = text.includes(",") ? text.replace(/\./g, "").replace(",", ".") : text;
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatPriceInput(value: number | null) {
  if (value == null || !Number.isFinite(value)) return "";
  return value.toFixed(2).replace(".", ",");
}

function calculateSalePricePreview(costPrice: string, marginPercentual: number) {
  const parsed = parsePriceInput(costPrice);
  if (parsed == null) return null;
  const safeMargin = 1 + Math.max(marginPercentual, 0) / 100;
  const gross = parsed * safeMargin;
  const whole = Math.floor(gross);
  let target = whole + 0.9;
  if (target < gross) {
    target = whole + 1.9;
  }
  return formatPriceInput(target);
}

function computeCurrentTotals(products: Product[], marginPercentual: number) {
  let quantidade = 0;
  let custo = 0;
  let venda = 0;
  for (const product of products) {
    const quantity = Number(product.quantidade || 0);
    const cost = parsePriceInput(product.preco) || 0;
    const sale = parsePriceInput(product.preco_final || calculateSalePricePreview(product.preco || "", marginPercentual)) || 0;
    quantidade += quantity;
    custo += cost * quantity;
    venda += sale * quantity;
  }
  return { quantidade, custo, venda };
}

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
  "01",
  "02",
  "03",
  "04",
  "06",
  "08",
  "UN",
];

const GRADE_UI_VERSION = 2;
const LAST_ACTIVE_GRADE_FAMILY_KEY = "lojasync:last-active-grade-family";
const GRADE_FAMILY_PRESET = [
  { id: "common", label: "Mais usadas", order: ["P", "M", "G", "GG", "U", "PP", "P/M", "M/G"] },
  { id: "letters", label: "Familia letras", order: ["XG", "XXG", "XGG", "G1", "G2", "G3", "G4", "G5", "G6"] },
  { id: "infantil", label: "Familia infantil", order: ["1", "2", "3", "4", "6", "8", "10", "12", "14", "16", "18", "20", "22", "3M", "6M", "9M", "12M", "18M"] },
  { id: "adulto", label: "Familia adulto", order: ["32", "34", "36", "38", "40", "42", "44", "46", "48", "50", "52", "54", "56", "58"] },
];

const GRADE_SIZE_PRIORITY_INDEX = new Map(GRADE_SIZE_PRIORITY.map((size, index) => [size, index]));

function normalizeGradeSizeLabel(value: string) {
  return String(value || "").trim().toUpperCase();
}

function compareGradeSizeLabels(left: string, right: string) {
  const leftLabel = normalizeGradeSizeLabel(left);
  const rightLabel = normalizeGradeSizeLabel(right);
  const leftRank = GRADE_SIZE_PRIORITY_INDEX.get(leftLabel) ?? Number.POSITIVE_INFINITY;
  const rightRank = GRADE_SIZE_PRIORITY_INDEX.get(rightLabel) ?? Number.POSITIVE_INFINITY;
  if (leftRank !== rightRank) {
    return leftRank - rightRank;
  }
  return leftLabel.localeCompare(rightLabel, "pt-BR");
}

function gradeItemsToMap(items: GradeItem[] | null | undefined) {
  const map: Record<string, string> = {};
  for (const item of items || []) {
    map[item.tamanho] = String(item.quantidade ?? 0);
  }
  return map;
}

function sumGradeDraftValues(draft: Record<string, string>) {
  return Object.values(draft).reduce((sum, item) => sum + (Number.parseInt(item, 10) || 0), 0);
}

function sumSavedGradeValues(product: Product) {
  return (product.grades || []).reduce((sum, item) => sum + (Number(item.quantidade || 0) || 0), 0);
}

function getIncompleteGradeProducts(products: Product[]) {
  return products
    .map((product) => {
      const total = sumSavedGradeValues(product);
      const expected = Number(product.quantidade || 0);
      const hasSavedGrade = (product.grades || []).length > 0 || total > 0;
      if (!hasSavedGrade || total === expected) {
        return null;
      }
      return { product, total, expected };
    })
    .filter((item): item is { product: Product; total: number; expected: number } => Boolean(item));
}

function buildVisualSizeOrder(config: GradeConfig | null, catalogSizes: string[], products: Product[]) {
  const merged = new Set<string>();
  for (const size of config?.ui_size_order || []) merged.add(size);
  for (const size of config?.erp_size_order || []) merged.add(size);
  for (const size of catalogSizes) merged.add(size);
  for (const product of products) {
    for (const item of product.grades || []) {
      merged.add(item.tamanho);
    }
  }
  return Array.from(merged).sort(compareGradeSizeLabels);
}

function classifyGradeFamily(size: string) {
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

function buildDefaultUiFamilies(sizes: string[]): UiGradeFamily[] {
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

function normalizeUiFamiliesDraft(families: UiGradeFamily[], fallbackSizes: string[]) {
  const seen = new Set<string>();
  const normalizedFamilies = families
    .map((family, index) => {
      const id = String(family.id || `family-${index + 1}`).trim().toLowerCase() || `family-${index + 1}`;
      const label = String(family.label || `Familia ${index + 1}`).trim() || `Familia ${index + 1}`;
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

export default function App() {
  const [state, setState] = useState<LoadState>(initialState);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<ProductPayload>({
    nome: "",
    codigo: "",
    quantidade: 1,
    preco: "",
    categoria: "",
    marca: "",
    preco_final: "",
    descricao_completa: "",
  });
  const [newBrand, setNewBrand] = useState("");
  const [showBrandComposer, setShowBrandComposer] = useState(false);
  const [showBulkCategoryMenu, setShowBulkCategoryMenu] = useState(false);
  const [showBulkBrandMenu, setShowBulkBrandMenu] = useState(false);
  const [bulkCategoryValue, setBulkCategoryValue] = useState("");
  const [bulkBrandValue, setBulkBrandValue] = useState("");
  const [simpleModeEnabled, setSimpleModeEnabled] = useState(false);
  const [globalEditMode, setGlobalEditMode] = useState(false);
  const [orderingMode, setOrderingMode] = useState(false);
  const [orderingSelectedKeys, setOrderingSelectedKeys] = useState<string[]>([]);
  const [createSetMode, setCreateSetMode] = useState(false);
  const [createSetKeys, setCreateSetKeys] = useState<string[]>([]);
  const [showFormatCodesPanel, setShowFormatCodesPanel] = useState(false);
  const [showDescriptionPanel, setShowDescriptionPanel] = useState(false);
  const [editingCell, setEditingCell] = useState<EditingCellState | null>(null);
  const [formatCodesOptions, setFormatCodesOptions] = useState({
    remover_primeiros_numeros: "",
    remover_ultimos_numeros: "",
  });
  const [descriptionOptions, setDescriptionOptions] = useState({
    remover_numeros: false,
    remover_especiais: false,
    remover_letras: false,
    remover_termos: "",
  });
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importJob, setImportJob] = useState<ImportStatus | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [automationError, setAutomationError] = useState<string | null>(null);
  const [gradeModalOpen, setGradeModalOpen] = useState(false);
  const [gradeModalError, setGradeModalError] = useState<string | null>(null);
  const [gradeValidationError, setGradeValidationError] = useState<string | null>(null);
  const [gradeSizesCatalog, setGradeSizesCatalog] = useState<string[]>([]);
  const [gradeConfig, setGradeConfig] = useState<GradeConfig | null>(null);
  const [gradeSelectedKey, setGradeSelectedKey] = useState<string | null>(null);
  const [gradeDraft, setGradeDraft] = useState<Record<string, string>>({});
  const [gradeOrderDraft, setGradeOrderDraft] = useState<string[]>([]);
  const [gradeFamiliesDraft, setGradeFamiliesDraft] = useState<UiGradeFamily[]>([]);
  const [activeGradeFamilyKey, setActiveGradeFamilyKey] = useState<string>(() => window.localStorage.getItem(LAST_ACTIVE_GRADE_FAMILY_KEY) || "common");
  const [newGradeSize, setNewGradeSize] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [importing, setImporting] = useState(false);
  const pendingScopes = useRef<Set<Scope>>(new Set());
  const flushTimer = useRef<number | null>(null);
  const importPollTimer = useRef<number | null>(null);
  const undoStackRef = useRef<Product[][]>([]);
  const redoStackRef = useRef<Product[][]>([]);
  const currentProductsSnapshotRef = useRef<Product[]>([]);
  const isRestoringSnapshotRef = useRef(false);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const bulkCategoryMenuRef = useRef<HTMLDivElement | null>(null);
  const bulkBrandMenuRef = useRef<HTMLDivElement | null>(null);
  const visitedProductFields = useRef<Set<ProductFormField>>(new Set());
  const gradeInputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const pendingGradeInputFocus = useRef(false);
  const gradeConfigSaveSeq = useRef(0);
  const previousAutomationStateRef = useRef<string | null>(null);
  const inlineEditInputRef = useRef<HTMLInputElement | HTMLSelectElement | null>(null);
  const nameInputRef = useRef<HTMLInputElement | null>(null);
  const codeInputRef = useRef<HTMLInputElement | null>(null);
  const quantityInputRef = useRef<HTMLInputElement | null>(null);
  const priceInputRef = useRef<HTMLInputElement | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState<string | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [settingsTargets, setSettingsTargets] = useState<AutomationTargets>({});
  const [settingsGradeConfig, setSettingsGradeConfig] = useState<GradeConfig>({});
  const [settingsContextText, setSettingsContextText] = useState("");
  const [settingsCaptureLabel, setSettingsCaptureLabel] = useState<string | null>(null);
  const [settingsCaptureCountdown, setSettingsCaptureCountdown] = useState<number | null>(null);

  const sortedBrands = useMemo(() => [...state.brands].sort((a, b) => a.localeCompare(b, "pt-BR")), [state.brands]);
  const productsByKey = useMemo(() => new Map(state.products.map((product) => [product.ordering_key, product])), [state.products]);
  const originalOrderingKeys = useMemo(() => state.products.map((product) => product.ordering_key), [state.products]);
  const incompleteGradeProducts = useMemo(() => getIncompleteGradeProducts(state.products), [state.products]);
  const displayedProducts = useMemo(() => {
    if (!orderingMode) {
      return state.products;
    }
    const remainingKeys = originalOrderingKeys.filter((key) => !orderingSelectedKeys.includes(key));
    return [...orderingSelectedKeys, ...remainingKeys].map((key) => productsByKey.get(key)).filter((product): product is Product => Boolean(product));
  }, [orderingMode, orderingSelectedKeys, originalOrderingKeys, productsByKey, state.products]);
  const orderingSelectionIndex = useMemo(
    () => new Map(orderingSelectedKeys.map((key, index) => [key, index + 1])),
    [orderingSelectedKeys],
  );
  const selectedGradeProduct = useMemo(
    () => (gradeSelectedKey ? state.products.find((product) => product.ordering_key === gradeSelectedKey) ?? null : null),
    [gradeSelectedKey, state.products],
  );
  const orderedGradeSizes = useMemo(() => {
    const merged = new Set<string>();
    for (const size of gradeOrderDraft) merged.add(size);
    for (const size of gradeConfig?.erp_size_order || []) merged.add(size);
    for (const size of gradeSizesCatalog) merged.add(size);
    for (const item of selectedGradeProduct?.grades || []) merged.add(item.tamanho);
    return Array.from(merged).sort(compareGradeSizeLabels);
  }, [gradeConfig, gradeOrderDraft, gradeSizesCatalog, selectedGradeProduct]);
  const groupedGradeSizes = useMemo(() => {
    const familyHints: Record<string, string> = {
      common: "PMG, tamanho unico e variacoes mais frequentes.",
      letters: "Tamanhos por letras expandidas e linhas plus size.",
      infantil: "Numeracao infantil e medidas em meses.",
      adulto: "Numeracao adulta em ordem crescente.",
      extras: "Itens extras fora das familias principais.",
    };
    return gradeFamiliesDraft
      .map((family) => ({
        key: family.id,
        label: family.label,
        hint: familyHints[family.id] || "Familia personalizada para acesso rapido.",
        items: family.sizes,
      }))
      .filter((group) => group.items.length);
  }, [gradeFamiliesDraft]);
  const activeGradeFamily = useMemo(
    () => groupedGradeSizes.find((group) => group.key === activeGradeFamilyKey) ?? groupedGradeSizes[0] ?? null,
    [activeGradeFamilyKey, groupedGradeSizes],
  );
  const currentGradeTotal = useMemo(() => sumGradeDraftValues(gradeDraft), [gradeDraft]);

  const applySnapshot = async (scopes: Scope[]) => {
    const tasks = scopes.map(async (scope) => {
      switch (scope) {
        case "products": {
          const payload = await fetchProducts();
          return { scope, value: payload.items };
        }
        case "totals": {
          const payload = await fetchTotals();
          return {
            scope,
            value: {
              totalsText: {
                atualCusto: formatCurrency(payload.atual.custo),
                atualVenda: formatCurrency(payload.atual.venda),
                historicoCusto: formatCurrency(payload.historico.custo),
                historicoVenda: formatCurrency(payload.historico.venda),
                tempo: formatDuration(payload.tempo_economizado),
              },
              totalsRaw: {
                atualQuantidade: payload.atual.quantidade,
                historicoQuantidade: payload.historico.quantidade,
                caracteres: payload.caracteres_digitados,
              },
            },
          };
        }
        case "brands": {
          const payload = await fetchBrands();
          return { scope, value: payload.marcas };
        }
        case "margin": {
          const payload = await fetchMargin();
          return { scope, value: payload.percentual };
        }
        case "automation": {
          const payload = await fetchAutomationStatus();
          return { scope, value: payload };
        }
      }
    });

    const settled = await Promise.all(tasks);
    startTransition(() => {
      setState((current) => {
        const next = { ...current };
        for (const item of settled) {
          if (item.scope === "products") next.products = item.value as Product[];
          if (item.scope === "brands") next.brands = item.value as string[];
          if (item.scope === "margin") next.marginPercentual = item.value as number;
          if (item.scope === "automation") next.automation = item.value as AutomationStatus;
          if (item.scope === "totals") {
            next.totalsText = (item.value as { totalsText: LoadState["totalsText"] }).totalsText;
            next.totalsRaw = (item.value as { totalsRaw: LoadState["totalsRaw"] }).totalsRaw;
          }
        }
        return next;
      });
      setLoading(false);
    });
  };

  const queueRefresh = (scopes: Scope[]) => {
    scopes.forEach((scope) => pendingScopes.current.add(scope));
    if (flushTimer.current !== null) return;
    flushTimer.current = window.setTimeout(() => {
      flushTimer.current = null;
      const currentScopes = Array.from(pendingScopes.current);
      pendingScopes.current.clear();
      void applySnapshot(currentScopes.length ? currentScopes : ["products", "totals", "brands", "margin", "automation"]);
    }, 120);
  };

  const applyProductsPreview = (products: Product[]) => {
    const currentTotals = computeCurrentTotals(products, state.marginPercentual);
    startTransition(() => {
      setState((current) => ({
        ...current,
        products,
        totalsText: {
          ...current.totalsText,
          atualCusto: formatCurrency(currentTotals.custo),
          atualVenda: formatCurrency(currentTotals.venda),
        },
        totalsRaw: {
          ...current.totalsRaw,
          atualQuantidade: currentTotals.quantidade,
        },
      }));
    });
  };

  const buildProductPreview = (product: Product, field: EditableField, rawValue: string): Product => {
    const next = { ...product };
    if (field === "quantidade") {
      const quantity = Number.parseInt(rawValue, 10);
      next.quantidade = Number.isFinite(quantity) && quantity >= 0 ? quantity : 0;
      return next;
    }
    if (field === "preco") {
      next.preco = rawValue;
      next.preco_final = calculateSalePricePreview(rawValue, state.marginPercentual);
      return next;
    }
    if (field === "preco_final") {
      next.preco_final = rawValue;
      return next;
    }
    if (field === "nome") next.nome = rawValue;
    if (field === "marca") next.marca = rawValue;
    if (field === "codigo") next.codigo = rawValue;
    if (field === "categoria") next.categoria = rawValue;
    return next;
  };

  const pushUndoSnapshot = (options?: { clearRedo?: boolean }) => {
    if (isRestoringSnapshotRef.current) {
      return;
    }
    const snapshot = cloneSnapshotProducts(currentProductsSnapshotRef.current);
    undoStackRef.current.push(snapshot);
    if (undoStackRef.current.length > MAX_UNDO_HISTORY) {
      undoStackRef.current.shift();
    }
    if (options?.clearRedo !== false) {
      redoStackRef.current = [];
    }
  };

  const restoreSnapshotState = async (snapshot: Product[]) => {
    isRestoringSnapshotRef.current = true;
    try {
      await restoreSnapshot(snapshot);
      await applySnapshot(["products", "totals", "brands", "margin"]);
    } finally {
      isRestoringSnapshotRef.current = false;
    }
  };

  const undoLastAction = async () => {
    if (!undoStackRef.current.length || isRestoringSnapshotRef.current) {
      return;
    }
    const snapshot = undoStackRef.current.pop();
    if (!snapshot) {
      return;
    }
    redoStackRef.current.push(cloneSnapshotProducts(currentProductsSnapshotRef.current));
    if (redoStackRef.current.length > MAX_UNDO_HISTORY) {
      redoStackRef.current.shift();
    }
    await restoreSnapshotState(snapshot);
  };

  const redoLastAction = async () => {
    if (!redoStackRef.current.length || isRestoringSnapshotRef.current) {
      return;
    }
    const snapshot = redoStackRef.current.pop();
    if (!snapshot) {
      return;
    }
    undoStackRef.current.push(cloneSnapshotProducts(currentProductsSnapshotRef.current));
    if (undoStackRef.current.length > MAX_UNDO_HISTORY) {
      undoStackRef.current.shift();
    }
    await restoreSnapshotState(snapshot);
  };

  useEffect(() => {
    queueRefresh(["products", "totals", "brands", "margin", "automation"]);
  }, []);

  useEffect(() => {
    currentProductsSnapshotRef.current = cloneSnapshotProducts(state.products);
  }, [state.products]);

  useEffect(() => {
    if (!orderingMode) {
      setOrderingSelectedKeys([]);
      return;
    }
    setOrderingSelectedKeys((current) => current.filter((key) => originalOrderingKeys.includes(key)));
  }, [orderingMode, originalOrderingKeys]);

  useEffect(() => {
    if (!createSetMode) {
      setCreateSetKeys([]);
    }
  }, [createSetMode]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (showBulkCategoryMenu && bulkCategoryMenuRef.current && target && !bulkCategoryMenuRef.current.contains(target)) {
        setShowBulkCategoryMenu(false);
      }
      if (showBulkBrandMenu && bulkBrandMenuRef.current && target && !bulkBrandMenuRef.current.contains(target)) {
        setShowBulkBrandMenu(false);
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [showBulkBrandMenu, showBulkCategoryMenu]);

  useEffect(() => {
    if (!editingCell) {
      return;
    }
    const timer = window.setTimeout(() => {
      const input = inlineEditInputRef.current;
      input?.focus();
      if (input instanceof HTMLInputElement && document.activeElement === input) {
        input.setSelectionRange(0, input.value.length);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [editingCell?.orderingKey, editingCell?.field]);

  useEffect(() => {
    if (!globalEditMode) {
      setEditingCell(null);
    }
  }, [globalEditMode]);

  useEffect(() => {
    const wsUrl = buildWsUrl("/ws/ui");
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;

    const connect = () => {
      socket = new WebSocket(wsUrl);
      socket.addEventListener("open", () => {
        socket?.send("ping");
      });
      socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data) as UiEvent;
        if (payload.type === "state.changed") {
          queueRefresh(payload.scopes as Scope[]);
        }
        if (payload.type === "job.updated" && payload.job === "import_romaneio") {
          setImportJob((current) =>
            current && current.job_id === payload.job_id
              ? {
                  ...current,
                  stage: payload.stage,
                  message: payload.message,
                  error: payload.error || null,
                  updated_at: payload.ts,
                }
              : current,
          );
        }
      });
      socket.addEventListener("close", () => {
        reconnectTimer = window.setTimeout(connect, 3000);
      });
    };

    connect();
    return () => {
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  useEffect(() => {
    if (state.automation.estado !== "running") {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const payload = await fetchAutomationStatus();
        startTransition(() => {
          setState((current) => ({ ...current, automation: payload }));
        });
      } catch {
        // keep the latest visible status until the next successful poll
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [state.automation.estado]);

  useEffect(() => {
    const currentState = state.automation.estado || "idle";
    if (previousAutomationStateRef.current === "running" && currentState !== "running") {
      queueRefresh(["products", "totals", "brands", "automation"]);
    }
    previousAutomationStateRef.current = currentState;
  }, [state.automation.estado]);

  useEffect(() => {
    const shouldIgnoreUndoEvent = (target: EventTarget | null) => {
      const node = target as HTMLElement | null;
      if (!node) return false;
      if (node.isContentEditable) return true;
      const tagName = node.tagName;
      return tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT";
    };

    const handleUndoRedoKeydown = (event: KeyboardEvent) => {
      const key = String(event.key || "").toLowerCase();
      if (key !== "z") {
        return;
      }
      if (!(event.ctrlKey || event.metaKey) || event.altKey) {
        return;
      }
      if (shouldIgnoreUndoEvent(event.target)) {
        return;
      }
      event.preventDefault();
      if (event.shiftKey) {
        void redoLastAction();
      } else {
        void undoLastAction();
      }
    };

    document.addEventListener("keydown", handleUndoRedoKeydown);
    return () => document.removeEventListener("keydown", handleUndoRedoKeydown);
  }, []);

  useEffect(() => {
    if (!importJob?.job_id) {
      if (importPollTimer.current !== null) {
        window.clearInterval(importPollTimer.current);
        importPollTimer.current = null;
      }
      return;
    }

    if (importPollTimer.current !== null) {
      window.clearInterval(importPollTimer.current);
    }

    importPollTimer.current = window.setInterval(async () => {
      try {
        const job = await fetchImportStatus(importJob.job_id);
        setImportJob(job);
        if (job.stage === "completed") {
          const result = await fetchImportResult(job.job_id);
          setImportResult(result);
          setImporting(false);
          queueRefresh(["products", "totals", "brands"]);
        }
        if (job.stage === "completed" || job.stage === "error") {
          if (importPollTimer.current !== null) {
            window.clearInterval(importPollTimer.current);
            importPollTimer.current = null;
          }
          if (job.error) {
            setImportError(job.error);
            setImporting(false);
          }
        }
      } catch (error) {
        setImportError(error instanceof Error ? error.message : "Falha ao consultar status da importacao.");
      }
    }, 1000);

    return () => {
      if (importPollTimer.current !== null) {
        window.clearInterval(importPollTimer.current);
        importPollTimer.current = null;
      }
    };
  }, [importJob?.job_id]);

  useEffect(() => {
    if (!gradeModalOpen) return;
    if (!selectedGradeProduct) {
      setGradeDraft({});
      return;
    }
    setGradeDraft(gradeItemsToMap(selectedGradeProduct.grades));
    setGradeValidationError(null);
  }, [gradeModalOpen, gradeSelectedKey]);

  useEffect(() => {
    if (!groupedGradeSizes.length) {
      return;
    }
    if (!groupedGradeSizes.some((group) => group.key === activeGradeFamilyKey)) {
      setActiveGradeFamilyKey(groupedGradeSizes[0].key);
    }
  }, [activeGradeFamilyKey, groupedGradeSizes]);

  useEffect(() => {
    if (activeGradeFamilyKey) {
      window.localStorage.setItem(LAST_ACTIVE_GRADE_FAMILY_KEY, activeGradeFamilyKey);
    }
  }, [activeGradeFamilyKey]);

  const handleInputChange = <K extends keyof ProductPayload>(key: K, value: ProductPayload[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const focusProductField = (field: ProductFormField) => {
    visitedProductFields.current.add(field);
    const target =
      field === "nome"
        ? nameInputRef.current
        : field === "codigo"
          ? codeInputRef.current
          : field === "quantidade"
            ? quantityInputRef.current
            : priceInputRef.current;
    target?.focus();
    target?.select?.();
  };

  const getProductFormFieldOrder = (): ProductFormField[] => {
    const order: ProductFormField[] = ["nome"];
    if (!simpleModeEnabled) {
      order.push("codigo");
    }
    order.push("quantidade", "preco");
    return order;
  };

  const getNextProductField = (current: ProductFormField | null): ProductFormField | null => {
    const order = getProductFormFieldOrder();
    if (!current) {
      return order[0] ?? null;
    }
    const currentIndex = order.indexOf(current);
    if (currentIndex < 0) {
      return order[0] ?? null;
    }
    return order[currentIndex + 1] ?? null;
  };

  const getFirstMissingProductField = (): ProductFormField | null => {
    if (!String(form.nome || "").trim()) {
      return "nome";
    }
    if (!simpleModeEnabled && !String(form.codigo || "").trim()) {
      return "codigo";
    }
    const quantityValue = Number(form.quantidade);
    if (!Number.isFinite(quantityValue) || quantityValue < 1) {
      return "quantidade";
    }
    if (!String(form.preco || "").trim()) {
      return "preco";
    }
    return null;
  };

  const handleProductFormKeyDown = (event: React.KeyboardEvent<HTMLFormElement>) => {
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return;
    const target = event.target as HTMLInputElement | HTMLSelectElement | null;
    if (!target) return;
    const tag = target.tagName;
    if (tag !== "INPUT" && tag !== "SELECT") return;
    event.preventDefault();

    const fieldMap: Record<string, ProductFormField> = {
      nome: "nome",
      codigo: "codigo",
      quantidade: "quantidade",
      preco: "preco",
    };
    const currentField = fieldMap[target.name] ?? null;
    if (currentField) {
      visitedProductFields.current.add(currentField);
      const nextField = getNextProductField(currentField);
      if (nextField && !visitedProductFields.current.has(nextField)) {
        focusProductField(nextField);
        return;
      }
    }
    const missing = getFirstMissingProductField();
    if (missing) {
      if (currentField && missing === currentField) {
        focusProductField(missing);
        return;
      }
      if (currentField && missing !== currentField) {
        focusProductField(missing);
        return;
      }
      const nextField = getNextProductField(currentField);
      if (nextField) {
        focusProductField(nextField);
        return;
      }
      focusProductField(missing);
      return;
    }

    void submitProduct();
  };

  const resetListModes = (keep?: Partial<Record<"globalEdit" | "ordering" | "createSet", boolean>>) => {
    if (!keep?.globalEdit) setGlobalEditMode(false);
    if (!keep?.ordering) setOrderingMode(false);
    if (!keep?.createSet) setCreateSetMode(false);
  };

  const submitProduct = async () => {
    const missing = getFirstMissingProductField();
    if (missing) {
      focusProductField(missing);
      return;
    }
    setSubmitting(true);
    try {
      pushUndoSnapshot();
      await createProduct({
        ...form,
        codigo: simpleModeEnabled ? "" : form.codigo,
        marca: "",
        categoria: "",
        quantidade: Number(form.quantidade) || 0,
      });
      setForm({
        nome: "",
        codigo: "",
        quantidade: 1,
        preco: "",
        categoria: "",
        marca: "",
        preco_final: "",
        descricao_completa: "",
      });
      visitedProductFields.current.clear();
      queueRefresh(["products", "totals", "brands"]);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Falha ao criar produto.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitImport = async (file: File) => {
    setImporting(true);
    setImportError(null);
    setImportResult(null);
    setImportJob(null);
    setSelectedFile(file);
    try {
      pushUndoSnapshot();
      const started = await importRomaneio(file);
      const status = await fetchImportStatus(started.job_id);
      setImportJob(status);
    } catch (error) {
      setImporting(false);
      setImportError(error instanceof Error ? error.message : "Falha ao iniciar importacao.");
    }
  };

  const handleImportPrimaryClick = () => {
    if (importing) return;
    importInputRef.current?.click();
  };

  const handleImportFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    void submitImport(file);
  };

  const submitBrand = async () => {
    if (!newBrand.trim()) return;
    try {
      const normalized = newBrand.trim();
      const result = await addBrand(normalized);
      setNewBrand("");
      setShowBrandComposer(false);
      setBulkBrandValue(normalized);
      startTransition(() => {
        setState((current) => ({ ...current, brands: result.marcas }));
      });
      pushUndoSnapshot();
      await applyBrand(normalized);
      setShowBulkBrandMenu(false);
      queueRefresh(["products", "totals", "brands"]);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Falha ao adicionar marca.");
    }
  };

  const handleAutomationAction = async (mode: "catalog" | "complete" | "stop") => {
    setAutomationError(null);
    try {
      if (mode === "catalog") {
        await startAutomationCatalog();
      } else if (mode === "complete") {
        await startAutomationComplete();
      } else {
        await stopAutomation();
      }
      queueRefresh(["automation"]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Falha na automacao.";
      setAutomationError(message);
    }
  };

  const buildIncompleteGradesAlert = () => {
    const sample = incompleteGradeProducts
      .slice(0, 3)
      .map(({ product, total, expected }) => `${product.nome} (${total}/${expected})`)
      .join("\n");
    const remaining = incompleteGradeProducts.length - Math.min(incompleteGradeProducts.length, 3);
    const more = remaining > 0 ? `\nE mais ${remaining} item(ns).` : "";
    return `Ainda existem grades pendentes.\n\nCorrija antes de usar o Cadastro Completo:\n${sample}${more}`;
  };

  const handleStartComplete = async () => {
    if (incompleteGradeProducts.length) {
      const firstPendingKey = incompleteGradeProducts[0]?.product.ordering_key || null;
      window.alert(`${buildIncompleteGradesAlert()}\n\nVou abrir o Inserir Grade no primeiro item pendente.`);
      await openGradeModal(firstPendingKey);
      return;
    }
    await handleAutomationAction("complete");
  };

  const handleClearProducts = async () => {
    const confirmed = window.confirm("Limpar toda a lista ativa?");
    if (!confirmed) return;
    pushUndoSnapshot();
    await clearProducts();
    queueRefresh(["products", "totals", "brands"]);
  };

  const handleApplyCategory = async (value?: string) => {
    const category = (value ?? bulkCategoryValue).trim();
    if (!category) {
      window.alert("Selecione uma categoria antes de aplicar.");
      return;
    }
    setBulkCategoryValue(category);
    pushUndoSnapshot();
    await applyCategory(category);
    setShowBulkCategoryMenu(false);
    queueRefresh(["products", "totals"]);
  };

  const handleApplyBrand = async (value?: string) => {
    const brand = (value ?? bulkBrandValue).trim();
    if (!brand) {
      window.alert("Selecione uma marca antes de aplicar.");
      return;
    }
    setBulkBrandValue(brand);
    pushUndoSnapshot();
    await applyBrand(brand);
    setShowBulkBrandMenu(false);
    queueRefresh(["products", "totals", "brands"]);
  };

  const handleJoinDuplicates = async () => {
    pushUndoSnapshot();
    const result = await joinDuplicates();
    queueRefresh(["products", "totals"]);
    window.alert(`Originais: ${result.originais}\nResultantes: ${result.resultantes}\nRemovidos: ${result.removidos}`);
  };

  const handleJoinGrades = async () => {
    pushUndoSnapshot();
    const result = await joinGrades();
    queueRefresh(["products", "totals"]);
    window.alert(`Produtos finais: ${result.resultantes}\nGrades atualizadas: ${result.atualizados_grades}\nLinhas unificadas: ${result.removidos}`);
  };

  const handleMargin = async () => {
    const raw = window.prompt("Margem percentual para venda:", state.marginPercentual.toFixed(2));
    if (raw == null) return;
    const percentual = Number(String(raw).replace(",", "."));
    if (!Number.isFinite(percentual) || percentual <= 0) {
      window.alert("Informe um percentual valido.");
      return;
    }
    pushUndoSnapshot();
    await saveMargin(percentual);
    const result = await applyMargin(percentual);
    queueRefresh(["products", "totals", "margin"]);
    window.alert(`Margem aplicada: ${result.percentual_utilizado.toFixed(2)}%\nProdutos atualizados: ${result.total_atualizados}`);
  };

  const handleFormatCodes = async () => {
    const payload = {
      remover_prefixo5: false,
      remover_zeros_a_esquerda: false,
      manter_primeiros_caracteres: null,
      manter_ultimos_caracteres: null,
      remover_primeiros_caracteres: null,
      remover_ultimos_caracteres: null,
      remover_letras: false,
      remover_numeros: false,
      remover_ultimos_numeros: parsePromptInteger(formatCodesOptions.remover_ultimos_numeros),
      remover_primeiros_numeros: parsePromptInteger(formatCodesOptions.remover_primeiros_numeros),
      ultimos_digitos: null,
      primeiros_digitos: null,
    };
    const hasAnyOption = Object.entries(payload).some(([key, value]) => {
      if (key === "remover_prefixo5" || key === "remover_zeros_a_esquerda") {
        return false;
      }
      if (key.startsWith("remover_") || key.startsWith("manter_")) {
        if (typeof value === "boolean") return value;
        return value !== null;
      }
      return false;
    });
    if (!hasAnyOption) {
      window.alert("Escolha pelo menos uma opcao para cortar numeros do codigo.");
      return;
    }
    pushUndoSnapshot();
    const result = await formatCodes(payload);
    queueRefresh(["products"]);
    setShowFormatCodesPanel(false);
    window.alert(`Total analisado: ${result.total}\nAlterados: ${result.alterados}${result.prefixo ? `\nPrefixo removido: ${result.prefixo}` : ""}`);
  };

  const handleImproveDescriptions = async () => {
    const termos = Array.from(new Set(descriptionOptions.remover_termos.split(",").map((item) => item.trim()).filter(Boolean)));
    if (!descriptionOptions.remover_numeros && !descriptionOptions.remover_especiais && !descriptionOptions.remover_letras && !termos.length) {
      window.alert("Selecione ao menos uma regra de limpeza.");
      return;
    }
    pushUndoSnapshot();
    const result = await improveDescriptions({
      remover_numeros: descriptionOptions.remover_numeros,
      remover_especiais: descriptionOptions.remover_especiais,
      remover_letras: descriptionOptions.remover_letras,
      remover_termos: termos,
    });
    queueRefresh(["products"]);
    setShowDescriptionPanel(false);
    window.alert(`Descricoes analisadas: ${result.total}\nDescricoes modificadas: ${result.modificados}`);
  };

  const handleExecuteGrades = async () => {
    await executeGradesProducts();
    queueRefresh(["automation"]);
  };

  const handleStopGrades = async () => {
    await stopGradesExecution();
    queueRefresh(["automation"]);
  };

  const openGradeModal = async (preferredOrderingKey?: string | null) => {
    if (!state.products.length) {
      window.alert("Nao ha itens na lista para inserir grades.");
      return;
    }
    const [sizesPayload, configPayload] = await Promise.all([fetchCatalogSizes(), fetchGradeConfig()]);
    const visualOrder = buildVisualSizeOrder(configPayload, sizesPayload.sizes || [], state.products);
    const shouldMigratePreset = Number(configPayload.ui_family_version || 0) < GRADE_UI_VERSION;
    const seededFamilies = shouldMigratePreset ? buildDefaultUiFamilies(visualOrder) : Array.isArray(configPayload.ui_families) && configPayload.ui_families.length ? configPayload.ui_families : buildDefaultUiFamilies(visualOrder);
    const familiesDraft = normalizeUiFamiliesDraft(seededFamilies, visualOrder);
    const flattenedOrder = familiesDraft.flatMap((family) => family.sizes);
    setGradeModalError(null);
    setGradeSizesCatalog(sizesPayload.sizes || []);
    setGradeConfig(configPayload);
    setGradeOrderDraft(flattenedOrder);
    setGradeFamiliesDraft(familiesDraft);
    setNewGradeSize("");
    setGradeSelectedKey((current) => {
      if (preferredOrderingKey && productsByKey.has(preferredOrderingKey)) {
        return preferredOrderingKey;
      }
      if (current && productsByKey.has(current)) {
        return current;
      }
      return state.products[0]?.ordering_key ?? null;
    });
    setGradeModalOpen(true);
    if (shouldMigratePreset) {
      void saveGradeConfig({
        ...configPayload,
        ui_size_order: flattenedOrder,
        ui_families: familiesDraft,
        ui_family_version: GRADE_UI_VERSION,
      }).then((response) => {
        setGradeConfig(response.config);
      }).catch(() => {
        // keep the modal usable even if migration persistence fails
      });
    }
  };

  const closeGradeModal = () => {
    setGradeModalOpen(false);
    setGradeModalError(null);
  };

  const persistVisualFamilies = async (nextFamilies: UiGradeFamily[]) => {
    const normalizedFamilies = normalizeUiFamiliesDraft(nextFamilies, orderedGradeSizes);
    const flattenedOrder = normalizedFamilies.flatMap((family) => family.sizes);
    const requestSeq = ++gradeConfigSaveSeq.current;
    setGradeFamiliesDraft(normalizedFamilies);
    setGradeOrderDraft(flattenedOrder);
    try {
      const nextConfig = { ...(gradeConfig || {}), ui_size_order: flattenedOrder, ui_families: normalizedFamilies };
      nextConfig.ui_family_version = GRADE_UI_VERSION;
      const response = await saveGradeConfig(nextConfig);
      if (requestSeq === gradeConfigSaveSeq.current) {
        setGradeConfig(response.config);
        setGradeModalError(null);
      }
    } catch (error) {
      if (requestSeq === gradeConfigSaveSeq.current) {
        setGradeModalError(error instanceof Error ? error.message : "Falha ao salvar ordem visual dos tamanhos.");
      }
    }
  };

  const moveVisualSize = async (familyId: string, size: string, direction: -1 | 1) => {
    const targetFamily = gradeFamiliesDraft.find((family) => family.id === familyId);
    if (!targetFamily) {
      return;
    }
    const index = targetFamily.sizes.indexOf(size);
    if (index < 0) {
      return;
    }
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= targetFamily.sizes.length) {
      return;
    }
    const nextFamilies = gradeFamiliesDraft.map((family) =>
      family.id === familyId ? { ...family, sizes: [...family.sizes] } : { ...family, sizes: [...family.sizes] },
    );
    const currentFamily = nextFamilies.find((family) => family.id === familyId);
    if (!currentFamily) {
      return;
    }
    const [item] = currentFamily.sizes.splice(index, 1);
    currentFamily.sizes.splice(nextIndex, 0, item);
    await persistVisualFamilies(nextFamilies);
  };

  const addVisualSize = async () => {
    const normalized = normalizeGradeSizeLabel(newGradeSize);
    if (!normalized) {
      return;
    }
    if (gradeOrderDraft.includes(normalized)) {
      setNewGradeSize("");
      return;
    }
    const targetFamilyId = activeGradeFamily?.key || gradeFamiliesDraft[0]?.id || "common";
    const nextFamilies = gradeFamiliesDraft.length
      ? gradeFamiliesDraft.map((family) =>
          family.id === targetFamilyId ? { ...family, sizes: [...family.sizes, normalized] } : { ...family, sizes: [...family.sizes] },
        )
      : [{ id: "common", label: "Mais usadas", sizes: [normalized] }];
    await persistVisualFamilies(nextFamilies);
    setNewGradeSize("");
  };

  const renameFamily = async (familyId: string, label: string) => {
    const nextFamilies = gradeFamiliesDraft.map((family) =>
      family.id === familyId ? { ...family, label: label.trim() || family.label } : { ...family, sizes: [...family.sizes] },
    );
    await persistVisualFamilies(nextFamilies);
  };

  const handleFamilyLabelChange = (familyId: string, label: string) => {
    const nextFamilies = gradeFamiliesDraft.map((family) =>
      family.id === familyId ? { ...family, label } : { ...family, sizes: [...family.sizes] },
    );
    void persistVisualFamilies(nextFamilies);
  };

  const addFamily = async () => {
    const nextId = `family-${Date.now()}`;
    await persistVisualFamilies([...gradeFamiliesDraft.map((family) => ({ ...family, sizes: [...family.sizes] })), { id: nextId, label: "Nova familia", sizes: [] }]);
    setActiveGradeFamilyKey(nextId);
  };

  const renameSizeInFamily = async (familyId: string, currentSize: string) => {
    const raw = window.prompt("Novo nome para o tamanho:", currentSize);
    if (raw === null) return;
    const normalized = normalizeGradeSizeLabel(raw);
    if (!normalized) return;
    const nextFamilies = gradeFamiliesDraft.map((family) => ({
      ...family,
      sizes: family.sizes.map((size) => (family.id === familyId && size === currentSize ? normalized : size)),
    }));
    setGradeDraft((current) => {
      const next = { ...current };
      if (current[currentSize] !== undefined) {
        next[normalized] = current[currentSize];
        delete next[currentSize];
      }
      return next;
    });
    await persistVisualFamilies(nextFamilies);
  };

  const moveSizeBetweenFamilies = async (familyId: string, size: string, direction: -1 | 1) => {
    const familyIndex = gradeFamiliesDraft.findIndex((family) => family.id === familyId);
    const nextFamilyIndex = familyIndex + direction;
    if (familyIndex < 0 || nextFamilyIndex < 0 || nextFamilyIndex >= gradeFamiliesDraft.length) {
      return;
    }
    const nextFamilies = gradeFamiliesDraft.map((family) => ({ ...family, sizes: [...family.sizes] }));
    const source = nextFamilies[familyIndex];
    const target = nextFamilies[nextFamilyIndex];
    source.sizes = source.sizes.filter((item) => item !== size);
    if (!target.sizes.includes(size)) {
      target.sizes.push(size);
    }
    await persistVisualFamilies(nextFamilies);
  };

  const removeSizeFromFamilies = async (size: string) => {
    const nextFamilies = gradeFamiliesDraft
      .map((family) => ({ ...family, sizes: family.sizes.filter((item) => item !== size) }))
      .filter((family) => family.sizes.length || family.label.trim());
    setGradeDraft((current) => {
      const next = { ...current };
      delete next[size];
      return next;
    });
    await persistVisualFamilies(nextFamilies);
  };

  const updateGradeDraftValue = (size: string, value: string) => {
    setGradeValidationError(null);
    setGradeDraft((current) => ({ ...current, [size]: value.replace(/[^\d]/g, "") }));
  };

  const validateSelectedGrade = () => {
    if (!selectedGradeProduct) {
      return { ok: false, message: "Nenhum item selecionado." };
    }
    const expected = Number(selectedGradeProduct.quantidade || 0);
    const total = currentGradeTotal;
    if (total !== expected) {
      return {
        ok: false,
        message: `A grade ainda nao fecha com a quantidade do item. Grade: ${total}. Quantidade do produto: ${expected}.`,
      };
    }
    return { ok: true, message: null };
  };

  const getProductGradeStatus = (product: Product) => {
    const total = product.ordering_key === gradeSelectedKey ? currentGradeTotal : (product.grades || []).reduce((sum, item) => sum + Number(item.quantidade || 0), 0);
    const expected = Number(product.quantidade || 0);
    const complete = total === expected && expected > 0;
    const hasAny = total > 0;
    const overflow = total > expected;
    return { total, expected, complete, hasAny, overflow };
  };

  const focusFirstActiveGradeInput = () => {
    const firstSize = activeGradeFamily?.items[0];
    if (!firstSize) {
      return;
    }
    const input = gradeInputRefs.current[firstSize];
    input?.focus();
    input?.select?.();
  };

  const handleGradeStartTab = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Tab" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    focusFirstActiveGradeInput();
  };

  const handleGradeInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.altKey || event.metaKey) {
      return;
    }
    event.preventDefault();
    void runBusyAction("salvar-proxima-grade", handleSaveAndNextGrade);
  };

  const saveSelectedGrade = async () => {
    if (!selectedGradeProduct) {
      return false;
    }
    const validation = validateSelectedGrade();
    if (!validation.ok) {
      setGradeValidationError(validation.message);
      return false;
    }
    const grades = Object.entries(gradeDraft)
      .map(([tamanho, quantidade]) => ({ tamanho, quantidade: Number.parseInt(quantidade, 10) || 0 }))
      .filter((item) => item.quantidade > 0);
    pushUndoSnapshot();
    await patchProduct(selectedGradeProduct.ordering_key, { grades });
    setGradeValidationError(null);
    queueRefresh(["products", "totals"]);
    return true;
  };

  const handleSaveSelectedGrade = async () => {
    await saveSelectedGrade();
  };

  const handleSaveAndNextGrade = async () => {
    if (!selectedGradeProduct) {
      return;
    }
    const saved = await saveSelectedGrade();
    if (!saved) {
      return;
    }
    const currentIndex = state.products.findIndex((product) => product.ordering_key === selectedGradeProduct.ordering_key);
    const nextProduct = state.products[currentIndex + 1] ?? state.products[0] ?? null;
    pendingGradeInputFocus.current = true;
    setGradeSelectedKey(nextProduct?.ordering_key ?? null);
  };

  const handleClearSelectedGrade = async () => {
    if (!selectedGradeProduct) {
      return;
    }
    pushUndoSnapshot();
    await patchProduct(selectedGradeProduct.ordering_key, { grades: [] });
    setGradeDraft({});
    setGradeValidationError(null);
    queueRefresh(["products", "totals"]);
  };

  const handleClearAllGrades = async () => {
    const confirmed = window.confirm("Limpar todas as grades cadastradas?\nClique em OK para confirmar.");
    if (!confirmed) {
      return;
    }
    pushUndoSnapshot();
    const productsWithGrades = state.products.filter((product) => (product.grades || []).length > 0 || product.ordering_key === gradeSelectedKey);
    await Promise.all(productsWithGrades.map((product) => patchProduct(product.ordering_key, { grades: [] })));
    setGradeDraft({});
    setGradeValidationError(null);
    queueRefresh(["products", "totals"]);
  };

  useEffect(() => {
    if (!gradeModalOpen || !pendingGradeInputFocus.current) {
      return;
    }
    pendingGradeInputFocus.current = false;
    const timer = window.setTimeout(() => {
      focusFirstActiveGradeInput();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [gradeModalOpen, gradeSelectedKey, activeGradeFamilyKey]);

  const handleToggleSimpleMode = () => {
    setSimpleModeEnabled((current) => !current);
    setShowBrandComposer(false);
  };

  const handleToggleGlobalEdit = () => {
    const next = !globalEditMode;
    resetListModes(next ? { globalEdit: true } : undefined);
    setGlobalEditMode(next);
  };

  const handleToggleOrdering = async () => {
    if (!orderingMode) {
      resetListModes({ ordering: true });
      setOrderingSelectedKeys([]);
      setOrderingMode(true);
      return;
    }
    const finalOrder = [...orderingSelectedKeys, ...originalOrderingKeys.filter((key) => !orderingSelectedKeys.includes(key))];
    if (finalOrder.length) {
      pushUndoSnapshot();
      await reorderProducts(finalOrder);
      queueRefresh(["products"]);
    }
    setOrderingMode(false);
    setOrderingSelectedKeys([]);
  };

  const handleOrderingSelection = (orderingKey: string, options?: { allowRemove?: boolean }) => {
    if (!orderingMode) return;
    setOrderingSelectedKeys((current) => {
      if (current.includes(orderingKey)) {
        if (!options?.allowRemove) {
          return current;
        }
        return current.filter((item) => item !== orderingKey);
      }
      return [...current, orderingKey];
    });
  };

  const moveOrderingItem = (orderingKey: string, _direction: -1 | 1) => {
    handleOrderingSelection(orderingKey);
  };

  const handleToggleCreateSets = () => {
    const next = !createSetMode;
    resetListModes(next ? { createSet: true } : undefined);
    setCreateSetMode(next);
  };

  const handleCreateSetSelection = async (orderingKey: string) => {
    if (!createSetMode) return;
    const futureKeys = createSetKeys.includes(orderingKey)
      ? createSetKeys.filter((item) => item !== orderingKey)
      : [...createSetKeys, orderingKey].slice(-2);
    setCreateSetKeys(futureKeys);
    if (futureKeys.length === 2) {
      pushUndoSnapshot();
      const result = await createSet(futureKeys[0], futureKeys[1]);
      setCreateSetMode(false);
      setCreateSetKeys([]);
      queueRefresh(["products", "totals"]);
      window.alert(`Conjunto criado: ${result.created}\nLinhas removidas: ${result.removed}`);
    }
  };

  const startInlineEdit = (product: Product, field: EditableField) => {
    const value = field === "preco_final" ? product.preco_final || "" : String(product[field] || "");
    setEditingCell({ orderingKey: product.ordering_key, field, value });
  };

  const handleInlineEditChange = (value: string) => {
    setEditingCell((current) => {
      if (!current) return current;
      const next = { ...current, value };
      const nextProducts = state.products.map((product) =>
        product.ordering_key === current.orderingKey ? buildProductPreview(product, current.field, value) : product,
      );
      applyProductsPreview(nextProducts);
      return next;
    });
  };

  const commitInlineEdit = async () => {
    if (!editingCell) return;
    const { orderingKey, field, value } = editingCell;
    let payload: Partial<ProductPayload> = {};
    if (field === "quantidade") {
      const quantity = Number.parseInt(value, 10);
      if (!Number.isFinite(quantity) || quantity < 0) {
        window.alert("Quantidade invalida.");
        return;
      }
      payload = { quantidade: quantity };
    } else if (field === "preco_final") {
      payload = { preco_final: value.trim() || null };
    } else if (field === "preco") {
      payload = { preco: value.trim() };
    } else if (field === "nome") {
      payload = { nome: value.trim() };
    } else if (field === "marca") {
      payload = { marca: value.trim() };
    } else if (field === "codigo") {
      payload = { codigo: value.trim() };
    } else if (field === "categoria") {
      payload = { categoria: value.trim() };
    }

    try {
      pushUndoSnapshot();
      await patchProduct(orderingKey, payload);
      setEditingCell(null);
      queueRefresh(["products", "totals", "brands"]);
    } catch (error) {
      setEditingCell(null);
      queueRefresh(["products", "totals", "brands"]);
      window.alert(error instanceof Error ? error.message : "Falha ao atualizar item.");
    }
  };

  const cancelInlineEdit = () => {
    setEditingCell(null);
    queueRefresh(["products", "totals", "brands"]);
  };

  const handleInlineEditKeyDown = (event: React.KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void commitInlineEdit();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      cancelInlineEdit();
    }
  };

  const runBusyAction = async (name: string, action: () => Promise<void>) => {
    if (busyAction) return;
    setBusyAction(name);
    try {
      await action();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : `Falha em ${name}.`);
    } finally {
      setBusyAction(null);
    }
  };

  const loadSettingsModal = async () => {
    setSettingsLoading(true);
    setSettingsError(null);
    setSettingsMessage(null);
    try {
      const [targetsPayload, gradeConfigPayload] = await Promise.all([fetchAutomationTargets(), fetchGradeConfig()]);
      setSettingsTargets(targetsPayload || {});
      setSettingsGradeConfig(normalizeGradeConfigState(gradeConfigPayload));
      setSettingsContextText("");
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Falha ao carregar configuracoes.");
    } finally {
      setSettingsLoading(false);
    }
  };

  const openSettingsModal = async () => {
    setSettingsOpen(true);
    await loadSettingsModal();
  };

  const closeSettingsModal = () => {
    setSettingsOpen(false);
    setSettingsError(null);
    setSettingsMessage(null);
    setSettingsCaptureLabel(null);
    setSettingsCaptureCountdown(null);
  };

  const waitSettingsCapture = async (label: string) => {
    setSettingsCaptureLabel(label);
    setSettingsError(null);
    setSettingsMessage(`Posicione o mouse no alvo "${label}". Captura em 3 segundos.`);
    for (const countdown of [3, 2, 1]) {
      setSettingsCaptureCountdown(countdown);
      await new Promise<void>((resolve) => window.setTimeout(resolve, 1000));
    }
    setSettingsCaptureCountdown(null);
    const captured = await captureAutomationTarget(label);
    setSettingsCaptureLabel(null);
    return captured.point;
  };

  const handleSettingsTargetChange = (key: keyof AutomationTargets, value: string | TargetPoint | null) => {
    setSettingsTargets((current) => ({ ...current, [key]: value }));
  };

  const handleSettingsGradeConfigChange = (updater: (current: GradeConfig) => GradeConfig) => {
    setSettingsGradeConfig((current) => normalizeGradeConfigState(updater(current)));
  };

  const handleSaveSettingsTargets = async () => {
    setSettingsSaving("targets");
    setSettingsError(null);
    try {
      const saved = await saveAutomationTargets(settingsTargets);
      setSettingsTargets(saved);
      setSettingsMessage("Targets salvos com sucesso.");
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Falha ao salvar targets.");
    } finally {
      setSettingsSaving(null);
    }
  };

  const handleSaveSettingsGradeConfig = async () => {
    setSettingsSaving("grade-config");
    setSettingsError(null);
    try {
      const saved = await saveGradeConfig(normalizeGradeConfigState(settingsGradeConfig));
      setSettingsGradeConfig(normalizeGradeConfigState(saved.config));
      setSettingsMessage("Configuracao de grades salva com sucesso.");
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Falha ao salvar configuracao de grades.");
    } finally {
      setSettingsSaving(null);
    }
  };

  const handleCaptureSettingsTarget = async (key: AutomationTargetKey, label: string) => {
    setSettingsSaving(`capture-target-${key}`);
    try {
      const point = await waitSettingsCapture(key);
      const nextTargets = { ...settingsTargets, [key]: point };
      const saved = await saveAutomationTargets(nextTargets);
      setSettingsTargets(saved);
      setSettingsMessage(`${label} capturado em ${formatTargetPoint(point)}.`);
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : `Falha ao capturar ${label}.`);
    } finally {
      setSettingsSaving(null);
    }
  };

  const handleCaptureSettingsGradeButton = async (key: GradeCaptureKey, label: string) => {
    setSettingsSaving(`capture-grade-${key}`);
    try {
      const point = await waitSettingsCapture(key);
      const nextConfig = normalizeGradeConfigState({
        ...settingsGradeConfig,
        buttons: {
          ...(settingsGradeConfig.buttons || {}),
          [key]: point,
        },
      });
      const saved = await saveGradeConfig(nextConfig);
      setSettingsGradeConfig(normalizeGradeConfigState(saved.config));
      setSettingsMessage(`${label} capturado em ${formatTargetPoint(point)}.`);
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : `Falha ao capturar ${label}.`);
    } finally {
      setSettingsSaving(null);
    }
  };

  const handleCaptureFirstQuantCell = async () => {
    setSettingsSaving("capture-first-quant");
    try {
      const point = await waitSettingsCapture("first_quant_cell");
      const nextConfig = normalizeGradeConfigState({
        ...settingsGradeConfig,
        first_quant_cell: point,
      });
      const saved = await saveGradeConfig(nextConfig);
      setSettingsGradeConfig(normalizeGradeConfigState(saved.config));
      setSettingsMessage(`Primeira celula de quantidade capturada em ${formatTargetPoint(point)}.`);
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Falha ao capturar a primeira celula.");
    } finally {
      setSettingsSaving(null);
    }
  };

  const handleSettingsContextRefresh = async () => {
    setSettingsSaving("context");
    setSettingsError(null);
    try {
      const payload = await fetchByteEmpresaContext();
      setSettingsContextText(formatJsonBlock(payload));
      setSettingsMessage("Contexto do ByteEmpresa carregado.");
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Falha ao consultar contexto do ByteEmpresa.");
    } finally {
      setSettingsSaving(null);
    }
  };

  const handleSettingsPrepare = async () => {
    setSettingsSaving("prepare");
    setSettingsError(null);
    try {
      const payload = await prepareByteEmpresa();
      setSettingsContextText(formatJsonBlock(payload));
      setSettingsMessage("Preparacao do ByteEmpresa executada.");
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Falha ao preparar a janela do ByteEmpresa.");
    } finally {
      setSettingsSaving(null);
    }
  };

  const isFieldEditable = (_field: EditableField) => globalEditMode;

  const renderCellContent = (product: Product, field: EditableField, displayValue: string | number) => {
    if (!isFieldEditable(field)) {
      return field === "nome" ? <strong>{displayValue || "-"}</strong> : <>{displayValue || "-"}</>;
    }
    const isEditing = editingCell?.orderingKey === product.ordering_key && editingCell.field === field;
    if (isEditing) {
      if (field === "categoria") {
        return (
          <select
            ref={inlineEditInputRef as React.RefObject<HTMLSelectElement>}
            className="cellEditInput"
            value={editingCell.value}
            onChange={(event) => handleInlineEditChange(event.target.value)}
            onBlur={() => void commitInlineEdit()}
            onKeyDown={handleInlineEditKeyDown}
          >
            <option value="">Selecionar...</option>
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        );
      }
      if (field === "marca") {
        return (
          <select
            ref={inlineEditInputRef as React.RefObject<HTMLSelectElement>}
            className="cellEditInput"
            value={editingCell.value}
            onChange={(event) => handleInlineEditChange(event.target.value)}
            onBlur={() => void commitInlineEdit()}
            onKeyDown={handleInlineEditKeyDown}
          >
            <option value="">Selecionar...</option>
            {sortedBrands.map((brand) => (
              <option key={brand} value={brand}>{brand}</option>
            ))}
          </select>
        );
      }
      return (
        <input
          ref={inlineEditInputRef as React.RefObject<HTMLInputElement>}
          className={`cellEditInput ${field === "quantidade" || field === "preco" || field === "preco_final" ? "numericCellEditInput" : ""}`}
          value={editingCell.value}
          onChange={(event) => handleInlineEditChange(event.target.value)}
          onBlur={() => void commitInlineEdit()}
          onKeyDown={handleInlineEditKeyDown}
          inputMode={field === "quantidade" ? "numeric" : field === "preco" || field === "preco_final" ? "decimal" : "text"}
        />
      );
    }
    return (
      <button
        className={`cellActionButton ${field === "nome" ? "nameCellButton" : ""}`}
        type="button"
        onClick={() => startInlineEdit(product, field)}
      >
        {field === "nome" ? <strong>{displayValue || "-"}</strong> : displayValue || "-"}
      </button>
    );
  };

  const automationIsRunning = state.automation.estado === "running";
  const automationCurrentOrderingKey = state.automation.ordering_key_atual || null;
  const automationCurrentName = state.automation.produto_atual || null;
  const automationTypedDescription = state.automation.descricao_digitada || null;
  const automationProgressWidth = automationIsRunning
    ? state.automation.item_atual && state.automation.total_itens && state.automation.total_itens > 0
      ? `${Math.max(8, Math.min(100, Math.round((state.automation.item_atual / state.automation.total_itens) * 100)))}%`
      : "68%"
    : "22%";

  return (
    <div className="shell">
      <main className="appShellTs">
        <aside className="leftPanelTs">
          <div className="actionsFloatingTs">
            <div className="panelActionCompact">
              <button className="iconShellButton" type="button" title="Configuracoes" onClick={() => void openSettingsModal()}>
                CFG
              </button>
              <button className={`ghostButton compactButton ${simpleModeEnabled ? "activeToggle" : ""}`} type="button" onClick={handleToggleSimpleMode}>
                {simpleModeEnabled ? "Modo completo" : "Modo simplificado"}
              </button>
            </div>

            <div className="importStageTs">
              <button className="primaryButton fullButton importButtonTs" disabled={importing} onClick={() => void handleImportPrimaryClick()}>
                {importing ? "Importando..." : "Importar Romaneio"}
              </button>
              <label className="fileInput compactFileInput">
                <span>{selectedFile ? selectedFile.name : "Selecionar arquivo do romaneio"}</span>
                <input
                  ref={importInputRef}
                  type="file"
                  accept=".pdf,.txt,.jpg,.jpeg,.png"
                  onChange={handleImportFileChange}
                />
              </label>
              {importing ? <div className="message subtle">Importacao em andamento...</div> : null}
              {!importing && importJob?.message ? <div className="message subtle">{importJob.message}</div> : null}
              {importError ? <div className="message error">{importError}</div> : null}
              {importResult ? <div className="message success">{importResult.total_itens} itens importados as {formatTimestamp(importJob?.updated_at)}.</div> : null}
            </div>
          </div>

          <section className="editorStageTs">
            <form className="productFormTs" onSubmit={(event) => event.preventDefault()} onKeyDown={handleProductFormKeyDown}>
              <div className={`formGridTs ${simpleModeEnabled ? "simpleModeGrid" : ""}`}>
                <label className="inputFieldTs fieldNameTs">
                  <span>Nome</span>
                  <input ref={nameInputRef} name="nome" value={form.nome} onChange={(event) => handleInputChange("nome", event.target.value)} placeholder="Ex.: Bolsa Couro" />
                </label>
                {!simpleModeEnabled ? (
                  <label className="inputFieldTs fieldCodeTs">
                    <span>Codigo</span>
                    <input ref={codeInputRef} name="codigo" value={form.codigo} onChange={(event) => handleInputChange("codigo", event.target.value)} placeholder="000000" />
                  </label>
                ) : null}
                <label className="inputFieldTs fieldQuantityTs">
                  <span>Quantidade</span>
                  <input
                    ref={quantityInputRef}
                    name="quantidade"
                    type="number"
                    min={0}
                    value={form.quantidade}
                    onChange={(event) => handleInputChange("quantidade", Number(event.target.value) || 0)}
                  />
                </label>
                <label className="inputFieldTs fieldPriceTs">
                  <span>Custo</span>
                  <input ref={priceInputRef} name="preco" value={form.preco} onChange={(event) => handleInputChange("preco", event.target.value)} placeholder="R$ 0,00" />
                </label>
              </div>

            </form>
          </section>

          <section className="marginStageTs">
            <button className="toolButtonTs warning fullWidthToolButton" type="button" onClick={() => void runBusyAction("margem", handleMargin)}>
              Margem <span className="marginBadgeTs">{state.marginPercentual.toFixed(1)}%</span>
            </button>
          </section>

          <section className="summaryStageTs">
            <div className="stageHeaderTs">
              <span className="sectionTag">Resumo operacional</span>
            </div>

            <div className="totalsBoardTs">
              <article className="totalsSectionTs">
                <div className="totalsSectionHeadTs">
                  <span className="totalsGroupTitleTs">Sessao atual</span>
                  <span className="totalsChipTs live">ao vivo</span>
                </div>
                <div className="totalsRowsTs">
                  <div className="totalsRowTs"><span>Quantidade</span><strong>{state.totalsRaw.atualQuantidade}</strong></div>
                  <div className="totalsRowTs"><span>Custo total</span><strong>{state.totalsText.atualCusto}</strong></div>
                  <div className="totalsRowTs"><span>Venda total</span><strong>{state.totalsText.atualVenda}</strong></div>
                </div>
              </article>

              <article className="totalsSectionTs">
                <div className="totalsSectionHeadTs">
                  <span className="totalsGroupTitleTs">Acumulado global</span>
                  <span className="totalsChipTs muted">historico</span>
                </div>
                <div className="totalsRowsTs">
                  <div className="totalsRowTs"><span>Quantidade</span><strong>{state.totalsRaw.historicoQuantidade}</strong></div>
                  <div className="totalsRowTs"><span>Custo total</span><strong>{state.totalsText.historicoCusto}</strong></div>
                  <div className="totalsRowTs"><span>Venda total</span><strong>{state.totalsText.historicoVenda}</strong></div>
                  <div className="totalsRowTs"><span>Tempo poupado</span><strong>{state.totalsText.tempo}</strong></div>
                  <div className="totalsRowTs"><span>Caracteres evitados</span><strong>{state.totalsRaw.caracteres.toLocaleString("pt-BR")}</strong></div>
                </div>
              </article>
            </div>
          </section>
        </aside>

        <section className="rightPanelTs">
          <section className="batchControlsTs">
            <div className="batchPrimaryTs">
              <span className="sectionTag">Centro de execucao</span>
              <div className="batchPrimaryActionsTs">
                <button className="actionButtonTs highlight large" type="button" onClick={() => void runBusyAction("cadastro-completo", handleStartComplete)}>
                  Cadastro Completo
                </button>
                <button className="actionButtonTs highlight" type="button" onClick={() => void runBusyAction("executar-grades", handleExecuteGrades)}>
                  Executar Grades
                </button>
                <button className="actionButtonTs accent large" type="button" onClick={() => void runBusyAction("cadastro-massa", async () => handleAutomationAction("catalog"))}>
                  Executar Cadastro em Massa
                </button>
                <button className="actionButtonTs danger" type="button" onClick={() => void runBusyAction("parar", async () => handleAutomationAction("stop"))}>
                  Parar
                </button>
              </div>
            </div>

            <div className="batchRightRail">
              <div className="batchUtilityActionsTs">
                <button className="toolButtonTs accent" type="button" onClick={() => void runBusyAction("juntar-grades", handleJoinGrades)}>Juntar Grades</button>
                <button className="toolButtonTs accent" type="button" onClick={() => void runBusyAction("inserir-grade", openGradeModal)}>Inserir Grade</button>
              </div>
              <div className="progressSummaryTs">
                <span className="sectionTag">Status da automacao</span>
                <strong>Estado: {state.automation.estado || "idle"}</strong>
                {state.automation.message ? <span className="automationStatusText">{state.automation.message}</span> : null}
                <div className="progressBarTs">
                  <div className="progressFillTs" style={{ width: automationProgressWidth }} />
                </div>
                {automationIsRunning && automationCurrentName ? (
                  <div className="automationCurrentCard">
                    <span className="automationCurrentLabel">Item em execucao</span>
                    <strong>{automationCurrentName}</strong>
                    {state.automation.item_atual && state.automation.total_itens ? (
                      <small>{`Item ${state.automation.item_atual} de ${state.automation.total_itens}`}</small>
                    ) : null}
                    {automationTypedDescription ? <small>{`Texto enviado: ${automationTypedDescription}`}</small> : null}
                  </div>
                ) : null}
                {automationError ? <div className="miniError">{automationError}</div> : null}
                {incompleteGradeProducts.length ? (
                  <div className="miniWarning">{`Cadastro Completo bloqueado: ${incompleteGradeProducts.length} item(ns) com grade pendente.`}</div>
                ) : null}
              </div>
            </div>
          </section>

          <section className="listControlsTs">
            <div className="listToolbarTs">
              <div className="listToolbarIntroTs">
                <span className="toolsTitleTs">Ferramentas da lista</span>
              </div>

              <div className="listContentTs">
                <div className="listHeadTs">
                  <span className="listGroupLabelTs">Edicao e estrutura</span>
                  <div className="listPrimaryActionsTs" role="group" aria-label="Acoes principais">
                    <button className={`toolButtonTs ${globalEditMode ? "activeToolButton" : ""}`} type="button" onClick={handleToggleGlobalEdit}>
                      {globalEditMode ? "Finalizar Edicoes" : "Permitir Edicoes"}
                    </button>
                    <button
                      className={`toolButtonTs ${showFormatCodesPanel ? "activeToolButton" : ""}`}
                      type="button"
                      onClick={() => {
                        setShowFormatCodesPanel((current) => !current);
                        setShowDescriptionPanel(false);
                      }}
                    >
                      Formatar Codigos
                    </button>
                    <button
                      className={`toolButtonTs ${showDescriptionPanel ? "activeToolButton" : ""}`}
                      type="button"
                      onClick={() => {
                        setShowDescriptionPanel((current) => !current);
                        setShowFormatCodesPanel(false);
                      }}
                    >
                      Melhorar Descricao
                    </button>
                    <button className={`toolButtonTs accent ${orderingMode ? "activeToolButton" : ""}`} type="button" onClick={() => void runBusyAction("ordenar-lista", handleToggleOrdering)}>
                      {orderingMode ? `Salvar Ordem (${orderingSelectedKeys.length})` : "Ordenar Lista"}
                    </button>
                    <button className={`toolButtonTs accent ${createSetMode ? "activeToolButton" : ""}`} type="button" onClick={handleToggleCreateSets}>
                      {createSetMode ? `Selecionar ${Math.max(0, 2 - createSetKeys.length)} item(ns)` : "Criar Conjuntos"}
                    </button>
                    <button className="toolButtonTs success" type="button" onClick={() => void runBusyAction("juntar-repetidos", handleJoinDuplicates)}>Juntar Repetidos</button>
                    <button className="toolButtonTs danger" type="button" onClick={() => void runBusyAction("limpar-lista", handleClearProducts)}>
                      Limpar Lista
                    </button>
                  </div>
                </div>

                {showFormatCodesPanel ? (
                  <div className="toolConfigPanel">
                    <div className="toolConfigIntro">
                      <strong>Limpar codigos com menos risco</strong>
                      <p>Use apenas estas opcoes para cortar numeros do comeco ou do fim do codigo. Se precisar voltar atras, use Restaurar Originais.</p>
                    </div>
                    <div className="toolConfigGrid">
                      <label className="toolField">
                        <span>Quantos numeros apagar do comeco</span>
                        <input
                          value={formatCodesOptions.remover_primeiros_numeros}
                          onChange={(event) => setFormatCodesOptions((current) => ({ ...current, remover_primeiros_numeros: event.target.value.replace(/[^\d]/g, "") }))}
                          placeholder="Ex.: 2"
                        />
                      </label>
                      <label className="toolField">
                        <span>Quantos numeros apagar do final</span>
                        <input
                          value={formatCodesOptions.remover_ultimos_numeros}
                          onChange={(event) => setFormatCodesOptions((current) => ({ ...current, remover_ultimos_numeros: event.target.value.replace(/[^\d]/g, "") }))}
                          placeholder="Ex.: 2"
                        />
                      </label>
                    </div>
                    <div className="toolConfigActions">
                      <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("restaurar-codigos", async () => {
                        pushUndoSnapshot();
                        const result = await restoreOriginalCodes();
                        queueRefresh(["products"]);
                        setShowFormatCodesPanel(false);
                        window.alert(`Total analisado: ${result.total}\nCodigos restaurados: ${result.restaurados}`);
                      })}>
                        Restaurar Originais
                      </button>
                      <button className="ghostButton miniActionButton" type="button" onClick={() => setShowFormatCodesPanel(false)}>
                        Fechar
                      </button>
                      <button className="primaryButton miniPrimaryButton" type="button" onClick={() => void runBusyAction("formatar-codigos", handleFormatCodes)}>
                        Aplicar
                      </button>
                    </div>
                  </div>
                ) : null}

                {showDescriptionPanel ? (
                  <div className="toolConfigPanel">
                    <div className="toolConfigGrid">
                      <label className="toolCheck">
                        <input
                          type="checkbox"
                          checked={descriptionOptions.remover_especiais}
                          onChange={(event) => setDescriptionOptions((current) => ({ ...current, remover_especiais: event.target.checked }))}
                        />
                        <span>Remover caracteres especiais</span>
                      </label>
                      <label className="toolCheck">
                        <input
                          type="checkbox"
                          checked={descriptionOptions.remover_numeros}
                          onChange={(event) => setDescriptionOptions((current) => ({ ...current, remover_numeros: event.target.checked }))}
                        />
                        <span>Remover numeros</span>
                      </label>
                      <label className="toolCheck">
                        <input
                          type="checkbox"
                          checked={descriptionOptions.remover_letras}
                          onChange={(event) => setDescriptionOptions((current) => ({ ...current, remover_letras: event.target.checked }))}
                        />
                        <span>Remover letras</span>
                      </label>
                      <label className="toolField toolFieldWide">
                        <span>Termos para remover, separados por virgula</span>
                        <input value={descriptionOptions.remover_termos} onChange={(event) => setDescriptionOptions((current) => ({ ...current, remover_termos: event.target.value }))} />
                      </label>
                    </div>
                    <div className="toolConfigActions">
                      <button className="ghostButton miniActionButton" type="button" onClick={() => setShowDescriptionPanel(false)}>
                        Fechar
                      </button>
                      <button className="primaryButton miniPrimaryButton" type="button" onClick={() => void runBusyAction("melhorar-descricao", handleImproveDescriptions)}>
                        Aplicar
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </section>

          <section className={`tableWrapperTs ${orderingMode ? "orderingModeActive" : ""}`}>
            <div className="tableScrollTs">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Nome</th>
                    <th>
                      <div className="bulkHeaderCell" ref={bulkBrandMenuRef}>
                        <button className="bulkHeaderButton" type="button" onClick={() => setShowBulkBrandMenu((current) => !current)}>
                          <span>Marca</span>
                          <small>{bulkBrandValue || "Aplicar..."}</small>
                        </button>
                        {showBulkBrandMenu ? (
                          <div className="bulkMenuPopover">
                            <div className="bulkMenuHeader">
                              <strong>Aplicar marca</strong>
                              <button className="bulkAddButton" type="button" onClick={() => setShowBrandComposer((current) => !current)}>
                                +
                              </button>
                            </div>
                            {showBrandComposer ? (
                              <div className="bulkComposer">
                                <input value={newBrand} onChange={(event) => setNewBrand(event.target.value)} placeholder="Nova marca" />
                                <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("nova-marca", submitBrand)} disabled={!newBrand.trim()}>
                                  Salvar
                                </button>
                              </div>
                            ) : null}
                            <div className="bulkMenuList">
                              {sortedBrands.map((brand) => (
                                <button key={brand} className="bulkMenuItem" type="button" onClick={() => void runBusyAction("aplicar-marca", async () => handleApplyBrand(brand))}>
                                  {brand}
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </th>
                    <th>Codigo</th>
                    <th>Qtd</th>
                    <th>Custo</th>
                    <th>Venda</th>
                    <th>
                      <div className="bulkHeaderCell" ref={bulkCategoryMenuRef}>
                        <button className="bulkHeaderButton" type="button" onClick={() => setShowBulkCategoryMenu((current) => !current)}>
                          <span>Categoria</span>
                          <small>{bulkCategoryValue || "Aplicar..."}</small>
                        </button>
                        {showBulkCategoryMenu ? (
                          <div className="bulkMenuPopover">
                            <div className="bulkMenuHeader">
                              <strong>Aplicar categoria</strong>
                            </div>
                            <div className="bulkMenuList">
                              {CATEGORIES.map((category) => (
                                <button key={category} className="bulkMenuItem" type="button" onClick={() => void runBusyAction("aplicar-categoria", async () => handleApplyCategory(category))}>
                                  {category}
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={9} className="emptyState">
                        Carregando dados...
                      </td>
                    </tr>
                  ) : displayedProducts.length ? (
                    displayedProducts.map((product, index) => {
                      const selectionPosition = orderingSelectionIndex.get(product.ordering_key);
                      const isAutomationCurrentRow = automationIsRunning && automationCurrentOrderingKey === product.ordering_key;
                      return (
                      <tr
                        key={product.ordering_key}
                        className={[
                          createSetKeys.includes(product.ordering_key) ? "selectedRow" : "",
                          orderingMode && selectionPosition ? "orderedRow" : "",
                          isAutomationCurrentRow ? "automationCurrentRow" : "",
                        ].filter(Boolean).join(" ")}
                          onClick={(event) => {
                            if (orderingMode) {
                              handleOrderingSelection(product.ordering_key, {
                                allowRemove: event.detail >= 3,
                              });
                              return;
                            }
                            void handleCreateSetSelection(product.ordering_key);
                          }}
                      >
                        <td>{orderingMode && selectionPosition ? selectionPosition : index + 1}</td>
                        <td>
                          <div className="nameCellStack">
                            {renderCellContent(product, "nome", product.nome)}
                            {isAutomationCurrentRow && automationTypedDescription && automationTypedDescription.trim() !== product.nome.trim() ? (
                              <small className="automationPreviewText">{`Texto enviado: ${automationTypedDescription}`}</small>
                            ) : null}
                          </div>
                        </td>
                        <td>{renderCellContent(product, "marca", product.marca || "-")}</td>
                        <td>{renderCellContent(product, "codigo", product.codigo || "-")}</td>
                        <td>{renderCellContent(product, "quantidade", product.quantidade)}</td>
                        <td>{renderCellContent(product, "preco", product.preco || "-")}</td>
                        <td>{renderCellContent(product, "preco_final", product.preco_final || product.preco || "-")}</td>
                        <td>{renderCellContent(product, "categoria", product.categoria || "-")}</td>
                        <td>
                          <div className="rowActionStack">
                            {orderingMode ? (
                              <span className={`orderingSelectionBadge ${selectionPosition ? "activeOrderingSelectionBadge" : ""}`}>
                                {selectionPosition ? `Posicao ${selectionPosition}` : "Clique para ordenar"}
                              </span>
                            ) : null}
                            {isAutomationCurrentRow ? <span className="automationCurrentBadge">Em execucao</span> : null}
                            {orderingMode ? (
                              <>
                                <button className="rowMiniButton" type="button" onClick={(event) => { event.stopPropagation(); moveOrderingItem(product.ordering_key, -1); }}>
                                  ↑
                                </button>
                                <button className="rowMiniButton" type="button" onClick={(event) => { event.stopPropagation(); moveOrderingItem(product.ordering_key, 1); }}>
                                  ↓
                                </button>
                              </>
                            ) : null}
                            <button
                              className="rowLink dangerRowLink"
                              onClick={(event) => {
                                event.stopPropagation();
                                void runBusyAction(`excluir-${product.ordering_key}`, async () => {
                                  pushUndoSnapshot();
                                  await deleteProduct(product.ordering_key);
                                  queueRefresh(["products", "totals"]);
                                });
                              }}
                            >
                              Excluir
                            </button>
                            {createSetMode ? <span className="selectionHint">{createSetKeys.includes(product.ordering_key) ? "Selecionado" : "Selecionar"}</span> : null}
                          </div>
                        </td>
                      </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={9} className="emptyState">
                        Nenhum produto ativo neste momento.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </section>
      </main>
      {settingsOpen ? (
        <div className="settingsModalBackdrop" onClick={closeSettingsModal}>
          <section className="settingsModalShell" onClick={(event) => event.stopPropagation()}>
            <header className="settingsModalHeader">
              <div>
                <span className="sectionTag">Configuracoes</span>
                <h3>Targets, gradebot e diagnostico</h3>
              </div>
              <div className="settingsModalHeaderActions">
                <button className="ghostButton miniActionButton" type="button" onClick={() => void handleSettingsContextRefresh()} disabled={Boolean(settingsSaving)}>
                  Ver contexto
                </button>
                <button className="ghostButton miniActionButton" type="button" onClick={() => void handleSettingsPrepare()} disabled={Boolean(settingsSaving)}>
                  Preparar ByteEmpresa
                </button>
              </div>
            </header>

            <div className="settingsModalBody">
              <section className="settingsPanel">
                <div className="settingsPanelHead">
                  <div>
                    <span className="sectionTag">Cadastro</span>
                    <strong>Targets do PyAutoGUI</strong>
                  </div>
                  <button className="ghostButton miniActionButton" type="button" onClick={() => void handleSaveSettingsTargets()} disabled={settingsSaving === "targets"}>
                    {settingsSaving === "targets" ? "Salvando..." : "Salvar targets"}
                  </button>
                </div>
                <label className="settingsField">
                  <span>Titulo da janela</span>
                  <input
                    value={settingsTargets.title || ""}
                    onChange={(event) => handleSettingsTargetChange("title", event.target.value)}
                    placeholder="Byte Empresa - 1 - NAPASSARELA"
                  />
                </label>
                <div className="settingsTargetList">
                  {AUTOMATION_TARGET_FIELDS.map((field) => (
                    <div key={field.key} className="settingsTargetRow">
                      <div>
                        <strong>{field.label}</strong>
                        <span>{formatTargetPoint((settingsTargets[field.key] as TargetPoint | null | undefined) || null)}</span>
                      </div>
                      <button
                        className="ghostButton miniActionButton"
                        type="button"
                        onClick={() => void handleCaptureSettingsTarget(field.key, field.label)}
                        disabled={Boolean(settingsSaving)}
                      >
                        {settingsSaving === `capture-target-${field.key}` ? "Capturando..." : "Capturar"}
                      </button>
                    </div>
                  ))}
                </div>
              </section>

              <section className="settingsPanel">
                <div className="settingsPanelHead">
                  <div>
                    <span className="sectionTag">Gradebot</span>
                    <strong>Coordenadas e ordem ERP</strong>
                  </div>
                  <button className="ghostButton miniActionButton" type="button" onClick={() => void handleSaveSettingsGradeConfig()} disabled={settingsSaving === "grade-config"}>
                    {settingsSaving === "grade-config" ? "Salvando..." : "Salvar grades"}
                  </button>
                </div>
                <div className="settingsFormGrid">
                  <label className="settingsField">
                    <span>Altura da linha</span>
                    <input
                      value={settingsGradeConfig.row_height ?? ""}
                      onChange={(event) => handleSettingsGradeConfigChange((current) => ({
                        ...current,
                        row_height: Number.parseInt(event.target.value.replace(/[^\d]/g, ""), 10) || null,
                      }))}
                      placeholder="44"
                    />
                  </label>
                  <label className="settingsField">
                    <span>Indice do modelo</span>
                    <input
                      value={settingsGradeConfig.model_index ?? ""}
                      onChange={(event) => handleSettingsGradeConfigChange((current) => ({
                        ...current,
                        model_index: Number.parseInt(event.target.value.replace(/[^\d]/g, ""), 10) || null,
                      }))}
                      placeholder="1"
                    />
                  </label>
                  <label className="settingsField">
                    <span>Hotkey do modelo</span>
                    <input
                      value={settingsGradeConfig.model_hotkey || ""}
                      onChange={(event) => handleSettingsGradeConfigChange((current) => ({ ...current, model_hotkey: event.target.value }))}
                      placeholder="f6"
                    />
                  </label>
                  <div className="settingsTargetRow compact">
                    <div>
                      <strong>Primeira celula da grade</strong>
                      <span>{formatTargetPoint(settingsGradeConfig.first_quant_cell)}</span>
                    </div>
                    <button className="ghostButton miniActionButton" type="button" onClick={() => void handleCaptureFirstQuantCell()} disabled={Boolean(settingsSaving)}>
                      {settingsSaving === "capture-first-quant" ? "Capturando..." : "Capturar"}
                    </button>
                  </div>
                </div>
                <div className="settingsTargetList">
                  {GRADE_CAPTURE_FIELDS.map((field) => (
                    <div key={field.key} className="settingsTargetRow">
                      <div>
                        <strong>{field.label}</strong>
                        <span>{formatTargetPoint(normalizeTargetPoint(settingsGradeConfig.buttons?.[field.key]))}</span>
                      </div>
                      <button
                        className="ghostButton miniActionButton"
                        type="button"
                        onClick={() => void handleCaptureSettingsGradeButton(field.key, field.label)}
                        disabled={Boolean(settingsSaving)}
                      >
                        {settingsSaving === `capture-grade-${field.key}` ? "Capturando..." : "Capturar"}
                      </button>
                    </div>
                  ))}
                </div>
                <label className="settingsField">
                  <span>Ordem ERP usada pela automacao</span>
                  <textarea
                    value={(settingsGradeConfig.erp_size_order || []).join(", ")}
                    onChange={(event) => handleSettingsGradeConfigChange((current) => ({
                      ...current,
                      erp_size_order: parseSizeOrderText(event.target.value),
                    }))}
                    placeholder="P, M, G, GG, 34, 36, 38"
                  />
                </label>
              </section>

              <section className="settingsPanel settingsPanelWide">
                <div className="settingsPanelHead">
                  <div>
                    <span className="sectionTag">Diagnostico</span>
                    <strong>Contexto atual do ByteEmpresa</strong>
                  </div>
                  <button className="ghostButton miniActionButton" type="button" onClick={() => void loadSettingsModal()} disabled={settingsLoading || Boolean(settingsSaving)}>
                    {settingsLoading ? "Atualizando..." : "Recarregar tudo"}
                  </button>
                </div>
                {settingsCaptureCountdown ? (
                  <div className="message subtle">
                    Capturando <strong>{settingsCaptureLabel}</strong> em {settingsCaptureCountdown}s...
                  </div>
                ) : null}
                {settingsMessage ? <div className="message success">{settingsMessage}</div> : null}
                {settingsError ? <div className="message error">{settingsError}</div> : null}
                <pre className="settingsContextBlock">{settingsContextText || "Use 'Ver contexto' ou 'Preparar ByteEmpresa' para carregar diagnostico."}</pre>
              </section>
            </div>

            <footer className="settingsModalFooter">
              <button className="ghostButton miniActionButton" type="button" onClick={closeSettingsModal}>
                Fechar
              </button>
            </footer>
          </section>
        </div>
      ) : null}
      {gradeModalOpen ? (
        <div className="gradeModalBackdrop" onClick={closeGradeModal}>
          <section className="gradeModalShell" onClick={(event) => event.stopPropagation()}>
            <header className="gradeModalHeader">
              <div>
                <span className="sectionTag">Inserir grade</span>
                <h3>{selectedGradeProduct ? `${selectedGradeProduct.nome} (${selectedGradeProduct.codigo || "sem codigo"})` : "Selecione um item"}</h3>
              </div>
              <div className="gradeModalHeaderActions">
                <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("executar-grades", handleExecuteGrades)}>
                  Executar Grades
                </button>
                <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("parar-grades", handleStopGrades)}>
                  Parar
                </button>
              </div>
            </header>

            <div className="gradeModalBody">
              <aside className="gradeModalProductList">
                {state.products.map((product) => {
                  const gradeStatus = getProductGradeStatus(product);
                  return (
                    <button
                      key={product.ordering_key}
                      className={`gradeProductRow ${product.ordering_key === gradeSelectedKey ? "activeGradeProductRow" : ""}`}
                      type="button"
                      tabIndex={0}
                      onClick={() => setGradeSelectedKey(product.ordering_key)}
                      onKeyDown={handleGradeStartTab}
                    >
                      <div className="gradeProductRowHead">
                        <strong>{product.nome}</strong>
                        {gradeStatus.complete ? <span className="gradeStatusBadge success">✓</span> : null}
                        {!gradeStatus.complete && gradeStatus.overflow ? <span className="gradeStatusBadge danger">!</span> : null}
                      </div>
                      <span>{product.codigo || "Sem codigo"}</span>
                      <small className={gradeStatus.overflow ? "gradeStatusTextDanger" : gradeStatus.complete ? "gradeStatusTextSuccess" : ""}>
                        {gradeStatus.hasAny ? `${gradeStatus.total}/${gradeStatus.expected} pecas em grade` : "Sem grade salva"}
                      </small>
                    </button>
                  );
                })}
              </aside>

              <div className="gradeModalEditor">
                {selectedGradeProduct ? (
                  <>
                    <div className="gradeModalMeta">
                      <div><span>Quantidade do item</span><strong>{selectedGradeProduct.quantidade}</strong></div>
                      <div><span>Categoria</span><strong>{selectedGradeProduct.categoria || "-"}</strong></div>
                      <div><span>Marca</span><strong>{selectedGradeProduct.marca || "-"}</strong></div>
                    </div>

                    <details className="gradeConfigDetails" onKeyDown={handleGradeStartTab}>
                      <summary>Personalizar familias e tamanhos</summary>
                      <div className="gradeSizeManager">
                        <div className="gradeSectionHead">
                          <div>
                            <span className="sectionTag">Ordem visual dos tamanhos</span>
                            <p>Essa ordem e personalizada para o usuario. A automacao continua respeitando a ordem ERP do ByteEmpresa.</p>
                          </div>
                          <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("nova-familia-grade", addFamily)}>
                            + Familia
                          </button>
                        </div>

                        <div className="gradeSizeCreateRow">
                          <input
                            value={newGradeSize}
                            onChange={(event) => setNewGradeSize(event.target.value)}
                            placeholder="Novo tamanho ou tipo"
                          />
                          <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("novo-tamanho-grade", addVisualSize)}>
                            Adicionar
                          </button>
                        </div>

                        <div className="gradeSizeList">
                          {groupedGradeSizes.map((group) => (
                            <section key={`manage-${group.key}`} className="gradeSizeFamilyGroup">
                              <header className="gradeFamilyHeader compact">
                                <div>
                                  <input
                                    className="familyLabelInput"
                                    value={group.label}
                                    onChange={(event) => handleFamilyLabelChange(group.key, event.target.value)}
                                  />
                                  <p>{group.hint}</p>
                                </div>
                                <span className="totalsChipTs muted">{group.items.length}</span>
                              </header>
                              <div className="gradeSizeFamilyRows">
                                {group.items.map((size) => {
                                  const familySizes = gradeFamiliesDraft.find((family) => family.id === group.key)?.sizes || [];
                                  const index = familySizes.indexOf(size);
                                  const familyIndex = gradeFamiliesDraft.findIndex((family) => family.id === group.key);
                                  return (
                                    <div key={size} className="gradeSizeRow">
                                      <strong>{size}</strong>
                                      <div className="gradeSizeRowMeta">
                                        {(gradeConfig?.erp_size_order || []).includes(size) ? <span className="totalsChipTs muted">ERP</span> : null}
                                        <button className="rowMiniButton" type="button" disabled={familyIndex <= 0} onClick={() => void runBusyAction(`mover-esquerda-${size}`, async () => moveSizeBetweenFamilies(group.key, size, -1))}>
                                          ←
                                        </button>
                                        <button className="rowMiniButton" type="button" onClick={() => void runBusyAction(`renomear-${size}`, async () => renameSizeInFamily(group.key, size))}>
                                          ✎
                                        </button>
                                        <button
                                          className="rowMiniButton dangerMiniButton"
                                          type="button"
                                          onClick={() => void runBusyAction(`remover-${size}`, async () => removeSizeFromFamilies(size))}
                                        >
                                          ×
                                        </button>
                                        <button className="rowMiniButton" type="button" disabled={index <= 0} onClick={() => void runBusyAction(`subir-${size}`, async () => moveVisualSize(group.key, size, -1))}>
                                          ↑
                                        </button>
                                        <button
                                          className="rowMiniButton"
                                          type="button"
                                          disabled={index < 0 || index === familySizes.length - 1}
                                          onClick={() => void runBusyAction(`descer-${size}`, async () => moveVisualSize(group.key, size, 1))}
                                        >
                                          ↓
                                        </button>
                                        <button
                                          className="rowMiniButton"
                                          type="button"
                                          disabled={familyIndex < 0 || familyIndex === gradeFamiliesDraft.length - 1}
                                          onClick={() => void runBusyAction(`mover-direita-${size}`, async () => moveSizeBetweenFamilies(group.key, size, 1))}
                                        >
                                          →
                                        </button>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </section>
                          ))}
                        </div>

                        <div className="gradeAutomationHint">
                          <span>Ordem ERP usada pela automacao:</span>
                          <strong>{(gradeConfig?.erp_size_order || []).join(" • ") || "Nao configurada"}</strong>
                        </div>
                      </div>
                    </details>

                    <div className="gradeTabsShell">
                      <div className="gradeTabsBar" role="tablist" aria-label="Familias de grade">
                        {groupedGradeSizes.map((group) => (
                          <button
                            key={group.key}
                            className={`gradeTabButton ${activeGradeFamily?.key === group.key ? "activeGradeTabButton" : ""}`}
                            type="button"
                            tabIndex={0}
                            role="tab"
                            aria-selected={activeGradeFamily?.key === group.key}
                            onClick={() => setActiveGradeFamilyKey(group.key)}
                            onKeyDown={handleGradeStartTab}
                          >
                            <span>{group.label}</span>
                            <small>{group.items.length}</small>
                          </button>
                        ))}
                      </div>

                      {activeGradeFamily ? (
                        <section className="gradeActiveFamilyPanel">
                          <header className="gradeFamilyHeader">
                            <div>
                              <strong>{activeGradeFamily.label}</strong>
                              <p>{activeGradeFamily.hint} Use Tab para avancar entre os campos e digite a quantidade de cada tamanho.</p>
                            </div>
                          </header>
                          <div className="gradeGridEditor horizontalGradeGrid">
                              {activeGradeFamily.items.map((size) => (
                                <label key={size} className="gradeInputCard">
                                  <span>{size}</span>
                                  <input
                                    ref={(node) => {
                                      gradeInputRefs.current[size] = node;
                                    }}
                                    inputMode="numeric"
                                    value={gradeDraft[size] ?? ""}
                                    onChange={(event) => updateGradeDraftValue(size, event.target.value)}
                                    onKeyDown={handleGradeInputKeyDown}
                                    placeholder="0"
                                  />
                                </label>
                              ))}
                          </div>
                        </section>
                      ) : (
                        <div className="message subtle">Nenhum tamanho configurado no catalogo.</div>
                      )}
                    </div>

                    <div className="gradeModalFooterInfo">
                      <span>Total da grade: {currentGradeTotal}</span>
                      <span>Quantidade do produto: {selectedGradeProduct.quantidade}</span>
                    </div>
                    {gradeValidationError ? <div className="message error gradeValidationAlert">{gradeValidationError}</div> : null}
                    {gradeModalError ? <div className="message error">{gradeModalError}</div> : null}
                  </>
                ) : (
                  <div className="message subtle">Selecione um produto para editar a grade.</div>
                )}
              </div>
            </div>

            <footer className="gradeModalFooter">
              <button className="ghostButton miniActionButton" type="button" onClick={closeGradeModal}>
                Fechar
              </button>
              <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("limpar-grade", handleClearSelectedGrade)}>
                Limpar Grade
              </button>
              <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("limpar-todas-grades", handleClearAllGrades)}>
                Limpar Todas as Grades
              </button>
              <button className="primaryButton gradeFooterButton" type="button" onClick={() => void runBusyAction("salvar-grade", handleSaveSelectedGrade)}>
                Salvar
              </button>
              <button className="primaryButton gradeFooterButton" type="button" onClick={() => void runBusyAction("salvar-proxima-grade", handleSaveAndNextGrade)}>
                Salvar e Proximo
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </div>
  );
}
