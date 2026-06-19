import assert from "node:assert/strict";
import test from "node:test";

const logic = await import(new URL("../.tmp-tests/gradeLogic.js", import.meta.url));

test("normalizes grade labels consistently", () => {
  assert.equal(logic.normalizeGradeSizeLabel(" P/M "), "PM");
  assert.equal(logic.normalizeGradeSizeLabel("003"), "3");
  assert.equal(logic.normalizeGradeSizeLabel(""), "");
});

test("orders slash sizes before extended letter sizes", () => {
  const ordered = ["XG", "M/G", "P/M", "GG"].sort(logic.compareGradeSizeLabels);

  assert.deepEqual(ordered, ["GG", "P/M", "M/G", "XG"]);
});

test("builds visual grade order from config, catalog, and product sizes", () => {
  const order = logic.buildVisualSizeOrder(
    { ui_size_order: ["M/G"], erp_size_order: ["P/M"] },
    ["XG"],
    [{ quantidade: 4, grades: [{ tamanho: "GG", quantidade: 1 }] }],
  );

  assert.deepEqual(order, ["GG", "PM", "MG", "XG"]);
});

test("keeps only products with mismatched saved grade totals", () => {
  const incomplete = logic.getIncompleteGradeProducts([
    { ordering_key: "ok", quantidade: 2, grades: [{ tamanho: "P", quantidade: 2 }] },
    { ordering_key: "missing", quantidade: 3, grades: [] },
    { ordering_key: "partial", quantidade: 3, grades: [{ tamanho: "P", quantidade: 1 }] },
  ]);

  assert.deepEqual(
    incomplete.map((item) => [item.product.ordering_key, item.total, item.expected]),
    [["partial", 1, 3]],
  );
});

test("builds grade product status for missing, partial, overflow and complete grades", () => {
  assert.deepEqual(logic.buildGradeProductStatus({ quantidade: 4, grades: [] }), {
    total: 0,
    expected: 4,
    difference: 4,
    complete: false,
    hasAny: false,
    overflow: false,
    pending: true,
    status: "missing",
    label: "Faltam 4 peças",
    tone: "warning",
  });

  assert.deepEqual(logic.buildGradeProductStatus({ quantidade: 4, grades: [{ tamanho: "P", quantidade: 2 }] }), {
    total: 2,
    expected: 4,
    difference: 2,
    complete: false,
    hasAny: true,
    overflow: false,
    pending: true,
    status: "under",
    label: "Faltam 2 peças",
    tone: "warning",
  });

  assert.deepEqual(logic.buildGradeProductStatus({ quantidade: 4, grades: [{ tamanho: "P", quantidade: 6 }] }), {
    total: 6,
    expected: 4,
    difference: -2,
    complete: false,
    hasAny: true,
    overflow: true,
    pending: true,
    status: "over",
    label: "Sobraram 2 peças",
    tone: "danger",
  });

  assert.deepEqual(logic.buildGradeProductStatus({ quantidade: 4, grades: [{ tamanho: "P", quantidade: 4 }] }), {
    total: 4,
    expected: 4,
    difference: 0,
    complete: true,
    hasAny: true,
    overflow: false,
    pending: false,
    status: "complete",
    label: "Grade fecha",
    tone: "success",
  });
});

test("finds the next pending grade key in circular product order", () => {
  const products = [
    { ordering_key: "a", quantidade: 2, grades: [{ tamanho: "P", quantidade: 2 }] },
    { ordering_key: "b", quantidade: 3, grades: [] },
    { ordering_key: "c", quantidade: 4, grades: [{ tamanho: "P", quantidade: 1 }] },
    { ordering_key: "d", quantidade: 1, grades: [{ tamanho: "P", quantidade: 1 }] },
  ];

  assert.equal(logic.findNextPendingGradeKey(products, "a"), "b");
  assert.equal(logic.findNextPendingGradeKey(products, "b"), "c");
  assert.equal(logic.findNextPendingGradeKey(products, "c"), "b");
  assert.equal(logic.findNextPendingGradeKey(products, "b", "b"), "c");
  assert.equal(logic.findNextPendingGradeKey([{ ordering_key: "ok", quantidade: 1, grades: [{ tamanho: "P", quantidade: 1 }] }], "ok"), null);
});

test("normalizes UI family drafts and assigns ungrouped fallback sizes", () => {
  const families = logic.normalizeUiFamiliesDraft(
    [{ id: " Main ", label: " Principal ", sizes: ["P", "p", "M/G"] }],
    ["P", "M/G", "40"],
  );

  assert.deepEqual(families, [
    { id: "main", label: "Principal", sizes: ["P", "MG"] },
    { id: "special", label: "Especiais", sizes: ["40"] },
  ]);
});

test("parses typed size order text with normalized unique sizes", () => {
  assert.deepEqual(logic.parseSizeOrderText("P/M, m/g; 003\nP/M"), ["PM", "MG", "3"]);
});

test("normalizes grade config state and drops invalid capture points", () => {
  const config = logic.normalizeGradeConfigState({
    buttons: {
      modelos: { x: "10", y: "20" },
      invalid: { x: "abc", y: 20 },
    },
    first_quant_cell: { x: "30", y: "40" },
    second_quant_cell: { x: "oops", y: 50 },
    row_height: "-10",
    model_index: "2",
    model_hotkey: 5,
    erp_size_order: ["P/M", "p/m", "003", ""],
    ui_size_order: ["M/G", "GG"],
    ui_families: [
      { id: " Principal ", label: " Principal ", sizes: ["P", "p", "M/G"] },
      { id: "", label: "", sizes: [] },
    ],
    ui_family_version: "2",
  });

  assert.deepEqual(config.buttons, { modelos: { x: 10, y: 20 } });
  assert.deepEqual(config.first_quant_cell, { x: 30, y: 40 });
  assert.equal(config.second_quant_cell, null);
  assert.equal(config.row_height, null);
  assert.equal(config.model_index, 2);
  assert.equal(config.model_hotkey, "5");
  assert.deepEqual(config.erp_size_order, ["PM", "3"]);
  assert.deepEqual(config.ui_size_order, ["MG", "GG"]);
  assert.deepEqual(config.ui_families, [
    { id: "principal", label: "Principal", sizes: ["P", "MG"] },
    { id: "family-2", label: "Família 2", sizes: [] },
  ]);
  assert.equal(config.ui_family_version, 2);
});
