import { LAST_ACTIVE_GRADE_FAMILY_KEY } from "./gradeLogic";
import type { ProductQuickFilter } from "./productFilters";
import { coerceProductQuickFilter } from "./productFilters";
import type { EditableField } from "./productEditing";
import {
  coerceImportHistoryEntries,
  coerceOperationDiaryEntries,
} from "./uiFormatting";
import type { ImportHistoryEntry, OperationDiaryEntry } from "./uiFormatting";

type BrowserStorage = Pick<Storage, "getItem" | "setItem">;

export type RuntimeHealthState = {
  status: "checking" | "ok" | "error";
  message: string | null;
  version: string | null;
  checkedAt: number | null;
};

export type ConfirmationDialogState = {
  title: string;
  message: string;
  detail?: string;
  confirmLabel: string;
  onCancel?: () => void;
  onConfirm: () => Promise<void>;
};

export type TextInputDialogState = {
  title: string;
  description: string;
  label: string;
  value: string;
  confirmLabel: string;
  sectionTag?: string;
  placeholder?: string;
  validate?: (value: string) => string | null;
  onConfirm: (value: string) => Promise<void>;
};

export const RECENT_IMPORT_HISTORY_KEY = "lojasync:recent-import-history";
export const RECENT_IMPORT_HISTORY_LIMIT = 3;
export const OPERATION_DIARY_KEY = "lojasync:operation-diary";
export const OPERATION_DIARY_LIMIT = 120;
export const PRODUCT_QUICK_FILTER_KEY = "lojasync:product-quick-filter";
export const ORDERING_DRAFT_KEY = "lojasync:ordering-draft";
export const INLINE_EDIT_FIELD_LABELS: Record<EditableField, string> = {
  nome: "Nome",
  marca: "Marca",
  codigo: "Codigo",
  quantidade: "Quantidade",
  preco: "Preco",
  preco_final: "Preco final",
  categoria: "Categoria",
};

function getBrowserStorage(): BrowserStorage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readStorageValue(key: string, storage: BrowserStorage | null = getBrowserStorage()): string | null {
  try {
    return storage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function writeStorageValue(key: string, value: string, storage: BrowserStorage | null = getBrowserStorage()): void {
  try {
    storage?.setItem(key, value);
  } catch {
    // Local storage is an optional convenience; never block the workflow.
  }
}

export function readInitialImportHistory(storage: BrowserStorage | null = getBrowserStorage()): ImportHistoryEntry[] {
  try {
    return coerceImportHistoryEntries(
      JSON.parse(readStorageValue(RECENT_IMPORT_HISTORY_KEY, storage) || "[]"),
      RECENT_IMPORT_HISTORY_LIMIT,
    );
  } catch {
    return [];
  }
}

export function saveRecentImportHistory(entries: ImportHistoryEntry[], storage: BrowserStorage | null = getBrowserStorage()): void {
  try {
    writeStorageValue(RECENT_IMPORT_HISTORY_KEY, JSON.stringify(entries), storage);
  } catch {
    // Import history is a convenience cache; never block the import flow.
  }
}

export function readInitialOperationDiary(storage: BrowserStorage | null = getBrowserStorage()): OperationDiaryEntry[] {
  try {
    return coerceOperationDiaryEntries(
      JSON.parse(readStorageValue(OPERATION_DIARY_KEY, storage) || "[]"),
      OPERATION_DIARY_LIMIT,
    );
  } catch {
    return [];
  }
}

export function saveOperationDiary(entries: OperationDiaryEntry[], storage: BrowserStorage | null = getBrowserStorage()): void {
  try {
    writeStorageValue(OPERATION_DIARY_KEY, JSON.stringify(entries), storage);
  } catch {
    // Operation diary is a local convenience cache; never block the action.
  }
}

export function readInitialProductQuickFilter(storage: BrowserStorage | null = getBrowserStorage()): ProductQuickFilter {
  return coerceProductQuickFilter(readStorageValue(PRODUCT_QUICK_FILTER_KEY, storage));
}

export function saveProductQuickFilter(filter: ProductQuickFilter, storage: BrowserStorage | null = getBrowserStorage()): ProductQuickFilter {
  const nextFilter = coerceProductQuickFilter(filter);
  writeStorageValue(PRODUCT_QUICK_FILTER_KEY, nextFilter, storage);
  return nextFilter;
}

export function readInitialOrderingDraft(storage: BrowserStorage | null = getBrowserStorage()): string[] {
  try {
    const parsed = JSON.parse(readStorageValue(ORDERING_DRAFT_KEY, storage) || "[]");
    if (!Array.isArray(parsed)) return [];
    const seen = new Set<string>();
    const keys: string[] = [];
    for (const item of parsed) {
      const key = String(item || "").trim();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      keys.push(key);
    }
    return keys;
  } catch {
    return [];
  }
}

export function saveOrderingDraft(keys: string[], storage: BrowserStorage | null = getBrowserStorage()): string[] {
  const seen = new Set<string>();
  const nextKeys: string[] = [];
  for (const item of keys) {
    const key = String(item || "").trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    nextKeys.push(key);
  }
  if (!nextKeys.length) {
    writeStorageValue(ORDERING_DRAFT_KEY, "[]", storage);
    return [];
  }
  writeStorageValue(ORDERING_DRAFT_KEY, JSON.stringify(nextKeys), storage);
  return nextKeys;
}

export function clearOrderingDraft(storage: BrowserStorage | null = getBrowserStorage()): void {
  writeStorageValue(ORDERING_DRAFT_KEY, "[]", storage);
}

export function readLastActiveGradeFamily(storage: BrowserStorage | null = getBrowserStorage()): string {
  return readStorageValue(LAST_ACTIVE_GRADE_FAMILY_KEY, storage) || "common";
}

export function saveLastActiveGradeFamily(familyKey: string, storage: BrowserStorage | null = getBrowserStorage()): void {
  writeStorageValue(LAST_ACTIVE_GRADE_FAMILY_KEY, familyKey, storage);
}
