import assert from "node:assert/strict";
import test from "node:test";

const editing = await import(new URL("../.tmp-tests/productEditing.js", import.meta.url));

const baseProduct = {
  nome: "Tenis Runner",
  codigo: "ABC-123",
  codigo_original: null,
  quantidade: 0,
  preco: "10,00",
  categoria: "Masculino",
  marca: "Marca X",
  preco_final: null,
  descricao_completa: null,
  ordering_key: "product-1",
  timestamp: "2026-01-01T00:00:00Z",
};

test("builds initial inline edit values without hiding zero quantity", () => {
  assert.equal(editing.getInlineEditInitialValue(baseProduct, "quantidade"), "0");
  assert.equal(editing.getInlineEditInitialValue(baseProduct, "preco_final"), "");
  assert.equal(editing.getInlineEditInitialValue({ ...baseProduct, preco_final: "13,90" }, "preco_final"), "13,90");
});

test("builds strict quantity payloads", () => {
  assert.deepEqual(editing.buildInlineEditPayload("quantidade", " 12 "), {
    ok: true,
    payload: { quantidade: 12 },
  });

  assert.deepEqual(editing.buildInlineEditPayload("quantidade", "12abc"), {
    ok: false,
    error: "Quantidade invalida.",
  });
  assert.deepEqual(editing.buildInlineEditPayload("quantidade", "4.5"), {
    ok: false,
    error: "Quantidade invalida.",
  });
  assert.deepEqual(editing.buildInlineEditPayload("quantidade", "-1"), {
    ok: false,
    error: "Quantidade invalida.",
  });
});

test("builds trimmed inline edit payloads for product text and final price fields", () => {
  assert.deepEqual(editing.buildInlineEditPayload("nome", "  Novo Nome  "), {
    ok: true,
    payload: { nome: "Novo Nome" },
  });
  assert.deepEqual(editing.buildInlineEditPayload("preco", " 19,90 "), {
    ok: true,
    payload: { preco: "19,90" },
  });
  assert.deepEqual(editing.buildInlineEditPayload("preco_final", "   "), {
    ok: true,
    payload: { preco_final: null },
  });
});

test("rejects malformed or negative inline price payloads", () => {
  assert.deepEqual(editing.buildInlineEditPayload("preco", "12,34abc"), {
    ok: false,
    error: "Preco invalido.",
  });
  assert.deepEqual(editing.buildInlineEditPayload("preco", "-1,00"), {
    ok: false,
    error: "Preco invalido.",
  });
  assert.deepEqual(editing.buildInlineEditPayload("preco_final", "abc"), {
    ok: false,
    error: "Preco invalido.",
  });
});

test("builds inline product previews without mutating the source product", () => {
  const pricePreview = editing.buildProductPreview(baseProduct, "preco", "10,00", 30);
  assert.equal(pricePreview.preco, "10,00");
  assert.equal(pricePreview.preco_final, "13,90");
  assert.equal(baseProduct.preco_final, null);

  const invalidQuantityPreview = editing.buildProductPreview(baseProduct, "quantidade", "12abc", 30);
  assert.equal(invalidQuantityPreview.quantidade, 0);

  const brandPreview = editing.buildProductPreview(baseProduct, "marca", "Marca Y", 30);
  assert.equal(brandPreview.marca, "Marca Y");
});
