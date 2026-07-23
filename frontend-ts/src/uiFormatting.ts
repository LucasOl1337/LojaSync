import type { ImportResult, ImportStatus, Product, TargetPoint } from "./types";

export type ImportProcessEntry = {
  index: number;
  source: string;
  level: string;
  message: string;
};

export type StatusTone = "neutral" | "success" | "warning" | "error";

export type StatusChip = {
  label: string;
  value: string;
  tone: StatusTone;
};

export type ImportDiagnosticsChip = StatusChip;

export type UiSocketStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

export type OperationalHealthInput = {
  backendStatus: "checking" | "ok" | "error";
  backendError?: string | null;
  authEnabled?: boolean | null;
  authenticated?: boolean | null;
  bootstrapRequired?: boolean | null;
  websocketStatus: UiSocketStatus;
  automationState?: string | null;
  automationError?: string | null;
  pendingGrades?: number | null;
};

export type ImportHistoryEntry = {
  id: string;
  completedAt: number;
  sourceName: string;
  mode: string;
  totalItems: number;
  totalValueLabel: string | null;
  warningCount: number;
  validationStatus: string;
  gradesAvailable: boolean;
  status: string;
  /** True when a local session snapshot exists (file + extraction) for reopen. */
  canReopen?: boolean;
};

export type OperationDiaryEntry = {
  id: string;
  occurredAt: number;
  kind: string;
  title: string;
  detail: string;
  tone: StatusTone;
  meta: string[];
};

export type OperationDiaryEntryInput = {
  id?: string | null;
  occurredAt?: number | null;
  kind?: string | null;
  title?: string | null;
  detail?: string | null;
  tone?: StatusTone | string | null;
  meta?: unknown[] | null;
};

export type ProductOperationDiaryAction =
  | "create"
  | "inline_edit"
  | "delete"
  | "clear"
  | "bulk_category"
  | "bulk_brand"
  | "reorder"
  | "create_set"
  | "format_codes"
  | "improve_descriptions"
  | "margin";

export type ProductOperationDiaryInput = {
  action: ProductOperationDiaryAction;
  productName?: string | null;
  productCount?: number | null;
  changedCount?: number | null;
  removedCount?: number | null;
  fieldLabel?: string | null;
  value?: string | number | null;
  occurredAt?: number | null;
  meta?: unknown[] | null;
};

export type UndoRedoHistoryState = {
  undoCount: number;
  redoCount: number;
  canUndo: boolean;
  canRedo: boolean;
  summary: string;
  undoLabel: string;
  redoLabel: string;
};

export type ClearProductsConfirmation = {
  title: string;
  message: string;
  detail: string;
  confirmLabel: string;
};

export type ExecutionReadinessInput = {
  productCount?: number | null;
  pendingGradeImportCount?: number | null;
  pendingGradeCount?: number | null;
  automationState?: string | null;
  automationError?: string | null;
};

export type AutomationStatusDetailInput = {
  automationState?: string | null;
  automationMessage?: string | null;
  automationError?: string | null;
  pendingGradeCount?: number | null;
};

export type ExecutionReadinessState = {
  ready: boolean;
  tone: StatusTone;
  title: string;
  detail: string;
  items: StatusChip[];
};

function safeCount(value: unknown) {
  const parsed = Math.floor(Number(value) || 0);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export function actionText(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function buildClearProductsConfirmation(
  totalCount: unknown,
  displayedCount: unknown,
): ClearProductsConfirmation {
  const total = safeCount(totalCount);
  const displayed = Math.min(total, safeCount(displayedCount));
  const hidden = Math.max(0, total - displayed);
  const productLabel = actionText(total, "produto", "produtos");
  const hiddenWarning = hidden
    ? ` A busca atual oculta ${actionText(hidden, "produto", "produtos")}, que também ${hidden === 1 ? "será removido" : "serão removidos"}.`
    : "";

  return {
    title: "Limpar toda a lista?",
    message: `${productLabel} ${total === 1 ? "será removido" : "serão removidos"} do catálogo ativo.`,
    detail: `${hiddenWarning.trimStart()} Esta ação pode ser desfeita pelo histórico da lista.`.trim(),
    confirmLabel: total === 1 ? "Remover produto" : `Remover ${total} produtos`,
  };
}

export function formatAutomationStateLabel(state: unknown) {
  const normalized = String(state || "").trim().toLowerCase();
  if (!normalized || normalized === "idle") return "Pronta";
  if (normalized === "running") return "Em execução";
  if (normalized === "stopping" || normalized === "canceling" || normalized === "cancelling") return "Parando";
  if (normalized === "failed" || normalized === "error") return "Falha";
  if (normalized === "queued") return "Na fila";
  if (normalized === "paused") return "Pausada";
  if (normalized === "succeeded" || normalized === "completed" || normalized === "success") return "Concluída";
  return String(state || "").trim();
}

function isStatusTone(value: unknown): value is StatusTone {
  return value === "neutral" || value === "success" || value === "warning" || value === "error";
}

function normalizeDiaryMeta(value: unknown[] | null | undefined) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item || "").trim()).filter(Boolean);
}

