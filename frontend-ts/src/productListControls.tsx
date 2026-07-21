import { useEffect, useRef } from "react";
import type { KeyboardEvent, RefObject } from "react";

import type { DescriptionCleanupSuggestion } from "./descriptionCleanup";
import {
  DescriptionPanel,
  FormatCodesPanel,
  type DescriptionOptions,
  type FormatCodesOptions,
} from "./productListToolPanels";
import { actionText, type UndoRedoHistoryState } from "./uiFormatting";

type ProductListControlsProps = {
  loading: boolean;
  displayedCount: number;
  totalCount: number;
  productSearchQuery: string;
  undoRedoHistoryState: UndoRedoHistoryState;
  busyAction: string | null;
  globalEditMode: boolean;
  showFormatCodesPanel: boolean;
  showDescriptionPanel: boolean;
  formatCodesOptions: FormatCodesOptions;
  descriptionOptions: DescriptionOptions;
  descriptionSuggestions: DescriptionCleanupSuggestion[];
  orderingMode: boolean;
  orderingSelectedCount: number;
  createSetMode: boolean;
  createSetKeys: string[];
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onUndo: () => Promise<void>;
  onRedo: () => Promise<void>;
  onProductSearchChange: (query: string) => void;
  onToggleGlobalEdit: () => void;
  onToggleFormatCodesPanel: () => void;
  onToggleDescriptionPanel: () => void;
  onToggleOrdering: () => Promise<void>;
  onCancelOrdering: () => void;
  onToggleCreateSets: () => void;
  onJoinDuplicates: () => Promise<void>;
  onExportVisibleProducts: () => void;
  onClearProducts: () => Promise<void>;
  onFormatCodeOptionChange: (field: keyof FormatCodesOptions, value: string) => void;
  onRestoreOriginalCodes: () => Promise<void>;
  onCloseFormatCodesPanel: () => void;
  onFormatCodes: () => Promise<void>;
  onDescriptionOptionChange: (field: keyof DescriptionOptions, value: boolean | string) => void;
  onCloseDescriptionPanel: () => void;
  onImproveDescriptions: () => Promise<void>;
};

type ListToolbarIntroProps = Pick<ProductListControlsProps,
  "loading" | "displayedCount" | "totalCount" | "undoRedoHistoryState" | "busyAction" | "runBusyAction" | "onUndo" | "onRedo"
>;

function ListToolbarIntro({
  loading,
  displayedCount,
  totalCount,
  undoRedoHistoryState,
  busyAction,
  runBusyAction,
  onUndo,
  onRedo,
}: ListToolbarIntroProps) {
  return (
    <div className="listToolbarIntroTs">
      <h2 className="toolsTitleTs" id="list-tools-title">Ferramentas</h2>
      <div className="listToolbarMetaTs">
        <span className={`contextChipTs ${loading ? "loadingContextChipTs" : ""}`} role={loading ? "status" : undefined} aria-live={loading ? "polite" : undefined}>
          {loading
            ? "Atualizando lista"
            : displayedCount === totalCount
            ? actionText(totalCount, "item ativo", "itens ativos")
            : `${displayedCount} de ${actionText(totalCount, "item", "itens")}`}
        </span>
        <span
          className={`contextChipTs undoRedoStatusChipTs ${undoRedoHistoryState.canUndo || undoRedoHistoryState.canRedo ? "historyReady" : ""}`}
          title={`${undoRedoHistoryState.undoLabel}. ${undoRedoHistoryState.redoLabel}.`}
          aria-label={`Histórico de edições: ${undoRedoHistoryState.summary}`}
        >
          {undoRedoHistoryState.summary}
        </span>
        <div className="undoRedoActionsTs" role="group" aria-label="Histórico reversível">
          <button
            className="historyIconButtonTs"
            type="button"
            onClick={() => void runBusyAction("desfazer", onUndo)}
            disabled={!undoRedoHistoryState.canUndo || busyAction === "desfazer" || busyAction === "refazer"}
            title={undoRedoHistoryState.undoLabel}
            aria-label={undoRedoHistoryState.undoLabel}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 14 4 9l5-5" />
              <path d="M4 9h10a6 6 0 0 1 0 12h-1" />
            </svg>
          </button>
          <button
            className="historyIconButtonTs"
            type="button"
            onClick={() => void runBusyAction("refazer", onRedo)}
            disabled={!undoRedoHistoryState.canRedo || busyAction === "desfazer" || busyAction === "refazer"}
            title={undoRedoHistoryState.redoLabel}
            aria-label={undoRedoHistoryState.redoLabel}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15 14 5-5-5-5" />
              <path d="M20 9H10a6 6 0 0 0 0 12h1" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

type ProductSearchFieldProps = Pick<ProductListControlsProps, "productSearchQuery" | "onProductSearchChange">;

function ProductSearchField({
  productSearchQuery,
  onProductSearchChange,
}: ProductSearchFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const clearSearch = () => {
    if (!productSearchQuery) return;
    onProductSearchChange("");
    window.setTimeout(() => inputRef.current?.focus(), 0);
  };

  return (
    <label className="listSearchTs">
      <span>Buscar na lista</span>
      <div className="listSearchInputWrapTs">
        <input
          ref={inputRef}
          className="listSearchInputTs"
          type="search"
          value={productSearchQuery}
          onChange={(event) => onProductSearchChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape" && productSearchQuery) {
              event.preventDefault();
              clearSearch();
            }
          }}
          placeholder="Nome, marca, código ou categoria"
          aria-label="Buscar produto na lista"
          aria-keyshortcuts={productSearchQuery ? "Escape" : undefined}
        />
        {productSearchQuery ? (
          <button
            className="listSearchClearTs"
            type="button"
            onClick={clearSearch}
            aria-label="Limpar busca"
            title="Limpar busca"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        ) : null}
      </div>
    </label>
  );
}

