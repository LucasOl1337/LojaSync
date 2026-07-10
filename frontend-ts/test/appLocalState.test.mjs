import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import test from "node:test";

const compiledModuleUrl = new URL("../.tmp-tests/appLocalState.js", import.meta.url);
const testableModuleUrl = new URL("../.tmp-tests/appLocalState.testable.mjs", import.meta.url);
const compiledModule = await readFile(compiledModuleUrl, "utf8");
await writeFile(
  testableModuleUrl,
  compiledModule
    .replaceAll('from "./gradeLogic"', 'from "./gradeLogic.js"')
    .replaceAll('from "./productFilters"', 'from "./productFilters.js"')
    .replaceAll('from "./uiFormatting"', 'from "./uiFormatting.js"'),
);
const localState = await import(testableModuleUrl);

function fakeStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    dump() {
      return Object.fromEntries(values.entries());
    },
  };
}

const historyEntry = {
  id: "import-1",
  completedAt: 10,
  sourceName: "romaneio.pdf",
  mode: "Leitura local",
  totalItems: 4,
  warningCount: 0,
  validationStatus: "approved",
  gradesAvailable: false,
  status: "ok",
};

const diaryEntry = {
  id: "op-1",
  occurredAt: 20,
  kind: "system",
  title: "Operacao",
  detail: "Concluida",
  tone: "success",
  meta: [],
};

test("reads persisted import history and operation diary through coercion limits", () => {
  const storage = fakeStorage({
    [localState.RECENT_IMPORT_HISTORY_KEY]: JSON.stringify([
      { ...historyEntry, id: "a", completedAt: 1 },
      { ...historyEntry, id: "b", completedAt: 2 },
      { ...historyEntry, id: "c", completedAt: 3 },
      { ...historyEntry, id: "d", completedAt: 4 },
    ]),
    [localState.OPERATION_DIARY_KEY]: JSON.stringify([
      { ...diaryEntry, id: "a", occurredAt: 1 },
      { ...diaryEntry, id: "b", occurredAt: 2 },
      { ...diaryEntry, id: "c", occurredAt: 3 },
      { ...diaryEntry, id: "d", occurredAt: 4 },
      { ...diaryEntry, id: "e", occurredAt: 5 },
      { ...diaryEntry, id: "f", occurredAt: 6 },
      { ...diaryEntry, id: "g", occurredAt: 7 },
    ]),
  });

  assert.deepEqual(localState.readInitialImportHistory(storage).map((entry) => entry.id), ["d", "c", "b"]);
  assert.equal(localState.OPERATION_DIARY_LIMIT, 120);
  assert.deepEqual(localState.readInitialOperationDiary(storage).map((entry) => entry.id), ["g", "f", "e", "d", "c", "b", "a"]);
});

test("persists product quick filter and grade family with safe fallbacks", () => {
  const storage = fakeStorage({
    [localState.PRODUCT_QUICK_FILTER_KEY]: "unknown",
    [localState.ORDERING_DRAFT_KEY]: JSON.stringify(["b", "", "a", "b"]),
  });

  assert.equal(localState.readInitialProductQuickFilter(storage), "all");
  assert.equal(localState.saveProductQuickFilter("missing_code", storage), "missing_code");
  assert.equal(storage.dump()[localState.PRODUCT_QUICK_FILTER_KEY], "missing_code");
  assert.equal(localState.readLastActiveGradeFamily(storage), "common");
  assert.deepEqual(localState.readInitialOrderingDraft(storage), ["b", "a"]);
  assert.deepEqual(localState.saveOrderingDraft(["c", "c", "a"], storage), ["c", "a"]);
  assert.deepEqual(JSON.parse(storage.dump()[localState.ORDERING_DRAFT_KEY]), ["c", "a"]);

  localState.saveLastActiveGradeFamily("adulto", storage);
  localState.clearOrderingDraft(storage);

  assert.equal(localState.readLastActiveGradeFamily(storage), "adulto");
  assert.deepEqual(JSON.parse(storage.dump()[localState.ORDERING_DRAFT_KEY]), []);
});

test("ignores broken storage without throwing", () => {
  const brokenStorage = {
    getItem() {
      throw new Error("blocked");
    },
    setItem() {
      throw new Error("blocked");
    },
  };

  assert.deepEqual(localState.readInitialImportHistory(brokenStorage), []);
  assert.deepEqual(localState.readInitialOperationDiary(brokenStorage), []);
  assert.equal(localState.readInitialProductQuickFilter(brokenStorage), "all");
  assert.deepEqual(localState.readInitialOrderingDraft(brokenStorage), []);
  assert.doesNotThrow(() => localState.saveRecentImportHistory([historyEntry], brokenStorage));
  assert.doesNotThrow(() => localState.saveOrderingDraft(["a"], brokenStorage));
});
