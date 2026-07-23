/**
 * Persist import conference sessions (file blob + extraction result) so hard refresh
 * and "Importações recentes" can reopen the note without re-picking the file.
 */

import type { ImportResult, ImportStatus } from "./types";
import type { ImportDocumentState, StagedImportDocument } from "./importWorkspace";
import { detectImportPreviewKind } from "./importWorkspace";
import type { ImportHistoryEntry } from "./uiFormatting";

const DB_NAME = "lojasync-import-sessions";
const DB_VERSION = 1;
const SESSIONS_STORE = "sessions";
const META_STORE = "meta";
const ACTIVE_META_KEY = "activeConferenceIds";

export type StoredImportSession = {
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
  documentState: ImportDocumentState;
  importMode: "llm" | "local" | null;
  result: ImportResult | null;
  importStatus: ImportStatus | null;
  error: string | null;
  errorReasons: string[];
  fileName: string;
  fileType: string;
  fileLastModified: number;
  fileSize: number;
  fileBlob: Blob;
};

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB indisponível"));
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(SESSIONS_STORE)) {
        const store = db.createObjectStore(SESSIONS_STORE, { keyPath: "id" });
        store.createIndex("completedAt", "completedAt", { unique: false });
      }
      if (!db.objectStoreNames.contains(META_STORE)) {
        db.createObjectStore(META_STORE, { keyPath: "key" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Falha ao abrir IndexedDB"));
  });
}

function runStore<T>(
  mode: IDBTransactionMode,
  storeName: string,
  execute: (store: IDBObjectStore) => IDBRequest<T> | void,
): Promise<T | undefined> {
  return openDb().then(
    (db) =>
      new Promise<T | undefined>((resolve, reject) => {
        const tx = db.transaction(storeName, mode);
        const store = tx.objectStore(storeName);
        let request: IDBRequest<T> | undefined;
        try {
          const maybe = execute(store);
          if (maybe) request = maybe;
        } catch (error) {
          reject(error);
          return;
        }
        tx.oncomplete = () => {
          db.close();
          resolve(request ? request.result : undefined);
        };
        tx.onerror = () => {
          db.close();
          reject(tx.error || new Error("Falha na transação IndexedDB"));
        };
        if (request) {
          request.onerror = () => {
            reject(request?.error || new Error("Falha na operação IndexedDB"));
          };
        }
      }),
  );
}

export async function putImportSession(session: StoredImportSession): Promise<void> {
  await runStore("readwrite", SESSIONS_STORE, (store) => {
    store.put(session);
  });
}

export async function getImportSession(id: string): Promise<StoredImportSession | null> {
  const result = await runStore<StoredImportSession>("readonly", SESSIONS_STORE, (store) => store.get(id));
  return result || null;
}

export async function deleteImportSession(id: string): Promise<void> {
  const key = String(id || "").trim();
  if (!key) return;
  await runStore("readwrite", SESSIONS_STORE, (store) => {
    store.delete(key);
  });
  try {
    const active = await getActiveConferenceIds();
    if (active.includes(key)) {
      await setActiveConferenceIds(active.filter((item) => item !== key));
    }
  } catch {
    /* meta is optional */
  }
}

export async function listImportSessions(limit = 8): Promise<StoredImportSession[]> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SESSIONS_STORE, "readonly");
    const store = tx.objectStore(SESSIONS_STORE);
    const index = store.index("completedAt");
    const request = index.openCursor(null, "prev");
    const items: StoredImportSession[] = [];
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) return;
      if (items.length >= limit) return;
      items.push(cursor.value as StoredImportSession);
      if (items.length < limit) cursor.continue();
    };
    tx.oncomplete = () => {
      db.close();
      resolve(items);
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error || new Error("Falha ao listar sessões"));
    };
  });
}

export async function pruneImportSessions(limit = 8): Promise<void> {
  const all = await listImportSessions(Math.max(limit * 3, 24));
  if (all.length <= limit) return;
  const drop = all.slice(limit);
  await openDb().then(
    (db) =>
      new Promise<void>((resolve, reject) => {
        const tx = db.transaction(SESSIONS_STORE, "readwrite");
        const store = tx.objectStore(SESSIONS_STORE);
        for (const item of drop) store.delete(item.id);
        tx.oncomplete = () => {
          db.close();
          resolve();
        };
        tx.onerror = () => {
          db.close();
          reject(tx.error || new Error("Falha ao limpar sessões"));
        };
      }),
  );
}

export async function setActiveConferenceIds(ids: string[]): Promise<void> {
  const clean = [...new Set(ids.map((id) => String(id || "").trim()).filter(Boolean))].slice(0, 12);
  await runStore("readwrite", META_STORE, (store) => {
    store.put({ key: ACTIVE_META_KEY, value: clean });
  });
}

