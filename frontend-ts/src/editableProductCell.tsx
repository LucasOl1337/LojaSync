import type { KeyboardEvent, RefObject } from "react";

import { CATEGORIES } from "./appConfig";
import type { EditingCellState } from "./appConfig";
import type { EditableField } from "./productEditing";
import type { Product } from "./types";

type EditableProductCellProps = {
  product: Product;
  field: EditableField;
  displayValue: string | number;
  editMode: boolean;
  editingCell: EditingCellState | null;
  inputRef: RefObject<HTMLInputElement | HTMLSelectElement | null>;
  sortedBrands: string[];
  onStartEdit: (product: Product, field: EditableField) => void;
  onChange: (value: string) => void;
  onCommit: () => Promise<void>;
  onKeyDown: (event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => void;
};

const FIELD_LABELS: Record<EditableField, string> = {
  nome: "nome",
  marca: "marca",
  codigo: "codigo",
  quantidade: "quantidade",
  preco: "custo",
  preco_final: "venda",
  categoria: "categoria",
};

const EMPTY_ACTION_LABELS: Record<EditableField, string> = {
  nome: "Adicionar nome",
  marca: "Adicionar marca",
  codigo: "Adicionar codigo",
  quantidade: "Adicionar quantidade",
  preco: "Adicionar custo",
  preco_final: "Adicionar venda",
  categoria: "Adicionar categoria",
};

export function EditableProductCell({
  product,
  field,
  displayValue,
  editMode,
  editingCell,
  inputRef,
  sortedBrands,
  onStartEdit,
  onChange,
  onCommit,
  onKeyDown,
}: EditableProductCellProps) {
  if (!editMode) {
    return field === "nome" ? <strong>{displayValue || "-"}</strong> : <>{displayValue || "-"}</>;
  }

  const isEditing = editingCell?.orderingKey === product.ordering_key && editingCell.field === field;
  if (!isEditing) {
    const rawValue = String(displayValue ?? "").trim();
    const emptyValue = !rawValue || rawValue === "-";
    const visibleValue = emptyValue ? EMPTY_ACTION_LABELS[field] : displayValue;
    const accessibleLabel = emptyValue
      ? `${EMPTY_ACTION_LABELS[field]} para ${product.nome}`
      : `Editar ${FIELD_LABELS[field]} de ${product.nome}: ${rawValue}`;
    const buttonTitle = emptyValue
      ? `${EMPTY_ACTION_LABELS[field]} para este item`
      : `Editar ${FIELD_LABELS[field]}`;
    return (
      <button
        className={`cellActionButton ${field === "nome" ? "nameCellButton" : ""}`}
        type="button"
        onClick={() => onStartEdit(product, field)}
        aria-label={accessibleLabel}
        title={buttonTitle}
      >
        {field === "nome" ? (
          <strong className={emptyValue ? "cellActionPlaceholderTs" : ""}>{visibleValue}</strong>
        ) : emptyValue ? (
          <span className="cellActionPlaceholderTs">{visibleValue}</span>
        ) : (
          visibleValue
        )}
      </button>
    );
  }

  if (field === "categoria") {
    const inputLabel = `Editar ${FIELD_LABELS[field]} de ${product.nome}`;
    return (
      <select
        ref={inputRef as RefObject<HTMLSelectElement>}
        className="cellEditInput"
        value={editingCell.value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={() => void onCommit()}
        onKeyDown={onKeyDown}
        aria-label={inputLabel}
        title={inputLabel}
      >
        <option value="">Selecionar...</option>
        {CATEGORIES.map((category) => (
          <option key={category} value={category}>{category}</option>
        ))}
      </select>
    );
  }

  if (field === "marca") {
    const inputLabel = `Editar ${FIELD_LABELS[field]} de ${product.nome}`;
    return (
      <select
        ref={inputRef as RefObject<HTMLSelectElement>}
        className="cellEditInput"
        value={editingCell.value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={() => void onCommit()}
        onKeyDown={onKeyDown}
        aria-label={inputLabel}
        title={inputLabel}
      >
        <option value="">Selecionar...</option>
        {sortedBrands.map((brand) => (
          <option key={brand} value={brand}>{brand}</option>
        ))}
      </select>
    );
  }

  const inputLabel = `Editar ${FIELD_LABELS[field]} de ${product.nome}`;
  return (
    <input
      ref={inputRef as RefObject<HTMLInputElement>}
      className={`cellEditInput ${field === "quantidade" || field === "preco" || field === "preco_final" ? "numericCellEditInput" : ""}`}
      value={editingCell.value}
      onChange={(event) => onChange(event.target.value)}
      onBlur={() => void onCommit()}
      onKeyDown={onKeyDown}
      inputMode={field === "quantidade" ? "numeric" : field === "preco" || field === "preco_final" ? "decimal" : "text"}
      aria-label={inputLabel}
      title={inputLabel}
    />
  );
}
