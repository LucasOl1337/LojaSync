import { parseNonNegativePriceInput } from "./productPricing.js";
import type { ProductPayload } from "./types";

export type ProductFormField = "nome" | "codigo" | "quantidade" | "preco";

export type CreateProductPayloadResult =
  | { ok: true; payload: ProductPayload }
  | { ok: false; missing: ProductFormField };

function parseNonNegativeInteger(value: unknown) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return 0;
  }
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const quantity = Number(trimmed);
  return Number.isSafeInteger(quantity) ? quantity : null;
}

export function normalizeProductQuantityInput(value: unknown) {
  return parseNonNegativeInteger(value) ?? 0;
}

export function buildProductFormFieldOrder(simpleModeEnabled: boolean): ProductFormField[] {
  const order: ProductFormField[] = ["nome"];
  if (!simpleModeEnabled) {
    order.push("codigo");
  }
  order.push("quantidade", "preco");
  return order;
}

export function getNextProductFormField(current: ProductFormField | null | string, simpleModeEnabled: boolean): ProductFormField | null {
  const order = buildProductFormFieldOrder(simpleModeEnabled);
  if (!current) {
    return order[0] ?? null;
  }
  const currentIndex = order.indexOf(current as ProductFormField);
  if (currentIndex < 0) {
    return order[0] ?? null;
  }
  return order[currentIndex + 1] ?? null;
}

function isValidProductPrice(value: unknown) {
  return parseNonNegativePriceInput(String(value ?? "")) != null;
}

export function findFirstMissingProductField(form: Pick<ProductPayload, "nome" | "codigo" | "quantidade" | "preco">, simpleModeEnabled: boolean): ProductFormField | null {
  if (!String(form.nome || "").trim()) {
    return "nome";
  }
  if (!simpleModeEnabled && !String(form.codigo || "").trim()) {
    return "codigo";
  }
  const quantityValue = parseNonNegativeInteger(form.quantidade);
  if (quantityValue == null || quantityValue < 1) {
    return "quantidade";
  }
  if (!isValidProductPrice(form.preco)) {
    return "preco";
  }
  return null;
}

export function buildCreateProductPayload(form: ProductPayload, simpleModeEnabled: boolean): CreateProductPayloadResult {
  const missing = findFirstMissingProductField(form, simpleModeEnabled);
  if (missing) {
    return { ok: false, missing };
  }

  return {
    ok: true,
    payload: {
      ...form,
      codigo: simpleModeEnabled ? "" : form.codigo,
      marca: "",
      categoria: "",
      quantidade: normalizeProductQuantityInput(form.quantidade),
      preco: String(form.preco || "").trim(),
    },
  };
}
