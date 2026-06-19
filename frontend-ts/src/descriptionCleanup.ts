import type { Product } from "./types";

export type DescriptionCleanupSuggestion = {
  term: string;
  count: number;
  examples: string[];
};

const MAX_SUGGESTIONS = 8;
const TOKEN_PATTERN = /[\p{L}\p{N}]+/gu;
const LETTER_PATTERN = /[A-Za-zÀ-ÿ]/;
const DIGIT_PATTERN = /\d/;
const VOWEL_PATTERN = /[AEIOUÁÉÍÓÚÂÊÔÃÕaeiouáéíóúâêôãõ]/;

const COMMON_PRODUCT_TERMS = new Set([
  "acessorio",
  "acessorios",
  "adulto",
  "algodao",
  "azul",
  "bege",
  "bermuda",
  "blusa",
  "bolsa",
  "bolso",
  "body",
  "boxer",
  "branco",
  "calca",
  "camisa",
  "camiseta",
  "cinza",
  "conjunto",
  "couro",
  "cropped",
  "curta",
  "curto",
  "faca",
  "feminino",
  "flare",
  "infantil",
  "jaqueta",
  "jeans",
  "legging",
  "longa",
  "longo",
  "masculino",
  "pocket",
  "pockets",
  "preto",
  "regata",
  "saia",
  "short",
  "slim",
  "top",
  "vestido",
]);

const KNOWN_NOISE_TERMS = new Set([
  "cod",
  "codigo",
  "ref",
  "referencia",
  "tam",
  "tamanho",
  "un",
  "und",
]);

const TRAILING_SINGLE_LETTER_BLOCKLIST = new Set([
  "a",
  "e",
  "o",
  "u",
  "p",
  "m",
  "g",
]);

const SIZE_TOKEN_KEYS = new Set([
  "pp",
  "p",
  "m",
  "g",
  "gg",
  "xg",
  "eg",
  "exg",
  "xxg",
]);

type Candidate = {
  term: string;
  productKeys: Set<string>;
  examples: string[];
  score: number;
};

