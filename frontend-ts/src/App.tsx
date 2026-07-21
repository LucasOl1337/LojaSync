import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";

import {
  addBrand,
  applyBrand,
  applyCategory,
  applyMargin,
  buildWsUrl,
  captureAutomationTarget,
  clearProducts,
  cleanupImportJob,
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
  fetchRuntimeHealth,
  importRomaneioLocalExperiment,
  fetchMargin,
  fetchProducts,
  fetchTotals,
  fetchUndoRedoHistory,
  formatCodes,
  improveDescriptions,
  importRomaneio,
  joinDuplicates,
  joinGrades,
  patchProduct,
  reorderProducts,
  redoHistorySnapshot,
  recordUndoSnapshot,
  restoreOriginalCodes,
  saveAutomationTargets,
  saveGradeConfig,
  saveMargin,
  startAutomationCatalog,
  startAutomationComplete,
  prepareByteEmpresa,
  stopAutomation,
  stopGradesExecution,
  undoHistorySnapshot,
  waitForImportJob,
} from "./api";
import type {
  AuthSessionResponse,
  AutomationTargets,
  GradeConfig,
  ImportResult,
  ImportStatus,
  Product,
  ProductPayload,
  TargetPoint,
  UiEvent,
  UiGradeFamily,
  UndoRedoHistoryResponse,
} from "./types";
import { initialState } from "./appConfig";
import type { AutomationTargetKey, EditingCellState, GradeCaptureKey, LoadState, Scope } from "./appConfig";
import {
  buildInlineEditPayload,
  buildProductPreview,
  getInlineEditInitialValue,
} from "./productEditing";
import type { EditableField } from "./productEditing";
import {
  buildCreateProductPayload,
  findFirstMissingProductField,
  getNextProductFormField,
} from "./productForm";
import type { ProductFormField } from "./productForm";
import {
  buildProductQuickFilterOptions,
  buildProductSearchIndex,
  buildProductSearchEmptyState,
  filterProductsByQuickFilter,
  filterProductSearchIndex,
  resolveStaleProductQuickFilter,
} from "./productFilters";
import type { ProductQuickFilter } from "./productFilters";
import {
  buildDescriptionCleanupSuggestions,
  parseDescriptionRemovalTerms,
} from "./descriptionCleanup";
import {
  GRADE_UI_VERSION,
  buildDefaultUiFamilies,
  buildGradeItemsFromDraft,
  buildGradeProductStatus,
  buildVisualSizeOrder,
  compareGradeSizeLabels,
  findNextPendingGradeKey,
  getIncompleteGradeProducts,
  gradeItemsToMap,
  hasGradeDraftChanges,
  normalizeGradeConfigState,
  normalizeGradeSizeLabel,
  normalizeUiFamiliesDraft,
  sumGradeDraftValues,
} from "./gradeLogic";
import { computeCurrentTotals, formatPercentDisplay, parsePositivePercentInput } from "./productPricing";
import {
  buildImportHistoryEntry,
  buildOperationDiaryEntry,
  buildExecutionReadiness,
  buildImportDiagnosticsChips,
  buildImportGradesAvailableMessage,
  buildImportProgressMessage,
  buildOperationalHealthChips,
  buildClearProductsConfirmation,
  buildProductOperationDiaryEntry,
  buildUndoRedoHistoryState,
  coerceStringList,
  formatCaughtErrorMessage,
  formatCurrency,
  formatDuration,
  formatJsonBlock,
  formatTargetPoint,
  formatTimestamp,
  parsePromptInteger,
  updateOperationDiaryEntries,
  updateRecentImportHistory,
} from "./uiFormatting";
import type { ImportHistoryEntry, OperationDiaryEntry, OperationDiaryEntryInput, ProductOperationDiaryInput, UiSocketStatus } from "./uiFormatting";
import {
  INLINE_EDIT_FIELD_LABELS,
  OPERATION_DIARY_LIMIT,
  RECENT_IMPORT_HISTORY_LIMIT,
  clearOrderingDraft,
  readInitialImportHistory,
  readInitialOperationDiary,
  readInitialOrderingDraft,
  readInitialProductQuickFilter,
  readLastActiveGradeFamily,
  saveOrderingDraft,
  saveLastActiveGradeFamily,
  saveOperationDiary,
  saveProductQuickFilter,
  saveRecentImportHistory,
} from "./appLocalState";
import type {
  ConfirmationDialogState,
  RuntimeHealthState,
  TextInputDialogState,
} from "./appLocalState";
import { useNoticeCenter } from "./appNotifications";
import { ImportStagePanel } from "./importStagePanel";
import { ImportWorkspacePanel } from "./importWorkspacePanel";
import {
  buildAutomaticImportLayout,
  createStagedImportDocuments,
  extractImportFailureReasons,
  type StagedImportDocument,
} from "./importWorkspace";
import { ProductEntryPanel } from "./productEntryPanel";
import { CatalogQuickEntryPanel } from "./catalogQuickEntryPanel";
import { CatalogActionDock } from "./catalogActionDock";
import { OperationalSummaryPanel } from "./operationalSummaryPanel";
import { OperationalHealthPanel } from "./operationalHealthPanel";
import { CatalogOverviewPanel } from "./catalogOverviewPanel";
import { ExecutionCenterPanel } from "./executionCenterPanel";
import { GradeModal } from "./gradeModal";
import { ProductListControls } from "./productListControls";
import { ProductTable } from "./productTable";
import { SettingsModal } from "./settingsModal";
import { ConfirmationDialog } from "./confirmationDialog";
import { MarginDialog } from "./marginDialog";
import { TextInputDialog } from "./textInputDialog";
import { NoticeDialog } from "./noticeDialog";
import { NoticeToastStack } from "./noticeToastStack";
import { HistoryPanel } from "./historyPanel";
import { getGlobalUndoRedoAction } from "./keyboardShortcuts";
import { buildProductCsv, buildProductCsvFilename } from "./productExport";
import { buildProductTemplatePayload } from "./productTemplate";
import { buildCatalogOverview } from "./catalogOverview";
import { buildUsageAnalytics } from "./usageAnalytics";
import {
  buildDisplayedProducts,
  buildFinalOrderingKeys,
  buildOrderingKeys,
  buildOrderingSelectionIndex,
  moveOrderingKey,
  sanitizeOrderingDraft,
  toggleOrderingKey,
} from "./productOrdering";

type AppProps = {
  authSession?: AuthSessionResponse | null;
};

type WorkspaceId = "overview" | "catalog" | "import" | "execution" | "history";

const WORKSPACES: Array<{ id: WorkspaceId; label: string; shortLabel: string; eyebrow: string }> = [
  { id: "catalog", label: "Catálogo", shortLabel: "Catálogo", eyebrow: "Produtos locais" },
  { id: "import", label: "Importação", shortLabel: "Importar", eyebrow: "Entrada de documentos" },
  { id: "execution", label: "Execução", shortLabel: "Executar", eyebrow: "Automação Windows" },
  { id: "overview", label: "Visão geral", shortLabel: "Visão", eyebrow: "Operação do catálogo" },
  { id: "history", label: "Histórico", shortLabel: "Histórico", eyebrow: "Controle reversível" },
];

function readInitialWorkspace(): WorkspaceId {
  if (typeof window === "undefined") return "catalog";
  try {
    const saved = window.localStorage.getItem("lojasync-workspace");
    return WORKSPACES.some((workspace) => workspace.id === saved) ? saved as WorkspaceId : "catalog";
  } catch {
    return "catalog";
  }
}

function WorkspaceIcon({ id }: { id: WorkspaceId }) {
  if (id === "overview") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h6v6H4zM14 4h6v10h-6zM4 14h6v6H4zM14 18h6v2h-6z" /></svg>;
  if (id === "catalog") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4zM4 10h16M9 10v9" /></svg>;
  if (id === "import") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 19h16" /></svg>;
  if (id === "execution") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7z" /></svg>;
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.3-5.7L4 8.6M4 4v4.6h4.6M12 8v5l3 2" /></svg>;
}