type ListPrimaryActionsProps = Pick<ProductListControlsProps,
  "loading" | "displayedCount" | "totalCount" | "globalEditMode" | "showFormatCodesPanel" | "showDescriptionPanel" | "orderingMode" | "createSetMode" |
  "runBusyAction" | "onToggleGlobalEdit" | "onToggleFormatCodesPanel" | "onToggleDescriptionPanel" |
  "onToggleOrdering" | "onToggleCreateSets" | "onJoinDuplicates" | "onExportVisibleProducts" | "onClearProducts"
> & {
  formatCodesButtonRef: RefObject<HTMLButtonElement>;
  descriptionButtonRef: RefObject<HTMLButtonElement>;
};

function ListPrimaryActions({
  loading,
  displayedCount,
  totalCount,
  globalEditMode,
  showFormatCodesPanel,
  showDescriptionPanel,
  orderingMode,
  createSetMode,
  runBusyAction,
  onToggleGlobalEdit,
  onToggleFormatCodesPanel,
  onToggleDescriptionPanel,
  onToggleOrdering,
  onToggleCreateSets,
  onJoinDuplicates,
  onExportVisibleProducts,
  onClearProducts,
  formatCodesButtonRef,
  descriptionButtonRef,
}: ListPrimaryActionsProps) {
  return (
    <div className="listHeadTs">
      <div className="listPrimaryActionsTs" aria-label="Ações principais">
        <button className={`toolButtonTs ${globalEditMode ? "activeToolButton" : ""}`} type="button" onClick={onToggleGlobalEdit} aria-pressed={globalEditMode}>{globalEditMode ? "Finalizar edições" : "Permitir edições"}</button>
        <button ref={formatCodesButtonRef} className={`toolButtonTs ${showFormatCodesPanel ? "activeToolButton" : ""}`} type="button" onClick={onToggleFormatCodesPanel} aria-pressed={showFormatCodesPanel}>Formatar códigos</button>
        <button ref={descriptionButtonRef} className={`toolButtonTs ${showDescriptionPanel ? "activeToolButton" : ""}`} type="button" onClick={onToggleDescriptionPanel} aria-pressed={showDescriptionPanel}>Melhorar descrição</button>
        <button className={`toolButtonTs orderingToolButton ${orderingMode ? "activeOrderingToolButton" : ""}`} type="button" onClick={() => void runBusyAction("ordenar-lista", onToggleOrdering)} aria-pressed={orderingMode}>{orderingMode ? "Salvar ordem" : "Ordenar"}</button>
        <button className={`toolButtonTs createSetToolButton ${createSetMode ? "activeCreateSetToolButton" : ""}`} type="button" onClick={onToggleCreateSets} aria-pressed={createSetMode}>{createSetMode ? "Cancelar conjuntos" : "Conjuntos"}</button>
        <button
          className="toolButtonTs joinDuplicatesToolButton"
          type="button"
          onClick={() => void runBusyAction("juntar-repetidos", onJoinDuplicates)}
          disabled={loading || displayedCount === 0}
          title={displayedCount === totalCount
            ? "Juntar repetidos em todo o catalogo"
            : `Juntar repetidos apenas nos ${displayedCount} produtos visiveis; itens ocultos serao preservados`}
        >Juntar repetidos</button>
        <button
          className="toolButtonTs exportToolButtonTs"
          type="button"
          onClick={onExportVisibleProducts}
          disabled={loading || displayedCount === 0}
          title={displayedCount === totalCount ? "Baixar o catálogo completo" : "Baixar apenas os produtos visíveis na busca"}
          aria-label={`Baixar ${actionText(displayedCount, "produto visível", "produtos visíveis")} em CSV`}
        >
          Baixar CSV
        </button>
        <button className="toolButtonTs danger" type="button" onClick={() => void runBusyAction("limpar-lista", onClearProducts)}>
          Limpar lista
        </button>
      </div>
    </div>
  );
}

