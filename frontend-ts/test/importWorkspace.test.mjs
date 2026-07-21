import test from "node:test";
import assert from "node:assert/strict";

import {
  buildAutomaticImportLayout,
  buildImportBatchSummary,
  clampImportRect,
  createStagedImportDocuments,
  detectImportPreviewKind,
  extractImportFailureReasons,
} from "../.tmp-tests/importWorkspace.js";

const documentState = (state, totalItems = 0) => ({
  id: state,
  file: { name: `${state}.pdf`, size: 1, lastModified: 1, type: "application/pdf" },
  previewKind: "pdf",
  rect: { x: 0, y: 0, width: 1, height: 1 },
  zIndex: 1,
  state,
  importMode: null,
  status: null,
  result: state === "succeeded" ? { total_itens: totalItems } : null,
  error: null,
  errorReasons: [],
});

test("detects preview kind by MIME and extension fallback", () => {
  assert.equal(detectImportPreviewKind({ name: "nota.bin", type: "application/pdf" }), "pdf");
  assert.equal(detectImportPreviewKind({ name: "foto.JPEG", type: "" }), "image");
  assert.equal(detectImportPreviewKind({ name: "romaneio.txt", type: "" }), "text");
  assert.equal(detectImportPreviewKind({ name: "dados.csv", type: "" }), "unsupported");
});

test("one document fills the workspace", () => {
  assert.deepEqual(buildAutomaticImportLayout(1), [{ x: 0, y: 0, width: 1, height: 1 }]);
});

test("stages unique files and appends new selections", () => {
  const first = { name: "nota-a.pdf", size: 10, lastModified: 1, type: "application/pdf" };
  const duplicate = { ...first };
  const second = { name: "nota-b.txt", size: 20, lastModified: 2, type: "text/plain" };
  const initial = createStagedImportDocuments([first, duplicate]);
  const appended = createStagedImportDocuments([duplicate, second], initial);

  assert.equal(initial.length, 1);
  assert.equal(appended.length, 2);
  assert.equal(appended[0].id, initial[0].id);
  assert.equal(appended[1].previewKind, "text");
  assert.equal(appended[1].importMode, null);
});

test("two documents split into equal columns", () => {
  const layout = buildAutomaticImportLayout(2);
  assert.equal(layout.length, 2);
  assert.equal(layout[0].height, 1);
  assert.equal(layout[0].width, layout[1].width);
  assert.ok(layout[1].x > layout[0].width);
});

test("three documents use a large left sheet and stacked right sheets", () => {
  const layout = buildAutomaticImportLayout(3);
  assert.equal(layout[0].height, 1);
  assert.equal(layout[1].width, layout[2].width);
  assert.ok(layout[2].y > layout[1].y);
});

test("larger collections form a bounded balanced grid", () => {
  const layout = buildAutomaticImportLayout(7);
  assert.equal(layout.length, 7);
  for (const rect of layout) {
    assert.ok(rect.x >= 0 && rect.y >= 0);
    assert.ok(rect.x + rect.width <= 1.000001);
    assert.ok(rect.y + rect.height <= 1.000001);
  }
});

test("movement and resize rectangles stay inside the workspace", () => {
  assert.deepEqual(clampImportRect({ x: -1, y: 2, width: 0.05, height: 4 }, 0.2, 0.25), {
    x: 0,
    y: 0,
    width: 0.2,
    height: 1,
  });
});

test("maps structured and legacy validation reasons to Portuguese", () => {
  assert.deepEqual(extractImportFailureReasons({ final_validation_reason_codes: ["product_total_mismatch"] }), [
    "A soma dos produtos extraídos não confere com o total de produtos impresso na nota.",
  ]);
  assert.deepEqual(extractImportFailureReasons({ final_validation_reasons: ["the extracted quantity does not match the remessa quantity"] }), [
    "A quantidade extraída não confere com a quantidade da remessa.",
  ]);
  assert.deepEqual(extractImportFailureReasons({}, "Falha específica"), ["Falha específica"]);
});

test("summarizes partial batches without hiding successful mutations", () => {
  const summary = buildImportBatchSummary([documentState("succeeded", 8), documentState("failed")]);
  assert.equal(summary.succeeded, 1);
  assert.equal(summary.failed, 1);
  assert.equal(summary.totalItems, 8);
  assert.match(summary.message, /1 de 2 documentos importados/);
});
