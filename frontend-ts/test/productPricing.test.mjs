import assert from "node:assert/strict";
import test from "node:test";

const pricing = await import(new URL("../.tmp-tests/productPricing.js", import.meta.url));

test("parses Brazilian currency text and plain decimal prices", () => {
  assert.equal(pricing.parsePriceInput("R$ 1.234,56"), 1234.56);
  assert.equal(pricing.parsePriceInput("10.50"), 10.5);
  assert.equal(pricing.parsePriceInput("  "), null);
});

test("rejects malformed price text instead of accepting parseFloat prefixes", () => {
  assert.equal(pricing.parsePriceInput("12,34abc"), null);
  assert.equal(pricing.parsePriceInput("R$ 1.234,56 extra"), null);
  assert.equal(pricing.parsePriceInput("1.234.56"), null);
});

test("formats price inputs with comma decimals", () => {
  assert.equal(pricing.formatPriceInput(12.9), "12,90");
  assert.equal(pricing.formatPriceInput(Number.NaN), "");
  assert.equal(pricing.formatPriceInput(null), "");
});

test("formats percent displays for Portuguese operator UI", () => {
  assert.equal(pricing.formatPercentDisplay(120), "120%");
  assert.equal(pricing.formatPercentDisplay(120.5), "120,5%");
  assert.equal(pricing.formatPercentDisplay(120.25), "120,25%");
  assert.equal(pricing.formatPercentDisplay(Number.NaN), "0%");
});

test("parses positive percent inputs for margin controls", () => {
  assert.equal(pricing.parsePositivePercentInput("120,5"), 120.5);
  assert.equal(pricing.parsePositivePercentInput("12.75"), 12.75);
  assert.equal(pricing.parsePositivePercentInput("0"), null);
  assert.equal(pricing.parsePositivePercentInput("-5"), null);
  assert.equal(pricing.parsePositivePercentInput("10abc"), null);
});

test("calculates sale preview using non-negative margin and .90 rounding", () => {
  assert.equal(pricing.calculateSalePricePreview("10,00", 30), "13,90");
  assert.equal(pricing.calculateSalePricePreview("10,99", 0), "11,90");
  assert.equal(pricing.calculateSalePricePreview("10,00", -20), "10,90");
  assert.equal(pricing.calculateSalePricePreview("abc", 20), null);
  assert.equal(pricing.calculateSalePricePreview("-1,00", 20), null);
});

test("computes current totals using explicit final prices or margin previews", () => {
  const totals = pricing.computeCurrentTotals(
    [
      { quantidade: 2, preco: "10,00", preco_final: "15,00" },
      { quantidade: 3, preco: "20,00", preco_final: null },
      { quantidade: 4, preco: "12,34abc", preco_final: null },
    ],
    10,
  );

  assert.deepEqual(totals, {
    quantidade: 9,
    custo: 80,
    venda: 98.7,
  });
});

test("ignores negative prices in totals and falls back to previews for invalid final prices", () => {
  const totals = pricing.computeCurrentTotals(
    [
      { quantidade: 2, preco: "-10,00", preco_final: null },
      { quantidade: 1, preco: "10,00", preco_final: "-5,00" },
    ],
    10,
  );

  assert.deepEqual(totals, {
    quantidade: 3,
    custo: 10,
    venda: 11.9,
  });
});
