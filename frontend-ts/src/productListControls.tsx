import { useEffect, useRef } from "react";
import type { KeyboardEvent, ReactNode, RefObject } from "react";

import type { DescriptionCleanupSuggestion } from "./descriptionCleanup";
import {
  BrandsPanel,
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
  showBrandsPanel: boolean;
  formatCodesOptions: FormatCodesOptions;
  descriptionOptions: DescriptionOptions;
  descriptionSuggestions: DescriptionCleanupSuggestion[];
  sortedBrands: string[];
  bulkBrandValue: string;
  newBrand: string;
  bulkBrandText: string;
  orderingMode: boolean;
  orderingSelectedCount: number;
  orderingDragEnabled: boolean;
  createSetMode: boolean;
  createSetKeys: string[];
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onUndo: () => Promise<void>;
  onRedo: () => Promise<void>;
  onProductSearchChange: (query: string) => void;
  onToggleGlobalEdit: () => void;
  onToggleFormatCodesPanel: () => void;
  onToggleDescriptionPanel: () => void;
  onToggleBrandsPanel: () => void;
  onToggleOrdering: () => Promise<void>;
  onCancelOrdering: () => void;
  onToggleOrderingDrag: () => void;
  onToggleCreateSets: () => void;
  onJoinDuplicates: () => Promise<void>;
  onApplyMargin: () => Promise<void>;
  marginLabel?: string | null;
  pendingAutomaticGradesCount: number;
  onImportAutomaticGrades: () => Promise<void>;
  onClearProducts: () => Promise<void>;
  onFormatCodeOptionChange: (field: keyof FormatCodesOptions, value: string) => void;
  onRestoreOriginalCodes: () => Promise<void>;
  onCloseFormatCodesPanel: () => void;
  onFormatCodes: () => Promise<void>;
  onDescriptionOptionChange: (field: keyof DescriptionOptions, value: boolean | string) => void;
  onCloseDescriptionPanel: () => void;
  onImproveDescriptions: () => Promise<void>;
  onSelectBrand: (brand: string) => void;
  onNewBrandChange: (value: string) => void;
  onBulkBrandTextChange: (value: string) => void;
  onAddBrand: () => Promise<void>;
  onAddBrandsBulk: () => Promise<void>;
  onApplyBrand: () => Promise<void>;
  onCloseBrandsPanel: () => void;
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
  "loading" | "displayedCount" | "totalCount" | "globalEditMode" | "showFormatCodesPanel" | "showDescriptionPanel" | "showBrandsPanel" | "orderingMode" | "createSetMode" |
  "runBusyAction" | "onToggleGlobalEdit" | "onToggleFormatCodesPanel" | "onToggleDescriptionPanel" | "onToggleBrandsPanel" |
  "onToggleOrdering" | "onToggleCreateSets" | "onJoinDuplicates" | "onApplyMargin" | "marginLabel" |
  "pendingAutomaticGradesCount" | "onImportAutomaticGrades" | "onClearProducts"
> & {
  formatCodesButtonRef: RefObject<HTMLButtonElement>;
  descriptionButtonRef: RefObject<HTMLButtonElement>;
  brandsButtonRef: RefObject<HTMLButtonElement>;
};

function ToolActionGroup({
  label,
  className = "",
  children,
}: {
  label: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`toolActionGroupTs ${className}`.trim()} role="group" aria-label={label}>
      <span className="toolActionGroupLabelTs">{label}</span>
      <div className="toolActionGroupButtonsTs">{children}</div>
    </div>
  );
}

