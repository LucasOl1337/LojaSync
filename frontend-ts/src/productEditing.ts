import { calculateSalePricePreview, parseNonNegativePriceInput } from "./productPricing.js";
import type { Product, ProductPayload } from "./types";

export type EditableField = "nome" | "marca" | "codigo" | "quantidade" | "preco" | "preco_final" | "categoria";

export type InlineEditPayloadResult =
  | { ok: true; payload: Partial<ProductPayload> }
  | { ok: false; error: string };

const INVALID_QUANTITY_ERROR = "Quantidade invalida.";
const INVALID_PRICE_ERROR = "Preco invalido.";

function parseQuantityInput(value: string) {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const quantity = Number(trimmed);
  return Number.isSafeInteger(quantity) ? quantity : null;
}

function isValidPriceInput(value: string) {
  return parseNonNegativePriceInput(value) != null;
}

export function getInlineEditInitialValue(product: Product, field: EditableField) {
  if (field === "preco_final") {
    return product.preco_final ?? "";
  }

  const value = product[field];
  return value == null ? "" : String(value);
}

export function buildProductPreview(
  product: Product,
  field: EditableField,
  rawValue: string,
  marginPercentual: number,
): Product {
  const next = { ...product };

  if (field === "quantidade") {
    next.quantidade = parseQuantityInput(rawValue) ?? 0;
    return next;
  }

  if (field === "preco") {
    next.preco = rawValue;
    next.preco_final = calculateSalePricePreview(rawValue, marginPercentual);
    return next;
  }

  if (field === "preco_final") {
    next.preco_final = rawValue;
    return next;
  }

  if (field === "nome") next.nome = rawValue;
  if (field === "marca") next.marca = rawValue;
  if (field === "codigo") next.codigo = rawValue;
  if (field === "categoria") next.categoria = rawValue;
  return next;
}

export function buildInlineEditPayload(field: EditableField, value: string): InlineEditPayloadResult {
  const trimmed = value.trim();

  if (field === "quantidade") {
    const quantity = parseQuantityInput(value);
    if (quantity == null) {
      return { ok: false, error: INVALID_QUANTITY_ERROR };
    }
    return { ok: true, payload: { quantidade: quantity } };
  }

  if (field === "preco_final") {
    if (trimmed && !isValidPriceInput(trimmed)) {
      return { ok: false, error: INVALID_PRICE_ERROR };
    }
    return { ok: true, payload: { preco_final: trimmed || null } };
  }

  if (field === "preco") {
    if (!isValidPriceInput(trimmed)) {
      return { ok: false, error: INVALID_PRICE_ERROR };
    }
    return { ok: true, payload: { preco: trimmed } };
  }

  if (field === "nome") {
    return { ok: true, payload: { nome: trimmed } };
  }

  if (field === "marca") {
    return { ok: true, payload: { marca: trimmed } };
  }

  if (field === "codigo") {
    return { ok: true, payload: { codigo: trimmed } };
  }

  return { ok: true, payload: { categoria: trimmed } };
}