export default function App({ authSession = null }: AppProps) {
  const [state, setState] = useState<LoadState>(initialState);
  const [sidebarClock, setSidebarClock] = useState(() => new Date());
  const [loading, setLoading] = useState(true);
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealthState>({
    status: "checking",
    message: null,
    version: null,
    checkedAt: null,
  });
  const [uiSocketStatus, setUiSocketStatus] = useState<UiSocketStatus>("connecting");
  const [recentImports, setRecentImports] = useState<ImportHistoryEntry[]>(readInitialImportHistory);
  const [operationDiary, setOperationDiary] = useState<OperationDiaryEntry[]>(readInitialOperationDiary);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceId>(readInitialWorkspace);
  const [catalogQuickEntryOpen, setCatalogQuickEntryOpen] = useState(false);
  const catalogQuickEntryTriggerRef = useRef<HTMLElement | null>(null);
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
  const [productSearchQuery, setProductSearchQuery] = useState("");
  const [productQuickFilter, setProductQuickFilter] = useState<ProductQuickFilter>(readInitialProductQuickFilter);
  const [undoRedoRevision, setUndoRedoRevision] = useState(0);
  const [globalEditMode, setGlobalEditMode] = useState(false);
  const [orderingMode, setOrderingMode] = useState(() => readInitialOrderingDraft().length > 0);
  const [orderingDraftKeys, setOrderingDraftKeys] = useState<string[]>(readInitialOrderingDraft);
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
    remover_termos: "",
  });
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [importDocuments, setImportDocuments] = useState<StagedImportDocument[]>([]);
  const [activeImportDocumentId, setActiveImportDocumentId] = useState<string | null>(null);
  const [importJob, setImportJob] = useState<ImportStatus | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [localExperimentLoading, setLocalExperimentLoading] = useState(false);
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
  const [activeGradeFamilyKey, setActiveGradeFamilyKey] = useState<string>(readLastActiveGradeFamily);
  const [newGradeSize, setNewGradeSize] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [importing, setImporting] = useState(false);
  const pendingScopes = useRef<Set<Scope>>(new Set());
  const flushTimer = useRef<number | null>(null);
  const undoStackRef = useRef<Product[][]>([]);
  const redoStackRef = useRef<Product[][]>([]);
  const isRestoringSnapshotRef = useRef(false);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const importModeRef = useRef<"llm" | "local">("llm");
  const importFileNameRef = useRef<string | null>(null);
  const bulkCategoryMenuRef = useRef<HTMLDivElement | null>(null);
  const bulkBrandMenuRef = useRef<HTMLDivElement | null>(null);
  const visitedProductFields = useRef<Set<ProductFormField>>(new Set());
  const pendingProductFocusFrame = useRef<number | null>(null);
  const gradeInputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const pendingGradeInputFocus = useRef(false);
  const gradeDraftBaselineRef = useRef<Record<string, string>>({});
  const gradeTransitionPendingRef = useRef(false);
  const gradeMutationPendingRef = useRef(false);
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
  const [confirmationDialog, setConfirmationDialog] = useState<ConfirmationDialogState | null>(null);
  const [confirmationBusy, setConfirmationBusy] = useState(false);
  const [confirmationError, setConfirmationError] = useState<string | null>(null);
  const [marginDialogOpen, setMarginDialogOpen] = useState(false);
  const [marginDraft, setMarginDraft] = useState("");
  const [marginBusy, setMarginBusy] = useState(false);
  const [marginError, setMarginError] = useState<string | null>(null);
  const [textInputDialog, setTextInputDialog] = useState<TextInputDialogState | null>(null);
  const [textInputBusy, setTextInputBusy] = useState(false);
  const [textInputError, setTextInputError] = useState<string | null>(null);
  const {
    noticeDialog,
    noticeToasts,
    showNoticeDialog,
    showErrorNotice,
    closeNoticeDialog,
    dismissNoticeToast,
  } = useNoticeCenter();

  const sortedBrands = useMemo(() => [...state.brands].sort((a, b) => a.localeCompare(b, "pt-BR")), [state.brands]);
  const sidebarClockText = useMemo(
    () => sidebarClock.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
    [sidebarClock],
  );
  const sidebarDateText = useMemo(
    () => sidebarClock.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
    [sidebarClock],
  );
  const productsByKey = useMemo(() => new Map(state.products.map((product) => [product.ordering_key, product])), [state.products]);
  const originalOrderingKeys = useMemo(() => buildOrderingKeys(state.products), [state.products]);
  const incompleteGradeProducts = useMemo(() => getIncompleteGradeProducts(state.products), [state.products]);
  const pendingGradeImportProducts = useMemo(
    () => state.products.filter((product) => Boolean(product.pending_grade_import)),
    [state.products],
  );
  const orderedProducts = useMemo(
    () => buildDisplayedProducts(state.products, orderingDraftKeys, orderingMode),
    [orderingDraftKeys, orderingMode, state.products],
  );
  const productQuickFilterOptions = useMemo(
    () => buildProductQuickFilterOptions(orderedProducts),
    [orderedProducts],
  );
  const quickFilteredProducts = useMemo(
    () => filterProductsByQuickFilter(orderedProducts, productQuickFilter),
    [orderedProducts, productQuickFilter],
  );
  const productSearchIndex = useMemo(
    () => buildProductSearchIndex(quickFilteredProducts),
    [quickFilteredProducts],
  );
  const displayedProducts = useMemo(
    () => filterProductSearchIndex(productSearchIndex, productSearchQuery),
    [productSearchIndex, productSearchQuery],
  );
  const visibleBulkActionKeys = useMemo<string[] | undefined>(
    () => displayedProducts.length === state.products.length
      ? undefined
      : displayedProducts.map((product) => product.ordering_key),
    [displayedProducts, state.products.length],
  );
  const descriptionCleanupSuggestions = useMemo(
    () => buildDescriptionCleanupSuggestions(displayedProducts, descriptionOptions.remover_termos),
    [descriptionOptions.remover_termos, displayedProducts],
  );
  const catalogOverview = useMemo(
    () => buildCatalogOverview(state.products, state.marginPercentual),
    [state.marginPercentual, state.products],
  );

  useEffect(() => {
    const nextFilter = resolveStaleProductQuickFilter(
      productQuickFilter,
      productQuickFilterOptions,
      orderedProducts.length,
    );
    if (nextFilter === productQuickFilter) return;
    setProductQuickFilter(saveProductQuickFilter(nextFilter));
  }, [orderedProducts.length, productQuickFilter, productQuickFilterOptions]);

  const handleCatalogFilterSelect = (filter: ProductQuickFilter) => {
    setProductQuickFilter(saveProductQuickFilter(filter));
    setProductSearchQuery("");
    window.setTimeout(() => {
      const workspacePanel = document.getElementById("workspace-panel");
      workspacePanel?.focus({ preventScroll: true });
      document.getElementById("list-tools-title")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  };

  const productTableEmptyState = useMemo(
    () => productSearchQuery.trim()
      ? buildProductSearchEmptyState(productSearchQuery, quickFilteredProducts.length)
      : {
          searchActive: false,
          title: state.products.length ? "Nenhum item visível" : "Lista vazia",
          detail: state.products.length
            ? "A lista atual não tem itens disponíveis no momento."
            : "Escolha um caminho para gerar o primeiro lote revisavel dentro do LojaSync.",
          actions: [],
        },
    [productSearchQuery, quickFilteredProducts.length, state.products.length],
  );
  const undoRedoHistoryState = useMemo(
    () => buildUndoRedoHistoryState(undoStackRef.current.length, redoStackRef.current.length),
    [undoRedoRevision],
  );
  const syncUndoRedoHistoryRefs = (history: UndoRedoHistoryResponse) => {
    undoStackRef.current = Array.from({ length: Math.max(0, Math.floor(history.undo_count || 0)) }, () => [] as Product[]);
    redoStackRef.current = Array.from({ length: Math.max(0, Math.floor(history.redo_count || 0)) }, () => [] as Product[]);
    setUndoRedoRevision((current) => current + 1);
  };
  const orderingSelectionIndex = useMemo(
    () => buildOrderingSelectionIndex(state.products, orderingDraftKeys),
    [orderingDraftKeys, state.products],
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
      common: "PMG, tamanho único e variações mais frequentes.",
      letters: "Tamanhos por letras expandidas e linhas plus size.",
      infantil: "Numeração infantil e medidas em meses.",
      adulto: "Numeração adulta em ordem crescente.",
      extras: "Itens extras fora das familias principais.",
    };
    return gradeFamiliesDraft
      .map((family) => ({
        key: family.id,
        label: family.label,
        hint: familyHints[family.id] || "Família personalizada para acesso rápido.",
        items: family.sizes,
      }))
      .filter((group) => group.items.length);
  }, [gradeFamiliesDraft]);
  const activeGradeFamily = useMemo(
    () => groupedGradeSizes.find((group) => group.key === activeGradeFamilyKey) ?? groupedGradeSizes[0] ?? null,
    [activeGradeFamilyKey, groupedGradeSizes],
  );
  const currentGradeTotal = useMemo(() => sumGradeDraftValues(gradeDraft), [gradeDraft]);
  const gradeDraftDirty = hasGradeDraftChanges(gradeDraft, gradeDraftBaselineRef.current);
  const gradeDraftMutationBusy = busyAction === "salvar-grade"
    || busyAction === "salvar-proxima-grade"
    || busyAction === "limpar-grade";
  const usageAnalytics = useMemo(
    () => buildUsageAnalytics(operationDiary, sidebarClock.getTime()),
    [operationDiary, sidebarClock],
  );
  const selectedGradeStatus = useMemo(
    () => (selectedGradeProduct ? buildGradeProductStatus(selectedGradeProduct, currentGradeTotal) : null),
    [currentGradeTotal, selectedGradeProduct],
  );
  const nextPendingGradeKey = useMemo(
    () => findNextPendingGradeKey(state.products, gradeSelectedKey, gradeSelectedKey),
    [gradeSelectedKey, state.products],
  );
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
        case "history": {
          const payload = await fetchUndoRedoHistory();
          return { scope, value: payload };
        }
      }
    });

    const settled = await Promise.all(tasks);
    for (const item of settled) {
      if (item.scope === "history") {
        syncUndoRedoHistoryRefs(item.value as UndoRedoHistoryResponse);
      }
    }
    startTransition(() => {
      setState((current) => {
        const next = { ...current };
        for (const item of settled) {
          if (item.scope === "products") next.products = item.value as Product[];
          if (item.scope === "brands") next.brands = item.value as string[];
          if (item.scope === "margin") next.marginPercentual = item.value as number;
          if (item.scope === "automation") next.automation = item.value as LoadState["automation"];
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
      void applySnapshot(currentScopes.length ? currentScopes : ["products", "totals", "brands", "margin", "automation", "history"]);
    }, 120);
  };

  const refreshAfterLocalImport = async (result: ImportResult) => {
    const importedKeys = new Set((result.imported_keys || []).filter(Boolean));
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const productsPayload = await fetchProducts();
      const loadedKeys = new Set(productsPayload.items.map((item) => item.ordering_key));
      const importedVisible = importedKeys.size === 0 || Array.from(importedKeys).every((key) => loadedKeys.has(key));

      startTransition(() => {
        setState((current) => ({
          ...current,
          products: productsPayload.items,
        }));
      });

      if (importedVisible || attempt === 4) {
        await applySnapshot(["totals", "brands"]);
        return;
      }

      await new Promise((resolve) => window.setTimeout(resolve, 180 * (attempt + 1)));
    }
  };

  const rememberImportHistory = (
    result: ImportResult,
    options?: {
      job?: Pick<ImportStatus, "job_id" | "updated_at" | "completed_at"> | null;
      mode?: "llm" | "local";
      selectedFileName?: string | null;
    },
  ) => {
    const entry = buildImportHistoryEntry(result, {
      job: options?.job,
      selectedFileName: options?.selectedFileName ?? importFileNameRef.current,
      mode: options?.mode,
    });
    setRecentImports((current) => {
      const next = updateRecentImportHistory(current, entry, RECENT_IMPORT_HISTORY_LIMIT);
      saveRecentImportHistory(next);
      return next;
    });
    return entry;
  };

  const rememberOperationDiary = (input: OperationDiaryEntryInput) => {
    const entry = buildOperationDiaryEntry(input);
    setOperationDiary((current) => {
      const next = updateOperationDiaryEntries(current, entry, OPERATION_DIARY_LIMIT);
      saveOperationDiary(next);
      return next;
    });
    return entry;
  };

  const rememberProductOperation = (input: ProductOperationDiaryInput) => {
    return rememberOperationDiary(buildProductOperationDiaryEntry(input));
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

  const pushUndoSnapshot = async (options?: { clearRedo?: boolean }) => {
    if (isRestoringSnapshotRef.current) {
      return;
    }
    try {
      const history = await recordUndoSnapshot(options?.clearRedo !== false);
      syncUndoRedoHistoryRefs(history);
    } catch (error) {
      console.warn("Historico de desfazer indisponivel; seguindo com a acao principal.", error);
    }
  };

  const undoLastAction = async () => {
    if (!undoStackRef.current.length || isRestoringSnapshotRef.current) {
      return;
    }
    isRestoringSnapshotRef.current = true;
    try {
      const result = await undoHistorySnapshot();
      syncUndoRedoHistoryRefs(result);
      if (result.restored) {
        await applySnapshot(["products", "totals", "brands", "margin"]);
      }
    } finally {
      isRestoringSnapshotRef.current = false;
    }
  };

  const redoLastAction = async () => {
    if (!redoStackRef.current.length || isRestoringSnapshotRef.current) {
      return;
    }
    isRestoringSnapshotRef.current = true;
    try {
      const result = await redoHistorySnapshot();
      syncUndoRedoHistoryRefs(result);
      if (result.restored) {
        await applySnapshot(["products", "totals", "brands", "margin"]);
      }
    } finally {
      isRestoringSnapshotRef.current = false;
    }
  };

  useEffect(() => {
    const timer = window.setInterval(() => setSidebarClock(new Date()), 30000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    queueRefresh(["products", "totals", "brands", "margin", "automation", "history"]);
  }, []);

  useEffect(() => {
    let disposed = false;
    const loadAutomationTargets = async () => {
      try {
        const payload = await fetchAutomationTargets();
        if (disposed) return;
        setSettingsTargets(payload || {});
      } catch {
        // Settings refreshes targets again when the modal opens.
      }
    };

    void loadAutomationTargets();
    return () => {
      disposed = true;
    };
  }, []);

  useEffect(() => {
    if (!orderingMode) {
      setOrderingDraftKeys([]);
      return;
    }
    if (!originalOrderingKeys.length) {
      return;
    }
    setOrderingDraftKeys((current) => sanitizeOrderingDraft(current, originalOrderingKeys));
  }, [orderingMode, originalOrderingKeys]);

  useEffect(() => {
    if (!orderingMode) {
      clearOrderingDraft();
      return;
    }
    saveOrderingDraft(orderingDraftKeys);
  }, [orderingDraftKeys, orderingMode]);

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
    let disposed = false;
    let timer: number | null = null;

    const refreshHealth = async () => {
      try {
        const payload = await fetchRuntimeHealth();
        if (disposed) return;
        setRuntimeHealth({
          status: String(payload.status || "").toLowerCase() === "ok" ? "ok" : "error",
          message: null,
          version: payload.version || null,
          checkedAt: Date.now(),
        });
      } catch (error) {
        if (disposed) return;
        setRuntimeHealth({
          status: "error",
          message: formatCaughtErrorMessage(error, "Falha ao consultar o backend."),
          version: null,
          checkedAt: Date.now(),
        });
      }
    };

    void refreshHealth();
    timer = window.setInterval(() => void refreshHealth(), 30000);
    return () => {
      disposed = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const wsUrl = buildWsUrl("/ws/ui");
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setUiSocketStatus("connecting");
      socket = new WebSocket(wsUrl);
      socket.addEventListener("open", () => {
        setUiSocketStatus("connected");
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
      socket.addEventListener("error", () => {
        setUiSocketStatus("reconnecting");
      });
      socket.addEventListener("close", () => {
        if (disposed) {
          return;
        }
        setUiSocketStatus("reconnecting");
        reconnectTimer = window.setTimeout(connect, 3000);
      });
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  useEffect(() => {
    if (uiSocketStatus === "connected") {
      return;
    }

    const pollFallback = () => queueRefresh(["products", "totals", "brands", "margin", "automation", "history"]);
    const timer = window.setInterval(pollFallback, 15000);
    return () => window.clearInterval(timer);
  }, [uiSocketStatus]);

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
    const handleUndoRedoKeydown = (event: KeyboardEvent) => {
      const action = getGlobalUndoRedoAction(event);
      if (!action) {
        return;
      }
      event.preventDefault();
      if (action === "redo") {
        void redoLastAction();
      } else {
        void undoLastAction();
      }
    };

    document.addEventListener("keydown", handleUndoRedoKeydown);
    return () => document.removeEventListener("keydown", handleUndoRedoKeydown);
  }, []);

  useEffect(() => {
    if (!gradeModalOpen) return;
    if (!selectedGradeProduct) {
      gradeDraftBaselineRef.current = {};
      setGradeDraft({});
      return;
    }
    const savedDraft = gradeItemsToMap(selectedGradeProduct.grades);
    gradeDraftBaselineRef.current = savedDraft;
    setGradeDraft(savedDraft);
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
      saveLastActiveGradeFamily(activeGradeFamilyKey);
    }
  }, [activeGradeFamilyKey]);

  const handleInputChange = <K extends keyof ProductPayload>(key: K, value: ProductPayload[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  useEffect(() => () => {
    if (pendingProductFocusFrame.current !== null) {
      window.cancelAnimationFrame(pendingProductFocusFrame.current);
    }
  }, []);

  const focusProductField = (field: ProductFormField) => {
    visitedProductFields.current.add(field);
    const quickEntryTarget = document.querySelector<HTMLInputElement>(`#catalog-quick-entry [name="${field}"]`);
    const target = quickEntryTarget ?? (
      field === "nome"
        ? nameInputRef.current
        : field === "codigo"
          ? codeInputRef.current
          : field === "quantidade"
            ? quantityInputRef.current
            : priceInputRef.current
    );
    target?.focus();
    target?.select?.();
  };

  const scheduleProductFieldFocus = (field: ProductFormField) => {
    if (pendingProductFocusFrame.current !== null) {
      window.cancelAnimationFrame(pendingProductFocusFrame.current);
    }
    pendingProductFocusFrame.current = window.requestAnimationFrame(() => {
      pendingProductFocusFrame.current = null;
      focusProductField(field);
    });
  };

  const getFirstMissingProductField = (): ProductFormField | null => {
    return findFirstMissingProductField(form, simpleModeEnabled);
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
      const nextField = getNextProductFormField(currentField, simpleModeEnabled);
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
      const nextField = getNextProductFormField(currentField, simpleModeEnabled);
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

  const runOrderingDraftTransition = (update: () => void) => {
    const transitionDocument = document as Document & {
      startViewTransition?: (callback: () => void) => void;
    };
    if (typeof transitionDocument.startViewTransition === "function") {
      transitionDocument.startViewTransition(() => flushSync(update));
      return;
    }
    update();
  };

  const submitProduct = async () => {
    const payloadResult = buildCreateProductPayload(form, simpleModeEnabled);
    if (!payloadResult.ok) {
      focusProductField(payloadResult.missing);
      return;
    }
    setSubmitting(true);
    try {
      await pushUndoSnapshot();
      await createProduct(payloadResult.payload);
      rememberProductOperation({
        action: "create",
        productName: payloadResult.payload.nome,
        value: payloadResult.payload.codigo,
        meta: [payloadResult.payload.marca, payloadResult.payload.categoria],
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
      scheduleProductFieldFocus("nome");
      queueRefresh(["products", "totals", "brands"]);
    } catch (error) {
      showErrorNotice("Falha ao criar produto", formatCaughtErrorMessage(error, "Falha ao criar produto."));
    } finally {
      setSubmitting(false);
    }
  };

  const updateImportDocument = (documentId: string, update: Partial<StagedImportDocument>) => {
    setImportDocuments((current) => current.map((document) => document.id === documentId ? { ...document, ...update } : document));
  };

  const runImportBatch = async (documents: StagedImportDocument[], mode: "llm" | "local") => {
    if (!documents.length || importing || localExperimentLoading) return;
    const targetIds = new Set(documents.map((document) => document.id));
    let succeededCount = 0;
    let failedCount = 0;
    let totalItems = 0;
    setImportError(null);
    setImportResult(null);
    setImportJob(null);
    setImportDocuments((current) => current.map((document) => targetIds.has(document.id)
      ? { ...document, state: "queued", importMode: mode, status: null, result: null, error: null, errorReasons: [] }
      : document));
    if (mode === "llm") setImporting(true);
    else setLocalExperimentLoading(true);

    try {
      await pushUndoSnapshot();
      for (const document of documents) {
        setActiveImportDocumentId(document.id);
        importFileNameRef.current = document.file.name;
        updateImportDocument(document.id, { state: "processing", importMode: mode, error: null, errorReasons: [] });
        try {
          if (mode === "local") {
            const result = await importRomaneioLocalExperiment(document.file);
            setImportResult(result);
            updateImportDocument(document.id, { state: "succeeded", importMode: mode, result });
            succeededCount += 1;
            totalItems += Number(result.total_itens || 0);
            const historyEntry = rememberImportHistory(result, { mode: "local", selectedFileName: document.file.name });
            rememberOperationDiary({ kind: "import", title: "Leitura local concluída", detail: historyEntry.sourceName, tone: historyEntry.warningCount ? "warning" : "success", occurredAt: historyEntry.completedAt, meta: [historyEntry.mode, `${historyEntry.totalItems} itens`, historyEntry.validationStatus] });
            await refreshAfterLocalImport(result);
          } else {
            const started = await importRomaneio(document.file);
            let terminalStatus: ImportStatus | null = null;
            try {
              terminalStatus = await waitForImportJob(started.job_id, {
                onStatus: (status) => {
                  setImportJob(status);
                  updateImportDocument(document.id, { status });
                },
              });
              if (terminalStatus.stage === "completed") {
                const result = await fetchImportResult(started.job_id);
                setImportResult(result);
                updateImportDocument(document.id, { state: "succeeded", importMode: mode, status: terminalStatus, result });
                succeededCount += 1;
                totalItems += Number(result.total_itens || 0);
                const historyEntry = rememberImportHistory(result, { job: terminalStatus, mode: "llm", selectedFileName: document.file.name });
                rememberOperationDiary({ kind: "import", title: "Importação concluída", detail: historyEntry.sourceName, tone: historyEntry.warningCount ? "warning" : "success", occurredAt: historyEntry.completedAt, meta: [historyEntry.mode, `${historyEntry.totalItems} itens`, historyEntry.validationStatus] });
                const gradesMessage = buildImportGradesAvailableMessage(result);
                if (gradesMessage) showNoticeDialog({ title: "Grades detectadas", message: gradesMessage, tone: "info" });
              } else {
                const message = terminalStatus.error || "A importação foi bloqueada.";
                const reasons = extractImportFailureReasons(terminalStatus.metrics, message);
                updateImportDocument(document.id, { state: "failed", importMode: mode, status: terminalStatus, error: message, errorReasons: reasons });
                failedCount += 1;
                setImportError(message);
                rememberOperationDiary({ kind: "import", title: "Falha na importação", detail: reasons.join(" ") || message, tone: "error", occurredAt: Number(terminalStatus.updated_at || 0) * 1000 || Date.now(), meta: [document.file.name] });
              }
            } finally {
              if (terminalStatus?.stage === "completed" || terminalStatus?.stage === "error") {
                try { await cleanupImportJob(started.job_id); } catch { /* terminal diagnostics stay visible */ }
              }
            }
          }
        } catch (error) {
          const message = formatCaughtErrorMessage(error, mode === "local" ? "Falha ao importar com leitura local." : "Falha ao iniciar importação.");
          updateImportDocument(document.id, { state: "failed", importMode: mode, error: message, errorReasons: [message] });
          failedCount += 1;
          setImportError(message);
          rememberOperationDiary({ kind: "import", title: mode === "local" ? "Falha na leitura local" : "Falha na importação", detail: message, tone: "error", meta: [document.file.name] });
        }
      }
      const batchTotal = succeededCount + failedCount;
      const batchMessage = failedCount
        ? succeededCount
          ? `${succeededCount} de ${batchTotal} documentos importados. ${failedCount} documento${failedCount === 1 ? " foi bloqueado" : "s foram bloqueados"}.`
          : "Nenhum documento foi importado. Revise os motivos no painel."
        : `${succeededCount} de ${batchTotal} documentos importados — ${totalItems} itens.`;
      rememberOperationDiary({
        kind: "import",
        title: failedCount ? (succeededCount ? "Lote importado parcialmente" : "Lote de importação bloqueado") : "Lote de importação concluído",
        detail: batchMessage,
        tone: failedCount ? (succeededCount ? "warning" : "error") : "success",
        meta: [mode === "local" ? "Leitura local" : "IA", `${totalItems} itens`],
      });
      setImportError(failedCount ? batchMessage : null);
      queueRefresh(["products", "totals", "brands"]);
    } finally {
      setActiveImportDocumentId(null);
      setImporting(false);
      setLocalExperimentLoading(false);
    }
  };

  const handleImportPrimaryClick = () => {
    if (importing || localExperimentLoading) return;
    importModeRef.current = "llm";
    importInputRef.current?.click();
  };

  const handleLocalExperimentClick = () => {
    if (importing || localExperimentLoading) return;
    importModeRef.current = "local";
    importInputRef.current?.click();
  };

  const handleFilePickerClick = () => {
    if (importing || localExperimentLoading) return;
    importModeRef.current = "llm";
  };

  const handleStartManualEntry = () => {
    setProductSearchQuery("");
    window.requestAnimationFrame(() => {
      focusProductField("nome");
    });
  };

  const handleUseProductAsTemplate = (product: Product) => {
    setForm(buildProductTemplatePayload(product));
    visitedProductFields.current.clear();
    showNoticeDialog({
      title: "Modelo pronto para cadastro",
      message: `Os dados de ${product.nome} foram reaproveitados. Revise o nome e informe um novo código.`,
      tone: "success",
    });
    window.requestAnimationFrame(() => {
      focusProductField("nome");
    });
  };

  const handleImportFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    const nextCollection = createStagedImportDocuments(files, importDocuments);
    const existingIds = new Set(importDocuments.map((document) => document.id));
    const addedDocuments = nextCollection.filter((document) => !existingIds.has(document.id));
    if (!addedDocuments.length) return;
    setImportDocuments(nextCollection);
    void runImportBatch(addedDocuments, importModeRef.current);
  };

  const handleImportDocumentsChange = (documents: StagedImportDocument[]) => {
    setImportDocuments(documents);
  };

  const handleRemoveImportDocument = (documentId: string) => {
    if (importing || localExperimentLoading) return;
    setImportDocuments((current) => {
      const next = current.filter((document) => document.id !== documentId);
      const layout = buildAutomaticImportLayout(next.length);
      return next.map((document, index) => ({ ...document, rect: layout[index], zIndex: index + 1 }));
    });
  };

  const handleRetryFailedImports = () => {
    if (importing || localExperimentLoading) return;
    const failed = importDocuments.filter((document) => document.state === "failed");
    void (async () => {
      for (const mode of ["llm", "local"] as const) {
        const matchingMode = failed.filter((document) => (document.importMode || importModeRef.current) === mode);
        if (!matchingMode.length) continue;
        importModeRef.current = mode;
        await runImportBatch(matchingMode, mode);
      }
    })();
  };

  const openConfirmationDialog = (dialog: ConfirmationDialogState) => {
    setConfirmationError(null);
    setConfirmationBusy(false);
    setConfirmationDialog(dialog);
  };

  const closeConfirmationDialog = () => {
    if (confirmationBusy) return;
    confirmationDialog?.onCancel?.();
    setConfirmationDialog(null);
    setConfirmationError(null);
  };

  const handleConfirmationDialogConfirm = async () => {
    if (!confirmationDialog || confirmationBusy) return;
    setConfirmationBusy(true);
    setConfirmationError(null);
    try {
      await confirmationDialog.onConfirm();
      setConfirmationDialog(null);
    } catch (error) {
      setConfirmationError(formatCaughtErrorMessage(error, "Falha ao executar a ação."));
    } finally {
      setConfirmationBusy(false);
    }
  };

  const confirmWithDialog = (dialog: Omit<ConfirmationDialogState, "onConfirm" | "onCancel">) => {
    return new Promise<boolean>((resolve) => {
      openConfirmationDialog({
        ...dialog,
        onCancel: () => resolve(false),
        onConfirm: async () => {
          resolve(true);
        },
      });
    });
  };

  const openTextInputDialog = (dialog: TextInputDialogState) => {
    setTextInputError(null);
    setTextInputBusy(false);
    setTextInputDialog(dialog);
  };

  const closeTextInputDialog = () => {
    if (textInputBusy) return;
    setTextInputDialog(null);
    setTextInputError(null);
  };

  const handleTextInputDialogConfirm = async () => {
    if (!textInputDialog || textInputBusy) return;
    const validationError = textInputDialog.validate?.(textInputDialog.value) ?? null;
    if (validationError) {
      setTextInputError(validationError);
      return;
    }

    setTextInputBusy(true);
    setTextInputError(null);
    try {
      await textInputDialog.onConfirm(textInputDialog.value);
      setTextInputDialog(null);
    } catch (error) {
      setTextInputError(formatCaughtErrorMessage(error, "Falha ao salvar."));
    } finally {
      setTextInputBusy(false);
    }
  };

  const submitBrand = async () => {
    if (!newBrand.trim()) return;
    const normalized = newBrand.trim();
    try {
      const result = await addBrand(normalized);
      setNewBrand("");
      setShowBrandComposer(false);
      setBulkBrandValue(normalized);
      startTransition(() => {
        setState((current) => ({ ...current, brands: result.marcas }));
      });
      await pushUndoSnapshot();
      const applied = await applyBrand(normalized, visibleBulkActionKeys);
      rememberProductOperation({
        action: "bulk_brand",
        value: applied.marca || normalized,
        productCount: applied.total,
        meta: ["Nova marca"],
      });
      setShowBulkBrandMenu(false);
      queueRefresh(["products", "totals", "brands"]);
    } catch (error) {
      showErrorNotice("Falha ao adicionar marca", formatCaughtErrorMessage(error, "Falha ao adicionar marca."));
    }
  };

  const handleAutomationAction = async (mode: "catalog" | "complete" | "stop") => {
    setAutomationError(null);
    const actionLabels: Record<typeof mode, { title: string; detail: string; tone: "success" | "warning" }> = {
      catalog: { title: "Cadastro iniciado", detail: "Execução de cadastro", tone: "success" },
      complete: { title: "Cadastro completo iniciado", detail: "Execução completa", tone: "success" },
      stop: { title: "Parada solicitada", detail: "Automação", tone: "warning" },
    };
    try {
      if (mode === "catalog") {
        await startAutomationCatalog();
      } else if (mode === "complete") {
        await startAutomationComplete();
      } else {
        await stopAutomation();
      }
      rememberOperationDiary({
        kind: "automation",
        title: actionLabels[mode].title,
        detail: actionLabels[mode].detail,
        tone: actionLabels[mode].tone,
        meta: [state.automation.estado || "idle"],
      });
      queueRefresh(["automation"]);
    } catch (error) {
      const message = formatCaughtErrorMessage(error, "Falha na automação.");
      setAutomationError(message);
      rememberOperationDiary({
        kind: "automation",
        title: "Falha na automação",
        detail: message,
        tone: "error",
        meta: [actionLabels[mode].detail],
      });
    }
  };

  const buildIncompleteGradesAlert = () => {
    const sample = incompleteGradeProducts
      .slice(0, 3)
      .map(({ product, total, expected }) => `${product.nome} (${total}/${expected})`)
      .join("\n");
    const remaining = incompleteGradeProducts.length - Math.min(incompleteGradeProducts.length, 3);
    const more = remaining > 0 ? `\nE mais ${remaining} item(ns).` : "";
    return `Ainda existem grades pendentes.\n\nCorrija antes de usar o cadastro completo:\n${sample}${more}`;
  };

  const buildPendingGradeImportAlert = () => {
    const sample = pendingGradeImportProducts
      .slice(0, 3)
      .map((product) => product.nome)
      .join("\n");
    const remaining = pendingGradeImportProducts.length - Math.min(pendingGradeImportProducts.length, 3);
    const more = remaining > 0 ? `\nE mais ${remaining} item(ns).` : "";
    return `Existem grades detectadas que ainda nao foram aplicadas.\n\nImporte as grades antes do cadastro completo:\n${sample}${more}`;
  };

  const handleStartComplete = async () => {
    if (pendingGradeImportProducts.length) {
      rememberOperationDiary({
        kind: "grade",
        title: "Cadastro completo pausado",
        detail: `${pendingGradeImportProducts.length} grade${pendingGradeImportProducts.length === 1 ? "" : "s"} para importar`,
        tone: "warning",
        meta: ["Importar grades pendente"],
      });
      showNoticeDialog({
        title: "Grades para importar",
        message: `${buildPendingGradeImportAlert()}\n\nUse Importar grades no centro de execução para aplicar as grades detectadas.`,
        tone: "warning",
      });
      return;
    }

    if (incompleteGradeProducts.length) {
      const firstPendingKey = incompleteGradeProducts[0]?.product.ordering_key || null;
      rememberOperationDiary({
        kind: "grade",
        title: "Cadastro completo pausado",
        detail: `${incompleteGradeProducts.length} grade${incompleteGradeProducts.length === 1 ? "" : "s"} pendente${incompleteGradeProducts.length === 1 ? "" : "s"}`,
        tone: "warning",
        meta: ["Inserir grade aberto"],
      });
      showNoticeDialog({
        title: "Grades pendentes",
        message: `${buildIncompleteGradesAlert()}\n\nVou abrir o Inserir grade no primeiro item pendente.`,
        tone: "warning",
      });
      await openGradeModal(firstPendingKey);
      return;
    }
    await handleAutomationAction("complete");
  };

  const handleClearProducts = async () => {
    if (!state.products.length) return;
    const confirmed = await confirmWithDialog(
      buildClearProductsConfirmation(state.products.length, displayedProducts.length),
    );
    if (!confirmed) return;
    await pushUndoSnapshot();
    const result = await clearProducts();
    rememberProductOperation({
      action: "clear",
      productCount: result.removed || state.products.length,
    });
    queueRefresh(["products", "totals", "brands"]);
  };

  const handleApplyCategory = async (value?: string) => {
    const category = (value ?? bulkCategoryValue).trim();
    if (!category) {
      showNoticeDialog({ title: "Seleção obrigatória", message: "Selecione uma categoria antes de aplicar.", tone: "warning" });
      return;
    }
    setBulkCategoryValue(category);
    await pushUndoSnapshot();
    const result = await applyCategory(category, visibleBulkActionKeys);
    rememberProductOperation({
      action: "bulk_category",
      value: result.categoria || category,
      productCount: result.total,
    });
    setShowBulkCategoryMenu(false);
    queueRefresh(["products", "totals"]);
  };

  const handleApplyBrand = async (value?: string) => {
    const brand = (value ?? bulkBrandValue).trim();
    if (!brand) {
      showNoticeDialog({ title: "Selecao obrigatoria", message: "Selecione uma marca antes de aplicar.", tone: "warning" });
      return;
    }
    setBulkBrandValue(brand);
    await pushUndoSnapshot();
    const result = await applyBrand(brand, visibleBulkActionKeys);
    rememberProductOperation({
      action: "bulk_brand",
      value: result.marca || brand,
      productCount: result.total,
    });
    setShowBulkBrandMenu(false);
    queueRefresh(["products", "totals", "brands"]);
  };

  const handleJoinDuplicates = async () => {
    if (visibleBulkActionKeys?.length === 0) {
      showNoticeDialog({
        title: "Sem produtos visiveis",
        message: "Ajuste ou limpe os filtros antes de juntar itens repetidos.",
        tone: "warning",
      });
      return;
    }
    await pushUndoSnapshot();
    const result = await joinDuplicates(visibleBulkActionKeys);
    queueRefresh(["products", "totals"]);
    const scopeMessage = visibleBulkActionKeys === undefined
      ? `Escopo: catalogo completo (${result.originais} produtos).`
      : `Escopo: ${result.originais} de ${state.products.length} produtos visiveis. Itens fora do resultado atual foram preservados e podem continuar repetidos.`;
    showNoticeDialog({
      title: result.removidos ? "Itens repetidos reunidos" : "Nenhum repetido no resultado",
      message: `${scopeMessage}\nOriginais: ${result.originais}\nResultantes: ${result.resultantes}\nRemovidos: ${result.removidos}`,
      tone: result.removidos ? "success" : "info",
    });
  };

  const handleExportVisibleProducts = () => {
    if (!displayedProducts.length) {
      showNoticeDialog({
        title: "Nada para exportar",
        message: "A busca atual não contém produtos para baixar.",
        tone: "warning",
      });
      return;
    }

    const csv = buildProductCsv(displayedProducts);
    const downloadUrl = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = buildProductCsvFilename();
    link.hidden = true;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);

    const isFiltered = displayedProducts.length < state.products.length;
    showNoticeDialog({
      title: "CSV pronto",
      message: `${displayedProducts.length === 1 ? "1 produto exportado" : `${displayedProducts.length} produtos exportados`}${isFiltered ? " da busca atual" : " do catálogo"}.`,
      tone: "success",
    });
  };

  const handleJoinGrades = async () => {
    await pushUndoSnapshot();
    const result = await joinGrades();
    queueRefresh(["products", "totals"]);
    if (!result.lotes_processados) {
      showNoticeDialog({ title: "Sem grades pendentes", message: "Não há lotes com grades pendentes para importar.", tone: "info" });
      return;
    }
    showNoticeDialog({
      title: "Grades importadas",
      message: `Lotes processados: ${result.lotes_processados}\nProdutos finais: ${result.resultantes}\nGrades importadas: ${result.atualizados_grades}\nLinhas unificadas: ${result.removidos}`,
      tone: "success",
    });
  };

  const closeMarginDialog = () => {
    if (marginBusy) return;
    setMarginDialogOpen(false);
    setMarginError(null);
  };

  const handleMargin = async () => {
    setMarginDraft(state.marginPercentual.toFixed(2).replace(".", ","));
    setMarginError(null);
    setMarginBusy(false);
    setMarginDialogOpen(true);
  };

  const handleApplyMarginDialog = async () => {
    if (marginBusy) {
      return;
    }
    const percentual = parsePositivePercentInput(marginDraft);
    if (percentual == null) {
      setMarginError("Informe um percentual maior que zero.");
      return;
    }
    if (visibleBulkActionKeys?.length === 0) {
      setMarginError("O resultado atual nao tem produtos para receber a margem.");
      return;
    }

    setMarginBusy(true);
    setMarginError(null);
    try {
      await pushUndoSnapshot();
      await saveMargin(percentual);
      const result = await applyMargin(percentual, visibleBulkActionKeys);
      rememberProductOperation({
        action: "margin",
        value: formatPercentDisplay(result.percentual_utilizado).replace("%", ""),
        changedCount: result.total_atualizados,
      });
      queueRefresh(["products", "totals", "margin"]);
      setMarginDialogOpen(false);
    } catch (error) {
      setMarginError(formatCaughtErrorMessage(error, "Falha ao aplicar margem."));
    } finally {
      setMarginBusy(false);
    }
  };

  const handleFormatCodes = async () => {
    if (visibleBulkActionKeys?.length === 0) {
      showNoticeDialog({ title: "Sem produtos visiveis", message: "Ajuste ou limpe os filtros antes de formatar codigos.", tone: "warning" });
      return;
    }
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
      keys: visibleBulkActionKeys,
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
      showNoticeDialog({ title: "Seleção obrigatória", message: "Escolha pelo menos uma opção para cortar números do código.", tone: "warning" });
      return;
    }
    await pushUndoSnapshot();
    const result = await formatCodes(payload);
    rememberProductOperation({
      action: "format_codes",
      productCount: result.total,
      changedCount: result.alterados,
      value: result.prefixo ? `Prefixo ${result.prefixo}` : null,
    });
    queueRefresh(["products"]);
    setShowFormatCodesPanel(false);
    showNoticeDialog({
      title: "Códigos formatados",
      message: `Total analisado: ${result.total}\nAlterados: ${result.alterados}${result.prefixo ? `\nPrefixo removido: ${result.prefixo}` : ""}`,
      tone: "success",
    });
  };

  const handleImproveDescriptions = async () => {
    if (visibleBulkActionKeys?.length === 0) {
      showNoticeDialog({ title: "Sem produtos visiveis", message: "Ajuste ou limpe os filtros antes de limpar nomes e descricoes.", tone: "warning" });
      return;
    }
    const termos = parseDescriptionRemovalTerms(descriptionOptions.remover_termos);
    if (!descriptionOptions.remover_numeros && !descriptionOptions.remover_especiais && !termos.length) {
      showNoticeDialog({ title: "Seleção obrigatória", message: "Selecione ao menos uma regra de limpeza.", tone: "warning" });
      return;
    }
    await pushUndoSnapshot();
    const result = await improveDescriptions({
      remover_numeros: descriptionOptions.remover_numeros,
      remover_especiais: descriptionOptions.remover_especiais,
      remover_termos: termos,
      keys: visibleBulkActionKeys,
    });
    rememberProductOperation({
      action: "improve_descriptions",
      productCount: result.total,
      changedCount: result.modificados,
    });
    queueRefresh(["products"]);
    setShowDescriptionPanel(false);
    showNoticeDialog({
      title: "Descrições atualizadas",
      message: `Descrições analisadas: ${result.total}\nDescrições modificadas: ${result.modificados}`,
      tone: "success",
    });
  };

  const handleExecuteGrades = async () => {
    if (gradeModalOpen && gradeDraftDirty) {
      showNoticeDialog({
        title: "Salve a grade antes de executar",
        message: "As quantidades alteradas ainda estão apenas no rascunho. Use Salvar para incluí-las na execução.",
        tone: "warning",
      });
      return;
    }
    await executeGradesProducts();
    queueRefresh(["automation"]);
  };

  const handleStopGrades = async () => {
    await stopGradesExecution();
    queueRefresh(["automation"]);
  };

  const openGradeModal = async (preferredOrderingKey?: string | null) => {
    if (!state.products.length) {
      showNoticeDialog({ title: "Lista vazia", message: "Não há itens na lista para inserir grades.", tone: "warning" });
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

  const confirmGradeDraftDiscard = async () => {
    if (gradeMutationPendingRef.current) {
      showNoticeDialog({
        title: "Aguarde a atualização da grade",
        message: "O salvamento atual precisa terminar antes de trocar de produto ou fechar esta tela.",
        tone: "warning",
      });
      return false;
    }
    if (!hasGradeDraftChanges(gradeDraft, gradeDraftBaselineRef.current) || !selectedGradeProduct) {
      return true;
    }
    if (gradeTransitionPendingRef.current) {
      return false;
    }
    gradeTransitionPendingRef.current = true;
    try {
      return await confirmWithDialog({
        title: "Descartar alterações da grade?",
        message: `"${selectedGradeProduct.nome}" tem quantidades alteradas que ainda não foram salvas.`,
        detail: "Ao continuar, o rascunho será perdido. Cancele e use Salvar ou Salvar e Próxima Pendência para manter as alterações.",
        confirmLabel: "Descartar e continuar",
      });
    } finally {
      gradeTransitionPendingRef.current = false;
    }
  };

  const closeGradeModal = () => {
    void (async () => {
      if (!(await confirmGradeDraftDiscard())) {
        return;
      }
      setGradeDraft({ ...gradeDraftBaselineRef.current });
      setGradeModalOpen(false);
      setGradeModalError(null);
    })();
  };

  const requestGradeProductSelection = async (
    orderingKey: string,
    options?: { focusInput?: boolean; skipDiscardCheck?: boolean },
  ) => {
    if (!orderingKey || orderingKey === gradeSelectedKey) {
      return false;
    }
    if (!options?.skipDiscardCheck && !(await confirmGradeDraftDiscard())) {
      return false;
    }
    const targetProduct = productsByKey.get(orderingKey);
    if (!targetProduct) {
      return false;
    }
    const targetDraft = gradeItemsToMap(targetProduct.grades);
    gradeDraftBaselineRef.current = targetDraft;
    setGradeDraft(targetDraft);
    setGradeValidationError(null);
    pendingGradeInputFocus.current = Boolean(options?.focusInput);
    setGradeSelectedKey(orderingKey);
    return true;
  };

  const handleSelectGradeProduct = (orderingKey: string) => {
    void requestGradeProductSelection(orderingKey);
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
        setGradeModalError(formatCaughtErrorMessage(error, "Falha ao salvar ordem visual dos tamanhos."));
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
    openTextInputDialog({
      title: "Renomear tamanho",
      description: "Atualize o nome exibido na grade visual. A ordem do ERP continua separada.",
      label: "Novo tamanho",
      value: currentSize,
      confirmLabel: "Salvar tamanho",
      sectionTag: "Grade",
      placeholder: currentSize,
      validate: (value) => {
        const normalized = normalizeGradeSizeLabel(value);
        if (!normalized) return "Informe um tamanho valido.";
        if (normalized !== currentSize && gradeOrderDraft.includes(normalized)) {
          return `"${normalized}" ja existe na grade.`;
        }
        return null;
      },
      onConfirm: async (value) => {
        const normalized = normalizeGradeSizeLabel(value);
        if (!normalized || normalized === currentSize) return;
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
      },
    });
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
    if (gradeMutationPendingRef.current) {
      return;
    }
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
    return buildGradeProductStatus(product, product.ordering_key === gradeSelectedKey ? currentGradeTotal : undefined);
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
    if (!selectedGradeProduct || gradeMutationPendingRef.current) {
      return false;
    }
    const validation = validateSelectedGrade();
    if (!validation.ok) {
      setGradeValidationError(validation.message);
      return false;
    }
    const grades = buildGradeItemsFromDraft(gradeDraft);
    gradeMutationPendingRef.current = true;
    try {
      await pushUndoSnapshot();
      await patchProduct(selectedGradeProduct.ordering_key, { grades });
      const savedDraft = gradeItemsToMap(grades);
      gradeDraftBaselineRef.current = savedDraft;
      setGradeDraft(savedDraft);
      setGradeValidationError(null);
      queueRefresh(["products", "totals"]);
      return true;
    } finally {
      gradeMutationPendingRef.current = false;
    }
  };

  const handleSaveSelectedGrade = async () => {
    await saveSelectedGrade();
  };

  const handleSaveAndNextGrade = async () => {
    if (!selectedGradeProduct) {
      return;
    }
    const currentOrderingKey = selectedGradeProduct.ordering_key;
    const saved = await saveSelectedGrade();
    if (!saved) {
      return;
    }
    const nextPendingKey = findNextPendingGradeKey(state.products, currentOrderingKey, currentOrderingKey);
    if (nextPendingKey) {
      await requestGradeProductSelection(nextPendingKey, { focusInput: true, skipDiscardCheck: true });
    }
  };

  const handleSelectNextPendingGrade = () => {
    if (!nextPendingGradeKey) {
      return;
    }
    void requestGradeProductSelection(nextPendingGradeKey, { focusInput: true });
  };

  const handleClearSelectedGrade = async () => {
    if (!selectedGradeProduct || gradeMutationPendingRef.current) {
      return;
    }
    gradeMutationPendingRef.current = true;
    try {
      await pushUndoSnapshot();
      await patchProduct(selectedGradeProduct.ordering_key, { grades: [] });
      gradeDraftBaselineRef.current = {};
      setGradeDraft({});
      setGradeValidationError(null);
      queueRefresh(["products", "totals"]);
    } finally {
      gradeMutationPendingRef.current = false;
    }
  };

  const handleClearAllGrades = async () => {
    if (gradeMutationPendingRef.current) {
      showNoticeDialog({
        title: "Aguarde a atualização da grade",
        message: "O salvamento atual precisa terminar antes de limpar as grades.",
        tone: "warning",
      });
      return;
    }
    const productsWithGrades = state.products.filter((product) => (product.grades || []).length > 0 || product.ordering_key === gradeSelectedKey);
    openConfirmationDialog({
      title: "Limpar todas as grades?",
      message: "As grades preenchidas serao removidas da lista ativa.",
      detail: `${productsWithGrades.length} itens serao afetados. A lista de produtos e os dados de cadastro permanecem intactos.`,
      confirmLabel: "Limpar grades",
      onConfirm: async () => {
        gradeMutationPendingRef.current = true;
        try {
          await pushUndoSnapshot();
          await Promise.all(productsWithGrades.map((product) => patchProduct(product.ordering_key, { grades: [] })));
          gradeDraftBaselineRef.current = {};
          setGradeDraft({});
          setGradeValidationError(null);
          queueRefresh(["products", "totals"]);
        } finally {
          gradeMutationPendingRef.current = false;
        }
      },
    });
  };

  useEffect(() => {
    if (!gradeModalOpen || confirmationDialog || !pendingGradeInputFocus.current) {
      return;
    }
    pendingGradeInputFocus.current = false;
    const timer = window.setTimeout(() => {
      focusFirstActiveGradeInput();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [activeGradeFamilyKey, confirmationDialog, gradeModalOpen, gradeSelectedKey]);

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
      clearOrderingDraft();
      setOrderingDraftKeys([]);
      setOrderingMode(true);
      return;
    }
    const finalOrder = buildFinalOrderingKeys(originalOrderingKeys, orderingDraftKeys);
    if (finalOrder.length) {
      await pushUndoSnapshot();
      const result = await reorderProducts(finalOrder);
      rememberProductOperation({
        action: "reorder",
        productCount: result.total || finalOrder.length,
        meta: [`${orderingDraftKeys.length} selecionados`],
      });
      queueRefresh(["products"]);
    }
    setOrderingMode(false);
    setOrderingDraftKeys([]);
    clearOrderingDraft();
  };

  const handleCancelOrdering = () => {
    setOrderingMode(false);
    setOrderingDraftKeys([]);
    clearOrderingDraft();
  };

  const handleOrderingSelection = (orderingKey: string, options?: { allowRemove?: boolean }) => {
    if (!orderingMode) return;
    runOrderingDraftTransition(() => {
      setOrderingDraftKeys((current) => toggleOrderingKey(current, orderingKey, options));
    });
  };

  const moveOrderingItem = (orderingKey: string, direction: -1 | 1) => {
    if (!orderingMode) return;
    runOrderingDraftTransition(() => {
      setOrderingDraftKeys((current) => moveOrderingKey(current, orderingKey, direction));
    });
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
      await pushUndoSnapshot();
      const result = await createSet(futureKeys[0], futureKeys[1]);
      rememberProductOperation({
        action: "create_set",
        value: `${result.created} conjunto${result.created === 1 ? "" : "s"}`,
        removedCount: result.removed,
      });
      setCreateSetMode(false);
      setCreateSetKeys([]);
      queueRefresh(["products", "totals"]);
      showNoticeDialog({
        title: "Conjunto criado",
        message: `Conjunto criado: ${result.created}\nLinhas removidas: ${result.removed}`,
        tone: "success",
      });
    }
  };

  const startInlineEdit = (product: Product, field: EditableField) => {
    const value = getInlineEditInitialValue(product, field);
    setEditingCell({ orderingKey: product.ordering_key, field, value });
  };

  const handleInlineEditChange = (value: string) => {
    setEditingCell((current) => {
      if (!current) return current;
      const next = { ...current, value };
      const nextProducts = state.products.map((product) =>
        product.ordering_key === current.orderingKey
          ? buildProductPreview(product, current.field, value, state.marginPercentual)
          : product,
      );
      applyProductsPreview(nextProducts);
      return next;
    });
  };

  const commitInlineEdit = async () => {
    if (!editingCell) return;
    const { orderingKey, field, value } = editingCell;
    const payloadResult = buildInlineEditPayload(field, value);
    if (!payloadResult.ok) {
      showNoticeDialog({ title: "Edição inválida", message: payloadResult.error, tone: "warning" });
      return;
    }

    try {
      await pushUndoSnapshot();
      await patchProduct(orderingKey, payloadResult.payload);
      const product = productsByKey.get(orderingKey);
      rememberProductOperation({
        action: "inline_edit",
        productName: product?.nome || orderingKey,
        fieldLabel: INLINE_EDIT_FIELD_LABELS[field],
      });
      setEditingCell(null);
      queueRefresh(["products", "totals", "brands"]);
    } catch (error) {
      setEditingCell(null);
      queueRefresh(["products", "totals", "brands"]);
      showErrorNotice("Falha ao atualizar item", formatCaughtErrorMessage(error, "Falha ao atualizar item."));
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
      showErrorNotice(`Falha em ${name}`, formatCaughtErrorMessage(error, `Falha em ${name}.`));
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
      setSettingsError(formatCaughtErrorMessage(error, "Falha ao carregar configurações."));
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
      setSettingsError(formatCaughtErrorMessage(error, "Falha ao salvar targets."));
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
      setSettingsMessage("Configuração de grades salva com sucesso.");
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(formatCaughtErrorMessage(error, "Falha ao salvar configuração de grades."));
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
      setSettingsError(formatCaughtErrorMessage(error, `Falha ao capturar ${label}.`));
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
      setSettingsError(formatCaughtErrorMessage(error, `Falha ao capturar ${label}.`));
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
      setSettingsMessage(`Primeira célula de quantidade capturada em ${formatTargetPoint(point)}.`);
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(formatCaughtErrorMessage(error, "Falha ao capturar a primeira célula."));
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
      setSettingsError(formatCaughtErrorMessage(error, "Falha ao consultar contexto do ByteEmpresa."));
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
      setSettingsMessage("Preparação do ByteEmpresa executada.");
      queueRefresh(["automation"]);
    } catch (error) {
      setSettingsError(formatCaughtErrorMessage(error, "Falha ao preparar a janela do ByteEmpresa."));
    } finally {
      setSettingsSaving(null);
    }
  };

  const automationIsRunning = state.automation.estado === "running";
  const automationCurrentOrderingKey = state.automation.ordering_key_atual || null;
  const automationCurrentName = state.automation.produto_atual || null;
  const automationTypedDescription = state.automation.descricao_digitada || null;
  const automationProgressWidth = automationIsRunning
    ? state.automation.item_atual && state.automation.total_itens && state.automation.total_itens > 0
      ? `${Math.max(8, Math.min(100, Math.round((state.automation.item_atual / state.automation.total_itens) * 100)))}%`
      : "68%"
    : "0%";
  const importMetrics =
    importJob?.metrics && Object.keys(importJob.metrics).length
      ? importJob.metrics
      : importResult?.metrics && Object.keys(importResult.metrics).length
        ? importResult.metrics
        : {};
  const importWarnings = importResult?.warnings?.length ? importResult.warnings : [];
  const importValidationStatus = String(importMetrics["final_validation_status"] || importMetrics["local_validation_status"] || "").trim();
  const importProgressMessage = buildImportProgressMessage(importing, importJob?.message);
  const importDiagnosticsChips = buildImportDiagnosticsChips(importMetrics, importWarnings);
  const importSuccessMessage = importResult ? `${importResult.total_itens} itens importados as ${formatTimestamp(importJob?.updated_at)}.` : null;
  const executionReadiness = buildExecutionReadiness({
    productCount: state.products.length,
    pendingGradeImportCount: pendingGradeImportProducts.length,
    pendingGradeCount: incompleteGradeProducts.length,
    automationState: state.automation.estado,
    automationError,
  });
  const activeWorkspaceMeta = WORKSPACES.find((workspace) => workspace.id === activeWorkspace) ?? WORKSPACES[0];
  const operationalHealthChips = buildOperationalHealthChips({
    backendStatus: runtimeHealth.status,
    authEnabled: authSession?.auth_enabled ?? false,
    authenticated: authSession?.authenticated ?? true,
    bootstrapRequired: authSession?.bootstrap_required ?? false,
    websocketStatus: uiSocketStatus,
    automationState: state.automation.estado,
    automationError,
    pendingGrades: pendingGradeImportProducts.length + incompleteGradeProducts.length,
  }).filter((chip) => chip.label !== "Auth");
  const navigateWorkspace = (workspace: WorkspaceId) => {
    if (workspace !== "catalog") setCatalogQuickEntryOpen(false);
    setActiveWorkspace(workspace);
    try { window.localStorage.setItem("lojasync-workspace", workspace); } catch { /* storage is optional */ }
    window.requestAnimationFrame(() => document.getElementById("workspace-panel")?.focus({ preventScroll: true }));
  };
  const startNewProduct = () => {
    catalogQuickEntryTriggerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    navigateWorkspace("catalog");
    setCatalogQuickEntryOpen(true);
  };
  const toggleCatalogQuickEntry = () => {
    if (catalogQuickEntryOpen) {
      setCatalogQuickEntryOpen(false);
      return;
    }
    startNewProduct();
  };

  return (
    <div className="shellViewport">
      <a
        className="skipLinkTs"
        href="#workspace-panel"
        onClick={(event) => {
          event.preventDefault();
          const workspacePanel = document.getElementById("workspace-panel");
          workspacePanel?.focus({ preventScroll: true });
          workspacePanel?.scrollIntoView({ block: "nearest", inline: "nearest" });
        }}
      >
        Pular para área de trabalho
      </a>
      <div className="shellStage">
        <main
          className="appShellTs"
          aria-labelledby={activeWorkspace === "catalog" ? undefined : "app-title"}
          aria-label={activeWorkspace === "catalog" ? "Catálogo" : undefined}
        >
          <aside className="nexSidebar" aria-label="Navegação principal">
            <div className="lojasyncBrandHeader">
              <img src="/logo.png" alt="" className="lojasyncLogoImg" />
              <div className="nexBrandCopy"><strong>LojaSync</strong><span>Estação operacional</span></div>
            </div>
            <nav className="nexNav">
              <span className="nexNavGroup">Operação</span>
              {WORKSPACES.slice(0, 4).map((workspace) => (
                <button key={workspace.id} className={`nexNavButton ${activeWorkspace === workspace.id ? "active" : ""}`} type="button" onClick={() => navigateWorkspace(workspace.id)} aria-current={activeWorkspace === workspace.id ? "page" : undefined} aria-pressed={activeWorkspace === workspace.id}>
                  <span className="nexNavIcon"><WorkspaceIcon id={workspace.id} /></span>{workspace.label}
                </button>
              ))}
              <span className="nexNavGroup nexControlGroup">Controle</span>
              {WORKSPACES.slice(4).map((workspace) => (
                <button key={workspace.id} className={`nexNavButton ${activeWorkspace === workspace.id ? "active" : ""}`} type="button" onClick={() => navigateWorkspace(workspace.id)} aria-current={activeWorkspace === workspace.id ? "page" : undefined} aria-pressed={activeWorkspace === workspace.id}>
                  <span className="nexNavIcon"><WorkspaceIcon id={workspace.id} /></span>{workspace.label}
                </button>
              ))}
            </nav>
            <div className="nexSidebarFoot"><span>{sidebarClockText}</span><span>{sidebarDateText}</span></div>
          </aside>

          <div className="nexMain">
            {activeWorkspace !== "catalog" ? (
              <header className="nexTopbar">
                <div className="nexTitleCluster"><span>{activeWorkspaceMeta.eyebrow}</span><h1 id="app-title">{activeWorkspaceMeta.label}</h1></div>
                <div className="nexTopbarActions">
                  <button className="ghostButton nexUndoButton" type="button" disabled={!undoRedoHistoryState.canUndo || busyAction === "desfazer"} onClick={() => void undoLastAction()} aria-label={undoRedoHistoryState.undoLabel}>Desfazer</button>
                  <button className="iconShellButton" type="button" title="Configurações" aria-label="Configurações" onClick={() => void openSettingsModal()}>
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33A1.65 1.65 0 0 0 14 20.83V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33M4.68 15A1.65 1.65 0 0 0 3.17 14H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9M9 4.68A1.65 1.65 0 0 0 10 3.17V3a2 2 0 0 1 4 0v.09A1.65 1.65 0 0 0 15 4.6"/></svg>
                  </button>
                  <button className="primaryButton nexNewProduct" type="button" onClick={startNewProduct} aria-label="Novo produto"><span aria-hidden="true">＋</span><span className="nexNewProductLabelTs">Novo produto</span></button>
                </div>
              </header>
            ) : null}

            <section className="rightPanelTs" id="workspace-panel" tabIndex={-1} aria-label="Área de trabalho operacional">
              <div className={`nexWorkspaceView nexOverviewView ${activeWorkspace === "overview" ? "active" : ""}`} aria-hidden={activeWorkspace !== "overview"}>
                <div className="nexOverviewGrid">
                  <div className="nexOverviewPrimary">
                    <CatalogOverviewPanel titleId="overview-catalog-title" overview={catalogOverview} activeFilter={productQuickFilter} onSelectFilter={(filter) => { handleCatalogFilterSelect(filter); navigateWorkspace("catalog"); }} />
                    <OperationalSummaryPanel totalsText={state.totalsText} totalsRaw={state.totalsRaw} usageAnalytics={usageAnalytics} />
                  </div>
                  <aside className="nexOverviewAside">
                    <OperationalHealthPanel chips={operationalHealthChips} checkedAt={runtimeHealth.checkedAt} />
                    <section className="nexNextActions" aria-labelledby="next-actions-title"><span className="sectionTag">Próximas ações</span><h2 id="next-actions-title">Continue de onde os dados estão</h2><p>{state.products.length ? `${state.products.length} produto${state.products.length === 1 ? "" : "s"} no catálogo para revisar ou executar.` : "O catálogo está vazio. Importe um documento ou cadastre o primeiro produto."}</p><div><button className="primaryButton" type="button" onClick={() => navigateWorkspace(state.products.length ? "catalog" : "import")}>{state.products.length ? "Revisar catálogo" : "Abrir importação"}</button><button className="ghostButton" type="button" onClick={() => navigateWorkspace("execution")}>Ver execução</button></div></section>
                  </aside>
                </div>
              </div>

              <div className={`nexWorkspaceView nexImportView ${activeWorkspace === "import" ? "active" : ""}`} aria-hidden={activeWorkspace !== "import"}>
                <div className="nexFlowColumn">
                  <div className="nexImportIntro"><span className="sectionTag">Duas entradas reais</span><h2>Documento assistido ou cadastro manual</h2><p>Escolha a leitura por IA ou local para um lote, ou inclua uma exceção sem sair deste fluxo.</p></div>
                  <div className="actionsFloatingTs">
                    <div className="panelActionCompact nexModeControl">
                      <button className={`ghostButton compactButton modeToggleButton ${simpleModeEnabled ? "activeToggle" : ""}`} type="button" onClick={handleToggleSimpleMode} aria-pressed={simpleModeEnabled}>{simpleModeEnabled ? "Modo completo" : "Modo simplificado"}</button>
                    </div>
            <ImportStagePanel
              importing={importing}
              localExperimentLoading={localExperimentLoading}
              documentCount={importDocuments.length}
              activeFileName={importDocuments.find((document) => document.id === activeImportDocumentId)?.file.name || null}
              importProgressMessage={importProgressMessage}
              importJobMessage={importJob?.message}
              importError={importError}
              importSuccessMessage={importSuccessMessage}
              validationStatus={importValidationStatus}
              diagnosticsChips={importDiagnosticsChips}
              warnings={importWarnings}
              recentImports={recentImports}
              inputRef={importInputRef}
              onImportPrimaryClick={handleImportPrimaryClick}
              onLocalExperimentClick={handleLocalExperimentClick}
              onFilePickerClick={handleFilePickerClick}
              onFileChange={handleImportFileChange}
            />
          </div>

          <ProductEntryPanel
            form={form}
            simpleModeEnabled={simpleModeEnabled}
            marginPercentual={state.marginPercentual}
            submitting={submitting}
            nameInputRef={nameInputRef}
            codeInputRef={codeInputRef}
            quantityInputRef={quantityInputRef}
            priceInputRef={priceInputRef}
            runBusyAction={runBusyAction}
            onFormKeyDown={handleProductFormKeyDown}
            onInputChange={handleInputChange}
            onSubmitProduct={submitProduct}
            onApplyMargin={handleMargin}
          />

                  </div>
                <ImportWorkspacePanel
                  documents={importDocuments}
                  busy={importing || localExperimentLoading}
                  activeDocumentId={activeImportDocumentId}
                  onDocumentsChange={handleImportDocumentsChange}
                  onOpenPicker={(mode) => {
                    importModeRef.current = mode;
                    importInputRef.current?.click();
                  }}
                  onRemove={handleRemoveImportDocument}
                  onRetryFailed={handleRetryFailedImports}
                />
              </div>

              <div className={`nexWorkspaceView nexCatalogView nexCatalogOverviewMount ${activeWorkspace === "catalog" ? "active" : ""}`} aria-hidden={activeWorkspace !== "catalog"}>
          <CatalogOverviewPanel
            titleId="catalog-workbench-title"
            overview={catalogOverview}
            activeFilter={productQuickFilter}
            onSelectFilter={handleCatalogFilterSelect}
            onOpenSettings={() => void openSettingsModal()}
          />
          <CatalogQuickEntryPanel
            open={catalogQuickEntryOpen}
            form={form}
            simpleModeEnabled={simpleModeEnabled}
            submitting={submitting}
            runBusyAction={runBusyAction}
            onFormKeyDown={handleProductFormKeyDown}
            onInputChange={handleInputChange}
            onSubmitProduct={submitProduct}
            onToggleSimpleMode={handleToggleSimpleMode}
            onClose={() => setCatalogQuickEntryOpen(false)}
            returnFocusTarget={catalogQuickEntryTriggerRef.current}
          />
              </div>

              <div className={`nexWorkspaceView nexExecutionView ${activeWorkspace === "execution" ? "active" : ""}`} aria-hidden={activeWorkspace !== "execution"}>
                <div className="nexExecutionContext"><span className="sectionTag">Contexto do catálogo</span><strong>{state.products.length} produto{state.products.length === 1 ? "" : "s"}</strong><span>{executionReadiness.detail}</span></div>
          <ExecutionCenterPanel
            automationState={state.automation.estado}
            automationMessage={state.automation.message}
            automationError={automationError}
            automationProgressWidth={automationProgressWidth}
            pendingGradeCount={pendingGradeImportProducts.length + incompleteGradeProducts.length}
            executionReadiness={executionReadiness}
            runBusyAction={runBusyAction}
            onStartComplete={handleStartComplete}
            onExecuteGrades={handleExecuteGrades}
            onStartCatalog={async () => handleAutomationAction("catalog")}
            onStopAutomation={async () => handleAutomationAction("stop")}
            onJoinGrades={handleJoinGrades}
            onOpenGradeModal={async () => openGradeModal()}
          />
              </div>

              <div className={`nexWorkspaceView nexCatalogView nexCatalogWorkbenchMount ${activeWorkspace === "catalog" ? "active" : ""}`} aria-hidden={activeWorkspace !== "catalog"}>
          <ProductListControls
            loading={loading}
            displayedCount={displayedProducts.length}
            totalCount={state.products.length}
            productSearchQuery={productSearchQuery}
            undoRedoHistoryState={undoRedoHistoryState}
            busyAction={busyAction}
            globalEditMode={globalEditMode}
            showFormatCodesPanel={showFormatCodesPanel}
            showDescriptionPanel={showDescriptionPanel}
            formatCodesOptions={formatCodesOptions}
            descriptionOptions={descriptionOptions}
            descriptionSuggestions={descriptionCleanupSuggestions}
            orderingMode={orderingMode}
            orderingSelectedCount={orderingDraftKeys.length}
            createSetMode={createSetMode}
            createSetKeys={createSetKeys}
            runBusyAction={runBusyAction}
            onUndo={undoLastAction}
            onRedo={redoLastAction}
            onProductSearchChange={setProductSearchQuery}
            onToggleGlobalEdit={handleToggleGlobalEdit}
            onToggleFormatCodesPanel={() => {
              setShowFormatCodesPanel((current) => !current);
              setShowDescriptionPanel(false);
            }}
            onToggleDescriptionPanel={() => {
              setShowDescriptionPanel((current) => !current);
              setShowFormatCodesPanel(false);
            }}
            onToggleOrdering={handleToggleOrdering}
            onCancelOrdering={handleCancelOrdering}
            onToggleCreateSets={handleToggleCreateSets}
            onJoinDuplicates={handleJoinDuplicates}
            onExportVisibleProducts={handleExportVisibleProducts}
            onClearProducts={handleClearProducts}
            onFormatCodeOptionChange={(field, value) => setFormatCodesOptions((current) => ({ ...current, [field]: value }))}
            onRestoreOriginalCodes={async () => {
              if (visibleBulkActionKeys?.length === 0) {
                showNoticeDialog({ title: "Sem produtos visiveis", message: "Ajuste ou limpe os filtros antes de restaurar codigos.", tone: "warning" });
                return;
              }
              await pushUndoSnapshot();
              const result = await restoreOriginalCodes(visibleBulkActionKeys);
              rememberProductOperation({
                action: "format_codes",
                productCount: result.total,
                changedCount: result.restaurados,
                value: "Códigos originais restaurados",
              });
              queueRefresh(["products"]);
              setShowFormatCodesPanel(false);
              showNoticeDialog({
                title: "Códigos restaurados",
                message: `Total analisado: ${result.total}\nCódigos restaurados: ${result.restaurados}`,
                tone: "success",
              });
            }}
            onCloseFormatCodesPanel={() => setShowFormatCodesPanel(false)}
            onFormatCodes={handleFormatCodes}
            onDescriptionOptionChange={(field, value) => setDescriptionOptions((current) => ({ ...current, [field]: value }))}
            onCloseDescriptionPanel={() => setShowDescriptionPanel(false)}
            onImproveDescriptions={handleImproveDescriptions}
          />

          <ProductTable
            loading={loading}
            products={displayedProducts}
            totalProductCount={state.products.length}
            orderingMode={orderingMode}
            orderingSelectionIndex={orderingSelectionIndex}
            automationIsRunning={automationIsRunning}
            automationCurrentOrderingKey={automationCurrentOrderingKey}
            automationTypedDescription={automationTypedDescription}
            createSetMode={createSetMode}
            createSetKeys={createSetKeys}
            sortedBrands={sortedBrands}
            newBrand={newBrand}
            bulkBrandValue={bulkBrandValue}
            bulkCategoryValue={bulkCategoryValue}
            showBulkBrandMenu={showBulkBrandMenu}
            showBulkCategoryMenu={showBulkCategoryMenu}
            showBrandComposer={showBrandComposer}
            bulkBrandMenuRef={bulkBrandMenuRef}
            bulkCategoryMenuRef={bulkCategoryMenuRef}
            emptyState={productTableEmptyState}
            globalEditMode={globalEditMode}
            editingCell={editingCell}
            inlineEditInputRef={inlineEditInputRef}
            runBusyAction={runBusyAction}
            onStartInlineEdit={startInlineEdit}
            onInlineEditChange={handleInlineEditChange}
            onCommitInlineEdit={commitInlineEdit}
            onInlineEditKeyDown={handleInlineEditKeyDown}
            onStartImport={() => {
              navigateWorkspace("import");
              window.setTimeout(handleImportPrimaryClick, 0);
            }}
            onStartManualEntry={startNewProduct}
            onToggleBulkBrandMenu={() => setShowBulkBrandMenu((current) => !current)}
            onToggleBulkCategoryMenu={() => setShowBulkCategoryMenu((current) => !current)}
            onCloseBulkBrandMenu={() => setShowBulkBrandMenu(false)}
            onCloseBulkCategoryMenu={() => setShowBulkCategoryMenu(false)}
            onToggleBrandComposer={() => setShowBrandComposer((current) => !current)}
            onNewBrandChange={setNewBrand}
            onSubmitBrand={submitBrand}
            onApplyBrand={handleApplyBrand}
            onApplyCategory={handleApplyCategory}
            onToggleGlobalEdit={handleToggleGlobalEdit}
            onOrderingSelection={handleOrderingSelection}
            onCreateSetSelection={handleCreateSetSelection}
            onMoveOrderingItem={moveOrderingItem}
            onUseProductAsTemplate={handleUseProductAsTemplate}
            onProductSearchChange={setProductSearchQuery}
            onDeleteProduct={async (orderingKey) => {
              const product = productsByKey.get(orderingKey);
              const productName = product?.nome || orderingKey;
              openConfirmationDialog({
                title: "Excluir item da lista?",
                message: `"${productName}" sera removido da lista ativa.`,
                detail: "A remoção afeta apenas este item e pode ser desfeita pelo histórico da lista.",
                confirmLabel: "Excluir item",
                onConfirm: async () => {
                  await pushUndoSnapshot();
                  await deleteProduct(orderingKey);
                  rememberProductOperation({
                    action: "delete",
                    productName,
                  });
                  queueRefresh(["products", "totals"]);
                },
              });
            }}
          />
              </div>

              <div className={`nexWorkspaceView nexHistoryView ${activeWorkspace === "history" ? "active" : ""}`} aria-hidden={activeWorkspace !== "history"}>
                <HistoryPanel entries={operationDiary} undoSummary={undoRedoHistoryState.summary} undoLabel={undoRedoHistoryState.undoLabel} redoLabel={undoRedoHistoryState.redoLabel} canUndo={undoRedoHistoryState.canUndo} canRedo={undoRedoHistoryState.canRedo} busy={busyAction === "desfazer" || busyAction === "refazer"} onUndo={undoLastAction} onRedo={redoLastAction} />
              </div>
        </section>
            {activeWorkspace === "catalog" ? (
              <CatalogActionDock
                manualEntryOpen={catalogQuickEntryOpen}
                onToggleManualEntry={toggleCatalogQuickEntry}
                onImport={() => navigateWorkspace("import")}
                onOpenGrades={() => void openGradeModal()}
                onExecute={() => navigateWorkspace("execution")}
                onHistory={() => navigateWorkspace("history")}
              />
            ) : null}
            <nav className="nexBottomDock" aria-label="Atalhos principais">
              {WORKSPACES.map((workspace) => <button key={workspace.id} className={activeWorkspace === workspace.id ? "active" : ""} type="button" onClick={() => navigateWorkspace(workspace.id)} aria-label={workspace.label} aria-current={activeWorkspace === workspace.id ? "page" : undefined} aria-pressed={activeWorkspace === workspace.id}><WorkspaceIcon id={workspace.id} /><span>{workspace.shortLabel}</span></button>)}
            </nav>
          </div>
          {automationIsRunning ? (
            <aside className="globalAutomationStopTs" role="status" aria-live="polite" aria-label="Automação em execução">
              <span><strong>Automação em execução</strong><small>{state.automation.message || "Cadastro no Byte Empresa em andamento."}</small></span>
              <button className="actionButtonTs danger stopActionButtonTs stopActionActiveTs" type="button" onClick={() => void runBusyAction("parar-global", async () => handleAutomationAction("stop"))}>
                Parar agora
              </button>
            </aside>
          ) : null}
      </main>
      </div>
      {confirmationDialog ? (
        <ConfirmationDialog
          title={confirmationDialog.title}
          message={confirmationDialog.message}
          detail={confirmationDialog.detail}
          confirmLabel={confirmationDialog.confirmLabel}
          busy={confirmationBusy}
          error={confirmationError}
          onCancel={closeConfirmationDialog}
          onConfirm={handleConfirmationDialogConfirm}
        />
      ) : null}
      {marginDialogOpen ? (
        <MarginDialog
          currentPercent={state.marginPercentual}
          value={marginDraft}
          busy={marginBusy}
          error={marginError}
          onChange={(value) => {
            setMarginDraft(value);
            if (marginError) setMarginError(null);
          }}
          onCancel={closeMarginDialog}
          onConfirm={handleApplyMarginDialog}
        />
      ) : null}
      {textInputDialog ? (
        <TextInputDialog
          title={textInputDialog.title}
          description={textInputDialog.description}
          label={textInputDialog.label}
          value={textInputDialog.value}
          confirmLabel={textInputDialog.confirmLabel}
          sectionTag={textInputDialog.sectionTag}
          placeholder={textInputDialog.placeholder}
          busy={textInputBusy}
          error={textInputError}
          onChange={(value) => {
            setTextInputDialog((current) => current ? { ...current, value } : current);
            if (textInputError) setTextInputError(null);
          }}
          onCancel={closeTextInputDialog}
          onConfirm={handleTextInputDialogConfirm}
        />
      ) : null}
      {noticeDialog ? (
        <NoticeDialog
          title={noticeDialog.title}
          message={noticeDialog.message}
          tone={noticeDialog.tone}
          confirmLabel={noticeDialog.confirmLabel}
          onClose={closeNoticeDialog}
        />
      ) : null}
      <NoticeToastStack
        toasts={noticeToasts}
        onDismiss={dismissNoticeToast}
      />
      {settingsOpen ? (
        <SettingsModal
          loading={settingsLoading}
          saving={settingsSaving}
          error={settingsError}
          message={settingsMessage}
          targets={settingsTargets}
          gradeConfig={settingsGradeConfig}
          contextText={settingsContextText}
          captureLabel={settingsCaptureLabel}
          captureCountdown={settingsCaptureCountdown}
          onClose={closeSettingsModal}
          onContextRefresh={handleSettingsContextRefresh}
          onPrepare={handleSettingsPrepare}
          onReloadAll={loadSettingsModal}
          onSaveTargets={handleSaveSettingsTargets}
          onSaveGradeConfig={handleSaveSettingsGradeConfig}
          onTargetChange={handleSettingsTargetChange}
          onGradeConfigChange={handleSettingsGradeConfigChange}
          onCaptureTarget={handleCaptureSettingsTarget}
          onCaptureGradeButton={handleCaptureSettingsGradeButton}
          onCaptureFirstQuantCell={handleCaptureFirstQuantCell}
        />
      ) : null}
      {gradeModalOpen ? (
        <GradeModal
          products={state.products}
          selectedProduct={selectedGradeProduct}
          selectedOrderingKey={gradeSelectedKey}
          selectedStatus={selectedGradeStatus}
          nextPendingGradeKey={nextPendingGradeKey}
          currentGradeTotal={currentGradeTotal}
          gradeDraft={gradeDraft}
          draftDirty={gradeDraftDirty}
          transitionLocked={gradeDraftMutationBusy}
          gradeFamiliesDraft={gradeFamiliesDraft}
          groupedGradeSizes={groupedGradeSizes}
          activeGradeFamily={activeGradeFamily}
          erpSizes={gradeConfig?.erp_size_order || []}
          erpOrderText={(gradeConfig?.erp_size_order || []).join(" • ") || "Não configurada"}
          newGradeSize={newGradeSize}
          validationError={gradeValidationError}
          modalError={gradeModalError}
          gradeInputRefs={gradeInputRefs}
          getProductStatus={getProductGradeStatus}
          runBusyAction={runBusyAction}
          onClose={closeGradeModal}
          onExecuteGrades={handleExecuteGrades}
          onStopGrades={handleStopGrades}
          onSelectProduct={handleSelectGradeProduct}
          onGradeStartTab={handleGradeStartTab}
          onSelectNextPendingGrade={handleSelectNextPendingGrade}
          onAddFamily={addFamily}
          onNewGradeSizeChange={setNewGradeSize}
          onAddVisualSize={addVisualSize}
          onFamilyLabelChange={handleFamilyLabelChange}
          onMoveSizeBetweenFamilies={moveSizeBetweenFamilies}
          onRenameSizeInFamily={renameSizeInFamily}
          onRemoveSizeFromFamilies={removeSizeFromFamilies}
          onMoveVisualSize={moveVisualSize}
          onSetActiveGradeFamily={setActiveGradeFamilyKey}
          onUpdateGradeDraftValue={updateGradeDraftValue}
          onGradeInputKeyDown={handleGradeInputKeyDown}
          onClearSelectedGrade={handleClearSelectedGrade}
          onClearAllGrades={handleClearAllGrades}
          onSaveSelectedGrade={handleSaveSelectedGrade}
          onSaveAndNextGrade={handleSaveAndNextGrade}
        />
      ) : null}
    </div>
  );
}