function EditModeContextPanel() {
  return (
    <div className="editModeContextTs" role="status" aria-live="polite">
      <div className="editModeContextMainTs">
        <strong>Edição livre</strong>
        <span>Células e exclusões por linha liberadas para ajuste manual.</span>
      </div>
    </div>
  );
}

function ListModeContextPanel({
  orderingMode,
  orderingSelectedCount,
  createSetMode,
  createSetKeys,
  onCancelOrdering,
}: Pick<
  ProductListControlsProps,
  "orderingMode" | "orderingSelectedCount" | "createSetMode" | "createSetKeys" | "onCancelOrdering"
>) {
  if (orderingMode) {
    return (
      <div className="listModeContextTs contextTone-ordering" role="status" aria-live="polite">
        <div className="listModeContextMainTs">
          <strong>Ordenação ativa</strong>
          <span>Selecione linhas para montar a prioridade. Enter seleciona; Shift+Enter remove; setas movem.</span>
        </div>
        <div className="listModeContextActionsTs">
          <span className="listModeContextMetaTs">{actionText(orderingSelectedCount, "item", "itens")} priorizado{orderingSelectedCount === 1 ? "" : "s"}</span>
          <button className="listModeContextButtonTs secondaryListModeContextButtonTs" type="button" onClick={onCancelOrdering}>
            Cancelar
          </button>
        </div>
      </div>
    );
  }

  if (createSetMode) {
    return (
      <div className="listModeContextTs contextTone-createSet" role="status" aria-live="polite">
        <div className="listModeContextMainTs">
          <strong>Conjunto ativo</strong>
          <span>Selecione dois itens; ao completar 2 de 2, o conjunto é criado automaticamente.</span>
        </div>
        <div className="listModeContextActionsTs">
          <span className="listModeContextMetaTs">{Math.min(createSetKeys.length, 2)}/2 selecionados</span>
        </div>
      </div>
    );
  }

  return null;
}

