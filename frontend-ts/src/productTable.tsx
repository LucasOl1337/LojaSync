import type { FocusEvent, KeyboardEvent, RefObject } from "react";

import { CATEGORIES } from "./appConfig";
import type { EditingCellState } from "./appConfig";
import type { EditableField } from "./productEditing";
import { ProductTableRow } from "./productTableRow";
import type { ProductQuickFilter, ProductQuickFilterEmptyState } from "./productFilters";
import type { Product } from "./types";
import { actionText } from "./uiFormatting";

type ProductTableProps = {
  loading: boolean;
  products: Product[];
  totalProductCount: number;
  orderingMode: boolean;
  orderingSelectionIndex: Map<string, number>;
  automationIsRunning: boolean;
  automationCurrentOrderingKey: string | null;
  automationTypedDescription: string | null;
  createSetMode: boolean;
  createSetKeys: string[];
  sortedBrands: string[];
  newBrand: string;
  bulkBrandValue: string;
  bulkCategoryValue: string;
  showBulkBrandMenu: boolean;
  showBulkCategoryMenu: boolean;
  showBrandComposer: boolean;
  bulkBrandMenuRef: RefObject<HTMLDivElement>;
  bulkCategoryMenuRef: RefObject<HTMLDivElement>;
  emptyState: ProductQuickFilterEmptyState;
  globalEditMode: boolean;
  editingCell: EditingCellState | null;
  inlineEditInputRef: RefObject<HTMLInputElement | HTMLSelectElement | null>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onStartInlineEdit: (product: Product, field: EditableField) => void;
  onInlineEditChange: (value: string) => void;
  onCommitInlineEdit: () => Promise<void>;
  onInlineEditKeyDown: (event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => void;
  onToggleBulkBrandMenu: () => void;
  onToggleBulkCategoryMenu: () => void;
  onCloseBulkBrandMenu: () => void;
  onCloseBulkCategoryMenu: () => void;
  onToggleBrandComposer: () => void;
  onNewBrandChange: (value: string) => void;
  onSubmitBrand: () => Promise<void>;
  onApplyBrand: (brand: string) => Promise<void>;
  onApplyCategory: (category: string) => Promise<void>;
  onToggleGlobalEdit: () => void;
  onOrderingSelection: (orderingKey: string, options?: { allowRemove?: boolean }) => void;
  onCreateSetSelection: (orderingKey: string) => Promise<void>;
  onMoveOrderingItem: (orderingKey: string, direction: -1 | 1) => void;
  onDeleteProduct: (orderingKey: string) => Promise<void>;
  onQuickFilterChange: (filter: ProductQuickFilter) => void;
  onProductSearchChange: (query: string) => void;
  onReviewFilterChange: (filter: ProductQuickFilter) => void;
};

function TableSkeleton({ columnCount }: { columnCount: number }) {
  return (
    <div className="tableSkeletonTs" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, rowIndex) => (
        <div className="tableSkeletonRowTs" key={`table-skeleton-${rowIndex}`}>
          {Array.from({ length: columnCount }).map((__, cellIndex) => (
            <span className="tableSkeletonCellTs" key={`table-skeleton-${rowIndex}-${cellIndex}`} />
          ))}
        </div>
      ))}
    </div>
  );
}

function LoadingTableState({ columnCount }: { columnCount: number }) {
  return (
    <div className="tableStateTs tableStateLoadingTs" role="status" aria-live="polite" aria-busy="true">
      <div className="tableStateMainTs">
        <span className="tableStateKickerTs">Sincronizando lista</span>
        <strong>Carregando produtos, totais e marcas.</strong>
        <span>O painel continua pronto para receber importações enquanto a tabela atualiza os dados locais.</span>
      </div>
      <TableSkeleton columnCount={columnCount} />
    </div>
  );
}

