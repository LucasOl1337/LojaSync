import assert from "node:assert/strict";
import test from "node:test";

const overview = await import(new URL("../.tmp-tests/catalogOverview.js", import.meta.url));

const baseProduct = {
  nome: "Camiseta",
  codigo: "A-1",
  codigo_original: null,
  quantidade: 2,
  preco: "10,00",
  categoria: "Feminino",
  marca: "Solira",
  preco_final: "15,00",
  descricao_completa: null,
  grades: null,
  cores: null,
  source_type: "manual",
  import_batch_id: null,
  import_source_name: null,
  pending_grade_import: false,
  ordering_key: "a",
  timestamp: "2026-07-09T12:00:00Z",
};

test("builds commercial totals and readiness from the active catalog", () => {
  const result = overview.buildCatalogOverview([
    baseProduct,
    {
      ...baseProduct,
      nome: "Calça",
      ordering_key: "b",
      quantidade: 3,
      preco: "20,00",
      preco_final: "30,00",
      codigo: "",
      marca: "",
      pending_grade_import: true,
    },
  ], 20);

  assert.deepEqual({
    totalProducts: result.totalProducts,
    totalUnits: result.totalUnits,
    costValue: result.costValue,
    saleValue: result.saleValue,
    grossPotential: result.grossPotential,
    grossReturnPercent: result.grossReturnPercent,
    readyCount: result.readyCount,
    reviewCount: result.reviewCount,
    readinessPercent: result.readinessPercent,
  }, {
    totalProducts: 2,
    totalUnits: 5,
    costValue: 80,
    saleValue: 120,
    grossPotential: 40,
    grossReturnPercent: 50,
    readyCount: 1,
    reviewCount: 1,
    readinessPercent: 50,
  });
});

test("orders actionable issues by affected product count", () => {
  const result = overview.buildCatalogOverview([
    { ...baseProduct, ordering_key: "a", codigo: "", marca: "" },
    { ...baseProduct, ordering_key: "b", codigo: "", pending_grade_import: true },
    { ...baseProduct, ordering_key: "c", categoria: "" },
  ], 20);

  assert.deepEqual(result.issues, [
    { filter: "missing_code", label: "Sem código", count: 2, tone: "warning" },
    { filter: "pending_grades", label: "Grades pendentes", count: 1, tone: "warning" },
    { filter: "missing_brand", label: "Sem marca", count: 1, tone: "warning" },
    { filter: "missing_category", label: "Sem categoria", count: 1, tone: "warning" },
  ]);
});

test("keeps an empty catalog neutral and avoids invalid percentages", () => {
  const result = overview.buildCatalogOverview([], 30);

  assert.equal(result.readinessPercent, 0);
  assert.equal(result.grossReturnPercent, 0);
  assert.equal(result.reviewCount, 0);
  assert.deepEqual(result.issues, []);
});
