import assert from "node:assert/strict";
import test from "node:test";

const cleanup = await import(new URL("../.tmp-tests/descriptionCleanup.js", import.meta.url));

const baseProduct = {
  nome: "Produto",
  codigo: "123",
  codigo_original: null,
  quantidade: 1,
  preco: "10,00",
  categoria: "Feminino",
  marca: "",
  preco_final: null,
  descricao_completa: null,
  grades: null,
  cores: null,
  source_type: null,
  import_batch_id: null,
  import_source_name: null,
  pending_grade_import: false,
  ordering_key: "base",
  timestamp: "2026-06-19",
};

test("parses description removal terms from commas and line breaks", () => {
  assert.deepEqual(
    cleanup.parseDescriptionRemovalTerms(" OGPT, use experience\nOGPT\n  REF "),
    ["OGPT", "use experience", "REF"],
  );
});

test("adds and removes description removal terms without duplicating existing entries", () => {
  assert.equal(
    cleanup.addDescriptionRemovalTerm("OGPT, USE EXPERIENCE", "ogpt"),
    "OGPT, USE EXPERIENCE",
  );
  assert.equal(
    cleanup.addDescriptionRemovalTerm("OGPT", "USE EXPERIENCE"),
    "OGPT, USE EXPERIENCE",
  );
  assert.equal(
    cleanup.removeDescriptionRemovalTerm("OGPT, USE EXPERIENCE, REF", "use experience"),
    "OGPT, REF",
  );
});

test("suggests suspicious repeated description terms from the current product list", () => {
  const products = [
    { ...baseProduct, ordering_key: "1", nome: "CALCA ENT POCKETS SLIM OGPT", marca: "K2B" },
    { ...baseProduct, ordering_key: "2", nome: "CALCA BOLSO FACA TRAD ESSENCIA", marca: "" },
    { ...baseProduct, ordering_key: "3", nome: "BERMUDA BOXER LONGA BOLSO FACA USE EXPERIENCE", marca: "" },
    { ...baseProduct, ordering_key: "4", nome: "CALCA ENT POCKETS SLIM OGPT", marca: "" },
    { ...baseProduct, ordering_key: "5", nome: "TOP NADADOR USE EXPERIENCE", marca: "K2B" },
    { ...baseProduct, ordering_key: "6", nome: "JAQUETA K2B", marca: "K2B" },
  ];

  const suggestions = cleanup.buildDescriptionCleanupSuggestions(products, "");
  const terms = suggestions.map((suggestion) => suggestion.term);

  assert.ok(terms.includes("OGPT"));
  assert.ok(terms.includes("USE EXPERIENCE"));
  assert.ok(!terms.includes("K2B"));
  assert.equal(suggestions.find((suggestion) => suggestion.term === "OGPT").count, 2);
});

test("hides terms that are already selected from suggestions", () => {
  const products = [
    { ...baseProduct, ordering_key: "1", nome: "CALCA ENT POCKETS SLIM OGPT" },
    { ...baseProduct, ordering_key: "2", nome: "CALCA ENT POCKETS SLIM OGPT" },
  ];

  assert.ok(
    cleanup.buildDescriptionCleanupSuggestions(products, "OGPT")
      .every((suggestion) => suggestion.term !== "OGPT"),
  );
});

test("suggests repeated stray trailing model letters from the current product list", () => {
  const products = [
    { ...baseProduct, ordering_key: "1", nome: "CALCA 5 POCKETS SLIM CONCEPT J" },
    { ...baseProduct, ordering_key: "2", nome: "CALCA 5 POCKETS SLIM CONCEPT J" },
    { ...baseProduct, ordering_key: "3", nome: "CALCA 5 POCKETS SLIM CONCEPT J" },
    { ...baseProduct, ordering_key: "4", nome: "CALCA 5 POCKETS SLIM CONCEPT J" },
    { ...baseProduct, ordering_key: "5", nome: "CALCA 5 POCKETS SLIM CONCEPT J" },
    { ...baseProduct, ordering_key: "6", nome: "CONJUNTO BLUSA E SAIA" },
    { ...baseProduct, ordering_key: "7", nome: "CONJUNTO BLUSA E SAIA" },
  ];

  const suggestions = cleanup.buildDescriptionCleanupSuggestions(products, "");
  const terms = suggestions.map((suggestion) => suggestion.term);

  assert.ok(terms.includes("J"));
  assert.ok(terms.includes("CONCEPT J"));
  assert.ok(!terms.includes("E"));
  assert.equal(suggestions.find((suggestion) => suggestion.term === "J").count, 5);
});
