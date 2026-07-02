import type { Product } from "./types";

export type PriceProduct = Pick<Product, "quantidade" | "preco" | "preco_final">;

function roundMoney(value: number) {
  return Math.round(value * 100) / 100;
}

function parseTotalsQuantity(value: unknown) {
  const quantity = typeof value === "number" ? value : Number(value);
  if (!Number.isSafeInteger(quantity) || quantity < 0) {
    return 0;
  }
  return quantity;
}

function normalizePriceText(value: string) {
  const text = value.trim().replace(/^R\$\s*/i, "").replace(/\s+/g, "").replace(/\u00a0/g, "");
  if (!text || !/^-?[0-9.,]+$/.test(text)) {
    return null;
  }

  const commaCount = (text.match(/,/g) || []).length;
  const dotCount = (text.match(/\./g) || []).length;
  if (commaCount > 1) {
    return null;
  }

  if (commaCount && dotCount) {
    const lastComma = text.lastIndexOf(",");
    const lastDot = text.lastIndexOf(".");
    if (lastComma > lastDot) {
      return text.replace(/\./g, "").replace(",", ".");
    }
    return text.replace(/,/g, "");
  }

  if (commaCount) {
    return text.replace(",", ".");
  }

  if (dotCount > 1) {
    return null;
  }

  return text;
}

export function parsePriceInput(value: string | null | undefined) {
  if (!value) return null;
  const normalized = normalizePriceText(String(value));
  if (!normalized || !/^-?\d+(\.\d+)?$/.test(normalized)) {
    return null;
  }
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function parseNonNegativePriceInput(value: string | null | undefined) {
  const parsed = parsePriceInput(value);
  return parsed != null && parsed >= 0 ? parsed : null;
}

export function parsePositivePercentInput(value: string | null | undefined) {
  const parsed = parsePriceInput(value);
  return parsed != null && parsed > 0 ? parsed : null;
}

export function formatPriceInput(value: number | null) {
  if (value == null || !Number.isFinite(value)) return "";
  return value.toFixed(2).replace(".", ",");
}

export function formatPercentDisplay(value: number | null | undefined) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return "0%";
  return `${new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(numericValue)}%`;
}

export function calculateSalePricePreview(costPrice: string, marginPercentual: number) {
  const parsed = parseNonNegativePriceInput(costPrice);
  if (parsed == null) return null;
  const safeMargin = 1 + Math.max(marginPercentual, 0) / 100;
  const gross = parsed * safeMargin;
  const whole = Math.floor(gross);
  let target = whole + 0.9;
  if (target < gross) {
    target = whole + 1.9;
  }
  return formatPriceInput(target);
}

export function computeCurrentTotals(products: PriceProduct[], marginPercentual: number) {
  let quantidade = 0;
  let custo = 0;
  let venda = 0;
  for (const product of products) {
    const quantity = parseTotalsQuantity(product.quantidade);
    const cost = parseNonNegativePriceInput(product.preco) || 0;
    const sale =
      parseNonNegativePriceInput(product.preco_final || undefined) ??
      parseNonNegativePriceInput(calculateSalePricePreview(product.preco || "", marginPercentual)) ??
      0;
    quantidade += quantity;
    custo += cost * quantity;
    venda += sale * quantity;
  }
  return { quantidade, custo: roundMoney(custo), venda: roundMoney(venda) };
}
