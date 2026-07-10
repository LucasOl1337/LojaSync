import assert from "node:assert/strict";
import test from "node:test";

const tableWindow = await import(new URL("../.tmp-tests/productTableWindow.js", import.meta.url));

test("limits the initial table render while preserving the original order", () => {
  const products = Array.from({ length: 20_000 }, (_, index) => `product-${index}`);
  const result = tableWindow.buildProductTableWindow(products, tableWindow.PRODUCT_TABLE_WINDOW_SIZE);

  assert.equal(result.visibleCount, 100);
  assert.equal(result.startIndex, 0);
  assert.equal(result.hiddenCount, 19_900);
  assert.equal(result.nextVisibleCount, 200);
  assert.equal(result.hasMore, true);
  assert.equal(result.visibleItems[0], "product-0");
  assert.equal(result.visibleItems.at(-1), "product-99");
});

test("expands the table by one stable window at a time", () => {
  const products = Array.from({ length: 250 }, (_, index) => index);
  const result = tableWindow.buildProductTableWindow(products, 200);

  assert.deepEqual(result.visibleItems, products.slice(0, 200));
  assert.equal(result.hiddenCount, 50);
  assert.equal(result.nextVisibleCount, 250);
});

test("keeps a distant automation item inside a bounded render window", () => {
  const products = Array.from({ length: 2_000 }, (_, index) => `product-${index}`);
  const result = tableWindow.buildProductTableWindow(products, 100, 100, 995);

  assert.equal(result.visibleCount, 100);
  assert.equal(result.startIndex, 945);
  assert.equal(result.visibleItems[0], "product-945");
  assert.equal(result.visibleItems.at(-1), "product-1044");
  assert.equal(result.visibleItems.includes("product-995"), true);
});

test("returns the original array when the complete result fits in the window", () => {
  const products = Array.from({ length: 80 }, (_, index) => index);
  const result = tableWindow.buildProductTableWindow(products, 100);

  assert.equal(result.visibleItems, products);
  assert.equal(result.startIndex, 0);
  assert.equal(result.visibleCount, 80);
  assert.equal(result.hiddenCount, 0);
  assert.equal(result.hasMore, false);
});

test("clamps invalid and oversized requests safely", () => {
  const products = Array.from({ length: 150 }, (_, index) => index);

  assert.equal(tableWindow.buildProductTableWindow(products, Number.NaN).visibleCount, 100);
  assert.equal(tableWindow.buildProductTableWindow(products, 10_000).visibleCount, 150);
  assert.equal(tableWindow.buildProductTableWindow([], 100).visibleCount, 0);
});
