import type { Product, ProductPayload } from "./types";

export function buildProductTemplatePayload(product: Product): ProductPayload {
  return {
    nome: product.nome,
    codigo: "",
    quantidade: 1,
    preco: product.preco,
    categoria: product.categoria,
    marca: product.marca,
    preco_final: product.preco_final ?? "",
    descricao_completa: product.descricao_completa ?? "",
    grades: product.grades?.map((item) => ({ ...item })) ?? null,
    cores: product.cores?.map((item) => ({ ...item })) ?? null,
  };
}
