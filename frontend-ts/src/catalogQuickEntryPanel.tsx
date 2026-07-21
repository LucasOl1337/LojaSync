import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { createPortal } from "react-dom";

import { normalizeProductQuantityInput } from "./productForm";
import type { ProductPayload } from "./types";

type CatalogQuickEntryField = "nome" | "codigo" | "quantidade" | "preco";
type PanelPosition = { x: number; y: number };

const POSITION_STORAGE_KEY = "lojasync-catalog-quick-entry-position";
const VIEWPORT_GUTTER = 12;

function readStoredPosition(): PanelPosition | null {
  try {
    const value = JSON.parse(window.localStorage.getItem(POSITION_STORAGE_KEY) || "null") as Partial<PanelPosition> | null;
    return value && Number.isFinite(value.x) && Number.isFinite(value.y)
      ? { x: Number(value.x), y: Number(value.y) }
      : null;
  } catch {
    return null;
  }
}

function clampPosition(position: PanelPosition, panel: HTMLElement): PanelPosition {
  return {
    x: Math.min(Math.max(VIEWPORT_GUTTER, position.x), Math.max(VIEWPORT_GUTTER, window.innerWidth - panel.offsetWidth - VIEWPORT_GUTTER)),
    y: Math.min(Math.max(VIEWPORT_GUTTER, position.y), Math.max(VIEWPORT_GUTTER, window.innerHeight - panel.offsetHeight - VIEWPORT_GUTTER)),
  };
}

type CatalogQuickEntryPanelProps = {
  open: boolean;
  form: ProductPayload;
  simpleModeEnabled: boolean;
  submitting: boolean;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onFormKeyDown: (event: KeyboardEvent<HTMLFormElement>) => void;
  onInputChange: <K extends CatalogQuickEntryField>(key: K, value: ProductPayload[K]) => void;
  onSubmitProduct: () => Promise<void>;
  onToggleSimpleMode: () => void;
  onClose: () => void;
  returnFocusTarget?: HTMLElement | null;
};

