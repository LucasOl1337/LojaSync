/**
 * App wallpaper default (admin global) + optional personal browser override.
 * Mirrors NexARQ / Sharingan shell appearance priority:
 *   personal localStorage → app default from API → hardcoded default
 */

export const LS_WALLPAPER = "lojasync-shell-wallpaper";
export const LS_BRIGHTNESS = "lojasync-shell-brightness";

export const DEFAULT_WALLPAPER = "/wallpapers/wallpaper-nexarq-cta.jpg";

export const WALLPAPER_CATALOG: { path: string; label: string; blurb: string }[] = [
  { path: "/wallpapers/wallpaper-nexarq-cta.jpg", label: "CTA Banner", blurb: "Padrão · brand" },
  { path: "/wallpapers/wallpaper-nexarq-aurora.jpg", label: "Aurora Nex", blurb: "Brand" },
  { path: "/wallpapers/wallpaper-quiet-mist.jpg", label: "Sombra Suave", blurb: "Suave" },
  { path: "/wallpapers/atelier.jpg", label: "Ateliê", blurb: "Galeria" },
  { path: "/wallpapers/vigia.jpg", label: "Vigia", blurb: "Galeria" },
  { path: "/wallpapers/dunas-estelares.jpg", label: "Dunas Estelares", blurb: "Galeria" },
  { path: "/wallpapers/aurora-verde.jpg", label: "Aurora Verde", blurb: "Galeria" },
];

export const WALLPAPER_PATHS = WALLPAPER_CATALOG.map((w) => w.path);

export type AppAppearance = {
  defaultWallpaper: string;
  defaultBrightness: number | null;
  wallpapers?: string[];
};

let appDefault: AppAppearance = {
  defaultWallpaper: DEFAULT_WALLPAPER,
  defaultBrightness: null,
};

export function getAppDefault(): AppAppearance {
  return { ...appDefault };
}

export function setAppDefaultCache(next: AppAppearance) {
  const wallpaper = WALLPAPER_PATHS.includes(next.defaultWallpaper)
    ? next.defaultWallpaper
    : DEFAULT_WALLPAPER;
  appDefault = {
    defaultWallpaper: wallpaper,
    defaultBrightness:
      next.defaultBrightness == null
        ? null
        : Math.min(1, Math.max(0.5, Number(next.defaultBrightness))),
    wallpapers: next.wallpapers,
  };
}

export function hasPersonalWallpaper(): boolean {
  try {
    const v = localStorage.getItem(LS_WALLPAPER);
    return Boolean(v && WALLPAPER_PATHS.includes(v));
  } catch {
    return false;
  }
}

export function resolveActiveWallpaper(): string {
  try {
    const personal = localStorage.getItem(LS_WALLPAPER);
    if (personal && WALLPAPER_PATHS.includes(personal)) return personal;
  } catch {
    /* ignore */
  }
  if (WALLPAPER_PATHS.includes(appDefault.defaultWallpaper)) {
    return appDefault.defaultWallpaper;
  }
  return DEFAULT_WALLPAPER;
}

export function resolveActiveBrightness(wallpaper: string): number {
  try {
    const raw = localStorage.getItem(LS_BRIGHTNESS);
    if (raw != null) {
      const n = Number(raw);
      if (!Number.isNaN(n)) return Math.min(1, Math.max(0.55, n));
    }
  } catch {
    /* ignore */
  }
  if (appDefault.defaultBrightness != null) {
    return Math.min(1, Math.max(0.55, appDefault.defaultBrightness));
  }
  void wallpaper;
  return 0.9;
}

export function setPersonalWallpaper(path: string, brightness?: number) {
  if (!WALLPAPER_PATHS.includes(path)) return;
  try {
    localStorage.setItem(LS_WALLPAPER, path);
    if (brightness != null) {
      localStorage.setItem(LS_BRIGHTNESS, String(Math.min(1, Math.max(0.55, brightness))));
    }
  } catch {
    /* ignore */
  }
  applyShellWallpaper();
}

export function clearPersonalWallpaper() {
  try {
    localStorage.removeItem(LS_WALLPAPER);
    localStorage.removeItem(LS_BRIGHTNESS);
  } catch {
    /* ignore */
  }
  applyShellWallpaper();
}

export function applyShellWallpaper(root: HTMLElement = document.documentElement) {
  const wallpaper = resolveActiveWallpaper();
  const brightness = resolveActiveBrightness(wallpaper);
  root.style.setProperty("--app-wallpaper", `url("${wallpaper}")`);
  root.style.setProperty("--app-wallpaper-brightness", String(brightness));
  root.dataset.wallpaper = wallpaper;
  return { wallpaper, brightness };
}