function normalizeTermKey(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function normalizeDisplayTerm(value: unknown) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

export function parseDescriptionRemovalTerms(value: string) {
  const seen = new Set<string>();
  const terms: string[] = [];
  for (const rawTerm of String(value || "").split(/[,\n]/g)) {
    const term = normalizeDisplayTerm(rawTerm);
    const key = normalizeTermKey(term);
    if (!term || seen.has(key)) continue;
    seen.add(key);
    terms.push(term);
  }
  return terms;
}

export function formatDescriptionRemovalTerms(terms: string[]) {
  const seen = new Set<string>();
  const normalizedTerms: string[] = [];
  for (const rawTerm of terms) {
    const term = normalizeDisplayTerm(rawTerm);
    const key = normalizeTermKey(term);
    if (!term || seen.has(key)) continue;
    seen.add(key);
    normalizedTerms.push(term);
  }
  return normalizedTerms.join(", ");
}

export function addDescriptionRemovalTerm(currentValue: string, term: string) {
  return formatDescriptionRemovalTerms([...parseDescriptionRemovalTerms(currentValue), term]);
}

export function removeDescriptionRemovalTerm(currentValue: string, term: string) {
  const removedKey = normalizeTermKey(term);
  return formatDescriptionRemovalTerms(
    parseDescriptionRemovalTerms(currentValue).filter((item) => normalizeTermKey(item) !== removedKey),
  );
}

function tokenizeText(text: string) {
  return Array.from(text.matchAll(TOKEN_PATTERN), (match) => match[0]).filter(Boolean);
}

function buildBrandKeys(products: Product[]) {
  const keys = new Set<string>();
  for (const product of products) {
    const brand = normalizeDisplayTerm(product.marca);
    if (!brand) continue;
    keys.add(normalizeTermKey(brand));
    for (const token of tokenizeText(brand)) {
      keys.add(normalizeTermKey(token));
    }
  }
  return keys;
}

function isAllCapsToken(token: string) {
  return token === token.toLocaleUpperCase("pt-BR") && LETTER_PATTERN.test(token);
}

function isSuspiciousToken(token: string, brandKeys: Set<string>) {
  const key = normalizeTermKey(token);
  if (key.length < 2 || brandKeys.has(key) || COMMON_PRODUCT_TERMS.has(key)) return false;
  if (KNOWN_NOISE_TERMS.has(key)) return true;

  const hasLetter = LETTER_PATTERN.test(token);
  const hasDigit = DIGIT_PATTERN.test(token);
  if (hasLetter && hasDigit) return true;

  if (!isAllCapsToken(token)) return false;
  if (token.length <= 3) return true;
  const vowelCount = Array.from(token).filter((char) => VOWEL_PATTERN.test(char)).length;
  return token.length <= 5 && vowelCount <= 1;
}

function isSuspiciousTrailingToken(token: string, brandKeys: Set<string>) {
  const key = normalizeTermKey(token);
  if (!key || brandKeys.has(key) || COMMON_PRODUCT_TERMS.has(key) || SIZE_TOKEN_KEYS.has(key)) return false;
  if (key.length === 1) {
    return isAllCapsToken(token) && !TRAILING_SINGLE_LETTER_BLOCKLIST.has(key);
  }
  return isSuspiciousToken(token, brandKeys);
}

function isUsefulSuffixPhrase(tokens: string[], brandKeys: Set<string>) {
  if (tokens.length < 2) return false;
  const phrase = tokens.join(" ");
  if (phrase.length > 36) return false;

  const keys = tokens.map(normalizeTermKey);
  if (keys.some((key) => brandKeys.has(key))) return false;
  if (keys.every((key) => COMMON_PRODUCT_TERMS.has(key))) return false;

  return tokens.some((token) => isSuspiciousToken(token, brandKeys))
    || isSuspiciousTrailingToken(tokens[tokens.length - 1] || "", brandKeys)
    || tokens.every((token, index) => isAllCapsToken(token) && keys[index].length >= 3 && !COMMON_PRODUCT_TERMS.has(keys[index]));
}

function addCandidate(
  candidates: Map<string, Candidate>,
  selectedKeys: Set<string>,
  product: Product,
  fallbackKey: string,
  rawTerm: string,
  score: number,
) {
  const term = normalizeDisplayTerm(rawTerm);
  const key = normalizeTermKey(term);
  if (!term || selectedKeys.has(key) || COMMON_PRODUCT_TERMS.has(key)) return;

  const candidate = candidates.get(key) ?? {
    term,
    productKeys: new Set<string>(),
    examples: [],
    score: 0,
  };
  candidate.productKeys.add(product.ordering_key || fallbackKey);
  candidate.score += score;

  const example = normalizeDisplayTerm(product.nome || product.descricao_completa || "");
  if (example && !candidate.examples.includes(example) && candidate.examples.length < 2) {
    candidate.examples.push(example);
  }

  candidates.set(key, candidate);
}

export function buildDescriptionCleanupSuggestions(products: Product[], selectedValue: string): DescriptionCleanupSuggestion[] {
  const selectedKeys = new Set(parseDescriptionRemovalTerms(selectedValue).map(normalizeTermKey));
  const brandKeys = buildBrandKeys(products);
  const candidates = new Map<string, Candidate>();

  products.forEach((product, index) => {
    const fallbackKey = `product-${index}`;
    const fields = [product.nome, product.descricao_completa]
      .map(normalizeDisplayTerm)
      .filter(Boolean);

    for (const field of fields) {
      const tokens = tokenizeText(field);
      tokens.forEach((token, tokenIndex) => {
        const tokenKey = normalizeTermKey(token);
        const isTrailingToken = tokenIndex === tokens.length - 1;
        if (isSuspiciousToken(token, brandKeys) || (isTrailingToken && isSuspiciousTrailingToken(token, brandKeys))) {
          addCandidate(candidates, selectedKeys, product, fallbackKey, token, KNOWN_NOISE_TERMS.has(tokenKey) ? 8 : 5);
        }
      });

      for (const size of [2, 3]) {
        const suffix = tokens.slice(-size);
        if (suffix.length === size && isUsefulSuffixPhrase(suffix, brandKeys)) {
          addCandidate(candidates, selectedKeys, product, fallbackKey, suffix.join(" "), 3);
        }
      }
    }
  });

  return Array.from(candidates.values())
    .map((candidate) => ({
      term: candidate.term,
      count: candidate.productKeys.size,
      examples: candidate.examples,
      score: candidate.score,
    }))
    .filter((candidate) => candidate.count >= 2)
    .sort((left, right) =>
      (right.count - left.count)
      || (right.score - left.score)
      || (left.term.length - right.term.length)
      || left.term.localeCompare(right.term, "pt-BR"),
    )
    .slice(0, MAX_SUGGESTIONS)
    .map(({ term, count, examples }) => ({ term, count, examples }));
}
