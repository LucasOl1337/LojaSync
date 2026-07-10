import assert from "node:assert/strict";
import test from "node:test";

const productTemplate = await import(new URL("../.tmp-tests/productTemplate.js", import.meta.url));

function buildProduct(overrides = {}) {
  return {
    nome: "Camiseta básica",
    codigo: "CAM-01",
    codigo_original: null,
    quantidade: 5,
    preco: "20,00",
    categoria: "Feminino",
    marca: "Loja Sync",
    preco_final: "39,90",
    descricao_completa: "Algodão",
    grades: [{ tamanho: "M", quantidade: 3 }],
    cores: [{ cor: "Azul", quantidade: 5 }],
    ordering_key: "1",
    timestamp: "2026-07-09T12:00:00Z",
    ...overrides,
  };
}

test("reuses product details while resetting unique and per-entry fields", () => {
  const source = buildProduct();
  const payload = productTemplate.buildProductTemplatePayload(source);

  assert.deepEqual(payload, {
    nome: "Camiseta básica",
    codigo: "",
    quantidade: 1,
    preco: "20,00",
    categoria: "Feminino",
    marca: "Loja Sync",
    preco_final: "39,90",
    descricao_completa: "Algodão",
    grades: [{ tamanho: "M", quantidade: 3 }],
    cores: [{ cor: "Azul", quantidade: 5 }],
  });
});

test("clones grade and color collections so editing the draft cannot mutate the list", () => {
  const source = buildProduct();
  const payload = productTemplate.buildProductTemplatePayload(source);

  payload.grades[0].quantidade = 9;
  payload.cores[0].cor = "Verde";

  assert.equal(source.grades[0].quantidade, 3);
  assert.equal(source.cores[0].cor, "Azul");
});

test("turns absent optional details into form-safe empty values", () => {
  const payload = productTemplate.buildProductTemplatePayload(buildProduct({
    preco_final: null,
    descricao_completa: null,
    grades: undefined,
    cores: null,
  }));

  assert.equal(payload.preco_final, "");
  assert.equal(payload.descricao_completa, "");
  assert.equal(payload.grades, null);
  assert.equal(payload.cores, null);
});