function EmptyTableState({
  emptyState,
  onQuickFilterChange,
  onProductSearchChange,
}: {
  emptyState: ProductQuickFilterEmptyState;
  onQuickFilterChange: (filter: ProductQuickFilter) => void;
  onProductSearchChange: (query: string) => void;
}) {
  const checklistItems = emptyState.searchActive
    ? [
        "A busca considera nome, marca, codigo, codigo original, categoria e descricao.",
        "Limpe a busca para voltar ao recorte atual da lista.",
        "Filtros rapidos continuam preservados enquanto voce pesquisa.",
      ]
    : emptyState.actions.length
    ? [
        "Volte para Todos para conferir itens fora do recorte atual.",
        "Use Revisar para priorizar pendencias reais quando houver alertas.",
        "Nenhuma acao em massa foi aplicada pelo filtro vazio.",
      ]
    : [
        "Importe um romaneio pelo painel lateral para preencher a tabela.",
        "Use a entrada manual quando houver poucos itens fora do arquivo.",
        "Filtros e revisao ficam disponiveis assim que houver produtos ativos.",
      ];
  const stateKicker = emptyState.searchActive
    ? "Busca sem resultado"
    : emptyState.actions.length
      ? "Filtro sem resultado"
      : "Lista vazia";

  return (
    <div className="tableStateTs">
      <div className="tableStateMainTs">
        <span className="tableStateKickerTs">{stateKicker}</span>
        <strong>{emptyState.title}</strong>
        <span>{emptyState.detail}</span>
        {emptyState.searchActive ? (
          <div className="tableStateActionsTs" role="group" aria-label="Acoes da busca">
            <button className="quickFilterContextButtonTs contextAction-review" type="button" onClick={() => onProductSearchChange("")}>
              Limpar busca
            </button>
          </div>
        ) : emptyState.actions.length ? (
          <div className="tableStateActionsTs" role="group" aria-label="Acoes do estado vazio">
            {emptyState.actions.map((action) => (
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
        ) : null}
      </div>

      <ul className="tableStateChecklistTs" aria-label="Proximos passos da lista">
        {checklistItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function ProductTable({
  loading,
  products,
  totalProductCount,
  orderingMode,
  orderingSelectionIndex,
  automationIsRunning,
  automationCurrentOrderingKey,
  automationTypedDescription,
  createSetMode,
  createSetKeys,
  sortedBrands,
  newBrand,
  bulkBrandValue,
  bulkCategoryValue,
  showBulkBrandMenu,
  showBulkCategoryMenu,
  showBrandComposer,
  bulkBrandMenuRef,
  bulkCategoryMenuRef,
  emptyState,
  globalEditMode,
  editingCell,
  inlineEditInputRef,
  runBusyAction,
  onStartInlineEdit,
  onInlineEditChange,
  onCommitInlineEdit,
  onInlineEditKeyDown,
  onToggleBulkBrandMenu,
  onToggleBulkCategoryMenu,
  onCloseBulkBrandMenu,
  onCloseBulkCategoryMenu,
  onToggleBrandComposer,
  onNewBrandChange,
  onSubmitBrand,
  onApplyBrand,
  onApplyCategory,
  onToggleGlobalEdit,
  onOrderingSelection,
  onCreateSetSelection,
  onMoveOrderingItem,
  onDeleteProduct,
  onQuickFilterChange,
  onProductSearchChange,
  onReviewFilterChange,
}: ProductTableProps) {
  const visibleItemsLabel = loading ? "Atualizando lista" : actionText(products.length, "item visivel", "itens visiveis");
  const totalItemsLabel = actionText(totalProductCount, "item", "itens");
  const bulkActionsBlockedByMode = !loading && products.length > 0 && (orderingMode || createSetMode);
  const bulkActionsBlockedByEditLock = !loading && products.length > 0 && !globalEditMode && !bulkActionsBlockedByMode;
  const bulkActionsDisabled = loading || products.length === 0 || bulkActionsBlockedByEditLock || bulkActionsBlockedByMode;
  const filteredBulkScopeActive = !loading && totalProductCount > products.length;
  const bulkScopeHint = filteredBulkScopeActive ? `${visibleItemsLabel} no filtro` : null;
  const bulkScopeLabel = (() => {
    if (loading) return "Atualizando escopo";
    if (products.length === 0) return "Sem itens no escopo";
    if (bulkActionsBlockedByMode) return "Edicao em lote pausada";
    if (bulkActionsBlockedByEditLock) return "Edicao em lote travada";
    if (filteredBulkScopeActive) return `Aplicar aos ${totalItemsLabel}`;
    return "Aplicar a todos";
  })();
  const bulkScopeDetail = (() => {
    if (loading) return "Aguardando atualizacao da lista.";
    if (products.length === 0) return "Importe ou adicione produtos para liberar acoes em lote.";
    if (orderingMode) return "Finalize a ordenacao para liberar a edicao em lote.";
    if (createSetMode) return "Finalize os conjuntos para liberar a edicao em lote.";
    if (bulkActionsBlockedByEditLock) return "Permita edicoes para aplicar marca ou categoria em lote.";
    if (filteredBulkScopeActive) return "Ha itens fora do filtro ativo; a confirmacao aparece antes de aplicar fora do recorte.";
    return `${totalItemsLabel} no escopo atual.`;
  })();
  const bulkActionsAriaLabel = bulkActionsDisabled
    ? `Acoes em lote indisponiveis: ${bulkScopeDetail}`
    : bulkScopeHint
    ? `Acoes em lote globais para ${totalItemsLabel}; ${bulkScopeHint}; confirmacao obrigatoria fora do filtro`
    : "Acoes em lote da tabela";
  const bulkBrandMenuId = "product-table-bulk-brand-panel";
  const bulkBrandTitleId = "product-table-bulk-brand-title";
  const bulkBrandComposerId = "product-table-bulk-brand-composer";
  const bulkCategoryMenuId = "product-table-bulk-category-panel";
  const bulkCategoryTitleId = "product-table-bulk-category-title";
  const tableModeLabel = orderingMode
    ? "Ordenacao ativa"
    : createSetMode
      ? `Conjunto ${Math.min(createSetKeys.length, 2)}/2`
      : "Fluxo normal";
  const showRowActions = globalEditMode || orderingMode || createSetMode || automationIsRunning;
  const tableColumnCount = showRowActions ? 9 : 8;
  const handleBulkPopoverKeyDown = <TElement extends HTMLElement>(
    event: KeyboardEvent<TElement>,
    onClose: () => void,
    returnFocusRef?: RefObject<HTMLDivElement>
  ) => {
    if (event.key !== "Escape") {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    onClose();
    window.setTimeout(() => {
      returnFocusRef?.current?.querySelector<HTMLButtonElement>(".tableBulkButtonTs")?.focus();
    }, 0);
  };
  const handleBulkControlBlur = (
    event: FocusEvent<HTMLDivElement>,
    onClose: () => void
  ) => {
    const nextTarget = event.relatedTarget;

    if (nextTarget instanceof Node && event.currentTarget.contains(nextTarget)) {
      return;
    }

    onClose();
  };

  return (
    <section className={["tableWrapperTs", orderingMode ? "orderingModeActive" : "", createSetMode ? "createSetModeActive" : ""].filter(Boolean).join(" ")} aria-labelledby="product-table-title">
      <div className="tableHeaderTs">
        <div className="tableHeaderCopyTs">
          <span className="tableHeaderKickerTs">Tabela de produtos</span>
          <h2 className="tableHeaderTitleTs" id="product-table-title">Itens preparados para ERP</h2>
        </div>
        <div className="tableHeaderChipsTs" aria-label="Resumo da tabela">
          <span className="tableHeaderChipTs">{visibleItemsLabel}</span>
          <span className={`tableHeaderChipTs ${globalEditMode ? "tableHeaderChipActiveTs" : ""}`}>
            {globalEditMode ? "Edicao livre" : "Edicao travada"}
          </span>
          <span className={`tableHeaderChipTs ${orderingMode || createSetMode ? "tableHeaderChipActiveTs" : ""}`}>
            {tableModeLabel}
          </span>
        </div>
      </div>

      <div
        className={[
          "tableBulkActionsTs",
          filteredBulkScopeActive ? "filteredBulkActionsTs" : "",
          bulkActionsDisabled && !loading && products.length ? "tableBulkActionsLockedTs" : "",
        ].filter(Boolean).join(" ")}
        aria-label={bulkActionsAriaLabel}
      >
        <div className="tableBulkActionsCopyTs">
          <span className="tableBulkActionsLabelTs">Escopo em lote</span>
          <div className="tableBulkScopeSummaryTs">
            <strong>{bulkScopeLabel}</strong>
            {bulkScopeHint ? <span className="tableBulkActionsHintTs">{bulkScopeHint}</span> : null}
            <small>{bulkScopeDetail}</small>
          </div>
        </div>
        {bulkActionsBlockedByEditLock ? (
          <button className="tableBulkUnlockButtonTs" type="button" onClick={onToggleGlobalEdit}>
            Permitir edicoes
          </button>
        ) : null}
        {!bulkActionsDisabled ? (
          <div className="tableBulkControlsTs">
            <div className="bulkHeaderCell tableBulkControlTs" ref={bulkBrandMenuRef} onBlur={(event) => handleBulkControlBlur(event, onCloseBulkBrandMenu)}>
              <button
                className="bulkHeaderButton tableBulkButtonTs"
                type="button"
                onClick={onToggleBulkBrandMenu}
                onKeyDown={(event) => handleBulkPopoverKeyDown(event, onCloseBulkBrandMenu)}
                title="Aplicar marca em lote"
                aria-haspopup="dialog"
                aria-controls={bulkBrandMenuId}
                aria-expanded={showBulkBrandMenu}
              >
                <span>Marca:</span>
                <small>{bulkBrandValue || "Selecionar"}</small>
              </button>
              {showBulkBrandMenu ? (
                <div
                  className="bulkMenuPopover"
                  id={bulkBrandMenuId}
                  role="dialog"
                  aria-labelledby={bulkBrandTitleId}
                  onKeyDown={(event) => handleBulkPopoverKeyDown(event, onCloseBulkBrandMenu, bulkBrandMenuRef)}
                >
                  <div className="bulkMenuHeader">
                    <strong id={bulkBrandTitleId}>Aplicar marca</strong>
                    <button
                      className="bulkAddButton"
                      type="button"
                      onClick={onToggleBrandComposer}
                      aria-label="Adicionar nova marca em lote"
                      aria-controls={bulkBrandComposerId}
                      aria-expanded={showBrandComposer}
                    >
                      +
                    </button>
                  </div>
                  {showBrandComposer ? (
                    <div className="bulkComposer" id={bulkBrandComposerId}>
                      <input value={newBrand} onChange={(event) => onNewBrandChange(event.target.value)} placeholder="Nova marca" aria-label="Nova marca" />
                      <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("nova-marca", onSubmitBrand)} disabled={!newBrand.trim()}>
                        Salvar
                      </button>
                    </div>
                  ) : null}
                  <div className="bulkMenuList">
                    {sortedBrands.map((brand) => (
                      <button key={brand} className="bulkMenuItem" type="button" onClick={() => void runBusyAction("aplicar-marca", async () => onApplyBrand(brand))}>
                        {brand}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="bulkHeaderCell tableBulkControlTs" ref={bulkCategoryMenuRef} onBlur={(event) => handleBulkControlBlur(event, onCloseBulkCategoryMenu)}>
              <button
                className="bulkHeaderButton tableBulkButtonTs"
                type="button"
                onClick={onToggleBulkCategoryMenu}
                onKeyDown={(event) => handleBulkPopoverKeyDown(event, onCloseBulkCategoryMenu)}
                title="Aplicar categoria em lote"
                aria-haspopup="dialog"
                aria-controls={bulkCategoryMenuId}
                aria-expanded={showBulkCategoryMenu}
              >
                <span>Categoria:</span>
                <small>{bulkCategoryValue || "Selecionar"}</small>
              </button>
              {showBulkCategoryMenu ? (
                <div
                  className="bulkMenuPopover"
                  id={bulkCategoryMenuId}
                  role="dialog"
                  aria-labelledby={bulkCategoryTitleId}
                  onKeyDown={(event) => handleBulkPopoverKeyDown(event, onCloseBulkCategoryMenu, bulkCategoryMenuRef)}
                >
                  <div className="bulkMenuHeader">
                    <strong id={bulkCategoryTitleId}>Aplicar categoria</strong>
                  </div>
                  <div className="bulkMenuList">
                    {CATEGORIES.map((category) => (
                      <button key={category} className="bulkMenuItem" type="button" onClick={() => void runBusyAction("aplicar-categoria", async () => onApplyCategory(category))}>
                        {category}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      <div className={`tableScrollTs ${loading || !products.length ? "tableScrollStateTs" : ""}`}>
        <table className={`productsTableTs ${showRowActions ? "" : "productsTableNoActionsTs"}`}>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Nome</th>
              <th scope="col">Marca</th>
              <th scope="col">Codigo</th>
              <th scope="col">Qtd</th>
              <th scope="col">Custo</th>
              <th scope="col">Venda</th>
              <th scope="col">Categoria</th>
              {showRowActions ? <th scope="col">Acoes</th> : null}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={tableColumnCount} className="emptyState richTableStateCell">
                  <LoadingTableState columnCount={tableColumnCount} />
                </td>
              </tr>
            ) : products.length ? (
              products.map((product, index) => {
                const selectionPosition = orderingSelectionIndex.get(product.ordering_key);
                const isAutomationCurrentRow = automationIsRunning && automationCurrentOrderingKey === product.ordering_key;
                return (
                  <ProductTableRow
                    key={product.ordering_key}
                    product={product}
                    index={index}
                    selectionPosition={selectionPosition}
                    orderingMode={orderingMode}
                    isAutomationCurrentRow={isAutomationCurrentRow}
                    automationTypedDescription={automationTypedDescription}
                    createSetMode={createSetMode}
                    isCreateSetSelected={createSetKeys.includes(product.ordering_key)}
                    sortedBrands={sortedBrands}
                    globalEditMode={globalEditMode}
                    showActionsColumn={showRowActions}
                    editingCell={editingCell}
                    inlineEditInputRef={inlineEditInputRef}
                    runBusyAction={runBusyAction}
                    onStartInlineEdit={onStartInlineEdit}
                    onInlineEditChange={onInlineEditChange}
                    onCommitInlineEdit={onCommitInlineEdit}
                    onInlineEditKeyDown={onInlineEditKeyDown}
                    onOrderingSelection={onOrderingSelection}
                    onCreateSetSelection={onCreateSetSelection}
                    onMoveOrderingItem={onMoveOrderingItem}
                    onDeleteProduct={onDeleteProduct}
                    onReviewFilterChange={onReviewFilterChange}
                  />
                );
              })
            ) : (
              <tr>
                <td colSpan={tableColumnCount} className="emptyState richTableStateCell">
                  <EmptyTableState
                    emptyState={emptyState}
                    onQuickFilterChange={onQuickFilterChange}
                    onProductSearchChange={onProductSearchChange}
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