export function ProductListControls({
  loading,
  displayedCount,
  totalCount,
  productSearchQuery,
  undoRedoHistoryState,
  busyAction,
  globalEditMode,
  showFormatCodesPanel,
  showDescriptionPanel,
  formatCodesOptions,
  descriptionOptions,
  descriptionSuggestions,
  orderingMode,
  orderingSelectedCount,
  createSetMode,
  createSetKeys,
  runBusyAction,
  onUndo,
  onRedo,
  onProductSearchChange,
  onToggleGlobalEdit,
  onToggleFormatCodesPanel,
  onToggleDescriptionPanel,
  onToggleOrdering,
  onCancelOrdering,
  onToggleCreateSets,
  onJoinDuplicates,
  onExportVisibleProducts,
  onClearProducts,
  onFormatCodeOptionChange,
  onRestoreOriginalCodes,
  onCloseFormatCodesPanel,
  onFormatCodes,
  onDescriptionOptionChange,
  onCloseDescriptionPanel,
  onImproveDescriptions,
}: ProductListControlsProps) {
  const formatCodesButtonRef = useRef<HTMLButtonElement>(null!);
  const descriptionButtonRef = useRef<HTMLButtonElement>(null!);
  const formatCodesPanelRef = useRef<HTMLDivElement>(null!);
  const descriptionPanelRef = useRef<HTMLDivElement>(null!);
  const focusFirstPanelControl = (panel: HTMLDivElement | null) => {
    const firstControl = panel?.querySelector<HTMLElement>("input, button, select, textarea");
    firstControl?.focus();
  };
  const closeFormatCodesPanelAndRestoreFocus = () => {
    onCloseFormatCodesPanel();
    window.setTimeout(() => formatCodesButtonRef.current?.focus(), 0);
  };
  const closeDescriptionPanelAndRestoreFocus = () => {
    onCloseDescriptionPanel();
    window.setTimeout(() => descriptionButtonRef.current?.focus(), 0);
  };
  const handlePanelEscape = (
    event: KeyboardEvent<HTMLDivElement>,
    onClose: () => void,
  ) => {
    if (event.key !== "Escape") {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    onClose();
  };

  useEffect(() => {
    if (!showFormatCodesPanel) {
      return;
    }

    const timerId = window.setTimeout(() => focusFirstPanelControl(formatCodesPanelRef.current), 0);
    return () => window.clearTimeout(timerId);
  }, [showFormatCodesPanel]);

  useEffect(() => {
    if (!showDescriptionPanel) {
      return;
    }

    const timerId = window.setTimeout(() => focusFirstPanelControl(descriptionPanelRef.current), 0);
    return () => window.clearTimeout(timerId);
  }, [showDescriptionPanel]);

  return (
    <section className="listControlsTs" aria-labelledby="list-tools-title">
      <div className="listToolbarTs">
        <ListToolbarIntro
          loading={loading}
          displayedCount={displayedCount}
          totalCount={totalCount}
          undoRedoHistoryState={undoRedoHistoryState}
          busyAction={busyAction}
          runBusyAction={runBusyAction}
          onUndo={onUndo}
          onRedo={onRedo}
        />

        <ProductSearchField
          productSearchQuery={productSearchQuery}
          onProductSearchChange={onProductSearchChange}
        />

        <div className="listContentTs">
          <ListPrimaryActions
            loading={loading}
            displayedCount={displayedCount}
            totalCount={totalCount}
            globalEditMode={globalEditMode}
            showFormatCodesPanel={showFormatCodesPanel}
            showDescriptionPanel={showDescriptionPanel}
            orderingMode={orderingMode}
            createSetMode={createSetMode}
            runBusyAction={runBusyAction}
            onToggleGlobalEdit={onToggleGlobalEdit}
            onToggleFormatCodesPanel={onToggleFormatCodesPanel}
            onToggleDescriptionPanel={onToggleDescriptionPanel}
            onToggleOrdering={onToggleOrdering}
            onToggleCreateSets={onToggleCreateSets}
            onJoinDuplicates={onJoinDuplicates}
            onExportVisibleProducts={onExportVisibleProducts}
            onClearProducts={onClearProducts}
            formatCodesButtonRef={formatCodesButtonRef}
            descriptionButtonRef={descriptionButtonRef}
          />

          {globalEditMode ? <EditModeContextPanel /> : null}

          <ListModeContextPanel
            orderingMode={orderingMode}
            orderingSelectedCount={orderingSelectedCount}
            createSetMode={createSetMode}
            createSetKeys={createSetKeys}
            onCancelOrdering={onCancelOrdering}
          />

          {showFormatCodesPanel ? (
            <FormatCodesPanel
              formatCodesOptions={formatCodesOptions}
              panelRef={formatCodesPanelRef}
              runBusyAction={runBusyAction}
              onFormatCodeOptionChange={onFormatCodeOptionChange}
              onRestoreOriginalCodes={onRestoreOriginalCodes}
              onCloseFormatCodesPanel={closeFormatCodesPanelAndRestoreFocus}
              onFormatCodes={onFormatCodes}
              onPanelKeyDown={(event) => handlePanelEscape(event, closeFormatCodesPanelAndRestoreFocus)}
            />
          ) : null}

          {showDescriptionPanel ? (
            <DescriptionPanel
              descriptionOptions={descriptionOptions}
              descriptionSuggestions={descriptionSuggestions}
              panelRef={descriptionPanelRef}
              runBusyAction={runBusyAction}
              onDescriptionOptionChange={onDescriptionOptionChange}
              onCloseDescriptionPanel={closeDescriptionPanelAndRestoreFocus}
              onImproveDescriptions={onImproveDescriptions}
              onPanelKeyDown={(event) => handlePanelEscape(event, closeDescriptionPanelAndRestoreFocus)}
            />
          ) : null}

        </div>
      </div>
    </section>
  );
}
