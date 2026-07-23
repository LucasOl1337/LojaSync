import { useMemo, useState, type KeyboardEvent, type ReactNode, type RefObject } from "react";

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

function buildScopeLabel(displayedCount: number, totalCount: number) {
  if (totalCount <= 0) return "Nenhum produto na lista";
  if (displayedCount === totalCount) return `Todo o catálogo · ${totalCount}`;
  return `Só visíveis · ${displayedCount} de ${totalCount}`;
}

function parseTrimCount(raw: string) {
  const value = Number.parseInt(String(raw || "").replace(/[^\d]/g, ""), 10);
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.min(value, 99);
}

function previewFormattedCode(sample: string, first: number, last: number) {
  let next = sample;
  if (first > 0) next = next.slice(first);
  if (last > 0) next = next.slice(0, Math.max(0, next.length - last));
  return next || "—";
}

function clampStep(raw: string, delta: number) {
  const current = parseTrimCount(raw);
  const next = Math.max(0, Math.min(99, current + delta));
  return next > 0 ? String(next) : "";
}

type ToolPanelShellProps = {
  panelRef?: RefObject<HTMLDivElement>;
  className?: string;
  icon: ReactNode;
  title: string;
  subtitle: string;
  scopeLabel: string;
  onClose: () => void;
  onPanelKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
  children: ReactNode;
  footer: ReactNode;
};

function ToolPanelShell({
  panelRef,
  className = "",
  icon,
  title,
  subtitle,
  scopeLabel,
  onClose,
  onPanelKeyDown,
  children,
  footer,
}: ToolPanelShellProps) {
  return (
    <div
      className={`toolConfigPanel toolPanelShell ${className}`.trim()}
      ref={panelRef}
      onKeyDown={onPanelKeyDown}
      role="region"
      aria-label={title}
    >
      <header className="toolPanelHeader">
        <div className="toolPanelHeaderMain">
          <span className="toolPanelIcon" aria-hidden="true">{icon}</span>
          <div className="toolPanelHeading">
            <div className="toolPanelTitleRow">
              <strong>{title}</strong>
              <span className="toolScopeChip" title="Escopo da ação">{scopeLabel}</span>
            </div>
            <p>{subtitle}</p>
          </div>
        </div>
        <button
          className="toolPanelCloseButton"
          type="button"
          onClick={onClose}
          aria-label={`Fechar ${title}`}
          title="Fechar (Esc)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </header>
      <div className="toolPanelBody">{children}</div>
      <footer className="toolConfigActions toolPanelFooter">{footer}</footer>
    </div>
  );
}

