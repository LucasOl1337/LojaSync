import { useEffect, useRef } from "react";
import type { KeyboardEvent, RefObject } from "react";

import type { PostProcessResult, PostProcessStatus } from "./types";
import type { ProductQuickFilter, ProductQuickFilterOption } from "./productFilters";
import {
  buildProductQuickFilterButtonLabel,
  buildProductQuickFilterContext,
  getProductQuickFilterVisualState,
  getVisibleProductQuickFilterOptions,
} from "./productFilters";
import {
  DescriptionPanel,
  FormatCodesPanel,
  PostProcessMessages,
  type DescriptionOptions,
  type FormatCodesOptions,
} from "./productListToolPanels";
import { actionText, type UndoRedoHistoryState } from "./uiFormatting";

type ProductListControlsProps = {
  displayedCount: number;
  totalCount: number;
  productSearchQuery: string;
  productQuickFilter: ProductQuickFilter;
  productQuickFilterOptions: ProductQuickFilterOption[];
  undoRedoHistoryState: UndoRedoHistoryState;
  busyAction: string | null;
  globalEditMode: boolean;
  showFormatCodesPanel: boolean;
  showDescriptionPanel: boolean;
  formatCodesOptions: FormatCodesOptions;
  descriptionOptions: DescriptionOptions;
  postProcessing: boolean;
  postProcessJob: PostProcessStatus | null;
  postProcessError: string | null;
  postProcessResult: PostProcessResult | null;
  orderingMode: boolean;
  orderingSelectedCount: number;
  createSetMode: boolean;
  createSetKeys: string[];
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onUndo: () => Promise<void>;
  onRedo: () => Promise<void>;
  onProductSearchChange: (query: string) => void;
  onQuickFilterChange: (filter: ProductQuickFilter) => void;
  onToggleGlobalEdit: () => void;
  onToggleFormatCodesPanel: () => void;
  onToggleDescriptionPanel: () => void;
  onStartPostProcess: () => Promise<void>;
  onToggleOrdering: () => Promise<void>;
  onCancelOrdering: () => void;
  onToggleCreateSets: () => void;
  onJoinDuplicates: () => Promise<void>;
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
  "displayedCount" | "totalCount" | "productQuickFilter" | "undoRedoHistoryState" | "busyAction" | "runBusyAction" | "onUndo" | "onRedo"
>;

function ListToolbarIntro({
  displayedCount,
  totalCount,
  productQuickFilter,
  undoRedoHistoryState,
  busyAction,
  runBusyAction,
  onUndo,
  onRedo,
}: ListToolbarIntroProps) {
  return (
    <div className="listToolbarIntroTs">
      <h2 className="toolsTitleTs" id="list-tools-title">Ferramentas da lista</h2>
      <div className="listToolbarMetaTs">
        <span className="contextChipTs">
          {productQuickFilter === "all"
            ? actionText(displayedCount, "item ativo", "itens ativos")
            : `${displayedCount} de ${actionText(totalCount, "item", "itens")}`}
        </span>
        <span className={`contextChipTs undoRedoStatusChipTs ${undoRedoHistoryState.canUndo || undoRedoHistoryState.canRedo ? "historyReady" : ""}`}>
          {undoRedoHistoryState.summary}
        </span>
        <div className="undoRedoActionsTs" role="group" aria-label="Historico reversivel">
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

type QuickFilterButtonsProps = Pick<ProductListControlsProps, "productQuickFilter" | "productQuickFilterOptions" | "onQuickFilterChange">;

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
      <span>Buscar</span>
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
          placeholder="Nome, marca, codigo ou categoria"
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

function QuickFilterButtons({
  productQuickFilter,
  productQuickFilterOptions,
  onQuickFilterChange,
}: QuickFilterButtonsProps) {
  const visibleQuickFilterOptions = getVisibleProductQuickFilterOptions(productQuickFilterOptions, productQuickFilter);

  return (
    <div className="quickFiltersTs" role="group" aria-label="Filtros rapidos da lista">
      <span className="quickFiltersLabelTs" aria-hidden="true">Filtros</span>
      {visibleQuickFilterOptions.map((option) => {
        const active = productQuickFilter === option.key;
        const accessibleLabel = buildProductQuickFilterButtonLabel(option, active);
        const visualState = getProductQuickFilterVisualState(option, active);
        const disabled = visualState === "empty";
        const buttonClassName = [
          "quickFilterButtonTs",
          visualState === "active" ? "activeQuickFilterButtonTs" : "",
          visualState === "empty" ? "emptyQuickFilterButtonTs" : "",
        ].filter(Boolean).join(" ");
        return (
          <button
            key={option.key}
            className={buttonClassName}
            type="button"
            onClick={() => onQuickFilterChange(option.key)}
            disabled={disabled}
            aria-pressed={active}
            aria-label={accessibleLabel}
            title={accessibleLabel}
          >
            <span>{option.label}</span>
            <strong aria-hidden="true">{option.count}</strong>
          </button>
        );
      })}
    </div>
  );
}

type QuickFilterContextPanelProps = Pick<
  ProductListControlsProps,
  "displayedCount" | "totalCount" | "productQuickFilter" | "productQuickFilterOptions" | "onQuickFilterChange"
>;

function QuickFilterContextPanel({
  displayedCount,
  totalCount,
  productQuickFilter,
  productQuickFilterOptions,
  onQuickFilterChange,
}: QuickFilterContextPanelProps) {
  const context = buildProductQuickFilterContext(productQuickFilter, productQuickFilterOptions, displayedCount, totalCount);
  if (!context) return null;

  return (
    <div className={`quickFilterContextTs contextTone-${context.tone}`} aria-live="polite">
      <div className="quickFilterContextMainTs">
        <strong>{context.title}</strong>
        <span>{context.detail}</span>
      </div>
      <div className="quickFilterContextActionsTs" role="group" aria-label="Acoes do filtro ativo">
        {context.actions.map((action) => (
          <button
            key={action.key}
            className={`quickFilterContextButtonTs contextAction-${action.tone}`}
            type="button"
            onClick={() => onQuickFilterChange(action.targetFilter)}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

type ListPrimaryActionsProps = Pick<ProductListControlsProps,
  "globalEditMode" | "showFormatCodesPanel" | "showDescriptionPanel" | "postProcessing" | "orderingMode" | "createSetMode" | "createSetKeys" |
  "runBusyAction" | "onToggleGlobalEdit" | "onToggleFormatCodesPanel" | "onToggleDescriptionPanel" | "onStartPostProcess" |
  "onToggleOrdering" | "onToggleCreateSets" | "onJoinDuplicates" | "onClearProducts"
> & {
  formatCodesButtonRef: RefObject<HTMLButtonElement>;
  descriptionButtonRef: RefObject<HTMLButtonElement>;
};

function ListPrimaryActions({
  globalEditMode,
  showFormatCodesPanel,
  showDescriptionPanel,
  postProcessing,
  orderingMode,
  createSetMode,
  createSetKeys,
  runBusyAction,
  onToggleGlobalEdit,
  onToggleFormatCodesPanel,
  onToggleDescriptionPanel,
  onStartPostProcess,
  onToggleOrdering,
  onToggleCreateSets,
  onJoinDuplicates,
  onClearProducts,
  formatCodesButtonRef,
  descriptionButtonRef,
}: ListPrimaryActionsProps) {
  return (
    <div className="listHeadTs">
      <div className="listPrimaryActionsTs" aria-label="Acoes principais">
        <div className="toolActionGroupTs" role="group" aria-label="Edicao">
          <span className="toolActionGroupLabelTs">Edicao</span>
          <div className="toolActionGroupButtonsTs">
            <button className={`toolButtonTs ${globalEditMode ? "activeToolButton" : ""}`} type="button" onClick={onToggleGlobalEdit} aria-pressed={globalEditMode}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>{globalEditMode ? "Finalizar Edicoes" : "Permitir Edicoes"}
            </button>
            <button ref={formatCodesButtonRef} className={`toolButtonTs ${showFormatCodesPanel ? "activeToolButton" : ""}`} type="button" onClick={onToggleFormatCodesPanel} aria-pressed={showFormatCodesPanel}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>Formatar Codigos
            </button>
          </div>
        </div>

        <div className="toolActionGroupTs" role="group" aria-label="Assistida">
          <span className="toolActionGroupLabelTs">Assistida</span>
          <div className="toolActionGroupButtonsTs">
            <button ref={descriptionButtonRef} className={`toolButtonTs ${showDescriptionPanel ? "activeToolButton" : ""}`} type="button" onClick={onToggleDescriptionPanel} aria-pressed={showDescriptionPanel}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>Melhorar Descricao
            </button>
            <button className="toolButtonTs aiReviewButton" type="button" onClick={() => void runBusyAction("revisar-itens-ia", onStartPostProcess)}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 8v4l3 3"/><circle cx="18" cy="6" r="3" fill="currentColor" stroke="none"/></svg>{postProcessing ? "Revisando com IA..." : "Revisar Itens com IA"}
            </button>
          </div>
        </div>

        <div className="toolActionGroupTs" role="group" aria-label="Organizacao">
          <span className="toolActionGroupLabelTs">Organizacao</span>
          <div className="toolActionGroupButtonsTs">
            <button className={`toolButtonTs accent orderingToolButton ${orderingMode ? "activeToolButton" : ""}`} type="button" onClick={() => void runBusyAction("ordenar-lista", onToggleOrdering)} aria-pressed={orderingMode}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><polyline points="3 6 4 7 6 5"/><polyline points="3 12 4 13 6 11"/><polyline points="3 18 4 19 6 17"/></svg>{orderingMode ? "Salvar Ordem" : "Ordenar Lista"}
            </button>
            <button className={`toolButtonTs accent ${createSetMode ? "activeToolButton" : ""}`} type="button" onClick={onToggleCreateSets} aria-pressed={createSetMode}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><rect x="2" y="3" width="9" height="9"/><rect x="13" y="3" width="9" height="9"/><rect x="2" y="13" width="9" height="9"/><path d="M17.5 17.5 22 22M13 17.5h9M17.5 13v9"/></svg>{createSetMode ? "Cancelar Conjuntos" : "Criar Conjuntos"}
            </button>
            <button className="toolButtonTs success" type="button" onClick={() => void runBusyAction("juntar-repetidos", onJoinDuplicates)}><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><path d="M8 17l4 4 4-4"/><path d="M12 12v9"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg>Juntar Repetidos</button>
          </div>
        </div>

        <div className="toolActionGroupTs toolActionGroupDangerTs" role="group" aria-label="Risco">
          <span className="toolActionGroupLabelTs">Risco</span>
          <div className="toolActionGroupButtonsTs">
            <button className="toolButtonTs danger" type="button" onClick={() => void runBusyAction("limpar-lista", onClearProducts)}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>Limpar Lista
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EditModeContextPanel({
  onToggleGlobalEdit,
}: Pick<ProductListControlsProps, "onToggleGlobalEdit">) {
  return (
    <div className="editModeContextTs" role="status" aria-live="polite">
      <div className="editModeContextMainTs">
        <strong>Edicao livre ativa</strong>
        <span>Celulas e exclusoes por linha estao liberadas para ajuste manual.</span>
      </div>
      <button className="editModeContextButtonTs" type="button" onClick={onToggleGlobalEdit}>
        Finalizar edicoes
      </button>
    </div>
  );
}

function ListModeContextPanel({
  orderingMode,
  orderingSelectedCount,
  createSetMode,
  createSetKeys,
  runBusyAction,
  onToggleOrdering,
  onCancelOrdering,
  onToggleCreateSets,
}: Pick<
  ProductListControlsProps,
  "orderingMode" | "orderingSelectedCount" | "createSetMode" | "createSetKeys" | "runBusyAction" | "onToggleOrdering" | "onToggleCreateSets"
  | "onCancelOrdering"
>) {
  if (orderingMode) {
    return (
      <div className="listModeContextTs contextTone-ordering" role="status" aria-live="polite">
        <div className="listModeContextMainTs">
          <strong>Ordenacao ativa</strong>
          <span>Clique ou pressione Enter nas linhas para montar a prioridade. Shift+Enter remove; as setas ajustam itens selecionados.</span>
        </div>
        <div className="listModeContextActionsTs">
          <span className="listModeContextMetaTs">{actionText(orderingSelectedCount, "item", "itens")} priorizado{orderingSelectedCount === 1 ? "" : "s"}</span>
          <button className="listModeContextButtonTs secondaryListModeContextButtonTs" type="button" onClick={onCancelOrdering}>
            Cancelar
          </button>
          <button className="listModeContextButtonTs" type="button" onClick={() => void runBusyAction("salvar-ordem", onToggleOrdering)}>
            Salvar ordem
          </button>
        </div>
      </div>
    );
  }

  if (createSetMode) {
    return (
      <div className="listModeContextTs contextTone-createSet" role="status" aria-live="polite">
        <div className="listModeContextMainTs">
          <strong>Criacao de conjunto ativa</strong>
          <span>Selecione dois itens na tabela; ao completar 2 de 2, o conjunto e criado automaticamente.</span>
        </div>
        <div className="listModeContextActionsTs">
          <span className="listModeContextMetaTs">{Math.min(createSetKeys.length, 2)}/2 selecionados</span>
          <button className="listModeContextButtonTs" type="button" onClick={onToggleCreateSets}>
            Cancelar
          </button>
        </div>
      </div>
    );
  }

  return null;
}

export function ProductListControls({
  displayedCount,
  totalCount,
  productSearchQuery,
  productQuickFilter,
  productQuickFilterOptions,
  undoRedoHistoryState,
  busyAction,
  globalEditMode,
  showFormatCodesPanel,
  showDescriptionPanel,
  formatCodesOptions,
  descriptionOptions,
  postProcessing,
  postProcessJob,
  postProcessError,
  postProcessResult,
  orderingMode,
  orderingSelectedCount,
  createSetMode,
  createSetKeys,
  runBusyAction,
  onUndo,
  onRedo,
  onProductSearchChange,
  onQuickFilterChange,
  onToggleGlobalEdit,
  onToggleFormatCodesPanel,
  onToggleDescriptionPanel,
  onStartPostProcess,
  onToggleOrdering,
  onCancelOrdering,
  onToggleCreateSets,
  onJoinDuplicates,
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
          displayedCount={displayedCount}
          totalCount={totalCount}
          productQuickFilter={productQuickFilter}
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

        <QuickFilterButtons
          productQuickFilter={productQuickFilter}
          productQuickFilterOptions={productQuickFilterOptions}
          onQuickFilterChange={onQuickFilterChange}
        />

        <QuickFilterContextPanel
          displayedCount={displayedCount}
          totalCount={totalCount}
          productQuickFilter={productQuickFilter}
          productQuickFilterOptions={productQuickFilterOptions}
          onQuickFilterChange={onQuickFilterChange}
        />

        <div className="listContentTs">
          <ListPrimaryActions
            globalEditMode={globalEditMode}
            showFormatCodesPanel={showFormatCodesPanel}
            showDescriptionPanel={showDescriptionPanel}
            postProcessing={postProcessing}
            orderingMode={orderingMode}
            createSetMode={createSetMode}
            createSetKeys={createSetKeys}
            runBusyAction={runBusyAction}
            onToggleGlobalEdit={onToggleGlobalEdit}
            onToggleFormatCodesPanel={onToggleFormatCodesPanel}
            onToggleDescriptionPanel={onToggleDescriptionPanel}
            onStartPostProcess={onStartPostProcess}
            onToggleOrdering={onToggleOrdering}
            onToggleCreateSets={onToggleCreateSets}
            onJoinDuplicates={onJoinDuplicates}
            onClearProducts={onClearProducts}
            formatCodesButtonRef={formatCodesButtonRef}
            descriptionButtonRef={descriptionButtonRef}
          />

          {globalEditMode ? <EditModeContextPanel onToggleGlobalEdit={onToggleGlobalEdit} /> : null}

          <ListModeContextPanel
            orderingMode={orderingMode}
            orderingSelectedCount={orderingSelectedCount}
            createSetMode={createSetMode}
            createSetKeys={createSetKeys}
            runBusyAction={runBusyAction}
            onToggleOrdering={onToggleOrdering}
            onCancelOrdering={onCancelOrdering}
            onToggleCreateSets={onToggleCreateSets}
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
              panelRef={descriptionPanelRef}
              runBusyAction={runBusyAction}
              onDescriptionOptionChange={onDescriptionOptionChange}
              onCloseDescriptionPanel={closeDescriptionPanelAndRestoreFocus}
              onImproveDescriptions={onImproveDescriptions}
              onPanelKeyDown={(event) => handlePanelEscape(event, closeDescriptionPanelAndRestoreFocus)}
            />
          ) : null}

          <PostProcessMessages
            postProcessing={postProcessing}
            postProcessJob={postProcessJob}
            postProcessError={postProcessError}
            postProcessResult={postProcessResult}
          />
        </div>
      </div>
    </section>
  );
}
