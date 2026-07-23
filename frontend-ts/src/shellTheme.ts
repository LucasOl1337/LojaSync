/**
 * Customizable UI color tokens + opacities for LojaSync.
 * Personal browser theme + named templates (localStorage).
 */

export const LS_THEME_COLORS = "lojasync-shell-theme-colors";
export const LS_THEME_OPACITIES = "lojasync-shell-theme-opacities";
export const LS_THEME_TEMPLATES = "lojasync-shell-theme-templates";

export type ThemeColorKey =
  | "accent"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "violet"
  | "surface"
  | "text"
  | "navActive"
  | "toolOrder"
  | "toolSets"
  | "toolJoin"
  | "toolMargin"
  | "toolBrands"
  | "badgeBrand"
  | "badgeCategory"
  | "tableRowEven"
  | "tableRowHover"
  | "tableNameGap";

export type ThemeOpacityKey =
  | "tools"
  | "toolsDisabled"
  | "badges"
  | "tableStripe"
  | "tableHover";

export type ThemeColors = Record<ThemeColorKey, string>;
export type ThemeOpacities = Record<ThemeOpacityKey, number>;

export type ThemeTemplate = {
  id: string;
  name: string;
  colors: ThemeColors;
  opacities: ThemeOpacities;
  savedAt: number;
};

export const THEME_COLOR_META: Array<{ key: ThemeColorKey; label: string; group: string; hint: string }> = [
  { key: "accent", label: "Destaque", group: "Sistema", hint: "Links, foco e acento principal" },
  { key: "primary", label: "Primário", group: "Sistema", hint: "Botões principais (ex.: Novo produto)" },
  { key: "success", label: "Sucesso", group: "Sistema", hint: "Estados ok e confirmações positivas" },
  { key: "warning", label: "Alerta", group: "Sistema", hint: "Avisos e pendências" },
  { key: "danger", label: "Perigo", group: "Sistema", hint: "Ações destrutivas" },
  { key: "violet", label: "Violeta", group: "Sistema", hint: "Acentos secundários" },
  { key: "surface", label: "Superfície", group: "Base", hint: "Painéis e cartões" },
  { key: "text", label: "Texto", group: "Base", hint: "Texto principal da interface" },
  { key: "navActive", label: "Nav ativa", group: "Navegação", hint: "Item selecionado da barra lateral" },
  { key: "toolOrder", label: "Ordenar", group: "Ferramentas", hint: "Botão Ordenar" },
  { key: "toolSets", label: "Conjuntos", group: "Ferramentas", hint: "Botão Conjuntos" },
  { key: "toolJoin", label: "Juntar", group: "Ferramentas", hint: "Botão Juntar repetidos" },
  { key: "toolMargin", label: "Margem", group: "Ferramentas", hint: "Botão Alterar margem" },
  { key: "toolBrands", label: "Marcas", group: "Ferramentas", hint: "Botão Marcas (cadastro e aplicação)" },
  { key: "badgeBrand", label: "Badge marca", group: "Catálogo / lista", hint: "Pílula Sem marca / status de marca" },
  { key: "badgeCategory", label: "Badge categoria", group: "Catálogo / lista", hint: "Pílula Sem categoria" },
  { key: "tableRowEven", label: "Linha zebra", group: "Catálogo / lista", hint: "Cor base das linhas pares da tabela" },
  { key: "tableRowHover", label: "Linha hover", group: "Catálogo / lista", hint: "Destaque ao passar o mouse na linha" },
  { key: "tableNameGap", label: "Fundo do nome", group: "Catálogo / lista", hint: "Área da coluna Nome (espaço vazio da célula)" },
];

export const THEME_OPACITY_META: Array<{ key: ThemeOpacityKey; label: string; hint: string; min: number; max: number }> = [
  { key: "tools", label: "Opacidade dos botões de ferramenta", hint: "Ordenar, Conjuntos, Margem, etc.", min: 0.35, max: 1 },
  { key: "toolsDisabled", label: "Opacidade de botões desativados", hint: "Ex.: Sem grades automáticas", min: 0.2, max: 0.85 },
  { key: "badges", label: "Opacidade das pílulas da lista", hint: "Sem marca / Sem categoria", min: 0.25, max: 1 },
  { key: "tableStripe", label: "Opacidade da zebra da lista", hint: "Intensidade do fundo das linhas pares", min: 0, max: 0.35 },
  { key: "tableHover", label: "Opacidade do hover da lista", hint: "Intensidade do destaque ao passar o mouse", min: 0.02, max: 0.35 },
];

