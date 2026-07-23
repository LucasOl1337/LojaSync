export type OrderingItem = {
  ordering_key: string;
};

function buildValidKeySet(keys: string[]) {
  return new Set(keys);
}

export function buildOrderingKeys<T extends OrderingItem>(products: T[]) {
  return products.map((product) => product.ordering_key);
}

export function sanitizeOrderingDraft(draftKeys: string[], validKeys: string[]) {
  const valid = buildValidKeySet(validKeys);
  const seen = new Set<string>();
  const sanitized: string[] = [];
  for (const key of draftKeys) {
    if (!valid.has(key) || seen.has(key)) continue;
    seen.add(key);
    sanitized.push(key);
  }
  return sanitized;
}

export function buildDisplayedProducts<T extends OrderingItem>(products: T[], draftKeys: string[], orderingMode: boolean) {
  if (!orderingMode) {
    return products;
  }
  const productByKey = new Map<string, T>();
  for (const product of products) {
    productByKey.set(product.ordering_key, product);
  }

  const selectedKeySet = new Set<string>();
  const selectedProducts: T[] = [];
  for (const key of draftKeys) {
    const product = productByKey.get(key);
    if (!product || selectedKeySet.has(key)) continue;
    selectedKeySet.add(key);
    selectedProducts.push(product);
  }

  if (!selectedProducts.length) {
    return products;
  }

  const remainingProducts = products.filter((product) => !selectedKeySet.has(product.ordering_key));
  return [...selectedProducts, ...remainingProducts];
}

export function buildOrderingSelectionIndex<T extends OrderingItem>(products: T[], draftKeys: string[]) {
  const selectedKeys = sanitizeOrderingDraft(draftKeys, buildOrderingKeys(products));
  return new Map(selectedKeys.map((key, index) => [key, index + 1] as const));
}

export function buildFinalOrderingKeys(originalKeys: string[], draftKeys: string[]) {
  const selectedKeys = sanitizeOrderingDraft(draftKeys, originalKeys);
  const selectedKeySet = new Set(selectedKeys);
  const remainingKeys = originalKeys.filter((key) => !selectedKeySet.has(key));
  return [...selectedKeys, ...remainingKeys];
}

export function toggleOrderingKey(currentKeys: string[], orderingKey: string, options?: { allowRemove?: boolean }) {
  if (currentKeys.includes(orderingKey)) {
    if (!options?.allowRemove) {
      return currentKeys;
    }
    return currentKeys.filter((key) => key !== orderingKey);
  }
  return [...currentKeys, orderingKey];
}

export function moveOrderingKey(currentKeys: string[], orderingKey: string, direction: -1 | 1) {
  const index = currentKeys.indexOf(orderingKey);
  if (index < 0) {
    return currentKeys;
  }
  const nextIndex = Math.max(0, Math.min(currentKeys.length - 1, index + direction));
  if (nextIndex === index) {
    return currentKeys;
  }
  const next = [...currentKeys];
  const [item] = next.splice(index, 1);
  next.splice(nextIndex, 0, item);
  return next;
}

export type OrderingDragPlacement = "before" | "after";

/**
 * Reorders a full key list by dragging `sourceKey` onto `targetKey`.
 * Used by the optional drag addon while click-to-prioritize stays unchanged.
 */
export function reorderKeysByDrag(
  currentKeys: string[],
  sourceKey: string,
  targetKey: string,
  placement: OrderingDragPlacement = "before",
) {
  const source = String(sourceKey || "").trim();
  const target = String(targetKey || "").trim();
  if (!source || !target || source === target) {
    return currentKeys;
  }
  if (!currentKeys.includes(source) || !currentKeys.includes(target)) {
    return currentKeys;
  }

  const withoutSource = currentKeys.filter((key) => key !== source);
  let targetIndex = withoutSource.indexOf(target);
  if (targetIndex < 0) {
    return currentKeys;
  }
  if (placement === "after") {
    targetIndex += 1;
  }
  const next = [...withoutSource];
  next.splice(targetIndex, 0, source);
  return next;
}

/**
 * Applies a drag onto the current draft using the same visual list the user sees
 * (selected draft first, then remaining original keys).
 */
export function applyOrderingDrag(
  originalKeys: string[],
  draftKeys: string[],
  sourceKey: string,
  targetKey: string,
  placement: OrderingDragPlacement = "before",
) {
  const fullKeys = buildFinalOrderingKeys(originalKeys, draftKeys);
  return reorderKeysByDrag(fullKeys, sourceKey, targetKey, placement);
}
