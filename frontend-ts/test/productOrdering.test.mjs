import assert from "node:assert/strict";
import test from "node:test";

const ordering = await import(new URL("../.tmp-tests/productOrdering.js", import.meta.url));

const products = [
  { ordering_key: "a", nome: "A" },
  { ordering_key: "b", nome: "B" },
  { ordering_key: "c", nome: "C" },
];

test("returns original products outside ordering mode", () => {
  assert.equal(ordering.buildDisplayedProducts(products, ["c"], false), products);
});

test("builds displayed products from selected draft keys then remaining original order", () => {
  assert.deepEqual(
    ordering.buildDisplayedProducts(products, ["c", "missing", "a", "c"], true).map((product) => product.ordering_key),
    ["c", "a", "b"],
  );
});

test("builds ordering selection indexes from unique valid draft keys", () => {
  assert.deepEqual(
    Array.from(ordering.buildOrderingSelectionIndex(products, ["c", "missing", "a", "c"]).entries()),
    [["c", 1], ["a", 2]],
  );
});

test("builds final ordering keys without stale or duplicated draft keys", () => {
  assert.deepEqual(ordering.buildFinalOrderingKeys(["a", "b", "c"], ["c", "missing", "a", "c"]), ["c", "a", "b"]);
});

test("toggles ordering selections without accidental removal", () => {
  assert.deepEqual(ordering.toggleOrderingKey(["a"], "a"), ["a"]);
  assert.deepEqual(ordering.toggleOrderingKey(["a"], "a", { allowRemove: true }), []);
  assert.deepEqual(ordering.toggleOrderingKey(["a"], "b"), ["a", "b"]);
});

test("moves selected ordering keys within bounds", () => {
  assert.deepEqual(ordering.moveOrderingKey(["a", "b", "c"], "b", -1), ["b", "a", "c"]);
  assert.deepEqual(ordering.moveOrderingKey(["a", "b", "c"], "c", 1), ["a", "b", "c"]);
  assert.deepEqual(ordering.moveOrderingKey(["a", "b", "c"], "missing", -1), ["a", "b", "c"]);
});

test("reorders keys by drag before and after the target", () => {
  assert.deepEqual(ordering.reorderKeysByDrag(["a", "b", "c", "d"], "d", "b", "before"), ["a", "d", "b", "c"]);
  assert.deepEqual(ordering.reorderKeysByDrag(["a", "b", "c", "d"], "a", "c", "after"), ["b", "c", "a", "d"]);
  assert.deepEqual(ordering.reorderKeysByDrag(["a", "b", "c"], "a", "a", "before"), ["a", "b", "c"]);
  assert.deepEqual(ordering.reorderKeysByDrag(["a", "b", "c"], "missing", "b", "before"), ["a", "b", "c"]);
});

test("applies ordering drag using the visible final key list", () => {
  // Draft prioritizes c then a; remaining original is b → visible [c, a, b]
  assert.deepEqual(
    ordering.applyOrderingDrag(["a", "b", "c"], ["c", "a"], "b", "c", "before"),
    ["b", "c", "a"],
  );
  assert.deepEqual(
    ordering.applyOrderingDrag(["a", "b", "c"], ["c"], "a", "c", "after"),
    ["c", "a", "b"],
  );
});