function ListPrimaryActions({
  loading,
  displayedCount,
  totalCount,
  globalEditMode,
  showFormatCodesPanel,
  showDescriptionPanel,
  showBrandsPanel,
  orderingMode,
  createSetMode,
  runBusyAction,
  onToggleGlobalEdit,
  onToggleFormatCodesPanel,
  onToggleDescriptionPanel,
  onToggleBrandsPanel,
  onToggleOrdering,
  onToggleCreateSets,
  onJoinDuplicates,
  onApplyMargin,
  marginLabel,
  pendingAutomaticGradesCount,
  onImportAutomaticGrades,
  onClearProducts,
  formatCodesButtonRef,
  descriptionButtonRef,
  brandsButtonRef,
}: ListPrimaryActionsProps) {
  const marginAccessible = (marginLabel || "").replace("%", " por cento");
  const hasAutomaticGrades = pendingAutomaticGradesCount > 0;
  const automaticGradesLabel = hasAutomaticGrades
    ? `Importar grades (${pendingAutomaticGradesCount})`
    : "Sem grades automáticas";
  const automaticGradesTitle = hasAutomaticGrades
    ? `Grades automáticas detectadas em ${pendingAutomaticGradesCount} item${pendingAutomaticGradesCount === 1 ? "" : "s"}. Clique para juntar e importar.`
    : "Nenhuma grade automática pendente de importação na lista atual.";
  return (
    <div className="listHeadTs">
      <div className="listPrimaryActionsTs" aria-label="Ações principais">
        <ToolActionGroup label="Editar">
          <button
            className={`toolButtonTs ${globalEditMode ? "activeToolButton" : ""}`}
            type="button"
            onClick={onToggleGlobalEdit}
            aria-pressed={globalEditMode}
            title={globalEditMode ? "Travar células e exclusões da tabela" : "Liberar edição direta nas células"}
          >
            {globalEditMode ? "Finalizar edição" : "Editar células"}
          </button>
          <button
            ref={formatCodesButtonRef}
            className={`toolButtonTs ${showFormatCodesPanel ? "activeToolButton" : ""}`}
            type="button"
            onClick={onToggleFormatCodesPanel}
            aria-pressed={showFormatCodesPanel}
            title="Cortar dígitos do começo ou fim dos códigos"
          >
            Códigos
          </button>
          <button
            ref={descriptionButtonRef}
            className={`toolButtonTs ${showDescriptionPanel ? "activeToolButton" : ""}`}
            type="button"
            onClick={onToggleDescriptionPanel}
            aria-pressed={showDescriptionPanel}
            title="Limpar nomes e descrições da lista"
          >
            Descrição
          </button>
          <button
            ref={brandsButtonRef}
            className={`toolButtonTs brandsToolButtonTs ${showBrandsPanel ? "activeToolButton" : ""}`}
            type="button"
            onClick={onToggleBrandsPanel}
            aria-pressed={showBrandsPanel}
            title="Cadastrar marcas e aplicar em lote"
          >
            Marcas
          </button>
          <button
            className="toolButtonTs marginToolButtonTs"
            type="button"
            onClick={() => void runBusyAction("margem", onApplyMargin)}
            disabled={loading || totalCount === 0}
            title="Alterar margem padrão e recalcular preços de venda"
            aria-label={marginLabel ? `Alterar margem. Valor atual ${marginAccessible}` : "Alterar margem"}
          >
            <span>Margem</span>
            {marginLabel ? <span className="marginBadgeTs">{marginLabel}</span> : null}
          </button>
        </ToolActionGroup>

        <ToolActionGroup label="Organizar">
          <button
            className={`toolButtonTs orderingToolButton ${orderingMode ? "activeOrderingToolButton" : ""}`}
            type="button"
            onClick={() => void runBusyAction("ordenar-lista", onToggleOrdering)}
            aria-pressed={orderingMode}
            title={orderingMode ? "Salvar a nova ordem do catálogo" : "Definir a ordem dos produtos"}
          >
            {orderingMode ? "Salvar ordem" : "Ordenar"}
          </button>
          <button
            className={`toolButtonTs createSetToolButton ${createSetMode ? "activeCreateSetToolButton" : ""}`}
            type="button"
            onClick={onToggleCreateSets}
            aria-pressed={createSetMode}
            title={createSetMode ? "Sair do modo conjuntos" : "Criar conjunto com dois produtos"}
          >
            {createSetMode ? "Cancelar conjuntos" : "Conjuntos"}
          </button>
          <button
            className="toolButtonTs joinDuplicatesToolButton"
            type="button"
            onClick={() => void runBusyAction("juntar-repetidos", onJoinDuplicates)}
            disabled={loading || displayedCount === 0}
            title={displayedCount === totalCount
              ? "Juntar itens iguais em todo o catálogo"
              : `Juntar iguais só nos ${displayedCount} produtos visíveis`}
          >
            Juntar iguais
          </button>
          <button
            className={`toolButtonTs automaticGradesToolButton ${hasAutomaticGrades ? "activeAutomaticGradesToolButton" : ""}`}
            type="button"
            onClick={() => void runBusyAction("importar-grades-catalogo", onImportAutomaticGrades)}
            disabled={loading || !hasAutomaticGrades}
            title={automaticGradesTitle}
            aria-label={automaticGradesTitle}
            aria-pressed={hasAutomaticGrades}
          >
            <span>{hasAutomaticGrades ? "Importar grades" : "Sem grades"}</span>
            {hasAutomaticGrades ? <span className="automaticGradesBadgeTs">{pendingAutomaticGradesCount}</span> : null}
          </button>
        </ToolActionGroup>

        <ToolActionGroup label="Lista" className="toolActionGroupDangerTs">
          <button
            className="toolButtonTs danger"
            type="button"
            onClick={() => void runBusyAction("limpar-lista", onClearProducts)}
            title="Remove todos os produtos do catálogo ativo"
          >
            Limpar lista
          </button>
        </ToolActionGroup>
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
  orderingDragEnabled,
  createSetMode,
  createSetKeys,
  onCancelOrdering,
  onToggleOrderingDrag,
}: Pick<
  ProductListControlsProps,
  "orderingMode" | "orderingSelectedCount" | "orderingDragEnabled" | "createSetMode" | "createSetKeys" | "onCancelOrdering" | "onToggleOrderingDrag"
>) {
  if (orderingMode) {
    return (
      <div className="listModeContextTs contextTone-ordering" role="status" aria-live="polite">
        <div className="listModeContextMainTs">
          <strong>Ordenação ativa</strong>
          <span>
            {orderingDragEnabled
              ? "Clique para priorizar como sempre. Com o addon ligado, use a alça ⋮⋮ para arrastar e soltar."
              : "Selecione linhas para montar a prioridade. Enter seleciona; Shift+Enter remove; setas movem."}
          </span>
        </div>
        <div className="listModeContextActionsTs">
          <span className="listModeContextMetaTs">{actionText(orderingSelectedCount, "item", "itens")} priorizado{orderingSelectedCount === 1 ? "" : "s"}</span>
          <button
            className={`listModeContextButtonTs ${orderingDragEnabled ? "activeListModeContextButtonTs" : "secondaryListModeContextButtonTs"}`}
            type="button"
            onClick={onToggleOrderingDrag}
            aria-pressed={orderingDragEnabled}
            title={orderingDragEnabled ? "Desligar arrastar itens" : "Ligar addon de arrastar itens"}
          >
            {orderingDragEnabled ? "Arrastar: ligado" : "Addon: arrastar"}
          </button>
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
  showBrandsPanel,
  formatCodesOptions,
  descriptionOptions,
  descriptionSuggestions,
  sortedBrands,
  bulkBrandValue,
  newBrand,
  bulkBrandText,
  orderingMode,
  orderingSelectedCount,
  orderingDragEnabled,
  createSetMode,
  createSetKeys,
  runBusyAction,
  onUndo,
  onRedo,
  onProductSearchChange,
  onToggleGlobalEdit,
  onToggleFormatCodesPanel,
  onToggleDescriptionPanel,
  onToggleBrandsPanel,
  onToggleOrdering,
  onCancelOrdering,
  onToggleOrderingDrag,
  onToggleCreateSets,
  onJoinDuplicates,
  onApplyMargin,
  marginLabel,
  pendingAutomaticGradesCount,
  onImportAutomaticGrades,
  onClearProducts,
  onFormatCodeOptionChange,
  onRestoreOriginalCodes,
  onCloseFormatCodesPanel,
  onFormatCodes,
  onDescriptionOptionChange,
  onCloseDescriptionPanel,
  onImproveDescriptions,
  onSelectBrand,
  onNewBrandChange,
  onBulkBrandTextChange,
  onAddBrand,
  onAddBrandsBulk,
  onApplyBrand,
  onCloseBrandsPanel,
}: ProductListControlsProps) {
  const formatCodesButtonRef = useRef<HTMLButtonElement>(null!);
  const descriptionButtonRef = useRef<HTMLButtonElement>(null!);
  const brandsButtonRef = useRef<HTMLButtonElement>(null!);
  const formatCodesPanelRef = useRef<HTMLDivElement>(null!);
  const descriptionPanelRef = useRef<HTMLDivElement>(null!);
  const brandsPanelRef = useRef<HTMLDivElement>(null!);
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
  const closeBrandsPanelAndRestoreFocus = () => {
    onCloseBrandsPanel();
    window.setTimeout(() => brandsButtonRef.current?.focus(), 0);
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

  useEffect(() => {
    if (!showBrandsPanel) {
      return;
    }

    const timerId = window.setTimeout(() => focusFirstPanelControl(brandsPanelRef.current), 0);
    return () => window.clearTimeout(timerId);
  }, [showBrandsPanel]);

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
            showBrandsPanel={showBrandsPanel}
            orderingMode={orderingMode}
            createSetMode={createSetMode}
            runBusyAction={runBusyAction}
            onToggleGlobalEdit={onToggleGlobalEdit}
            onToggleFormatCodesPanel={onToggleFormatCodesPanel}
            onToggleDescriptionPanel={onToggleDescriptionPanel}
            onToggleBrandsPanel={onToggleBrandsPanel}
            onToggleOrdering={onToggleOrdering}
            onToggleCreateSets={onToggleCreateSets}
            onJoinDuplicates={onJoinDuplicates}
            onApplyMargin={onApplyMargin}
            marginLabel={marginLabel}
            pendingAutomaticGradesCount={pendingAutomaticGradesCount}
            onImportAutomaticGrades={onImportAutomaticGrades}
            onClearProducts={onClearProducts}
            formatCodesButtonRef={formatCodesButtonRef}
            descriptionButtonRef={descriptionButtonRef}
            brandsButtonRef={brandsButtonRef}
          />

          {globalEditMode ? <EditModeContextPanel /> : null}

          <ListModeContextPanel
            orderingMode={orderingMode}
            orderingSelectedCount={orderingSelectedCount}
            orderingDragEnabled={orderingDragEnabled}
            createSetMode={createSetMode}
            createSetKeys={createSetKeys}
            onCancelOrdering={onCancelOrdering}
            onToggleOrderingDrag={onToggleOrderingDrag}
          />

          {showFormatCodesPanel ? (
            <FormatCodesPanel
              formatCodesOptions={formatCodesOptions}
              displayedCount={displayedCount}
              totalCount={totalCount}
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
              displayedCount={displayedCount}
              totalCount={totalCount}
              panelRef={descriptionPanelRef}
              runBusyAction={runBusyAction}
              onDescriptionOptionChange={onDescriptionOptionChange}
              onCloseDescriptionPanel={closeDescriptionPanelAndRestoreFocus}
              onImproveDescriptions={onImproveDescriptions}
              onPanelKeyDown={(event) => handlePanelEscape(event, closeDescriptionPanelAndRestoreFocus)}
            />
          ) : null}

          {showBrandsPanel ? (
            <BrandsPanel
              brands={sortedBrands}
              selectedBrand={bulkBrandValue}
              newBrand={newBrand}
              bulkBrandText={bulkBrandText}
              displayedCount={displayedCount}
              totalCount={totalCount}
              panelRef={brandsPanelRef}
              runBusyAction={runBusyAction}
              onSelectBrand={onSelectBrand}
              onNewBrandChange={onNewBrandChange}
              onBulkBrandTextChange={onBulkBrandTextChange}
              onAddBrand={onAddBrand}
              onAddBrandsBulk={onAddBrandsBulk}
              onApplyBrand={onApplyBrand}
              onCloseBrandsPanel={closeBrandsPanelAndRestoreFocus}
              onPanelKeyDown={(event) => handlePanelEscape(event, closeBrandsPanelAndRestoreFocus)}
            />
          ) : null}

        </div>
      </div>
    </section>
  );
}