export function CatalogQuickEntryPanel({
  open,
  form,
  simpleModeEnabled,
  submitting,
  runBusyAction,
  onFormKeyDown,
  onInputChange,
  onSubmitProduct,
  onToggleSimpleMode,
  onClose,
  returnFocusTarget,
}: CatalogQuickEntryPanelProps) {
  const nameInputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const dragRef = useRef<{ pointerId: number; offsetX: number; offsetY: number } | null>(null);
  const [position, setPosition] = useState<PanelPosition | null>(null);
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.innerWidth <= 720);

  const normalizePosition = (candidate?: PanelPosition | null) => {
    const panel = panelRef.current;
    if (!panel || window.innerWidth <= 720) return;
    const fallback = {
      x: window.innerWidth - panel.offsetWidth - 24,
      y: Math.max(72, (window.innerHeight - panel.offsetHeight) / 2),
    };
    setPosition(clampPosition(candidate ?? position ?? readStoredPosition() ?? fallback, panel));
  };
  const resetPosition = () => {
    const panel = panelRef.current;
    if (!panel) return;
    const fallback = {
      x: window.innerWidth - panel.offsetWidth - 24,
      y: Math.max(72, (window.innerHeight - panel.offsetHeight) / 2),
    };
    setPosition(clampPosition(fallback, panel));
  };

  useEffect(() => {
    if (!open) return;
    returnFocusRef.current = returnFocusTarget ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    const timerId = window.setTimeout(() => nameInputRef.current?.focus(), 0);
    return () => {
      window.clearTimeout(timerId);
      const target = returnFocusRef.current;
      if (target?.isConnected) window.setTimeout(() => target.focus(), 0);
    };
  }, [open, returnFocusTarget]);

  useLayoutEffect(() => {
    if (open && !narrow) normalizePosition(position);
  }, [open, narrow]);

  useEffect(() => {
    if (!open) return;
    const handleResize = () => {
      const isNarrow = window.innerWidth <= 720;
      setNarrow(isNarrow);
      if (!isNarrow) window.requestAnimationFrame(() => normalizePosition());
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [open, position]);

  useEffect(() => {
    if (!position) return;
    try { window.localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify(position)); } catch { /* storage is optional */ }
  }, [position]);

  if (!open) return null;

  return createPortal(
    <aside
      ref={panelRef}
      id="catalog-quick-entry"
      className={`catalogQuickEntryTs ${narrow ? "catalogQuickEntrySheetTs" : ""}`}
      role="dialog"
      aria-modal="false"
      aria-labelledby="catalog-quick-entry-title"
      style={!narrow && position ? { left: position.x, top: position.y } : undefined}
      onKeyDown={(event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        onClose();
      }}
    >
      <div
        className="catalogQuickEntryHeaderTs"
        onPointerDown={(event) => {
          if (narrow || event.button !== 0 || (event.target as HTMLElement).closest("button")) return;
          const panel = panelRef.current;
          if (!panel) return;
          const bounds = panel.getBoundingClientRect();
          dragRef.current = { pointerId: event.pointerId, offsetX: event.clientX - bounds.left, offsetY: event.clientY - bounds.top };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const drag = dragRef.current;
          const panel = panelRef.current;
          if (!drag || !panel || drag.pointerId !== event.pointerId) return;
          setPosition(clampPosition({ x: event.clientX - drag.offsetX, y: event.clientY - drag.offsetY }, panel));
        }}
        onPointerUp={(event) => {
          if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
          if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onPointerCancel={() => { dragRef.current = null; }}
      >
        <div>
          <span className="sectionTag">Cadastro manual</span>
          <h2 id="catalog-quick-entry-title">Novo produto</h2>
        </div>
        <div className="catalogQuickEntryHeaderActionsTs">
          {!narrow ? (
            <button
              className="catalogQuickEntryResetTs"
              type="button"
              onClick={() => {
                try { window.localStorage.removeItem(POSITION_STORAGE_KEY); } catch { /* storage is optional */ }
                window.requestAnimationFrame(resetPosition);
              }}
              aria-label="Redefinir posição do cadastro manual"
              title="Redefinir posição"
            >
              Redefinir posição
            </button>
          ) : null}
          <button
            className={`ghostButton compactButton ${simpleModeEnabled ? "activeToggle" : ""}`}
            type="button"
            onClick={onToggleSimpleMode}
            aria-pressed={simpleModeEnabled}
          >
            {simpleModeEnabled ? "Usar modo completo" : "Usar modo simples"}
          </button>
          <button className="catalogQuickEntryCloseTs" type="button" onClick={onClose} aria-label="Fechar cadastro manual" title="Fechar">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>
      </div>

      <form
        className={`catalogQuickEntryFormTs ${simpleModeEnabled ? "simple" : ""}`}
        onKeyDown={onFormKeyDown}
        onSubmit={(event) => {
          event.preventDefault();
          void runBusyAction("adicionar-produto", onSubmitProduct);
        }}
      >
        <label>
          <span>Nome</span>
          <input ref={nameInputRef} name="nome" value={form.nome} onChange={(event) => onInputChange("nome", event.target.value)} placeholder="Ex.: Bolsa Couro" required />
        </label>
        {!simpleModeEnabled ? (
          <label>
            <span>Código</span>
            <input name="codigo" value={form.codigo} onChange={(event) => onInputChange("codigo", event.target.value)} placeholder="000000" required />
          </label>
        ) : null}
        <label>
          <span>Quantidade</span>
          <input
            name="quantidade"
            type="number"
            min={1}
            step={1}
            value={form.quantidade}
            onChange={(event) => onInputChange("quantidade", normalizeProductQuantityInput(event.target.value))}
            required
          />
        </label>
        <label>
          <span>Custo</span>
          <input name="preco" value={form.preco} onChange={(event) => onInputChange("preco", event.target.value)} placeholder="R$ 0,00" required />
        </label>
        <button className="primaryButton catalogQuickEntrySubmitTs" type="submit" disabled={submitting}>
          {submitting ? "Adicionando..." : "Adicionar à lista"}
        </button>
      </form>
    </aside>,
    document.body,
  );
}
