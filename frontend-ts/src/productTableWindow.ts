export const PRODUCT_TABLE_WINDOW_SIZE = 100;

export type ProductTableWindow<TItem> = {
  visibleItems: TItem[];
  startIndex: number;
  visibleCount: number;
  hiddenCount: number;
  nextVisibleCount: number;
  hasMore: boolean;
};

function normalizePositiveInteger(value: number, fallback: number): number {
  if (!Number.isFinite(value) || value <= 0) {
    return fallback;
  }

  return Math.max(1, Math.trunc(value));
}

export function buildProductTableWindow<TItem>(
  items: TItem[],
  requestedVisibleCount: number,
  step = PRODUCT_TABLE_WINDOW_SIZE,
  anchorIndex: number | null = null,
): ProductTableWindow<TItem> {
  const normalizedStep = normalizePositiveInteger(step, PRODUCT_TABLE_WINDOW_SIZE);
  const normalizedRequestedCount = normalizePositiveInteger(requestedVisibleCount, normalizedStep);
  const visibleCount = Math.min(items.length, Math.max(normalizedStep, normalizedRequestedCount));
  const hiddenCount = items.length - visibleCount;
  const normalizedAnchorIndex = anchorIndex !== null && Number.isFinite(anchorIndex)
    ? Math.trunc(anchorIndex)
    : -1;
  const startIndex = normalizedAnchorIndex >= visibleCount && normalizedAnchorIndex < items.length
    ? Math.min(items.length - visibleCount, Math.max(0, normalizedAnchorIndex - Math.floor(visibleCount / 2)))
    : 0;

  return {
    visibleItems: hiddenCount > 0 ? items.slice(startIndex, startIndex + visibleCount) : items,
    startIndex,
    visibleCount,
    hiddenCount,
    nextVisibleCount: Math.min(items.length, visibleCount + normalizedStep),
    hasMore: hiddenCount > 0,
  };
}