function slugifyDiaryText(value: string) {
  const slug = value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "evento";
}

export function buildUndoRedoHistoryState(undoCount: unknown, redoCount: unknown): UndoRedoHistoryState {
  const safeUndoCount = safeCount(undoCount);
  const safeRedoCount = safeCount(redoCount);
  const canUndo = safeUndoCount > 0;
  const canRedo = safeRedoCount > 0;
  return {
    undoCount: safeUndoCount,
    redoCount: safeRedoCount,
    canUndo,
    canRedo,
    summary: canUndo || canRedo
      ? `Histórico: ${safeUndoCount} desfazer / ${safeRedoCount} refazer`
      : "Histórico vazio",
    undoLabel: canUndo
      ? `Desfazer ${actionText(safeUndoCount, "ação", "ações")}`
      : "Nada para desfazer",
    redoLabel: canRedo
      ? `Refazer ${actionText(safeRedoCount, "ação", "ações")}`
      : "Nada para refazer",
  };
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value || 0);
}

export function formatDuration(seconds: number) {
  const totalSeconds = Math.max(0, Math.floor(Number(seconds) || 0));
  if (!totalSeconds) return "0s";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remaining = totalSeconds % 60;
  const parts: string[] = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}min`);
  if (remaining || !parts.length) parts.push(`${remaining}s`);
  return parts.join(" ");
}

export function formatTimestamp(value?: number | null) {
  if (!value) return "agora";
  return new Date(value * 1000).toLocaleTimeString("pt-BR");
}

export function parsePromptInteger(raw: string | null) {
  const text = raw?.trim();
  if (!text || !/^\d+$/.test(text)) return null;
  const value = Number.parseInt(text, 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}

export function cloneSnapshotProducts(items: Product[]) {
  return JSON.parse(JSON.stringify(items || [])) as Product[];
}

export function pushBoundedHistorySnapshot<T>(stack: T[], snapshot: T, limit: number) {
  const safeLimit = Math.max(0, Math.floor(Number.isFinite(limit) ? limit : 0));
  stack.push(snapshot);
  const overflow = stack.length - safeLimit;
  if (overflow > 0) {
    stack.splice(0, overflow);
  }
  return stack;
}

export function formatTargetPoint(point?: TargetPoint | null) {
  if (!point) return "Não calibrado";
  return `X: ${point.x} | Y: ${point.y}`;
}

export function formatCaughtErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function normalizeTargetPoint(value: unknown): TargetPoint | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (!("x" in record) || !("y" in record)) {
    return null;
  }
  const x = Number(record.x);
  const y = Number(record.y);
  return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
}

export function formatJsonBlock(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export function coerceImportProcessLog(metrics: Record<string, unknown> | null | undefined): ImportProcessEntry[] {
  const raw = metrics?.["process_log"];
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item) => item && typeof item === "object")
    .map((item, index) => {
      const entry = item as Record<string, unknown>;
      return {
        index: Number(entry.index || index + 1) || index + 1,
        source: String(entry.source || "system").trim() || "system",
        level: String(entry.level || "info").trim() || "info",
        message: String(entry.message || "").trim(),
      };
    })
    .filter((entry) => entry.message);
}

export function coerceStringList(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item || "").trim()).filter(Boolean);
}

export function formatImportProgressCopy(message: string) {
  const raw = String(message || "").trim();
  if (!raw) return "";
  return raw
    .replace(/\bservi[cç]o LLM\b/gi, "IA")
    .replace(/\bservico de IA\b/gi, "IA")
    .replace(/\bservi[cç]o de IA\b/gi, "IA")
    .replace(/\bLLM\b/g, "IA")
    .replace(/\bMinimax\b/gi, "IA")
    .replace(/\bConcluido\b/g, "Concluído")
    .replace(/\bvalidacao\b/gi, "validação")
    .replace(/\bimportacao\b/gi, "importação")
    .replace(/\bFalling back to the LLM import pipeline\.?/gi, "Indo para a leitura com IA.")
    .replace(/\bImport started\.?/gi, "Importação iniciada.")
    .replace(/\bImport persisted successfully with (\d+) item\(s\)\.?/gi, "Salvos $1 itens no catálogo.")
    .replace(/\bLocal parser approved by invoice validation\. Skipping the LLM fallback\.?/gi, "Parser local aprovado; IA não foi necessária.")
    .replace(/\bLocal parser skipped because IA import was requested\.?/gi, "Parser local ignorado; importação pedida via IA.")
    .replace(/\bFull-page OCR fallback returned no valid items; trying vertical slices\.?/gi, "OCR da página inteira sem itens; tentando recortes verticais.")
    .replace(/\bProcessando com servico de IA\b/gi, "Processando com IA")
    .replace(/\bProcessando com servico LLM\b/gi, "Processando com IA")
    .replace(/\bEnviando arquivo para servico de IA\b/gi, "Enviando arquivo para a IA")
    .replace(/\bEnviando arquivo para servico LLM\b/gi, "Enviando arquivo para a IA")
    .replace(/\bValidando itens retornados pelo LLM\b/gi, "Validando itens retornados pela IA")
    .replace(/\bTentando parser local e validacao da nota\b/gi, "Tentando parser local e validação da nota")
    .replace(/\bParser local aprovado; preparando importacao\b/gi, "Parser local aprovado; preparando importação")
    .replace(/\bValidacao local aprovada; enviando arquivo para servico LLM\b/gi, "Validação local aprovada; enviando para a IA")
    .replace(/\bParser local reprovado; enviando arquivo para servico LLM\b/gi, "Parser local reprovado; enviando para a IA");
}

export function buildImportProgressMessage(importing: boolean, jobMessage?: string | null) {
  if (!importing) return null;
  const message = String(jobMessage || "").trim();
  return message ? formatImportProgressCopy(message) : "Importação em andamento...";
}

export type ImportProgressStep = {
  id: string;
  label: string;
  state: "pending" | "active" | "done";
};

export function formatImportElapsed(elapsedMs: number) {
  const totalSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes <= 0) return `${seconds}s`;
  return `${minutes}min ${String(seconds).padStart(2, "0")}s`;
}

export function buildImportProgressSteps(input: {
  stage?: string | null;
  message?: string | null;
  mode?: "llm" | "local" | null;
  active?: boolean;
}): ImportProgressStep[] {
  const stage = String(input.stage || "").trim().toLowerCase();
  const message = String(input.message || "").toLowerCase();
  const mode = input.mode || null;
  const active = Boolean(input.active);

  const steps: Array<{ id: string; label: string }> = [
    { id: "receive", label: "Arquivo" },
    { id: "read", label: "Leitura" },
    { id: "ai", label: mode === "local" ? "Parser local" : "IA" },
    { id: "validate", label: "Validação" },
    { id: "save", label: "Salvar" },
  ];

  let activeIndex = 0;
  if (!active && (stage === "completed" || stage === "error")) {
    activeIndex = steps.length;
  } else if (stage === "completed") {
    activeIndex = steps.length;
  } else if (stage === "error") {
    activeIndex = Math.max(0, steps.findIndex((step) => step.id === "validate"));
  } else if (stage === "parsing" || /valid|guard|itens retornados|aprovad|reprovad/.test(message)) {
    activeIndex = 3;
  } else if (stage === "processing" || /processando|ocr|recorte|chat|llm|ia\b|texto \d/.test(message)) {
    activeIndex = 2;
  } else if (stage === "uploading" || /enviando|upload/.test(message)) {
    activeIndex = 1;
  } else if (stage === "queued" || stage === "pending" || !stage) {
    activeIndex = 0;
  } else {
    activeIndex = 1;
  }

  if (mode === "local" && active && activeIndex < 2) {
    activeIndex = 2;
  }

  return steps.map((step, index) => {
    if (!active && stage === "completed") {
      return { ...step, state: "done" as const };
    }
    if (index < activeIndex) {
      return { ...step, state: "done" as const };
    }
    if (index === activeIndex && (active || stage === "error")) {
      return { ...step, state: "active" as const };
    }
    return { ...step, state: "pending" as const };
  });
}

function parseImportMoneyValue(raw: unknown): number | null {
  if (raw == null || raw === "") return null;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  const text = String(raw).trim();
  if (!text) return null;
  // Accept "4613.76", "4.613,76" or "4613,76"
  const normalized = text.includes(",")
    ? text.replace(/\./g, "").replace(",", ".")
    : text.replace(/[^\d.-]/g, "");
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

function pickImportMetricValue(metrics: Record<string, unknown> | null | undefined, keys: string[]): unknown {
  if (!metrics) return null;
  for (const key of keys) {
    if (metrics[key] != null && metrics[key] !== "") return metrics[key];
  }
  return null;
}

export function formatImportMoneyLabel(raw: unknown): string | null {
  const value = parseImportMoneyValue(raw);
  if (value == null) return null;
  return formatCurrency(value);
}

export function buildImportDiagnosticsChips(
  metrics: Record<string, unknown> | null | undefined,
  _warnings: string[] = [],
  options: {
    totalItems?: number | null;
  } = {},
): ImportDiagnosticsChip[] {
  const source = String(metrics?.["selected_source"] || "").trim().toLowerCase();
  const chips: ImportDiagnosticsChip[] = [];

  if (source === "local" || source.includes("local")) {
    chips.push({ label: "Origem", value: "Leitura local", tone: "success" });
  } else if (source === "llm" || source.includes("llm") || source === "ia") {
    chips.push({ label: "Origem", value: "IA", tone: "neutral" });
  }

  const totalItems = Math.max(0, Math.floor(Number(options.totalItems ?? metrics?.["imported_items"] ?? metrics?.["grouped_items"] ?? 0)));
  if (totalItems > 0) {
    chips.push({
      label: "Itens",
      value: String(totalItems),
      tone: "success",
    });
  }

  const extractedLabel = formatImportMoneyLabel(
    pickImportMetricValue(metrics, ["extracted_total_products", "local_extracted_total_products"]),
  );
  if (extractedLabel) {
    chips.push({ label: "Total detectado", value: extractedLabel, tone: "neutral" });
  }

  const noteTotalLabel = formatImportMoneyLabel(
    pickImportMetricValue(metrics, ["document_total_note", "local_document_total_note"]),
  );
  const productsTotalLabel = formatImportMoneyLabel(
    pickImportMetricValue(metrics, ["document_total_products", "local_document_total_products"]),
  );
  if (noteTotalLabel) {
    chips.push({ label: "Total da nota", value: noteTotalLabel, tone: "neutral" });
  }
  if (productsTotalLabel && productsTotalLabel !== noteTotalLabel) {
    chips.push({ label: "Total produtos", value: productsTotalLabel, tone: "neutral" });
  }

  const matchRaw = pickImportMetricValue(metrics, ["products_value_matches_document", "local_products_value_matches_document"]);
  if (matchRaw === true) {
    chips.push({ label: "Conferência", value: "Valores batem", tone: "success" });
  } else if (matchRaw === false) {
    chips.push({ label: "Conferência", value: "Divergência de valor", tone: "warning" });
  }

  return chips;
}

export function buildOperationalHealthChips(input: OperationalHealthInput): StatusChip[] {
  const chips: StatusChip[] = [];

  if (input.backendStatus === "ok") {
    chips.push({ label: "Backend", value: "Ativo", tone: "success" });
  } else if (input.backendStatus === "error") {
    chips.push({ label: "Backend", value: "Indisponível", tone: "error" });
  } else {
    chips.push({ label: "Backend", value: "Verificando", tone: "warning" });
  }

  if (input.bootstrapRequired) {
    chips.push({ label: "Auth", value: "Configurar", tone: "warning" });
  } else if (input.authEnabled === false) {
    chips.push({ label: "Auth", value: "Livre", tone: "neutral" });
  } else if (input.authenticated) {
    chips.push({ label: "Auth", value: "Sessão ativa", tone: "success" });
  } else {
    chips.push({ label: "Auth", value: "Login pendente", tone: "warning" });
  }

  const websocketMap: Record<UiSocketStatus, StatusChip> = {
    connecting: { label: "Tempo real", value: "Conectando", tone: "warning" },
    connected: { label: "Tempo real", value: "Conectado", tone: "success" },
    reconnecting: { label: "Tempo real", value: "Polling API", tone: "neutral" },
    disconnected: { label: "Tempo real", value: "Offline", tone: "error" },
  };
  chips.push(websocketMap[input.websocketStatus]);

  const automationError = String(input.automationError || "").trim();
  const automationState = String(input.automationState || "").trim();
  if (automationError) {
    chips.push({ label: "Automação", value: automationError, tone: "error" });
  } else if (automationState === "running") {
    chips.push({ label: "Automação", value: formatAutomationStateLabel(automationState), tone: "warning" });
  } else {
    chips.push({ label: "Automação", value: formatAutomationStateLabel(automationState), tone: "neutral" });
  }

  const pendingGrades = Math.max(0, Math.floor(Number(input.pendingGrades || 0)));
  chips.push({
    label: "Grades",
    value: pendingGrades ? `${pendingGrades} pendente${pendingGrades === 1 ? "" : "s"}` : "Sem pendências",
    tone: pendingGrades ? "warning" : "success",
  });

  return chips;
}

export function buildAutomationStatusDetail(input: AutomationStatusDetailInput) {
  const pendingGradeCount = safeCount(input.pendingGradeCount);
  if (pendingGradeCount) {
    return `${pendingGradeCount} grade${pendingGradeCount === 1 ? "" : "s"} pendente${pendingGradeCount === 1 ? "" : "s"}`;
  }

  const automationError = String(input.automationError || "").trim();
  if (automationError) return automationError;

  const automationState = String(input.automationState || "").trim() || "idle";
  const automationMessage = String(input.automationMessage || "").trim();
  if (automationState === "running" && automationMessage) return automationMessage;

  return "Sem automação em execução";
}

export function buildExecutionReadiness(input: ExecutionReadinessInput): ExecutionReadinessState {
  const productCount = safeCount(input.productCount);
  const pendingGradeImportCount = safeCount(input.pendingGradeImportCount);
  const pendingGradeCount = safeCount(input.pendingGradeCount);
  const totalGradeIssueCount = pendingGradeImportCount + pendingGradeCount;
  const automationError = String(input.automationError || "").trim();
  const automationState = String(input.automationState || "").trim() || "idle";
  const automationRunning = automationState === "running";

  const items: StatusChip[] = [];
  if (!productCount) {
    items.push({ label: "Lista", value: "Sem produtos", tone: "warning" });
  }
  if (totalGradeIssueCount) {
    const gradeValue = pendingGradeImportCount && pendingGradeCount
      ? `${totalGradeIssueCount} ajustes`
      : pendingGradeImportCount
        ? `${pendingGradeImportCount} a importar`
        : `${pendingGradeCount} divergente${pendingGradeCount === 1 ? "" : "s"}`;
    items.push({ label: "Grades", value: gradeValue, tone: "warning" });
  }
  if (automationError || automationRunning) {
    items.push({
      label: "Automação",
      value: automationError || formatAutomationStateLabel(automationState),
      tone: automationError ? "error" : "warning",
    });
  }

  if (automationError) {
    return {
      ready: false,
      tone: "error",
      title: "Revisar automação",
      detail: "Corrija o erro da automação antes de iniciar o cadastro completo.",
      items,
    };
  }

  if (automationRunning) {
    return {
      ready: false,
      tone: "warning",
      title: "Automação em execução",
      detail: "Aguarde a execução atual terminar ou use Parar antes de iniciar outro fluxo.",
      items,
    };
  }

  if (totalGradeIssueCount) {
    const title = pendingGradeImportCount && pendingGradeCount
      ? `${totalGradeIssueCount} ajustes de grade pendentes`
      : pendingGradeImportCount
        ? `${pendingGradeImportCount} grade${pendingGradeImportCount === 1 ? "" : "s"} para importar`
        : `${pendingGradeCount} grade${pendingGradeCount === 1 ? "" : "s"} com divergência`;
    const detail = pendingGradeImportCount && pendingGradeCount
      ? "Importe as grades detectadas e corrija as divergências antes do cadastro completo."
      : pendingGradeImportCount
        ? "Use Importar grades para aplicar as grades detectadas antes do cadastro completo."
        : "Abra Inserir grade para fechar as divergências antes do cadastro completo.";
    return {
      ready: false,
      tone: "warning",
      title,
      detail,
      items,
    };
  }

  if (!productCount) {
    return {
      ready: false,
      tone: "warning",
      title: "Lista vazia",
      detail: "Importe ou cadastre produtos antes de iniciar o cadastro completo.",
      items,
    };
  }

  return {
    ready: true,
    tone: "success",
    title: "Pronto",
    detail: "",
    items: [],
  };
}

export function buildImportGradesAvailableMessage(result: Pick<ImportResult, "grades_disponiveis" | "total_grades_disponiveis">) {
  if (!result.grades_disponiveis) {
    return null;
  }
  const baseMessage = "Grades automáticas disponíveis.\n\nClique em Importar grades para aplicar.";
  if (Number(result.total_grades_disponiveis || 0) > 0) {
    return `${baseMessage}\nGrupos detectados: ${result.total_grades_disponiveis}`;
  }
  return baseMessage;
}

function normalizeImportMode(source: string, fallback?: "llm" | "local" | null) {
  const normalized = source.toLowerCase();
  if (normalized === "local" || normalized.includes("local") || fallback === "local") return "Leitura local";
  if (normalized === "llm" || normalized.includes("llm") || fallback === "llm") return "IA";
  return "Importação";
}

export function formatImportSourceDisplayName(sourceName: unknown) {
  const fallback = "Romaneio importado";
  const value = String(sourceName || "").trim();
  if (!value) return fallback;

  const normalizedPath = value.replace(/\\/g, "/");
  const lastSegment = normalizedPath.split("/").filter(Boolean).pop();
  return lastSegment?.trim() || fallback;
}

export function formatImportValidationStatus(status: unknown) {
  const value = String(status || "").trim();
  const normalized = value.toLowerCase();

  if (!normalized || normalized === "sem validacao") return "Sem validação";
  if (normalized === "approved") return "Aprovado";
  if (normalized === "rejected") return "Rejeitado";
  if (normalized === "unverified") return "Não validado";
  if (normalized === "error" || normalized === "failed") return "Erro";
  return value;
}

export function importValidationStatusTone(status: unknown): StatusTone {
  const normalized = String(status || "").trim().toLowerCase();
  if (normalized === "approved") return "success";
  if (normalized === "rejected" || normalized === "error" || normalized === "failed") return "error";
  if (normalized === "unverified") return "warning";
  return "neutral";
}

export function formatImportHistoryWhen(completedAt: number): { dateLabel: string; timeLabel: string; fullLabel: string; iso: string } {
  const date = new Date(Number(completedAt) || 0);
  if (!Number.isFinite(date.getTime()) || date.getTime() <= 0) {
    return { dateLabel: "—", timeLabel: "—", fullLabel: "Data desconhecida", iso: "" };
  }
  const dateLabel = date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  const timeLabel = date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const fullLabel = date.toLocaleString("pt-BR");
  return { dateLabel, timeLabel, fullLabel, iso: date.toISOString() };
}

export function buildImportHistoryEntry(
  result: Pick<ImportResult, "status" | "local_file" | "warnings" | "total_itens" | "grades_disponiveis" | "metrics">,
  options: {
    job?: Pick<ImportStatus, "job_id" | "updated_at" | "completed_at"> | null;
    selectedFileName?: string | null;
    mode?: "llm" | "local" | null;
    now?: number;
  } = {},
): ImportHistoryEntry {
  const metrics = result.metrics || {};
  const source = String(metrics["selected_source"] || "").trim();
  const validationStatus = String(metrics["final_validation_status"] || metrics["local_validation_status"] || "").trim();
  const completedSeconds = Number(options.job?.completed_at || options.job?.updated_at || 0);
  const completedAt = completedSeconds > 0 ? completedSeconds * 1000 : options.now || Date.now();
  const sourceName = String(result.local_file || options.selectedFileName || "Romaneio importado").trim() || "Romaneio importado";

  const totalValueLabel = formatImportMoneyLabel(
    pickImportMetricValue(metrics as Record<string, unknown>, [
      "extracted_total_products",
      "local_extracted_total_products",
      "document_total_products",
      "local_document_total_products",
      "document_total_note",
      "local_document_total_note",
    ]),
  );

  return {
    id: String(options.job?.job_id || `${sourceName}-${completedAt}`).trim(),
    completedAt,
    sourceName,
    mode: normalizeImportMode(source, options.mode),
    totalItems: Math.max(0, Math.floor(Number(result.total_itens || 0))),
    totalValueLabel,
    warningCount: Array.isArray(result.warnings) ? result.warnings.length : 0,
    validationStatus: validationStatus || "sem validacao",
    gradesAvailable: Boolean(result.grades_disponiveis),
    status: String(result.status || "").trim() || "ok",
    canReopen: true,
  };
}

export function updateRecentImportHistory(
  current: ImportHistoryEntry[],
  entry: ImportHistoryEntry,
  limit = 3,
): ImportHistoryEntry[] {
  const safeLimit = Math.max(1, Math.floor(Number(limit) || 3));
  return [entry, ...current.filter((item) => item.id !== entry.id)]
    .sort((left, right) => right.completedAt - left.completedAt)
    .slice(0, safeLimit);
}

export function coerceImportHistoryEntries(value: unknown, limit = 3): ImportHistoryEntry[] {
  if (!Array.isArray(value)) return [];
  const safeLimit = Math.max(1, Math.floor(Number(limit) || 3));
  const entries: ImportHistoryEntry[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const record = item as Record<string, unknown>;
    const id = String(record.id || "").trim();
    const completedAt = Number(record.completedAt || 0);
    if (!id || !Number.isFinite(completedAt) || completedAt <= 0) continue;
    const totalValueLabelRaw = record.totalValueLabel == null ? null : String(record.totalValueLabel).trim();
    entries.push({
      id,
      completedAt,
      sourceName: String(record.sourceName || "Romaneio importado").trim() || "Romaneio importado",
      mode: String(record.mode || "Importação").trim() || "Importação",
      totalItems: Math.max(0, Math.floor(Number(record.totalItems || 0))),
      totalValueLabel: totalValueLabelRaw || null,
      warningCount: Math.max(0, Math.floor(Number(record.warningCount || 0))),
      validationStatus: String(record.validationStatus || "sem validacao").trim() || "sem validacao",
      gradesAvailable: Boolean(record.gradesAvailable),
      status: String(record.status || "ok").trim() || "ok",
      canReopen: record.canReopen == null ? true : Boolean(record.canReopen),
    });
  }
  return entries.sort((left, right) => right.completedAt - left.completedAt).slice(0, safeLimit);
}

export function buildOperationDiaryEntry(input: OperationDiaryEntryInput): OperationDiaryEntry {
  const occurredAt = Number(input.occurredAt || 0) > 0 ? Number(input.occurredAt) : Date.now();
  const kind = String(input.kind || "system").trim() || "system";
  const title = String(input.title || "Evento operacional").trim() || "Evento operacional";
  const detail = String(input.detail || "").trim();
  const tone = isStatusTone(input.tone) ? input.tone : "neutral";
  const id = String(input.id || "").trim() || `${slugifyDiaryText(kind)}-${Math.floor(occurredAt)}-${slugifyDiaryText(title)}`;

  return {
    id,
    occurredAt,
    kind,
    title,
    detail,
    tone,
    meta: normalizeDiaryMeta(input.meta),
  };
}

function productCountText(count: number) {
  return `${count} produto${count === 1 ? "" : "s"}`;
}

function removedProductText(count: number) {
  return `${productCountText(count)} removido${count === 1 ? "" : "s"}`;
}

function productItemMeta(count: number) {
  return count ? actionText(count, "item", "itens") : null;
}

export function buildProductOperationDiaryEntry(input: ProductOperationDiaryInput): OperationDiaryEntry {
  const productName = String(input.productName || "").trim();
  const value = String(input.value ?? "").trim();
  const productCount = safeCount(input.productCount);
  const changedCount = safeCount(input.changedCount);
  const removedCount = safeCount(input.removedCount);
  const fieldLabel = String(input.fieldLabel || "").trim();
  const baseMeta = normalizeDiaryMeta(input.meta);
  const entry: OperationDiaryEntryInput = {
    kind: "product",
    title: "Produtos atualizados",
    detail: productName || value,
    tone: "success",
    occurredAt: input.occurredAt,
    meta: baseMeta,
  };

  if (input.action === "create") {
    entry.title = "Produto criado";
    entry.detail = productName || "Novo produto";
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount || 1), value, ...baseMeta]);
  } else if (input.action === "inline_edit") {
    entry.title = "Produto editado";
    entry.detail = productName || "Item da lista";
    entry.meta = normalizeDiaryMeta([fieldLabel ? `Campo: ${fieldLabel}` : null, value, ...baseMeta]);
  } else if (input.action === "delete") {
    entry.title = "Produto removido";
    entry.detail = productName || "Item removido";
    entry.tone = "warning";
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount || 1), ...baseMeta]);
  } else if (input.action === "clear") {
    entry.title = "Lista limpa";
    entry.detail = productCount ? removedProductText(productCount) : "Produtos removidos";
    entry.tone = "warning";
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount), ...baseMeta]);
  } else if (input.action === "bulk_category") {
    entry.title = "Categoria aplicada";
    entry.detail = value || "Categoria";
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount), ...baseMeta]);
  } else if (input.action === "bulk_brand") {
    entry.title = "Marca aplicada";
    entry.detail = value || "Marca";
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount), ...baseMeta]);
  } else if (input.action === "reorder") {
    entry.title = "Ordem atualizada";
    entry.detail = productCount ? `${productCount} itens na sequencia` : "Sequencia manual aplicada";
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount), ...baseMeta]);
  } else if (input.action === "create_set") {
    entry.title = "Conjunto criado";
    entry.detail = value || "Produtos agrupados";
    entry.meta = normalizeDiaryMeta([
      removedCount ? `${removedCount} linha${removedCount === 1 ? "" : "s"} removida${removedCount === 1 ? "" : "s"}` : null,
      ...baseMeta,
    ]);
  } else if (input.action === "format_codes") {
    entry.title = "Códigos formatados";
    entry.detail = `${changedCount} alterado${changedCount === 1 ? "" : "s"}`;
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount), value, ...baseMeta]);
  } else if (input.action === "improve_descriptions") {
    entry.title = "Descrições revisadas";
    entry.detail = `${changedCount} modificada${changedCount === 1 ? "" : "s"}`;
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount), ...baseMeta]);
  } else if (input.action === "margin") {
    entry.title = "Margem aplicada";
    entry.detail = value ? `${value}%` : "Margem atualizada";
    entry.meta = normalizeDiaryMeta([changedCount ? `${changedCount} produto${changedCount === 1 ? "" : "s"} atualizado${changedCount === 1 ? "" : "s"}` : null, ...baseMeta]);
  }

  return buildOperationDiaryEntry(entry);
}

export function updateOperationDiaryEntries(
  current: OperationDiaryEntry[],
  entry: OperationDiaryEntry,
  limit = 6,
): OperationDiaryEntry[] {
  const safeLimit = Math.max(1, Math.floor(Number(limit) || 6));
  return [entry, ...current.filter((item) => item.id !== entry.id)]
    .sort((left, right) => right.occurredAt - left.occurredAt)
    .slice(0, safeLimit);
}

export function coerceOperationDiaryEntries(value: unknown, limit = 6): OperationDiaryEntry[] {
  if (!Array.isArray(value)) return [];
  const safeLimit = Math.max(1, Math.floor(Number(limit) || 6));
  return value
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const record = item as Record<string, unknown>;
      const id = String(record.id || "").trim();
      const occurredAt = Number(record.occurredAt || 0);
      if (!id || !Number.isFinite(occurredAt) || occurredAt <= 0) return null;
      return buildOperationDiaryEntry({
        id,
        occurredAt,
        kind: String(record.kind || "system"),
        title: String(record.title || "Evento operacional"),
        detail: String(record.detail || ""),
        tone: isStatusTone(record.tone) ? record.tone : "neutral",
        meta: Array.isArray(record.meta) ? record.meta : [],
      });
    })
    .filter((item): item is OperationDiaryEntry => Boolean(item))
    .sort((left, right) => right.occurredAt - left.occurredAt)
    .slice(0, safeLimit);
}