type FormatCodesPanelProps = {
  formatCodesOptions: FormatCodesOptions;
  displayedCount: number;
  totalCount: number;
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
  displayedCount,
  totalCount,
  panelRef,
  runBusyAction,
  onFormatCodeOptionChange,
  onRestoreOriginalCodes,
  onCloseFormatCodesPanel,
  onFormatCodes,
  onPanelKeyDown,
}: FormatCodesPanelProps) {
  const first = parseTrimCount(formatCodesOptions.remover_primeiros_numeros);
  const last = parseTrimCount(formatCodesOptions.remover_ultimos_numeros);
  const sample = "2601300103";
  const preview = previewFormattedCode(sample, first, last);
  const canApply = (first > 0 || last > 0) && displayedCount > 0;
  const scopeLabel = buildScopeLabel(displayedCount, totalCount);

  return (
    <ToolPanelShell
      panelRef={panelRef}
      className="formatCodesToolPanel"
      icon={
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 7h16" />
          <path d="M4 12h10" />
          <path d="M4 17h7" />
          <path d="m15 15 5 5" />
          <path d="m20 15-5 5" />
        </svg>
      }
      title="Formatar códigos"
      subtitle="Corte dígitos do começo ou do fim. Ideal após importar barcodes longos."
      scopeLabel={scopeLabel}
      onClose={onCloseFormatCodesPanel}
      onPanelKeyDown={onPanelKeyDown}
      footer={(
        <>
          <button
            className="ghostButton miniActionButton"
            type="button"
            onClick={() => void runBusyAction("restaurar-codigos", onRestoreOriginalCodes)}
            disabled={displayedCount === 0}
            title="Volta o código original de cada produto no escopo"
          >
            Restaurar originais
          </button>
          <button className="ghostButton miniActionButton" type="button" onClick={onCloseFormatCodesPanel}>
            Cancelar
          </button>
          <button
            className="primaryButton miniPrimaryButton"
            type="button"
            disabled={!canApply}
            onClick={() => void runBusyAction("formatar-codigos", onFormatCodes)}
            title={canApply ? "Aplicar corte nos códigos do escopo" : "Informe quantos dígitos cortar"}
          >
            Aplicar formatação
          </button>
        </>
      )}
    >
      <div className="toolStepCards">
        <div className="toolStepCard">
          <div className="toolStepCardHeader">
            <span className="toolStepBadge">1</span>
            <div>
              <strong>Cortar do começo</strong>
              <small>Remove dígitos à esquerda</small>
            </div>
          </div>
          <div className="toolStepper">
            <button
              type="button"
              className="toolStepperButton"
              aria-label="Diminuir dígitos do começo"
              onClick={() => onFormatCodeOptionChange("remover_primeiros_numeros", clampStep(formatCodesOptions.remover_primeiros_numeros, -1))}
            >
              −
            </button>
            <input
              className="toolStepperInput"
              inputMode="numeric"
              value={formatCodesOptions.remover_primeiros_numeros}
              onChange={(event) => onFormatCodeOptionChange("remover_primeiros_numeros", event.target.value.replace(/[^\d]/g, ""))}
              placeholder="0"
              aria-label="Quantos números apagar do começo"
            />
            <button
              type="button"
              className="toolStepperButton"
              aria-label="Aumentar dígitos do começo"
              onClick={() => onFormatCodeOptionChange("remover_primeiros_numeros", clampStep(formatCodesOptions.remover_primeiros_numeros, 1))}
            >
              +
            </button>
          </div>
        </div>

        <div className="toolStepCard">
          <div className="toolStepCardHeader">
            <span className="toolStepBadge">2</span>
            <div>
              <strong>Cortar do final</strong>
              <small>Remove dígitos à direita</small>
            </div>
          </div>
          <div className="toolStepper">
            <button
              type="button"
              className="toolStepperButton"
              aria-label="Diminuir dígitos do final"
              onClick={() => onFormatCodeOptionChange("remover_ultimos_numeros", clampStep(formatCodesOptions.remover_ultimos_numeros, -1))}
            >
              −
            </button>
            <input
              className="toolStepperInput"
              inputMode="numeric"
              value={formatCodesOptions.remover_ultimos_numeros}
              onChange={(event) => onFormatCodeOptionChange("remover_ultimos_numeros", event.target.value.replace(/[^\d]/g, ""))}
              placeholder="0"
              aria-label="Quantos números apagar do final"
            />
            <button
              type="button"
              className="toolStepperButton"
              aria-label="Aumentar dígitos do final"
              onClick={() => onFormatCodeOptionChange("remover_ultimos_numeros", clampStep(formatCodesOptions.remover_ultimos_numeros, 1))}
            >
              +
            </button>
          </div>
        </div>
      </div>

      <div className="toolPreviewCard" aria-live="polite">
        <div className="toolPreviewLabel">
          <strong>Exemplo ao vivo</strong>
          <span>{first || last ? `−${first} início · −${last} fim` : "Ajuste os valores para ver o efeito"}</span>
        </div>
        <div className="toolPreviewFlow">
          <code className="toolPreviewCode">{sample}</code>
          <span className="toolPreviewArrow" aria-hidden="true">→</span>
          <code className={`toolPreviewCode toolPreviewResult ${canApply ? "isReady" : ""}`}>{preview}</code>
        </div>
      </div>
    </ToolPanelShell>
  );
}

