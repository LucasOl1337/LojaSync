import type { ImportResult, ImportStatus } from "./types";

export type ImportPreviewKind = "pdf" | "image" | "text" | "unsupported";
export type ImportDocumentState = "staged" | "queued" | "processing" | "succeeded" | "failed";

export type NormalizedRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type ImportProcessEntry = {
  index: number;
  source: string;
  level: string;
  message: string;
};

export type StagedImportDocument = {
  id: string;
  file: File;
  previewKind: ImportPreviewKind;
  rect: NormalizedRect;
  zIndex: number;
  state: ImportDocumentState;
  importMode: "llm" | "local" | null;
  status: ImportStatus | null;
  result: ImportResult | null;
  error: string | null;
  errorReasons: string[];
};

export type ImportBatchSummary = {
  total: number;
  succeeded: number;
  failed: number;
  pending: number;
  totalItems: number;
  message: string;
};

const REASON_MESSAGES: Record<string, string> = {
  no_importable_items: "A IA não encontrou itens de produto que pudessem ser importados.",
  product_total_mismatch: "A soma dos produtos extraídos não confere com o total de produtos impresso na nota.",
  remessa_quantity_mismatch: "A quantidade extraída não confere com a quantidade da remessa.",
  "no importable items were detected": "A IA não encontrou itens de produto que pudessem ser importados.",
  "the extracted product total does not match the invoice total": "A soma dos produtos extraídos não confere com o total de produtos impresso na nota.",
  "the extracted quantity does not match the remessa quantity": "A quantidade extraída não confere com a quantidade da remessa.",
};

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

export function buildFileDedupeKey(file: Pick<File, "name" | "size" | "lastModified">) {
  return `${file.name}\0${file.size}\0${file.lastModified}`;
}

export function detectImportPreviewKind(file: Pick<File, "name" | "type">): ImportPreviewKind {
  const mime = file.type.toLowerCase();
  const extension = file.name.toLowerCase().split(".").pop() || "";
  if (mime === "application/pdf" || extension === "pdf") return "pdf";
  if (mime.startsWith("image/") || ["png", "jpg", "jpeg"].includes(extension)) return "image";
  if (mime.startsWith("text/") || extension === "txt") return "text";
  return "unsupported";
}

export function buildAutomaticImportLayout(count: number): NormalizedRect[] {
  if (count <= 0) return [];
  const gutter = 0.012;
  if (count === 1) return [{ x: 0, y: 0, width: 1, height: 1 }];
  if (count === 2) {
    const width = (1 - gutter) / 2;
    return [
      { x: 0, y: 0, width, height: 1 },
      { x: width + gutter, y: 0, width, height: 1 },
    ];
  }
  if (count === 3) {
    const halfWidth = (1 - gutter) / 2;
    const halfHeight = (1 - gutter) / 2;
    return [
      { x: 0, y: 0, width: halfWidth, height: 1 },
      { x: halfWidth + gutter, y: 0, width: halfWidth, height: halfHeight },
      { x: halfWidth + gutter, y: halfHeight + gutter, width: halfWidth, height: halfHeight },
    ];
  }
  const columns = Math.ceil(Math.sqrt(count));
  const rows = Math.ceil(count / columns);
  const width = (1 - gutter * (columns - 1)) / columns;
  const height = (1 - gutter * (rows - 1)) / rows;
  return Array.from({ length: count }, (_, index) => ({
    x: (index % columns) * (width + gutter),
    y: Math.floor(index / columns) * (height + gutter),
    width,
    height,
  }));
}

export function clampImportRect(rect: NormalizedRect, minimumWidth = 0.16, minimumHeight = 0.18): NormalizedRect {
  const width = clamp(rect.width, minimumWidth, 1);
  const height = clamp(rect.height, minimumHeight, 1);
  return {
    x: clamp(rect.x, 0, 1 - width),
    y: clamp(rect.y, 0, 1 - height),
    width,
    height,
  };
}

export function createStagedImportDocuments(files: File[], existing: StagedImportDocument[] = []): StagedImportDocument[] {
  const seen = new Set(existing.map((document) => buildFileDedupeKey(document.file)));
  const uniqueFiles = files.filter((file) => {
    const key = buildFileDedupeKey(file);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const allFiles = [...existing.map((document) => document.file), ...uniqueFiles];
  const layout = buildAutomaticImportLayout(allFiles.length);
  const byKey = new Map(existing.map((document) => [buildFileDedupeKey(document.file), document]));
  return allFiles.map((file, index) => {
    const previous = byKey.get(buildFileDedupeKey(file));
    return previous
      ? { ...previous, rect: layout[index] }
      : {
          id: `${file.name}-${file.size}-${file.lastModified}-${index}`,
          file,
          previewKind: detectImportPreviewKind(file),
          rect: layout[index],
          zIndex: index + 1,
          state: "staged",
          importMode: null,
          status: null,
          result: null,
          error: null,
          errorReasons: [],
        };
  });
}

function coerceStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item).trim()).filter(Boolean) : [];
}

export function extractImportFailureReasons(metrics: Record<string, unknown> | null | undefined, fallbackError?: string | null): string[] {
  const codes = coerceStringArray(metrics?.["final_validation_reason_codes"]);
  const rawReasons = coerceStringArray(metrics?.["final_validation_reasons"]);
  const source = codes.length ? codes : rawReasons;
  const mapped = source.map((reason) => REASON_MESSAGES[reason] || reason);
  const unique = [...new Set(mapped.filter(Boolean))];
  if (unique.length) return unique;
  return fallbackError?.trim() ? [fallbackError.trim()] : [];
}

export function coerceImportProcessEntries(metrics: Record<string, unknown> | null | undefined): ImportProcessEntry[] {
  const raw = metrics?.["process_log"];
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((item, index) => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const message = String(record.message || "").trim();
    if (!message) return [];
    return [{
      index: Number(record.index || index + 1),
      source: String(record.source || "system"),
      level: String(record.level || "info"),
      message,
    }];
  });
}

export function buildImportBatchSummary(documents: StagedImportDocument[]): ImportBatchSummary {
  const succeeded = documents.filter((document) => document.state === "succeeded");
  const failed = documents.filter((document) => document.state === "failed");
  const pending = documents.length - succeeded.length - failed.length;
  const totalItems = succeeded.reduce((total, document) => total + Number(document.result?.total_itens || 0), 0);
  let message = documents.length ? `${documents.length} documento${documents.length === 1 ? "" : "s"} pronto${documents.length === 1 ? "" : "s"}.` : "Selecione as notas para começar.";
  if (!pending && documents.length) {
    if (!failed.length) message = `${succeeded.length} de ${documents.length} documentos importados — ${totalItems} itens.`;
    else if (!succeeded.length) message = "Nenhum documento foi importado. Revise os motivos no painel.";
    else message = `${succeeded.length} de ${documents.length} documentos importados. ${failed.length} documento${failed.length === 1 ? " foi bloqueado" : "s foram bloqueados"}.`;
  }
  return { total: documents.length, succeeded: succeeded.length, failed: failed.length, pending, totalItems, message };
}
