import type { Product } from "./types";

export const PRODUCT_CSV_HEADERS = [
  "Nome",
  "Código",
  "Quantidade",
  "Preço de custo",
  "Preço de venda",
  "Categoria",
  "Marca",
  "Grade",
  "Cores",
  "Descrição",
] as const;

function protectSpreadsheetFormula(value: string) {
  return /^[\s]*[=+\-@]/.test(value) ? `'${value}` : value;
}

function serializeCsvCell(value: string | number | null | undefined) {
  const text = protectSpreadsheetFormula(String(value ?? ""));
  return `"${text.replace(/"/g, '""')}"`;
}

function formatGrade(product: Product) {
  return (product.grades ?? [])
    .filter((item) => item.tamanho.trim())
    .map((item) => `${item.tamanho.trim()}: ${item.quantidade}`)
    .join(" | ");
}

function formatColors(product: Product) {
  return (product.cores ?? [])
    .filter((item) => item.cor.trim())
    .map((item) => `${item.cor.trim()}: ${item.quantidade}`)
    .join(" | ");
}

export function buildProductCsv(products: Product[]) {
  const rows = products.map((product) => [
    product.nome,
    product.codigo,
    product.quantidade,
    product.preco,
    product.preco_final,
    product.categoria,
    product.marca,
    formatGrade(product),
    formatColors(product),
    product.descricao_completa,
  ]);

  return `\uFEFF${[PRODUCT_CSV_HEADERS, ...rows]
    .map((row) => row.map(serializeCsvCell).join(";"))
    .join("\r\n")}`;
}

export function buildProductCsvFilename(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `lojasync-produtos-${year}-${month}-${day}.csv`;
}