export async function getActiveConferenceIds(): Promise<string[]> {
  const row = await runStore<{ key: string; value: string[] }>("readonly", META_STORE, (store) =>
    store.get(ACTIVE_META_KEY),
  );
  if (!row || !Array.isArray(row.value)) return [];
  return row.value.map((id) => String(id || "").trim()).filter(Boolean);
}

export async function clearActiveConference(): Promise<void> {
  await setActiveConferenceIds([]);
}

export function sessionToStagedDocument(session: StoredImportSession): StagedImportDocument {
  const file = new File([session.fileBlob], session.fileName || "romaneio", {
    type: session.fileType || session.fileBlob.type || "application/octet-stream",
    lastModified: session.fileLastModified || Date.now(),
  });
  return {
    id: session.id,
    file,
    previewKind: detectImportPreviewKind(file),
    rect: { x: 0, y: 0, width: 1, height: 1 },
    zIndex: 1,
    state: session.documentState || (session.result ? "succeeded" : session.error ? "failed" : "staged"),
    importMode: session.importMode,
    status: session.importStatus,
    result: session.result,
    error: session.error,
    errorReasons: Array.isArray(session.errorReasons) ? session.errorReasons : [],
  };
}

export async function loadActiveConferenceDocuments(): Promise<StagedImportDocument[]> {
  const ids = await getActiveConferenceIds();
  if (!ids.length) return [];
  const docs: StagedImportDocument[] = [];
  for (const id of ids) {
    const session = await getImportSession(id);
    if (!session?.fileBlob) continue;
    docs.push(sessionToStagedDocument(session));
  }
  if (docs.length <= 1) return docs;
  const layoutCount = docs.length;
  const gutter = 0.012;
  return docs.map((document, index) => {
    if (layoutCount === 1) return document;
    if (layoutCount === 2) {
      const width = (1 - gutter) / 2;
      return {
        ...document,
        zIndex: index + 1,
        rect: { x: index * (width + gutter), y: 0, width, height: 1 },
      };
    }
    const columns = Math.ceil(Math.sqrt(layoutCount));
    const rows = Math.ceil(layoutCount / columns);
    const width = (1 - gutter * (columns - 1)) / columns;
    const height = (1 - gutter * (rows - 1)) / rows;
    return {
      ...document,
      zIndex: index + 1,
      rect: {
        x: (index % columns) * (width + gutter),
        y: Math.floor(index / columns) * (height + gutter),
        width,
        height,
      },
    };
  });
}

export async function persistStagedDocuments(
  documents: StagedImportDocument[],
  options: { markActive?: boolean; historyById?: Record<string, ImportHistoryEntry | undefined> } = {},
): Promise<void> {
  if (!documents.length) {
    if (options.markActive !== false) await clearActiveConference();
    return;
  }
  const ids: string[] = [];
  for (const document of documents) {
    const history = options.historyById?.[document.id];
    const session = buildSessionFromDocument(document, history);
    await putImportSession(session);
    ids.push(session.id);
  }
  await pruneImportSessions(8);
  if (options.markActive !== false) {
    await setActiveConferenceIds(ids);
  }
}

export function buildSessionFromDocument(
  document: StagedImportDocument,
  history?: ImportHistoryEntry | null,
): StoredImportSession {
  const completedAt =
    history?.completedAt ||
    (document.status?.completed_at ? document.status.completed_at * 1000 : 0) ||
    (document.status?.updated_at ? document.status.updated_at * 1000 : 0) ||
    Date.now();
  const result = document.result;
  return {
    id: String(history?.id || document.id).trim() || document.id,
    completedAt,
    sourceName: history?.sourceName || document.file.name,
    mode: history?.mode || (document.importMode === "local" ? "Leitura local" : document.importMode === "llm" ? "IA" : "Importação"),
    totalItems: history?.totalItems ?? Math.max(0, Math.floor(Number(result?.total_itens || 0))),
    totalValueLabel: history?.totalValueLabel ?? null,
    warningCount: history?.warningCount ?? (Array.isArray(result?.warnings) ? result.warnings.length : 0),
    validationStatus: history?.validationStatus || "sem validacao",
    gradesAvailable: history?.gradesAvailable ?? Boolean(result?.grades_disponiveis),
    status: history?.status || String(result?.status || document.state || "ok"),
    documentState: document.state,
    importMode: document.importMode,
    result: document.result,
    importStatus: document.status,
    error: document.error,
    errorReasons: document.errorReasons || [],
    fileName: document.file.name,
    fileType: document.file.type || "application/octet-stream",
    fileLastModified: document.file.lastModified || Date.now(),
    fileSize: document.file.size || 0,
    fileBlob: document.file,
  };
}

export async function historyEntryHasSession(id: string): Promise<boolean> {
  const session = await getImportSession(id);
  return Boolean(session?.fileBlob);
}
