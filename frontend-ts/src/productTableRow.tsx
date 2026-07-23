import type { CSSProperties, DragEvent, KeyboardEvent, RefObject } from "react";

import type { EditingCellState } from "./appConfig";
import { EditableProductCell } from "./editableProductCell";
import type { EditableField } from "./productEditing";
import { buildProductNameReviewBadges, buildProductReviewFieldStatus } from "./productFilters";
import type { OrderingDragPlacement } from "./productOrdering";
import type { Product } from "./types";

type ProductTableRowProps = {
  product: Product;
  index: number;
  selectionPosition: number | undefined;
  orderingMode: boolean;
  orderingDragEnabled: boolean;
  orderingDragSourceKey: string | null;
  orderingDragOverKey: string | null;
  orderingDragPlacement: OrderingDragPlacement | null;
  isAutomationCurrentRow: boolean;
  automationTypedDescription: string | null;
  createSetMode: boolean;
  isCreateSetSelected: boolean;
  sortedBrands: string[];
  globalEditMode: boolean;
  showActionsColumn: boolean;
  editingCell: EditingCellState | null;
  inlineEditInputRef: RefObject<HTMLInputElement | HTMLSelectElement | null>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onStartInlineEdit: (product: Product, field: EditableField) => void;
  onInlineEditChange: (value: string) => void;
  onCommitInlineEdit: () => Promise<void>;
  onInlineEditKeyDown: (event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => void;
  onOrderingSelection: (orderingKey: string, options?: { allowRemove?: boolean }) => void;
  onCreateSetSelection: (orderingKey: string) => Promise<void>;
  onMoveOrderingItem: (orderingKey: string, direction: -1 | 1) => void;
  onOrderingDragStart: (orderingKey: string) => void;
  onOrderingDragOver: (orderingKey: string, placement: OrderingDragPlacement) => void;
  onOrderingDragLeave: (orderingKey: string) => void;
  onOrderingDrop: (sourceKey: string, targetKey: string, placement: OrderingDragPlacement) => void;
  onOrderingDragEnd: () => void;
  onUseProductAsTemplate: (product: Product) => void;
  onDeleteProduct: (orderingKey: string) => Promise<void>;
};

function resolveDragPlacement(event: DragEvent<HTMLElement>): OrderingDragPlacement {
  const bounds = event.currentTarget.getBoundingClientRect();
  const midpoint = bounds.top + bounds.height / 2;
  return event.clientY < midpoint ? "before" : "after";
}

export function ProductTableRow({
  product,
  index,
  selectionPosition,
  orderingMode,
  orderingDragEnabled,
  orderingDragSourceKey,
  orderingDragOverKey,
  orderingDragPlacement,
  isAutomationCurrentRow,
  automationTypedDescription,
  createSetMode,
  isCreateSetSelected,
  sortedBrands,
  globalEditMode,
  showActionsColumn,
  editingCell,
  inlineEditInputRef,
  runBusyAction,
  onStartInlineEdit,
  onInlineEditChange,
  onCommitInlineEdit,
  onInlineEditKeyDown,
  onOrderingSelection,
  onCreateSetSelection,
  onMoveOrderingItem,
  onOrderingDragStart,
  onOrderingDragOver,
  onOrderingDragLeave,
  onOrderingDrop,
  onOrderingDragEnd,
  onUseProductAsTemplate,
  onDeleteProduct,
}: ProductTableRowProps) {
  const reviewBadges = buildProductNameReviewBadges(product);
  const selectableRowActive = orderingMode || createSetMode;
  const selectedForMode = orderingMode ? Boolean(selectionPosition) : isCreateSetSelected;
  const dragActive = orderingMode && orderingDragEnabled;
  const isDragSource = dragActive && orderingDragSourceKey === product.ordering_key;
  const isDragOver = dragActive && orderingDragOverKey === product.ordering_key && orderingDragSourceKey !== product.ordering_key;
  const rowTransitionName = `product-row-${product.ordering_key.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const rowStyle = orderingMode
    ? ({ "--row-transition-name": rowTransitionName } as CSSProperties)
    : undefined;
  const rowModeLabel = orderingMode
      ? selectionPosition
      ? `Linha ${index + 1}: ${product.nome}. Posição ${selectionPosition} na nova ordem. Pressione Shift Enter para remover.${dragActive ? " Arraste pela alça para reposicionar." : ""}`
      : `Linha ${index + 1}: ${product.nome}. Pressione Enter para adicionar à ordenação.${dragActive ? " Arraste pela alça para definir a posição." : ""}`
    : createSetMode
      ? `Linha ${index + 1}: ${product.nome}. ${isCreateSetSelected ? "Selecionado para conjunto" : "Pressione Enter para selecionar para conjunto"}.`
      : undefined;
  const renderCellContent = (field: EditableField, displayValue: string | number) => (
    <EditableProductCell
      product={product}
      field={field}
      displayValue={displayValue}
      editMode={globalEditMode}
      editingCell={editingCell}
      inputRef={inlineEditInputRef}
      sortedBrands={sortedBrands}
      onStartEdit={onStartInlineEdit}
      onChange={onInlineEditChange}
      onCommit={onCommitInlineEdit}
      onKeyDown={onInlineEditKeyDown}
    />
  );
  const renderReviewableCellContent = (field: "marca" | "codigo" | "categoria", displayValue: string) => {
    const fieldStatus = buildProductReviewFieldStatus(product, field);
    if (!fieldStatus || globalEditMode) return renderCellContent(field, displayValue);

    return (
      <span
        className={`tableFieldStatusTs fieldStatus-${fieldStatus.tone}`}
        title={fieldStatus.label}
        aria-label={fieldStatus.label}
      >
        <span className="tableFieldStatusDotTs" aria-hidden="true" />
        <span className="tableFieldStatusLabelTs">{fieldStatus.label}</span>
      </span>
    );
  };

  return (
    <tr
      style={rowStyle}
      className={[
        isCreateSetSelected ? "selectedRow" : "",
        orderingMode && selectionPosition ? "orderedRow" : "",
        isAutomationCurrentRow ? "automationCurrentRow" : "",
        isDragSource ? "orderingDragSourceRow" : "",
        isDragOver && orderingDragPlacement === "before" ? "orderingDragOverBefore" : "",
        isDragOver && orderingDragPlacement === "after" ? "orderingDragOverAfter" : "",
        dragActive ? "orderingDragEnabledRow" : "",
      ].filter(Boolean).join(" ")}
      tabIndex={selectableRowActive ? 0 : undefined}
      aria-label={rowModeLabel}
      aria-selected={selectableRowActive ? selectedForMode : undefined}
      onClick={(event) => {
        if (orderingMode) {
          onOrderingSelection(product.ordering_key, {
            allowRemove: event.detail >= 3,
          });
          return;
        }
        void onCreateSetSelection(product.ordering_key);
      }}
      onKeyDown={(event) => {
        if (!selectableRowActive || event.target !== event.currentTarget) {
          return;
        }

        if (event.key !== "Enter" && event.key !== " ") {
          return;
        }

        event.preventDefault();
        if (orderingMode) {
          onOrderingSelection(product.ordering_key, {
            allowRemove: event.shiftKey,
          });
          return;
        }

        void onCreateSetSelection(product.ordering_key);
      }}
      onDragOver={(event) => {
        if (!dragActive || !orderingDragSourceKey || orderingDragSourceKey === product.ordering_key) {
          return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        onOrderingDragOver(product.ordering_key, resolveDragPlacement(event));
      }}
      onDragLeave={(event) => {
        if (!dragActive) return;
        const related = event.relatedTarget as Node | null;
        if (related && event.currentTarget.contains(related)) {
          return;
        }
        onOrderingDragLeave(product.ordering_key);
      }}
      onDrop={(event) => {
        if (!dragActive) return;
        event.preventDefault();
        event.stopPropagation();
        const sourceKey = event.dataTransfer.getData("text/plain") || orderingDragSourceKey || "";
        if (!sourceKey || sourceKey === product.ordering_key) {
          onOrderingDragEnd();
          return;
        }
        onOrderingDrop(sourceKey, product.ordering_key, resolveDragPlacement(event));
      }}
    >
      <th className="rowIndexHeaderTs" scope="row" aria-label={`Linha ${index + 1}: ${product.nome}`}>
        <div className="rowIndexCellStackTs">
          {dragActive ? (
            <button
              className="orderingDragHandleTs"
              type="button"
              draggable
              title="Arrastar para reordenar"
              aria-label={`Arrastar ${product.nome} para reordenar`}
              onClick={(event) => event.stopPropagation()}
              onDragStart={(event) => {
                event.stopPropagation();
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", product.ordering_key);
                try {
                  event.dataTransfer.setData("application/x-lojasync-ordering-key", product.ordering_key);
                } catch {
                  // Some browsers only allow a single payload type in tests/edge cases.
                }
                onOrderingDragStart(product.ordering_key);
              }}
              onDragEnd={(event) => {
                event.stopPropagation();
                onOrderingDragEnd();
              }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <circle cx="9" cy="6" r="1.6" />
                <circle cx="15" cy="6" r="1.6" />
                <circle cx="9" cy="12" r="1.6" />
                <circle cx="15" cy="12" r="1.6" />
                <circle cx="9" cy="18" r="1.6" />
                <circle cx="15" cy="18" r="1.6" />
              </svg>
            </button>
          ) : null}
          <span>{orderingMode && selectionPosition ? selectionPosition : index + 1}</span>
        </div>
      </th>
      <td>
        <div className="nameCellStack">
          {renderCellContent("nome", product.nome)}
          {isAutomationCurrentRow && automationTypedDescription && automationTypedDescription.trim() !== product.nome.trim() ? (
            <small className="automationPreviewText">{`Texto enviado: ${automationTypedDescription}`}</small>
          ) : null}
          {reviewBadges.length ? (
            <div className="productReviewBadgesTs" aria-label="Pendências de revisão">
              {reviewBadges.map((badge) => (
                <span
                  key={badge.key}
                  className={`productReviewBadgeTs reviewBadge-${badge.tone}`}
                  title={badge.label}
                >
                  {badge.label}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </td>
      <td>{renderReviewableCellContent("marca", product.marca || "-")}</td>
      <td>{renderReviewableCellContent("codigo", product.codigo || "-")}</td>
      <td>{renderCellContent("quantidade", product.quantidade)}</td>
      <td>{renderCellContent("preco", product.preco || "-")}</td>
      <td>{renderCellContent("preco_final", product.preco_final || product.preco || "-")}</td>
      <td>{renderReviewableCellContent("categoria", product.categoria || "-")}</td>
      {showActionsColumn ? (
        <td>
          <div className={`rowActionStack ${orderingMode ? "orderingRowActionStack" : ""}`}>
            {orderingMode ? (
              <button
                className={`orderingSelectionBadge compactOrderingSelectionBadge ${selectionPosition ? "activeOrderingSelectionBadge" : ""}`}
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onOrderingSelection(product.ordering_key, { allowRemove: false });
                }}
                aria-pressed={Boolean(selectionPosition)}
                aria-label={selectionPosition ? `${product.nome} está na posição ${selectionPosition}` : `Priorizar ${product.nome}`}
                title={selectionPosition ? `Posição ${selectionPosition}` : "Priorizar item"}
              >
                {selectionPosition ? `${selectionPosition}` : "Priorizar"}
              </button>
            ) : null}
            {isAutomationCurrentRow ? <span className="automationCurrentBadge">Em execução</span> : null}
            {orderingMode && selectionPosition ? (
              <>
                <button
                  className="rowMiniButton"
                  type="button"
                  onClick={(event) => { event.stopPropagation(); onMoveOrderingItem(product.ordering_key, -1); }}
                  aria-label={`Mover ${product.nome} para cima`}
                  title="Mover para cima"
                >
                  ↑
                </button>
                <button
                  className="rowMiniButton"
                  type="button"
                  onClick={(event) => { event.stopPropagation(); onMoveOrderingItem(product.ordering_key, 1); }}
                  aria-label={`Mover ${product.nome} para baixo`}
                  title="Mover para baixo"
                >
                  ↓
                </button>
              </>
            ) : null}
            {!orderingMode && !createSetMode ? (
              <>
                <button
                  className="rowTemplateButtonTs"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onUseProductAsTemplate(product);
                  }}
                  aria-label={`Usar ${product.nome} como modelo de novo produto`}
                  title="Usar como modelo"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <rect x="9" y="9" width="11" height="11" rx="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    <path d="M14.5 12v5" />
                    <path d="M12 14.5h5" />
                  </svg>
                </button>
                <button
                  className="rowDeleteButtonTs"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    void runBusyAction(`excluir-${product.ordering_key}`, async () => onDeleteProduct(product.ordering_key));
                  }}
                  aria-label={`Excluir ${product.nome}`}
                  title={`Excluir ${product.nome}`}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    <path d="M10 11v6" />
                    <path d="M14 11v6" />
                    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                  </svg>
                </button>
              </>
            ) : null}
            {createSetMode ? (
              <button
                className={`selectionHint ${isCreateSetSelected ? "selectedSelectionHint" : ""}`}
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  void onCreateSetSelection(product.ordering_key);
                }}
                aria-pressed={isCreateSetSelected}
                aria-label={isCreateSetSelected ? `${product.nome} selecionado para conjunto` : `Selecionar ${product.nome} para conjunto`}
                title={isCreateSetSelected ? "Selecionado para conjunto" : "Selecionar para conjunto"}
              >
                {isCreateSetSelected ? "Selecionado" : "Selecionar"}
              </button>
            ) : null}
          </div>
        </td>
      ) : null}
    </tr>
  );
}