/**
 * Profissional — default project palette (clareza v5).
 * Glass panels stay soft; essential buttons use bright solid tints so tools scan clearly.
 */
export const THEME_COLOR_DEFAULTS: ThemeColors = {
  accent: "#5aadff",
  primary: "#2dd4bf",
  success: "#34d399",
  warning: "#f5b942",
  danger: "#f87171",
  violet: "#a78bfa",
  surface: "#141820",
  text: "#f4f7fc",
  navActive: "#3b9eff",
  toolOrder: "#7eb0ff",
  toolSets: "#e8b86a",
  toolJoin: "#4ad4a8",
  toolMargin: "#f0c14d",
  toolBrands: "#c084fc",
  badgeBrand: "#f0b84a",
  badgeCategory: "#7eb6e8",
  tableRowEven: "#e8eef8",
  tableRowHover: "#5aadff",
  tableNameGap: "#141820",
};

export const THEME_OPACITY_DEFAULTS: ThemeOpacities = {
  tools: 1,
  toolsDisabled: 0.55,
  badges: 1,
  tableStripe: 0.035,
  tableHover: 0.1,
};

/** Built-in templates always available in Configurações. */
export const BUILT_IN_THEME_TEMPLATES: Array<{ id: string; name: string; colors: ThemeColors; opacities: ThemeOpacities }> = [
  {
    id: "builtin-profissional",
    name: "Profissional",
    colors: { ...THEME_COLOR_DEFAULTS },
    opacities: { ...THEME_OPACITY_DEFAULTS },
  },
  {
    id: "builtin-minimal",
    name: "Minimal neutro",
    colors: {
      ...THEME_COLOR_DEFAULTS,
      accent: "#8a93a3",
      primary: "#7a8699",
      success: "#6f9b80",
      warning: "#a89870",
      danger: "#a88080",
      violet: "#8a8f9a",
      navActive: "#7a8494",
      toolOrder: "#7a8494",
      toolSets: "#8a8578",
      toolJoin: "#6f8a7c",
      toolMargin: "#948a70",
      badgeBrand: "#8a8680",
      badgeCategory: "#80848c",
      tableRowHover: "#8a93a3",
    },
    opacities: {
      tools: 0.9,
      toolsDisabled: 0.42,
      badges: 0.78,
      tableStripe: 0.02,
      tableHover: 0.06,
    },
  },
  {
    id: "builtin-oceano",
    name: "Oceano",
    colors: {
      ...THEME_COLOR_DEFAULTS,
      accent: "#38bdf8",
      primary: "#2dd4bf",
      success: "#34d399",
      warning: "#fbbf24",
      danger: "#f87171",
      violet: "#a78bfa",
      navActive: "#0ea5e9",
      toolOrder: "#60a5fa",
      toolSets: "#f59e0b",
      toolJoin: "#14b8a6",
      toolMargin: "#eab308",
      badgeBrand: "#f59e0b",
      badgeCategory: "#38bdf8",
      tableRowHover: "#38bdf8",
    },
    opacities: {
      tools: 1,
      toolsDisabled: 0.52,
      badges: 0.98,
      tableStripe: 0.035,
      tableHover: 0.1,
    },
  },
];

export const THEME_PRESET_VERSION = 5;
export const LS_THEME_PRESET_VERSION = "lojasync-shell-theme-preset-version";

function isHexColor(value: string) {
  return /^#([0-9a-fA-F]{6})$/.test(value.trim());
}

export function normalizeHexColor(value: string, fallback = "#ffffff") {
  const raw = String(value || "").trim();
  if (isHexColor(raw)) return raw.toLowerCase();
  if (/^#([0-9a-fA-F]{3})$/.test(raw)) {
    const short = raw.slice(1);
    return `#${short[0]}${short[0]}${short[1]}${short[1]}${short[2]}${short[2]}`.toLowerCase();
  }
  return fallback.toLowerCase();
}

export function hexToRgb(hex: string) {
  const normalized = normalizeHexColor(hex);
  return {
    r: Number.parseInt(normalized.slice(1, 3), 16),
    g: Number.parseInt(normalized.slice(3, 5), 16),
    b: Number.parseInt(normalized.slice(5, 7), 16),
  };
}

export function rgbToHex(r: number, g: number, b: number) {
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(Number(n) || 0)));
  return `#${[clamp(r), clamp(g), clamp(b)].map((n) => n.toString(16).padStart(2, "0")).join("")}`;
}

