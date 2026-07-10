export function prepareImportWarnings(warnings: readonly string[]): string[] {
  const seen = new Set<string>();

  return warnings.flatMap((warning) => {
    const normalized = warning.trim();
    if (!normalized || seen.has(normalized)) {
      return [];
    }
    seen.add(normalized);
    return [normalized];
  });
}
