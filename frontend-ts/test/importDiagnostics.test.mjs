import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const { ImportDiagnosticsPanel } = await import(new URL("../.tmp-tests/importDiagnostics.js", import.meta.url));
const { prepareImportWarnings } = await import(new URL("../.tmp-tests/importWarnings.js", import.meta.url));

test("normalizes import warnings before presenting them", () => {
  assert.deepEqual(
    prepareImportWarnings(["  Confira o total. ", "", "Confira o total.", "Revise o código do item 2."]),
    ["Confira o total.", "Revise o código do item 2."],
  );
});

test("renders every actionable warning outside the collapsed diagnostics", () => {
  const markup = renderToStaticMarkup(createElement(ImportDiagnosticsPanel, {
    validationStatus: "warning",
    chips: [],
    warnings: ["Quantidade diferente da remessa.", "Revise <SKU-2> antes de cadastrar."],
  }));

  assert.match(markup, /Revise esta importação/);
  assert.match(markup, /2 avisos/);
  assert.match(markup, /Quantidade diferente da remessa\./);
  assert.match(markup, /Revise &lt;SKU-2&gt; antes de cadastrar\./);
  assert.match(markup, /aria-live="polite"/);
});
