import assert from "node:assert/strict";
import test from "node:test";

const productExport = await import(new URL("../.tmp-tests/productExport.js", import.meta.url));

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
    grades: [{ tamanho: "M", quantidade: 3 }, { tamanho: "G", quantidade: 2 }],
    cores: [{ cor: "Azul", quantidade: 5 }],
    ordering_key: "1",
    timestamp: "2026-07-09T12:00:00Z",
    ...overrides,
  };
}

test("exports the operational product fields as Excel-friendly semicolon CSV", () => {
  const csv = productExport.buildProductCsv([buildProduct()]);
  const lines = csv.slice(1).split("\r\n");

  assert.equal(csv.charCodeAt(0), 0xfeff);
  assert.equal(lines.length, 2);
  assert.equal(lines[0], '"Nome";"Código";"Quantidade";"Preço de custo";"Preço de venda";"Categoria";"Marca";"Grade";"Cores";"Descrição"');
  assert.equal(lines[1], '"Camiseta básica";"CAM-01";"5";"20,00";"39,90";"Feminino";"Loja Sync";"M: 3 | G: 2";"Azul: 5";"Algodão"');
});

test("escapes quotes, preserves line breaks and blocks spreadsheet formulas", () => {
  const csv = productExport.buildProductCsv([
    buildProduct({
      nome: '=HYPERLINK("https://example.invalid";"clique")',
      codigo: "+1+1",
      descricao_completa: "Linha 1\nLinha 2",
      grades: null,
      cores: [],
    }),
  ]);

  assert.match(csv, /"'=HYPERLINK\(""https:\/\/example\.invalid"";""clique""\)"/);
  assert.match(csv, /"'\+1\+1"/);
  assert.match(csv, /"Linha 1\nLinha 2"/);
  assert.match(csv, /;"";"";"Linha 1/);
});

test("builds a stable local-date filename", () => {
  assert.equal(
    productExport.buildProductCsvFilename(new Date(2026, 6, 9, 23, 30)),
    "lojasync-produtos-2026-07-09.csv",
  );
});