export function coerceThemeColors(value: unknown): ThemeColors {
  const source = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const next = { ...THEME_COLOR_DEFAULTS };
  for (const key of Object.keys(THEME_COLOR_DEFAULTS) as ThemeColorKey[]) {
    next[key] = normalizeHexColor(String(source[key] || ""), THEME_COLOR_DEFAULTS[key]);
  }
  return next;
}

export function coerceThemeOpacities(value: unknown): ThemeOpacities {
  const source = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const next = { ...THEME_OPACITY_DEFAULTS };
  for (const meta of THEME_OPACITY_META) {
    const raw = Number(source[meta.key]);
    if (!Number.isFinite(raw)) continue;
    next[meta.key] = Math.min(meta.max, Math.max(meta.min, raw));
  }
  return next;
}

export function readThemeColors(): ThemeColors {
  try {
    const raw = window.localStorage.getItem(LS_THEME_COLORS);
    if (!raw) return { ...THEME_COLOR_DEFAULTS };
    return coerceThemeColors(JSON.parse(raw));
  } catch {
    return { ...THEME_COLOR_DEFAULTS };
  }
}

export function readThemeOpacities(): ThemeOpacities {
  try {
    const raw = window.localStorage.getItem(LS_THEME_OPACITIES);
    if (!raw) return { ...THEME_OPACITY_DEFAULTS };
    return coerceThemeOpacities(JSON.parse(raw));
  } catch {
    return { ...THEME_OPACITY_DEFAULTS };
  }
}

export function saveThemeColors(colors: ThemeColors, opacities: ThemeOpacities = readThemeOpacities()) {
  const nextColors = coerceThemeColors(colors);
  const nextOpacities = coerceThemeOpacities(opacities);
  try {
    window.localStorage.setItem(LS_THEME_COLORS, JSON.stringify(nextColors));
    window.localStorage.setItem(LS_THEME_OPACITIES, JSON.stringify(nextOpacities));
  } catch {
    /* ignore */
  }
  applyShellTheme(nextColors, nextOpacities);
  return { colors: nextColors, opacities: nextOpacities };
}

export function resetThemeColors() {
  try {
    window.localStorage.removeItem(LS_THEME_COLORS);
    window.localStorage.removeItem(LS_THEME_OPACITIES);
  } catch {
    /* ignore */
  }
  applyShellTheme(THEME_COLOR_DEFAULTS, THEME_OPACITY_DEFAULTS);
  return {
    colors: { ...THEME_COLOR_DEFAULTS },
    opacities: { ...THEME_OPACITY_DEFAULTS },
  };
}

export function readThemeTemplates(): ThemeTemplate[] {
  const builtIns: ThemeTemplate[] = BUILT_IN_THEME_TEMPLATES.map((item, index) => ({
    id: item.id,
    name: item.name,
    colors: coerceThemeColors(item.colors),
    opacities: coerceThemeOpacities(item.opacities),
    savedAt: Date.UTC(2026, 0, 1) - index,
  }));
  try {
    const raw = window.localStorage.getItem(LS_THEME_TEMPLATES);
    if (!raw) return builtIns;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return builtIns;
    const custom = parsed
      .filter((item) => item && typeof item === "object")
      .map((item) => {
        const record = item as Record<string, unknown>;
        const name = String(record.name || "").trim();
        const id = String(record.id || "").trim();
        const savedAt = Number(record.savedAt || 0);
        if (!name || !id || !Number.isFinite(savedAt)) return null;
        if (id.startsWith("builtin-")) return null;
        return {
          id,
          name,
          savedAt,
          colors: coerceThemeColors(record.colors),
          opacities: coerceThemeOpacities(record.opacities),
        };
      })
      .filter((item): item is ThemeTemplate => Boolean(item))
      .sort((left, right) => right.savedAt - left.savedAt)
      .slice(0, 24);
    return [...builtIns, ...custom];
  } catch {
    return builtIns;
  }
}

/** Apply the project professional preset once when the default palette ships/updates. */
export function ensureProfessionalThemePreset() {
  try {
    const current = Number(window.localStorage.getItem(LS_THEME_PRESET_VERSION) || 0);
    if (current >= THEME_PRESET_VERSION) {
      applyShellTheme(readThemeColors(), readThemeOpacities());
      return readThemeColors();
    }
    const saved = saveThemeColors(THEME_COLOR_DEFAULTS, THEME_OPACITY_DEFAULTS);
    window.localStorage.setItem(LS_THEME_PRESET_VERSION, String(THEME_PRESET_VERSION));
    return saved.colors;
  } catch {
    applyShellTheme(THEME_COLOR_DEFAULTS, THEME_OPACITY_DEFAULTS);
    return { ...THEME_COLOR_DEFAULTS };
  }
}

