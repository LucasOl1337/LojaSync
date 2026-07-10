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
  const productByKey = new Map(products.map((product) => [product.ordering_key, product] as const));
  const originalKeys = buildOrderingKeys(products);
  const selectedKeys = sanitizeOrderingDraft(draftKeys, originalKeys);
  const selectedKeySet = new Set(selectedKeys);
  const remainingKeys = originalKeys.filter((key) => !selectedKeySet.has(key));
  return [...selectedKeys, ...remainingKeys].map((key) => productByKey.get(key)).filter((product): product is T => Boolean(product));
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