type DescriptionPanelProps = {
  descriptionOptions: DescriptionOptions;
  descriptionSuggestions: DescriptionCleanupSuggestion[];
  displayedCount: number;
  totalCount: number;
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
  displayedCount,
  totalCount,
  panelRef,
  runBusyAction,
  onDescriptionOptionChange,
  onCloseDescriptionPanel,
  onImproveDescriptions,
  onPanelKeyDown,
}: DescriptionPanelProps) {
  const [termDraft, setTermDraft] = useState("");
  const selectedTerms = parseDescriptionRemovalTerms(descriptionOptions.remover_termos);
  const scopeLabel = buildScopeLabel(displayedCount, totalCount);
  const hasRules = descriptionOptions.remover_especiais || descriptionOptions.remover_numeros || selectedTerms.length > 0;
  const canApply = hasRules && displayedCount > 0;

  const visibleSuggestions = useMemo(() => {
    const selected = new Set(selectedTerms.map((term) => term.toLocaleLowerCase("pt-BR")));
    return descriptionSuggestions.filter((item) => !selected.has(item.term.toLocaleLowerCase("pt-BR")));
  }, [descriptionSuggestions, selectedTerms]);

  const addTerm = (term: string) => {
    onDescriptionOptionChange("remover_termos", addDescriptionRemovalTerm(descriptionOptions.remover_termos, term));
  };
  const removeTerm = (term: string) => {
    onDescriptionOptionChange("remover_termos", removeDescriptionRemovalTerm(descriptionOptions.remover_termos, term));
  };
  const commitTermDraft = () => {
    const next = termDraft.trim();
    if (!next) return;
    addTerm(next);
    setTermDraft("");
  };

  return (
    <ToolPanelShell
      panelRef={panelRef}
      className="descriptionCleanupPanel"
      icon={
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
        </svg>
      }
      title="Melhorar descrição"
      subtitle="Limpe nomes ruidosos da nota: caracteres, números e termos que se repetem."
      scopeLabel={scopeLabel}
      onClose={onCloseDescriptionPanel}
      onPanelKeyDown={onPanelKeyDown}
      footer={(
        <>
          <button className="ghostButton miniActionButton" type="button" onClick={onCloseDescriptionPanel}>
            Cancelar
          </button>
          <button
            className="primaryButton miniPrimaryButton"
            type="button"
            disabled={!canApply}
            onClick={() => void runBusyAction("melhorar-descricao", onImproveDescriptions)}
            title={canApply ? "Aplicar limpeza nas descrições do escopo" : "Ative uma regra ou adicione um termo"}
          >
            Aplicar limpeza
          </button>
        </>
      )}
    >
      <div className="toolOptionCards" role="group" aria-label="Regras gerais">
        <button
          type="button"
          className={`toolOptionCard ${descriptionOptions.remover_especiais ? "isActive" : ""}`}
          aria-pressed={descriptionOptions.remover_especiais}
          onClick={() => onDescriptionOptionChange("remover_especiais", !descriptionOptions.remover_especiais)}
        >
          <span className="toolOptionCardCheck" aria-hidden="true">{descriptionOptions.remover_especiais ? "✓" : ""}</span>
          <span className="toolOptionCardCopy">
            <strong>Caracteres especiais</strong>
            <small>Remove símbolos como * / # e pontuação solta</small>
          </span>
        </button>
        <button
          type="button"
          className={`toolOptionCard ${descriptionOptions.remover_numeros ? "isActive" : ""}`}
          aria-pressed={descriptionOptions.remover_numeros}
          onClick={() => onDescriptionOptionChange("remover_numeros", !descriptionOptions.remover_numeros)}
        >
          <span className="toolOptionCardCheck" aria-hidden="true">{descriptionOptions.remover_numeros ? "✓" : ""}</span>
          <span className="toolOptionCardCopy">
            <strong>Números</strong>
            <small>Tira dígitos soltos do nome/descrição</small>
          </span>
        </button>
      </div>

      <section className="toolTermsSection" aria-label="Termos para remover">
        <div className="toolTermsHeader">
          <strong>Termos para remover</strong>
          <span>{selectedTerms.length ? `${selectedTerms.length} selecionado${selectedTerms.length === 1 ? "" : "s"}` : "Opcional"}</span>
        </div>

        <div className="toolTermComposer">
          <input
            value={termDraft}
            onChange={(event) => setTermDraft(event.target.value)}
            placeholder="Digite um termo e Enter"
            aria-label="Novo termo para remover"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                commitTermDraft();
              }
            }}
          />
          <button
            className="ghostButton miniActionButton"
            type="button"
            disabled={!termDraft.trim()}
            onClick={commitTermDraft}
          >
            Adicionar
          </button>
        </div>

        <div
          className={`descriptionTermChips ${selectedTerms.length ? "" : "emptyDescriptionTermChips"}`}
          aria-label={selectedTerms.length ? "Termos selecionados para remoção" : undefined}
          aria-hidden={selectedTerms.length ? undefined : true}
        >
          {selectedTerms.length ? selectedTerms.map((term) => (
            <button
              key={term}
              className="descriptionTermChip"
              type="button"
              onClick={() => removeTerm(term)}
              title={`Remover ${term}`}
              aria-label={`Remover ${term} da seleção`}
            >
              <span>{term}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </button>
          )) : (
            <span className="toolEmptyInlineHint">Nenhum termo ainda — use as sugestões abaixo ou digite um.</span>
          )}
        </div>

        <div className="descriptionSuggestionPanel">
          <div className="descriptionSuggestionHeader">
            <strong>Sugestões da lista</strong>
            <span>{visibleSuggestions.length ? "Clique para incluir" : "Sem candidatos claros agora"}</span>
          </div>
          <div className="descriptionSuggestionList">
            {visibleSuggestions.map((suggestion) => (
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
                <span className="descriptionSuggestionCount">
                  {suggestion.count === 1 ? "1 item" : `${suggestion.count} itens`}
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>
    </ToolPanelShell>
  );
}

export function parseBrandBulkText(raw: string): string[] {
  const seen = new Set<string>();
  const brands: string[] = [];
  for (const chunk of String(raw || "").split(/[\n,;]+/)) {
    const name = chunk.trim().replace(/\s+/g, " ");
    if (!name) continue;
    const key = name.toLocaleLowerCase("pt-BR");
    if (seen.has(key)) continue;
    seen.add(key);
    brands.push(name);
  }
  return brands;
}

type BrandsPanelProps = {
  brands: string[];
  selectedBrand: string;
  newBrand: string;
  bulkBrandText: string;
  displayedCount: number;
  totalCount: number;
  panelRef?: RefObject<HTMLDivElement>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onSelectBrand: (brand: string) => void;
  onNewBrandChange: (value: string) => void;
  onBulkBrandTextChange: (value: string) => void;
  onAddBrand: () => Promise<void>;
  onAddBrandsBulk: () => Promise<void>;
  onApplyBrand: () => Promise<void>;
  onCloseBrandsPanel: () => void;
  onPanelKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
};

export function BrandsPanel({
  brands,
  selectedBrand,
  newBrand,
  bulkBrandText,
  displayedCount,
  totalCount,
  panelRef,
  runBusyAction,
  onSelectBrand,
  onNewBrandChange,
  onBulkBrandTextChange,
  onAddBrand,
  onAddBrandsBulk,
  onApplyBrand,
  onCloseBrandsPanel,
  onPanelKeyDown,
}: BrandsPanelProps) {
  const bulkPreview = parseBrandBulkText(bulkBrandText);
  const scopeLabel = buildScopeLabel(displayedCount, totalCount);
  const canApply = Boolean(selectedBrand.trim()) && displayedCount > 0;

  return (
    <ToolPanelShell
      panelRef={panelRef}
      className="brandsToolPanel"
      icon={
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20.59 13.41 11 3H4v7l9.59 9.59a2 2 0 0 0 2.82 0l4.18-4.18a2 2 0 0 0 0-2.82Z" />
          <circle cx="7.5" cy="7.5" r="1.5" />
        </svg>
      }
      title="Marcas"
      subtitle="Cadastre marcas e aplique em lote nos produtos do escopo atual."
      scopeLabel={scopeLabel}
      onClose={onCloseBrandsPanel}
      onPanelKeyDown={onPanelKeyDown}
      footer={(
        <>
          <button className="ghostButton miniActionButton" type="button" onClick={onCloseBrandsPanel}>
            Fechar
          </button>
          <button
            className="primaryButton miniPrimaryButton"
            type="button"
            disabled={!canApply}
            onClick={() => void runBusyAction("aplicar-marca", onApplyBrand)}
            title={canApply ? `Aplicar “${selectedBrand}”` : "Selecione uma marca e tenha produtos na lista"}
          >
            {selectedBrand ? `Aplicar “${selectedBrand}”` : "Aplicar marca"}
          </button>
        </>
      )}
    >
      <div className="brandsPanelLayout">
        <section className="brandsPanelSection" aria-label="Marcas cadastradas">
          <div className="brandsPanelSectionHeader">
            <strong>Escolher marca</strong>
            <span>{brands.length ? `${brands.length} salva${brands.length === 1 ? "" : "s"}` : "Nenhuma ainda"}</span>
          </div>
          <div className="brandsChipList" role="listbox" aria-label="Lista de marcas">
            {brands.length ? brands.map((brand) => {
              const active = brand === selectedBrand;
              return (
                <button
                  key={brand}
                  className={`brandsChipButton ${active ? "activeBrandsChipButton" : ""}`}
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => onSelectBrand(brand)}
                  title={active ? `${brand} (selecionada)` : `Selecionar ${brand}`}
                >
                  {brand}
                </button>
              );
            }) : (
              <span className="brandsEmptyHint">Cadastre a primeira marca ao lado.</span>
            )}
          </div>
          <p className="toolFieldHint brandsScopeHint">
            {canApply
              ? `Pronto para aplicar em ${scopeLabel.toLowerCase()}.`
              : "Selecione uma marca para liberar a aplicação."}
          </p>
        </section>

        <section className="brandsPanelSection" aria-label="Cadastrar marcas">
          <div className="brandsPanelSectionHeader">
            <strong>Cadastrar</strong>
            <span>Uma ou várias</span>
          </div>
          <div className="toolConfigGrid brandsComposerGrid">
            <label className="toolField">
              <span>Nova marca</span>
              <input
                value={newBrand}
                onChange={(event) => onNewBrandChange(event.target.value)}
                placeholder="Ex.: Nike"
                aria-label="Nova marca"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && newBrand.trim()) {
                    event.preventDefault();
                    void runBusyAction("nova-marca", onAddBrand);
                  }
                }}
              />
            </label>
            <div className="brandsComposerActions">
              <button
                className="ghostButton miniActionButton"
                type="button"
                disabled={!newBrand.trim()}
                onClick={() => void runBusyAction("nova-marca", onAddBrand)}
              >
                Adicionar
              </button>
            </div>
            <label className="toolField toolFieldWide">
              <span>Em massa</span>
              <textarea
                value={bulkBrandText}
                onChange={(event) => onBulkBrandTextChange(event.target.value)}
                placeholder={"Uma por linha\nNike\nAdidas\nPuma"}
                aria-label="Marcas em massa"
                rows={3}
              />
              <span className="toolFieldHint">
                {bulkPreview.length
                  ? `${bulkPreview.length} pronta${bulkPreview.length === 1 ? "" : "s"} · Enter, vírgula ou ;`
                  : "Separe por linha, vírgula ou ponto e vírgula"}
              </span>
            </label>
            <div className="brandsComposerActions toolFieldWide">
              <button
                className="ghostButton miniActionButton"
                type="button"
                disabled={!bulkPreview.length}
                onClick={() => void runBusyAction("marcas-em-massa", onAddBrandsBulk)}
              >
                Cadastrar em massa
              </button>
            </div>
          </div>
        </section>
      </div>
    </ToolPanelShell>
  );
}
