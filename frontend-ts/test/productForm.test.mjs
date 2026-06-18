import assert from "node:assert/strict";
import test from "node:test";

const form = await import(new URL("../.tmp-tests/productForm.js", import.meta.url));

const completeForm = {
  nome: "Bolsa Couro",
  codigo: "B-100",
  quantidade: 2,
  preco: "50,00",
  categoria: "",
  marca: "",
  preco_final: "",
  descricao_completa: "",
};

test("normalizes product quantity input to non-negative safe integers only", () => {
  assert.equal(form.normalizeProductQuantityInput("12"), 12);
  assert.equal(form.normalizeProductQuantityInput(""), 0);
  assert.equal(form.normalizeProductQuantityInput("4.5"), 0);
  assert.equal(form.normalizeProductQuantityInput("-1"), 0);
  assert.equal(form.normalizeProductQuantityInput("12abc"), 0);
});

test("finds the first missing product field and rejects fractional quantities", () => {
  assert.equal(form.findFirstMissingProductField({ ...completeForm, nome: "" }, false), "nome");
  assert.equal(form.findFirstMissingProductField({ ...completeForm, codigo: "" }, false), "codigo");
  assert.equal(form.findFirstMissingProductField({ ...completeForm, codigo: "" }, true), null);
  assert.equal(form.findFirstMissingProductField({ ...completeForm, quantidade: 4.5 }, false), "quantidade");
  assert.equal(form.findFirstMissingProductField({ ...completeForm, preco: "" }, false), "preco");
});

test("finds the price field when product cost is malformed or negative", () => {
  assert.equal(form.findFirstMissingProductField({ ...completeForm, preco: "12,34abc" }, false), "preco");
  assert.equal(form.findFirstMissingProductField({ ...completeForm, preco: "-1,00" }, false), "preco");
  assert.equal(form.findFirstMissingProductField({ ...completeForm, preco: "R$ 1.234,56" }, false), null);
});

test("builds product form field order and next-field navigation", () => {
  assert.deepEqual(form.buildProductFormFieldOrder(false), ["nome", "codigo", "quantidade", "preco"]);
  assert.deepEqual(form.buildProductFormFieldOrder(true), ["nome", "quantidade", "preco"]);

  assert.equal(form.getNextProductFormField(null, false), "nome");
  assert.equal(form.getNextProductFormField("nome", false), "codigo");
  assert.equal(form.getNextProductFormField("nome", true), "quantidade");
  assert.equal(form.getNextProductFormField("preco", false), null);
  assert.equal(form.getNextProductFormField("unknown", false), "nome");
});

test("builds create product payloads with normalized quantity and simple-mode code", () => {
  assert.deepEqual(form.buildCreateProductPayload(completeForm, false), {
    ok: true,
    payload: {
      ...completeForm,
      marca: "",
      categoria: "",
      quantidade: 2,
    },
  });

  assert.deepEqual(form.buildCreateProductPayload(completeForm, true), {
    ok: true,
    payload: {
      ...completeForm,
      codigo: "",
      marca: "",
      categoria: "",
      quantidade: 2,
    },
  });

  assert.deepEqual(form.buildCreateProductPayload({ ...completeForm, quantidade: 4.5 }, false), {
    ok: false,
    missing: "quantidade",
  });

  assert.deepEqual(form.buildCreateProductPayload({ ...completeForm, preco: "12,34abc" }, false), {
    ok: false,
    missing: "preco",
  });
});
