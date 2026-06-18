import type { ImportResult, ImportStatus, PostProcessResult, Product, TargetPoint } from "./types";

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
  warningCount: number;
  validationStatus: string;
  gradesAvailable: boolean;
  status: string;
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

export type ExecutionReadinessInput = {
  productCount?: number | null;
  pendingGradeCount?: number | null;
  automationState?: string | null;
  automationError?: string | null;
  missingTargetLabels?: string[] | null;
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

export function formatAutomationStateLabel(state: unknown) {
  const normalized = String(state || "").trim().toLowerCase();
  if (!normalized || normalized === "idle") return "Pronta";
  if (normalized === "running") return "Em execucao";
  if (normalized === "stopping" || normalized === "canceling" || normalized === "cancelling") return "Parando";
  if (normalized === "failed" || normalized === "error") return "Falha";
  if (normalized === "queued") return "Na fila";
  if (normalized === "paused") return "Pausada";
  if (normalized === "succeeded" || normalized === "completed" || normalized === "success") return "Concluida";
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
      ? `${safeUndoCount} desfazer | ${safeRedoCount} refazer`
      : "Sem historico",
    undoLabel: canUndo
      ? `Desfazer ${actionText(safeUndoCount, "acao", "acoes")}`
      : "Nada para desfazer",
    redoLabel: canRedo
      ? `Refazer ${actionText(safeRedoCount, "acao", "acoes")}`
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

export function formatTargetPoint(point?: TargetPoint | null) {
  if (!point) return "Nao calibrado";
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

export function buildImportProgressMessage(importing: boolean, jobMessage?: string | null) {
  if (!importing) return null;
  const message = String(jobMessage || "").trim();
  return message || "Importacao em andamento...";
}

function positiveMetric(metrics: Record<string, unknown>, key: string) {
  const value = Number(metrics[key] || 0);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

function hasVerticalSliceFallback(metrics: Record<string, unknown>) {
  const details = metrics["llm_chat_calls_details"];
  return Array.isArray(details)
    ? details.some((item) => item && typeof item === "object" && String((item as Record<string, unknown>).attempt || "") === "vertical_slices")
    : false;
}

export function buildImportDiagnosticsChips(
  metrics: Record<string, unknown> | null | undefined,
  warnings: string[] = [],
): ImportDiagnosticsChip[] {
  const source = String(metrics?.["selected_source"] || "").trim();
  const chips: ImportDiagnosticsChip[] = [];
  const safeMetrics: Record<string, unknown> = metrics || {};

  if (source === "local") {
    chips.push({ label: "Origem", value: "Parser local", tone: "success" });
  } else if (source === "llm") {
    chips.push({ label: "Origem", value: "LLM", tone: "neutral" });
  }

  const chatCalls = positiveMetric(safeMetrics, "llm_chat_calls");
  if (chatCalls) {
    chips.push({ label: "LLM", value: `${chatCalls} chamada${chatCalls === 1 ? "" : "s"}`, tone: "neutral" });
  }

  const chunkCount = positiveMetric(safeMetrics, "llm_chunk_count");
  if (chunkCount > 1) {
    chips.push({ label: "Partes", value: String(chunkCount), tone: "neutral" });
  }

  const uploadImages = positiveMetric(safeMetrics, "upload_images");
  if (uploadImages) {
    chips.push({ label: "Imagens", value: String(uploadImages), tone: "neutral" });
  }

  if (hasVerticalSliceFallback(safeMetrics)) {
    chips.push({ label: "Fallback", value: "Recortes verticais", tone: "warning" });
  }

  if (warnings.length) {
    chips.push({ label: "Avisos", value: String(warnings.length), tone: "warning" });
  }

  return chips;
}

export function buildOperationalHealthChips(input: OperationalHealthInput): StatusChip[] {
  const chips: StatusChip[] = [];

  if (input.backendStatus === "ok") {
    chips.push({ label: "Backend", value: "Ativo", tone: "success" });
  } else if (input.backendStatus === "error") {
    chips.push({ label: "Backend", value: "Indisponivel", tone: "error" });
  } else {
    chips.push({ label: "Backend", value: "Verificando", tone: "warning" });
  }

  if (input.bootstrapRequired) {
    chips.push({ label: "Auth", value: "Configurar", tone: "warning" });
  } else if (input.authEnabled === false) {
    chips.push({ label: "Auth", value: "Livre", tone: "neutral" });
  } else if (input.authenticated) {
    chips.push({ label: "Auth", value: "Sessao ativa", tone: "success" });
  } else {
    chips.push({ label: "Auth", value: "Login pendente", tone: "warning" });
  }

  const websocketMap: Record<UiSocketStatus, StatusChip> = {
    connecting: { label: "Tempo real", value: "Conectando", tone: "warning" },
    connected: { label: "Tempo real", value: "Conectado", tone: "success" },
    reconnecting: { label: "Tempo real", value: "Reconectando", tone: "warning" },
    disconnected: { label: "Tempo real", value: "Offline", tone: "error" },
  };
  chips.push(websocketMap[input.websocketStatus]);

  const automationError = String(input.automationError || "").trim();
  const automationState = String(input.automationState || "").trim();
  if (automationError) {
    chips.push({ label: "Automacao", value: automationError, tone: "error" });
  } else if (automationState === "running") {
    chips.push({ label: "Automacao", value: formatAutomationStateLabel(automationState), tone: "warning" });
  } else {
    chips.push({ label: "Automacao", value: formatAutomationStateLabel(automationState), tone: "neutral" });
  }

  const pendingGrades = Math.max(0, Math.floor(Number(input.pendingGrades || 0)));
  chips.push({
    label: "Grades",
    value: pendingGrades ? `${pendingGrades} pendente${pendingGrades === 1 ? "" : "s"}` : "Sem pendencias",
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

  return "Sem automacao em execucao";
}

export function buildExecutionReadiness(input: ExecutionReadinessInput): ExecutionReadinessState {
  const productCount = safeCount(input.productCount);
  const pendingGradeCount = safeCount(input.pendingGradeCount);
  const automationError = String(input.automationError || "").trim();
  const automationState = String(input.automationState || "").trim() || "idle";
  const automationRunning = automationState === "running";
  const targetLabels = Array.isArray(input.missingTargetLabels)
    ? input.missingTargetLabels.map((item) => String(item || "").trim()).filter(Boolean)
    : null;
  const missingTargetCount = targetLabels?.length ?? 0;
  const items: StatusChip[] = [
    {
      label: "Lista",
      value: productCount ? actionText(productCount, "item", "itens") : "Sem produtos",
      tone: productCount ? "success" : "warning",
    },
    {
      label: "Grades",
      value: pendingGradeCount ? `${pendingGradeCount} pendente${pendingGradeCount === 1 ? "" : "s"}` : "Fechadas",
      tone: pendingGradeCount ? "warning" : "success",
    },
    {
      label: "Automacao",
      value: automationError || formatAutomationStateLabel(automationState),
      tone: automationError ? "error" : automationRunning ? "warning" : "neutral",
    },
  ];
  if (targetLabels) {
    items.push({
      label: "Targets",
      value: missingTargetCount ? `${missingTargetCount} faltando` : "Calibrados",
      tone: missingTargetCount ? "warning" : "success",
    });
  }

  if (automationError) {
    return {
      ready: false,
      tone: "error",
      title: "Revisar automacao",
      detail: "Corrija o erro da automacao antes de iniciar o cadastro completo.",
      items,
    };
  }

  if (automationRunning) {
    return {
      ready: false,
      tone: "warning",
      title: "Automacao em execucao",
      detail: "Aguarde a execucao atual terminar ou use Parar antes de iniciar outro fluxo.",
      items,
    };
  }

  if (pendingGradeCount) {
    return {
      ready: false,
      tone: "warning",
      title: `${pendingGradeCount} grade${pendingGradeCount === 1 ? "" : "s"} pendente${pendingGradeCount === 1 ? "" : "s"}`,
      detail: "Abra Inserir Grade para fechar as pendencias antes do cadastro completo.",
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

  if (missingTargetCount) {
    return {
      ready: false,
      tone: "warning",
      title: `${missingTargetCount} target${missingTargetCount === 1 ? "" : "s"} incompleto${missingTargetCount === 1 ? "" : "s"}`,
      detail: "Calibre os alvos de automacao nas configuracoes antes do cadastro completo.",
      items,
    };
  }

  return {
    ready: true,
    tone: "success",
    title: "Pronto para cadastro completo",
    detail: targetLabels
      ? "Lista com produtos, grades fechadas, targets calibrados e automacao sem erro ativo."
      : "Lista com produtos, grades fechadas e automacao sem erro ativo.",
    items,
  };
}

export function buildImportGradesAvailableMessage(result: Pick<ImportResult, "grades_disponiveis" | "total_grades_disponiveis">) {
  if (!result.grades_disponiveis) {
    return null;
  }
  const baseMessage = "Grades automaticas disponiveis.\n\nClique em Importar Grades para aplicar.";
  if (Number(result.total_grades_disponiveis || 0) > 0) {
    return `${baseMessage}\nGrupos detectados: ${result.total_grades_disponiveis}`;
  }
  return baseMessage;
}

function normalizeImportMode(source: string, fallback?: "llm" | "local" | null) {
  if (source === "local" || fallback === "local") return "Parser local";
  if (source === "llm" || fallback === "llm") return "LLM";
  return "Importacao";
}

export function formatImportSourceDisplayName(sourceName: unknown) {
  const fallback = "Romaneio importado";
  const value = String(sourceName || "").trim();
  if (!value) return fallback;

  const normalizedPath = value.replace(/\\/g, "/");
  const lastSegment = normalizedPath.split("/").filter(Boolean).pop();
  return lastSegment?.trim() || fallback;
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

  return {
    id: String(options.job?.job_id || `${sourceName}-${completedAt}`).trim(),
    completedAt,
    sourceName,
    mode: normalizeImportMode(source, options.mode),
    totalItems: Math.max(0, Math.floor(Number(result.total_itens || 0))),
    warningCount: Array.isArray(result.warnings) ? result.warnings.length : 0,
    validationStatus: validationStatus || "sem validacao",
    gradesAvailable: Boolean(result.grades_disponiveis),
    status: String(result.status || "").trim() || "ok",
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
  return value
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const record = item as Record<string, unknown>;
      const id = String(record.id || "").trim();
      const completedAt = Number(record.completedAt || 0);
      if (!id || !Number.isFinite(completedAt) || completedAt <= 0) return null;
      return {
        id,
        completedAt,
        sourceName: String(record.sourceName || "Romaneio importado").trim() || "Romaneio importado",
        mode: String(record.mode || "Importacao").trim() || "Importacao",
        totalItems: Math.max(0, Math.floor(Number(record.totalItems || 0))),
        warningCount: Math.max(0, Math.floor(Number(record.warningCount || 0))),
        validationStatus: String(record.validationStatus || "sem validacao").trim() || "sem validacao",
        gradesAvailable: Boolean(record.gradesAvailable),
        status: String(record.status || "ok").trim() || "ok",
      };
    })
    .filter((item): item is ImportHistoryEntry => Boolean(item))
    .sort((left, right) => right.completedAt - left.completedAt)
    .slice(0, safeLimit);
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
    entry.title = "Codigos formatados";
    entry.detail = `${changedCount} alterado${changedCount === 1 ? "" : "s"}`;
    entry.meta = normalizeDiaryMeta([productItemMeta(productCount), value, ...baseMeta]);
  } else if (input.action === "improve_descriptions") {
    entry.title = "Descricoes revisadas";
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

export function buildPostProcessCompletionMessage(result: Pick<PostProcessResult, "total_itens" | "total_modificados" | "dry_run" | "warnings">) {
  const summaryLines = [
    `Itens revisados: ${result.total_itens}`,
    `Alteracoes aplicadas nesta fase: ${result.total_modificados}`,
  ];
  if (result.dry_run) {
    summaryLines.push("Modo inicial ativo: a IA revisou os itens, mas ainda nao aplicamos as sugestoes automaticamente.");
  }
  if (result.warnings?.length) {
    summaryLines.push(`Avisos: ${result.warnings.join(" | ")}`);
  }
  return summaryLines.join("\n");
}
