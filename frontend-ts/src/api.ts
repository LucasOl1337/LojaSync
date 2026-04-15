import type {
  AutomationStatus,
  AutomationTargets,
  BrandsResponse,
  CatalogSizesResponse,
  GradeConfig,
  GradeConfigResponse,
  ImportResult,
  ImportStartResponse,
  ImportStatus,
  MarginSettingsResponse,
  Product,
  ProductListResponse,
  ProductPayload,
  TargetCaptureResponse,
  TotalsResponse,
} from "./types";

const API_BASE_URL = (window as Window & { __BACKEND_URL__?: string }).__BACKEND_URL__ || window.location.origin;

function buildRequestUrl(path: string, method: string) {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (method.toUpperCase() === "GET") {
    url.searchParams.set("_", String(Date.now()));
  }
  return url.toString();
}

async function parseError(response: Response) {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text) as { detail?: string };
    return parsed.detail || text || response.statusText;
  } catch {
    return text || response.statusText;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method || "GET";
  const response = await fetch(buildRequestUrl(path, method), {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as T;
}

export function buildWsUrl(path: string) {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = path;
  url.search = "";
  url.hash = "";
  return url.toString();
}

export function fetchProducts() {
  return requestJson<ProductListResponse>("/products");
}

export function fetchTotals() {
  return requestJson<TotalsResponse>("/totals");
}

export function fetchBrands() {
  return requestJson<BrandsResponse>("/brands");
}

export function fetchMargin() {
  return requestJson<MarginSettingsResponse>("/settings/margin");
}

export function fetchAutomationStatus() {
  return requestJson<AutomationStatus>("/automation/status");
}

export function fetchAutomationTargets() {
  return requestJson<AutomationTargets>("/automation/targets");
}

export function saveAutomationTargets(payload: AutomationTargets) {
  return requestJson<AutomationTargets>("/automation/targets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function captureAutomationTarget(target: string) {
  return requestJson<TargetCaptureResponse>("/automation/targets/capture", {
    method: "POST",
    body: JSON.stringify({ target }),
  });
}

export function fetchByteEmpresaContext() {
  return requestJson<Record<string, unknown>>("/automation/byteempresa/context");
}

export function prepareByteEmpresa() {
  return requestJson<Record<string, unknown>>("/automation/byteempresa/prepare", {
    method: "POST",
  });
}

export function fetchCatalogSizes() {
  return requestJson<CatalogSizesResponse>("/catalog/sizes");
}

export async function fetchGradeConfig() {
  const payload = await requestJson<GradeConfigResponse>("/automation/grades/config");
  return payload.config;
}

export function saveGradeConfig(config: GradeConfig) {
  return requestJson<GradeConfigResponse>("/automation/grades/config", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

export function startAutomationCatalog() {
  return requestJson<{ status: string; message: string }>("/automation/execute", {
    method: "POST",
  });
}

export function startAutomationComplete() {
  return requestJson<{ status: string; message: string }>("/automation/execute-complete", {
    method: "POST",
  });
}

export function stopAutomation() {
  return requestJson<{ status: string; message: string }>("/automation/cancel", {
    method: "POST",
  });
}

export function createProduct(payload: ProductPayload) {
  return requestJson("/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchProduct(orderingKey: string, payload: Partial<ProductPayload>) {
  return requestJson(`/products/${encodeURIComponent(orderingKey)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteProduct(orderingKey: string) {
  return requestJson(`/products/${encodeURIComponent(orderingKey)}`, {
    method: "DELETE",
  });
}

export function restoreSnapshot(items: Product[]) {
  return requestJson<{ total: number }>("/actions/restore-snapshot", {
    method: "POST",
    body: JSON.stringify({
      items: items.map((item) => ({
        nome: item.nome,
        codigo: item.codigo,
        ordering_key: item.ordering_key,
        codigo_original: item.codigo_original,
        quantidade: item.quantidade,
        preco: item.preco,
        categoria: item.categoria,
        marca: item.marca,
        preco_final: item.preco_final,
        descricao_completa: item.descricao_completa,
        grades: item.grades || null,
        cores: item.cores || null,
        timestamp: item.timestamp,
      })),
    }),
  });
}

export function clearProducts() {
  return requestJson<{ removed: number }>("/products", {
    method: "DELETE",
  });
}

export function addBrand(nome: string) {
  return requestJson<BrandsResponse>("/brands", {
    method: "POST",
    body: JSON.stringify({ nome }),
  });
}

export function applyCategory(valor: string) {
  return requestJson<{ status: string; categoria: string; total: number }>("/actions/apply-category", {
    method: "POST",
    body: JSON.stringify({ valor }),
  });
}

export function applyBrand(valor: string) {
  return requestJson<{ status: string; marca: string; total: number }>("/actions/apply-brand", {
    method: "POST",
    body: JSON.stringify({ valor }),
  });
}

export function joinDuplicates() {
  return requestJson<{ originais: number; resultantes: number; removidos: number }>("/actions/join-duplicates", {
    method: "POST",
  });
}

export function reorderProducts(keys: string[]) {
  return requestJson<{ total: number }>("/actions/reorder", {
    method: "POST",
    body: JSON.stringify({ keys }),
  });
}

export function joinGrades() {
  return requestJson<{ originais: number; resultantes: number; removidos: number; atualizados_grades: number }>("/actions/join-grades", {
    method: "POST",
  });
}

export function saveMargin(percentual: number) {
  return requestJson<MarginSettingsResponse>("/settings/margin", {
    method: "POST",
    body: JSON.stringify({ percentual }),
  });
}

export function applyMargin(percentual: number) {
  return requestJson<{ total_atualizados: number; margem_utilizada: number; percentual_utilizado: number }>("/actions/apply-margin", {
    method: "POST",
    body: JSON.stringify({ percentual }),
  });
}

export function formatCodes(payload: {
  remover_prefixo5: boolean;
  remover_zeros_a_esquerda: boolean;
  ultimos_digitos: number | null;
  primeiros_digitos: number | null;
  remover_ultimos_numeros: number | null;
  remover_primeiros_numeros: number | null;
  manter_primeiros_caracteres: number | null;
  manter_ultimos_caracteres: number | null;
  remover_primeiros_caracteres: number | null;
  remover_ultimos_caracteres: number | null;
  remover_letras: boolean;
  remover_numeros: boolean;
}) {
  return requestJson<{ total: number; alterados: number; prefixo: string | null }>("/actions/format-codes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function restoreOriginalCodes() {
  return requestJson<{ total: number; restaurados: number }>("/actions/restore-original-codes", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function improveDescriptions(payload: {
  remover_numeros: boolean;
  remover_especiais: boolean;
  remover_letras: boolean;
  remover_termos: string[];
}) {
  return requestJson<{ total: number; modificados: number }>("/actions/improve-descriptions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createSet(keyA: string, keyB: string) {
  return requestJson<{ created: number; removed: number; remaining_a: number; remaining_b: number }>("/actions/create-set", {
    method: "POST",
    body: JSON.stringify({ key_a: keyA, key_b: keyB }),
  });
}

export function executeGradesProducts() {
  return requestJson<{ status?: string; message?: string }>("/automation/grades/execute-products", {
    method: "POST",
  });
}

export function runGrades(grades: Record<string, number>, options?: { model_index?: number | null; pause?: number | null; speed?: number | null }) {
  return requestJson<{ status?: string; message?: string }>("/automation/grades/run", {
    method: "POST",
    body: JSON.stringify({
      grades,
      model_index: options?.model_index,
      pause: options?.pause,
      speed: options?.speed,
    }),
  });
}

export function runGradesBatch(tasks: Array<{ grades: Record<string, number>; model_index?: number | null }>, options?: { pause?: number | null; speed?: number | null }) {
  return requestJson<{ status?: string; message?: string }>("/automation/grades/batch", {
    method: "POST",
    body: JSON.stringify({
      tasks,
      pause: options?.pause,
      speed: options?.speed,
    }),
  });
}

export function stopGradesExecution() {
  return requestJson<{ status?: string; message?: string }>("/automation/grades/stop", {
    method: "POST",
  });
}

export async function importRomaneio(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/actions/import-romaneio`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ImportStartResponse;
}

export function fetchImportStatus(jobId: string) {
  return requestJson<ImportStatus>(`/actions/import-romaneio/status/${jobId}`);
}

export function fetchImportResult(jobId: string) {
  return requestJson<ImportResult>(`/actions/import-romaneio/result/${jobId}`);
}

export { API_BASE_URL };
