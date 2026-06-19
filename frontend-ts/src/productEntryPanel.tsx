import type { KeyboardEvent, LegacyRef } from "react";

import { normalizeProductQuantityInput } from "./productForm";
import { formatPercentDisplay } from "./productPricing";
import type { ProductPayload } from "./types";

type ProductEntryField = "nome" | "codigo" | "quantidade" | "preco";

type ProductEntryPanelProps = {
  form: ProductPayload;
  simpleModeEnabled: boolean;
  marginPercentual: number;
  submitting: boolean;
  nameInputRef: LegacyRef<HTMLInputElement>;
  codeInputRef: LegacyRef<HTMLInputElement>;
  quantityInputRef: LegacyRef<HTMLInputElement>;
  priceInputRef: LegacyRef<HTMLInputElement>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onFormKeyDown: (event: KeyboardEvent<HTMLFormElement>) => void;
  onInputChange: <K extends ProductEntryField>(key: K, value: ProductPayload[K]) => void;
  onSubmitProduct: () => Promise<void>;
  onApplyMargin: () => Promise<void>;
};

export function ProductEntryPanel({
  form,
  simpleModeEnabled,
  marginPercentual,
  submitting,
  nameInputRef,
  codeInputRef,
  quantityInputRef,
  priceInputRef,
  runBusyAction,
  onFormKeyDown,
  onInputChange,
  onSubmitProduct,
  onApplyMargin,
}: ProductEntryPanelProps) {
  const marginDisplay = formatPercentDisplay(marginPercentual);
  const marginAccessibleValue = marginDisplay.replace("%", " por cento");

  return (
    <>
      <section className="editorStageTs" aria-labelledby="product-entry-title">
        <div className="stageHeaderTs">
          <div className="stageLabelRowTs">
            <span className="stageStepBadgeTs" aria-hidden="true">2</span>
            <span className="sectionTag">Cadastro rápido</span>
          </div>
          <h2 className="stageTitleTs" id="product-entry-title">Entrada manual</h2>
        </div>
        <form
          className="productFormTs"
          onSubmit={(event) => {
            event.preventDefault();
            void runBusyAction("adicionar-produto", onSubmitProduct);
          }}
          onKeyDown={onFormKeyDown}
        >
          <div className={`formGridTs ${simpleModeEnabled ? "simpleModeGrid" : ""}`}>
            <label className="inputFieldTs fieldNameTs">
              <span>Nome</span>
              <input ref={nameInputRef} name="nome" value={form.nome} onChange={(event) => onInputChange("nome", event.target.value)} placeholder="Ex.: Bolsa Couro" />
            </label>
            {!simpleModeEnabled ? (
              <label className="inputFieldTs fieldCodeTs">
                <span>Código</span>
                <input ref={codeInputRef} name="codigo" value={form.codigo} onChange={(event) => onInputChange("codigo", event.target.value)} placeholder="000000" />
              </label>
            ) : null}
            <label className="inputFieldTs fieldQuantityTs">
              <span>Quantidade</span>
              <input
                ref={quantityInputRef}
                name="quantidade"
                type="number"
                min={1}
                step={1}
                aria-label="Quantidade do produto"
                value={form.quantidade}
                onChange={(event) => onInputChange("quantidade", normalizeProductQuantityInput(event.target.value))}
              />
            </label>
            <label className="inputFieldTs fieldPriceTs">
              <span>Custo</span>
              <input ref={priceInputRef} name="preco" value={form.preco} onChange={(event) => onInputChange("preco", event.target.value)} placeholder="R$ 0,00" />
            </label>
            <button className="primaryButton fullButton manualSubmitButtonTs" type="submit" disabled={submitting}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 5v14" />
                <path d="M5 12h14" />
              </svg>
              {submitting ? "Adicionando..." : "Adicionar à lista"}
            </button>
          </div>
        </form>
      </section>

      <section className="marginStageTs" aria-labelledby="margin-stage-title">
        <div className="stageHeaderTs compactStageHeader">
          <div className="stageLabelRowTs">
            <span className="stageStepBadgeTs" aria-hidden="true">3</span>
            <span className="sectionTag">Financeiro</span>
          </div>
          <h2 className="stageTitleTs" id="margin-stage-title">Margem padrão da sessão</h2>
        </div>
        <button
          className="marginControlButtonTs fullWidthToolButton"
          type="button"
          onClick={() => void runBusyAction("margem", onApplyMargin)}
          aria-label={`Alterar margem padrão da sessão. Valor atual ${marginAccessibleValue}`}
          title="Alterar margem padrão da sessão"
        >
          <span className="marginControlLabelTs">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            <span>Alterar margem</span>
          </span>
          <span className="marginBadgeTs">{marginDisplay}</span>
        </button>
      </section>
    </>
  );
}