function writeThemeTemplates(templates: ThemeTemplate[]) {
  try {
    window.localStorage.setItem(LS_THEME_TEMPLATES, JSON.stringify(templates.slice(0, 24)));
  } catch {
    /* ignore */
  }
}

export function saveThemeTemplate(name: string, colors: ThemeColors, opacities: ThemeOpacities): ThemeTemplate {
  const cleanName = String(name || "").trim() || "Template sem nome";
  const template: ThemeTemplate = {
    id: `theme-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: cleanName,
    colors: coerceThemeColors(colors),
    opacities: coerceThemeOpacities(opacities),
    savedAt: Date.now(),
  };
  const next = [template, ...readThemeTemplates().filter((item) => item.name.toLowerCase() !== cleanName.toLowerCase())];
  writeThemeTemplates(next);
  return template;
}

export function deleteThemeTemplate(id: string) {
  if (String(id || "").startsWith("builtin-")) return;
  writeThemeTemplates(
    readThemeTemplates().filter((item) => item.id !== id && !item.id.startsWith("builtin-")),
  );
}

export function applyThemeTemplate(id: string) {
  const template = readThemeTemplates().find((item) => item.id === id);
  if (!template) return null;
  return saveThemeColors(template.colors, template.opacities);
}

function withAlpha(hex: string, alpha: number) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function applyShellTheme(
  colors: ThemeColors = readThemeColors(),
  opacities: ThemeOpacities = readThemeOpacities(),
  root: HTMLElement = document.documentElement,
) {
  const theme = coerceThemeColors(colors);
  const alpha = coerceThemeOpacities(opacities);
  root.style.setProperty("--blue", theme.accent);
  root.style.setProperty("--blue-dim", withAlpha(theme.accent, 0.16));
  root.style.setProperty("--blue-border", withAlpha(theme.accent, 0.34));
  root.style.setProperty("--green", theme.success);
  root.style.setProperty("--green-dim", withAlpha(theme.success, 0.16));
  root.style.setProperty("--green-border", withAlpha(theme.success, 0.34));
  root.style.setProperty("--red", theme.danger);
  root.style.setProperty("--red-dim", withAlpha(theme.danger, 0.16));
  root.style.setProperty("--red-border", withAlpha(theme.danger, 0.34));
  root.style.setProperty("--amber", theme.warning);
  root.style.setProperty("--amber-dim", withAlpha(theme.warning, 0.16));
  root.style.setProperty("--amber-border", withAlpha(theme.warning, 0.34));
  root.style.setProperty("--violet", theme.violet);
  root.style.setProperty("--violet-dim", withAlpha(theme.violet, 0.2));
  root.style.setProperty("--violet-border", withAlpha(theme.violet, 0.4));
  root.style.setProperty("--surface", theme.surface);
  root.style.setProperty("--text", theme.text);
  root.style.setProperty("--accent", theme.warning);
  root.style.setProperty("--danger", theme.danger);
  root.style.setProperty("--success", theme.success);
  root.style.setProperty("--theme-primary", theme.primary);
  root.style.setProperty("--theme-nav-active", theme.navActive);
  root.style.setProperty("--theme-tool-order", theme.toolOrder);
  root.style.setProperty("--theme-tool-sets", theme.toolSets);
  root.style.setProperty("--theme-tool-join", theme.toolJoin);
  root.style.setProperty("--theme-tool-margin", theme.toolMargin);
  root.style.setProperty("--theme-tool-brands", theme.toolBrands);
  root.style.setProperty("--theme-badge-brand", theme.badgeBrand);
  root.style.setProperty("--theme-badge-category", theme.badgeCategory);
  root.style.setProperty("--theme-table-row-even", theme.tableRowEven);
  root.style.setProperty("--theme-table-row-hover", theme.tableRowHover);
  root.style.setProperty("--theme-table-name-gap", theme.tableNameGap);
  root.style.setProperty("--theme-opacity-tools", String(alpha.tools));
  root.style.setProperty("--theme-opacity-tools-disabled", String(alpha.toolsDisabled));
  root.style.setProperty("--theme-opacity-badges", String(alpha.badges));
  root.style.setProperty("--theme-opacity-table-stripe", String(alpha.tableStripe));
  root.style.setProperty("--theme-opacity-table-hover", String(alpha.tableHover));
  root.style.setProperty("--status-warning-rgb", Object.values(hexToRgb(theme.badgeBrand)).join(", "));
  root.dataset.themeCustom = "1";
  return { colors: theme, opacities: alpha };
}
