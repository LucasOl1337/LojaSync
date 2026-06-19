import type { KeyboardEvent, RefObject } from "react";

import {
  addDescriptionRemovalTerm,
  parseDescriptionRemovalTerms,
  removeDescriptionRemovalTerm,
  type DescriptionCleanupSuggestion,
} from "./descriptionCleanup";

export type FormatCodesOptions = {
  remover_primeiros_numeros: string;
  remover_ultimos_numeros: string;
};

export type DescriptionOptions = {
  remover_especiais: boolean;
  remover_numeros: boolean;
  remover_termos: string;
};

type FormatCodesPanelProps = {
  formatCodesOptions: FormatCodesOptions;
  panelRef?: RefObject<HTMLDivElement>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onFormatCodeOptionChange: (field: keyof FormatCodesOptions, value: string) => void;
  onRestoreOriginalCodes: () => Promise<void>;
  onCloseFormatCodesPanel: () => void;
  onFormatCodes: () => Promise<void>;
  onPanelKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
};

export function FormatCodesPanel({
  formatCodesOptions,
  panelRef,
  runBusyAction,
  onFormatCodeOptionChange,
  onRestoreOriginalCodes,
  onCloseFormatCodesPanel,
  onFormatCodes,
  onPanelKeyDown,
}: FormatCodesPanelProps) {
  return (
    <div className="toolConfigPanel" ref={panelRef} onKeyDown={onPanelKeyDown}>
      <div className="toolConfigIntro">
        <strong>Limpar códigos com menos risco</strong>
        <p>Use apenas estas opções para cortar números do começo ou do fim do código. Se precisar voltar atrás, use Restaurar originais.</p>
      </div>
      <div className="toolConfigGrid">
        <label className="toolField">
          <span>Quantos números apagar do começo</span>
          <input
            value={formatCodesOptions.remover_primeiros_numeros}
            onChange={(event) => onFormatCodeOptionChange("remover_primeiros_numeros", event.target.value.replace(/[^\d]/g, ""))}
            placeholder="Ex.: 2"
          />
        </label>
        <label className="toolField">
          <span>Quantos números apagar do final</span>
          <input
            value={formatCodesOptions.remover_ultimos_numeros}
            onChange={(event) => onFormatCodeOptionChange("remover_ultimos_numeros", event.target.value.replace(/[^\d]/g, ""))}
            placeholder="Ex.: 2"
          />
        </label>
      </div>
      <div className="toolConfigActions">
        <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("restaurar-codigos", onRestoreOriginalCodes)}>
          Restaurar originais
        </button>
        <button className="ghostButton miniActionButton" type="button" onClick={onCloseFormatCodesPanel}>
          Fechar
        </button>
        <button className="primaryButton miniPrimaryButton" type="button" onClick={() => void runBusyAction("formatar-codigos", onFormatCodes)}>
          Aplicar
        </button>
      </div>
    </div>
  );
}

type DescriptionPanelProps = {
  descriptionOptions: DescriptionOptions;
  descriptionSuggestions: DescriptionCleanupSuggestion[];
  panelRef?: RefObject<HTMLDivElement>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onDescriptionOptionChange: (field: keyof DescriptionOptions, value: boolean | string) => void;
  onCloseDescriptionPanel: () => void;
  onImproveDescriptions: () => Promise<void>;
  onPanelKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
};

export function DescriptionPanel({
  descriptionOptions,
  descriptionSuggestions,
  panelRef,
  runBusyAction,
  onDescriptionOptionChange,
  onCloseDescriptionPanel,
  onImproveDescriptions,
  onPanelKeyDown,
}: DescriptionPanelProps) {
  const selectedTerms = parseDescriptionRemovalTerms(descriptionOptions.remover_termos);
  const addTerm = (term: string) => {
    onDescriptionOptionChange("remover_termos", addDescriptionRemovalTerm(descriptionOptions.remover_termos, term));
  };
  const removeTerm = (term: string) => {
    onDescriptionOptionChange("remover_termos", removeDescriptionRemovalTerm(descriptionOptions.remover_termos, term));
  };

  return (
    <div className="toolConfigPanel descriptionCleanupPanel" ref={panelRef} onKeyDown={onPanelKeyDown}>
      <div className="toolConfigIntro">
        <strong>Limpar nomes e descrições</strong>
        <p>Escolha regras gerais ou adicione termos exatos encontrados na lista.</p>
      </div>
      <div className="toolConfigGrid descriptionConfigGrid">
        <label className="toolCheck">
          <input
            type="checkbox"
            checked={descriptionOptions.remover_especiais}
            onChange={(event) => onDescriptionOptionChange("remover_especiais", event.target.checked)}
          />
          <span>Remover caracteres especiais</span>
        </label>
        <label className="toolCheck">
          <input
            type="checkbox"
            checked={descriptionOptions.remover_numeros}
            onChange={(event) => onDescriptionOptionChange("remover_numeros", event.target.checked)}
          />
          <span>Remover números</span>
        </label>
        <label className="toolField toolFieldWide">
          <span>Termos exatos para remover</span>
          <textarea
            value={descriptionOptions.remover_termos}
            onChange={(event) => onDescriptionOptionChange("remover_termos", event.target.value)}
            placeholder="Ex.: OGPT, USE EXPERIENCE"
            rows={3}
          />
          <small className="toolFieldHint">Use vírgula ou Enter para separar termos.</small>
        </label>
      </div>
      <div
        className={`descriptionTermChips ${selectedTerms.length ? "" : "emptyDescriptionTermChips"}`}
        aria-label={selectedTerms.length ? "Termos selecionados para remoção" : undefined}
        aria-hidden={selectedTerms.length ? undefined : true}
      >
        {selectedTerms.map((term) => (
          <button
            key={term}
            className="descriptionTermChip"
            type="button"
            onClick={() => removeTerm(term)}
            title={`Remover ${term} da seleção`}
            aria-label={`Remover ${term} da seleção`}
          >
            <span>{term}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        ))}
      </div>
      <div className="descriptionSuggestionPanel">
        <div className="descriptionSuggestionHeader">
          <strong>Sugestões da lista atual</strong>
          <span>{descriptionSuggestions.length ? "Clique em + para adicionar" : "Sem candidatos claros agora"}</span>
        </div>
        <div className="descriptionSuggestionList">
          {descriptionSuggestions.map((suggestion) => (
            <button
              key={suggestion.term}
              className="descriptionSuggestionButton"
              type="button"
              onClick={() => addTerm(suggestion.term)}
              title={suggestion.examples[0] ? `Ex.: ${suggestion.examples[0]}` : `Adicionar ${suggestion.term}`}
              aria-label={`Adicionar ${suggestion.term} aos termos para remover`}
            >
              <span className="descriptionSuggestionPlus" aria-hidden="true">+</span>
              <span className="descriptionSuggestionTerm">{suggestion.term}</span>
              <span className="descriptionSuggestionCount">{suggestion.count === 1 ? "1 item" : `${suggestion.count} itens`}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="toolConfigActions">
        <button className="ghostButton miniActionButton" type="button" onClick={onCloseDescriptionPanel}>
          Fechar
        </button>
        <button className="primaryButton miniPrimaryButton" type="button" onClick={() => void runBusyAction("melhorar-descricao", onImproveDescriptions)}>
          Aplicar
        </button>
      </div>
    </div>
  );
}
