import type { KeyboardEvent, MutableRefObject } from "react";

import type { GradeProductStatus } from "./gradeLogic";
import type { Product, UiGradeFamily } from "./types";

type GradeSizeGroup = {
  key: string;
  label: string;
  hint: string;
  items: string[];
};

type GradeModalProps = {
  products: Product[];
  selectedProduct: Product | null;
  selectedOrderingKey: string | null;
  selectedStatus: GradeProductStatus | null;
  nextPendingGradeKey: string | null;
  currentGradeTotal: number;
  gradeDraft: Record<string, string>;
  draftDirty: boolean;
  transitionLocked: boolean;
  gradeFamiliesDraft: UiGradeFamily[];
  groupedGradeSizes: GradeSizeGroup[];
  activeGradeFamily: GradeSizeGroup | null;
  erpSizes: string[];
  erpOrderText: string;
  newGradeSize: string;
  validationError: string | null;
  modalError: string | null;
  gradeInputRefs: MutableRefObject<Record<string, HTMLInputElement | null>>;
  getProductStatus: (product: Product) => GradeProductStatus;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onClose: () => void;
  onExecuteGrades: () => Promise<void>;
  onStopGrades: () => Promise<void>;
  onSelectProduct: (orderingKey: string) => void;
  onGradeStartTab: (event: KeyboardEvent<HTMLElement>) => void;
  onSelectNextPendingGrade: () => void;
  onAddFamily: () => Promise<void>;
  onNewGradeSizeChange: (value: string) => void;
  onAddVisualSize: () => Promise<void>;
  onFamilyLabelChange: (familyId: string, label: string) => void;
  onMoveSizeBetweenFamilies: (familyId: string, size: string, direction: -1 | 1) => Promise<void>;
  onRenameSizeInFamily: (familyId: string, size: string) => Promise<void>;
  onRemoveSizeFromFamilies: (size: string) => Promise<void>;
  onMoveVisualSize: (familyId: string, size: string, direction: -1 | 1) => Promise<void>;
  onSetActiveGradeFamily: (familyId: string) => void;
  onUpdateGradeDraftValue: (size: string, value: string) => void;
  onGradeInputKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onClearSelectedGrade: () => Promise<void>;
  onClearAllGrades: () => Promise<void>;
  onSaveSelectedGrade: () => Promise<void>;
  onSaveAndNextGrade: () => Promise<void>;
};

export function GradeModal({
  products,
  selectedProduct,
  selectedOrderingKey,
  selectedStatus,
  nextPendingGradeKey,
  currentGradeTotal,
  gradeDraft,
  draftDirty,
  transitionLocked,
  gradeFamiliesDraft,
  groupedGradeSizes,
  activeGradeFamily,
  erpSizes,
  erpOrderText,
  newGradeSize,
  validationError,
  modalError,
  gradeInputRefs,
  getProductStatus,
  runBusyAction,
  onClose,
  onExecuteGrades,
  onStopGrades,
  onSelectProduct,
  onGradeStartTab,
  onSelectNextPendingGrade,
  onAddFamily,
  onNewGradeSizeChange,
  onAddVisualSize,
  onFamilyLabelChange,
  onMoveSizeBetweenFamilies,
  onRenameSizeInFamily,
  onRemoveSizeFromFamilies,
  onMoveVisualSize,
  onSetActiveGradeFamily,
  onUpdateGradeDraftValue,
  onGradeInputKeyDown,
  onClearSelectedGrade,
  onClearAllGrades,
  onSaveSelectedGrade,
  onSaveAndNextGrade,
}: GradeModalProps) {
  return (
    <div className="gradeModalBackdrop" onClick={transitionLocked ? undefined : onClose}>
      <section className="gradeModalShell" onClick={(event) => event.stopPropagation()}>
        <header className="gradeModalHeader">
          <div>
            <span className="sectionTag">Inserir grade</span>
            <h3>{selectedProduct ? `${selectedProduct.nome} (${selectedProduct.codigo || "sem código"})` : "Selecione um item"}</h3>
          </div>
          <div className="gradeModalHeaderActions">
            <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("executar-grades", onExecuteGrades)} disabled={transitionLocked}>
              Executar grades
            </button>
            <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("parar-grades", onStopGrades)}>
              Parar
            </button>
          </div>
        </header>

        <div className="gradeModalBody">
          <aside className="gradeModalProductList">
            {products.map((product) => {
              const gradeStatus = getProductStatus(product);
              return (
                <button
                  key={product.ordering_key}
                  className={`gradeProductRow ${product.ordering_key === selectedOrderingKey ? "activeGradeProductRow" : ""}`}
                  type="button"
                  tabIndex={0}
                  aria-current={product.ordering_key === selectedOrderingKey ? "true" : undefined}
                  onClick={() => onSelectProduct(product.ordering_key)}
                  onKeyDown={onGradeStartTab}
                  disabled={transitionLocked}
                >
                  <div className="gradeProductRowHead">
                    <strong>{product.nome}</strong>
                    {gradeStatus.complete ? <span className="gradeStatusBadge success">✓</span> : null}
                    {!gradeStatus.complete && gradeStatus.overflow ? <span className="gradeStatusBadge danger">!</span> : null}
                    {!gradeStatus.complete && !gradeStatus.overflow && gradeStatus.pending ? <span className="gradeStatusBadge warning">!</span> : null}
                  </div>
                  <div className="gradeProductRowMeta">
                    <span>{product.codigo || "Sem código"}</span>
                    <small className={gradeStatus.overflow ? "gradeStatusTextDanger" : gradeStatus.complete ? "gradeStatusTextSuccess" : gradeStatus.pending ? "gradeStatusTextWarning" : ""}>
                      {`${gradeStatus.total}/${gradeStatus.expected} - ${gradeStatus.label}`}
                    </small>
                  </div>
                </button>
              );
            })}
          </aside>

          <div className="gradeModalEditor">
            {selectedProduct ? (
              <>
                <div className="gradeModalMeta">
                  <div><span>Quantidade do item</span><strong>{selectedProduct.quantidade}</strong></div>
                  <div><span>Categoria</span><strong>{selectedProduct.categoria || "-"}</strong></div>
                  <div><span>Marca</span><strong>{selectedProduct.marca || "-"}</strong></div>
                </div>

                {selectedStatus ? (
                  <div className={`gradeProgressSummaryTs gradeProgress-${selectedStatus.tone}`}>
                    <div>
                      <span>Fechamento da grade</span>
                      <strong>{selectedStatus.label}</strong>
                      <small>{`${selectedStatus.total}/${selectedStatus.expected} peças em grade`}</small>
                    </div>
                    <button
                      className="ghostButton miniActionButton"
                      type="button"
                      onClick={onSelectNextPendingGrade}
                      disabled={!nextPendingGradeKey || transitionLocked}
                    >
                      Próxima pendência
                    </button>
                  </div>
                ) : null}

                <details className="gradeConfigDetails" onKeyDown={onGradeStartTab}>
                  <summary>Personalizar famílias e tamanhos</summary>
                  <div className="gradeSizeManager">
                    <div className="gradeSectionHead">
                      <div>
                        <span className="sectionTag">Ordem visual dos tamanhos</span>
                        <p>Essa ordem é personalizada para o usuário. A automação continua respeitando a ordem ERP do ByteEmpresa.</p>
                      </div>
                      <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("nova-familia-grade", onAddFamily)}>
                        + Família
                      </button>
                    </div>

                    <div className="gradeSizeCreateRow">
                      <input
                        value={newGradeSize}
                        onChange={(event) => onNewGradeSizeChange(event.target.value)}
                        placeholder="Novo tamanho ou tipo"
                      />
                      <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("novo-tamanho-grade", onAddVisualSize)}>
                        Adicionar
                      </button>
                    </div>

                    <div className="gradeSizeList">
                      {groupedGradeSizes.map((group) => (
                        <section key={`manage-${group.key}`} className="gradeSizeFamilyGroup">
                          <header className="gradeFamilyHeader compact">
                            <div>
                              <input
                                className="familyLabelInput"
                                value={group.label}
                                onChange={(event) => onFamilyLabelChange(group.key, event.target.value)}
                              />
                              <p>{group.hint}</p>
                            </div>
                            <span className="totalsChipTs muted">{group.items.length}</span>
                          </header>
                          <div className="gradeSizeFamilyRows">
                            {group.items.map((size) => {
                              const familySizes = gradeFamiliesDraft.find((family) => family.id === group.key)?.sizes || [];
                              const index = familySizes.indexOf(size);
                              const familyIndex = gradeFamiliesDraft.findIndex((family) => family.id === group.key);
                              return (
                                <div key={size} className="gradeSizeRow">
                                  <strong>{size}</strong>
                                  <div className="gradeSizeRowMeta">
                                    {erpSizes.includes(size) ? <span className="totalsChipTs muted">ERP</span> : null}
                                    <button className="rowMiniButton" type="button" disabled={familyIndex <= 0} onClick={() => void runBusyAction(`mover-esquerda-${size}`, async () => onMoveSizeBetweenFamilies(group.key, size, -1))}>
                                      ←
                                    </button>
                                    <button className="rowMiniButton" type="button" onClick={() => void runBusyAction(`renomear-${size}`, async () => onRenameSizeInFamily(group.key, size))}>
                                      ✎
                                    </button>
                                    <button
                                      className="rowMiniButton dangerMiniButton"
                                      type="button"
                                      onClick={() => void runBusyAction(`remover-${size}`, async () => onRemoveSizeFromFamilies(size))}
                                    >
                                      ×
                                    </button>
                                    <button className="rowMiniButton" type="button" disabled={index <= 0} onClick={() => void runBusyAction(`subir-${size}`, async () => onMoveVisualSize(group.key, size, -1))}>
                                      ↑
                                    </button>
                                    <button
                                      className="rowMiniButton"
                                      type="button"
                                      disabled={index < 0 || index === familySizes.length - 1}
                                      onClick={() => void runBusyAction(`descer-${size}`, async () => onMoveVisualSize(group.key, size, 1))}
                                    >
                                      ↓
                                    </button>
                                    <button
                                      className="rowMiniButton"
                                      type="button"
                                      disabled={familyIndex < 0 || familyIndex === gradeFamiliesDraft.length - 1}
                                      onClick={() => void runBusyAction(`mover-direita-${size}`, async () => onMoveSizeBetweenFamilies(group.key, size, 1))}
                                    >
                                      →
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </section>
                      ))}
                    </div>

                    <div className="gradeAutomationHint">
                      <span>Ordem ERP usada pela automação:</span>
                      <strong>{erpOrderText}</strong>
                    </div>
                  </div>
                </details>

                <div className="gradeTabsShell">
                  <div className="gradeTabsBar" role="tablist" aria-label="Famílias de grade">
                    {groupedGradeSizes.map((group) => (
                      <button
                        key={group.key}
                        className={`gradeTabButton ${activeGradeFamily?.key === group.key ? "activeGradeTabButton" : ""}`}
                        type="button"
                        tabIndex={0}
                        role="tab"
                        aria-selected={activeGradeFamily?.key === group.key}
                        onClick={() => onSetActiveGradeFamily(group.key)}
                        onKeyDown={onGradeStartTab}
                      >
                        <span>{group.label}</span>
                        <small>{group.items.length}</small>
                      </button>
                    ))}
                  </div>

                  {activeGradeFamily ? (
                    <section className="gradeActiveFamilyPanel">
                      <header className="gradeFamilyHeader">
                        <div>
                          <strong>{activeGradeFamily.label}</strong>
                          <p>{activeGradeFamily.hint} Use Tab para avancar entre os campos e digite a quantidade de cada tamanho.</p>
                        </div>
                      </header>
                      <div className="gradeGridEditor horizontalGradeGrid">
                        {activeGradeFamily.items.map((size) => (
                          <label key={size} className="gradeInputCard">
                            <span>{size}</span>
                            <input
                              ref={(node) => {
                                gradeInputRefs.current[size] = node;
                              }}
                              inputMode="numeric"
                              value={gradeDraft[size] ?? ""}
                              onChange={(event) => onUpdateGradeDraftValue(size, event.target.value)}
                              onKeyDown={onGradeInputKeyDown}
                              placeholder="0"
                              disabled={transitionLocked}
                            />
                          </label>
                        ))}
                      </div>
                    </section>
                  ) : (
                    <div className="message subtle">Nenhum tamanho configurado no catálogo.</div>
                  )}
                </div>

                <div className="gradeModalFooterInfo">
                  <span>Total da grade: {currentGradeTotal}</span>
                  <span>Quantidade do produto: {selectedProduct.quantidade}</span>
                  {transitionLocked ? <span role="status">Atualizando grade...</span> : null}
                  {!transitionLocked && draftDirty ? <span className="gradeStatusTextWarning" role="status">Alterações não salvas</span> : null}
                </div>
                {validationError ? <div className="message error gradeValidationAlert">{validationError}</div> : null}
                {modalError ? <div className="message error">{modalError}</div> : null}
              </>
            ) : (
              <div className="message subtle">Selecione um produto para editar a grade.</div>
            )}
          </div>
        </div>

        <footer className="gradeModalFooter">
          <button className="ghostButton miniActionButton" type="button" onClick={onClose} disabled={transitionLocked}>
            Fechar
          </button>
          <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("limpar-grade", onClearSelectedGrade)} disabled={transitionLocked}>
            Limpar Grade
          </button>
          <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("limpar-todas-grades", onClearAllGrades)} disabled={transitionLocked}>
            Limpar Todas as Grades
          </button>
          <button className="primaryButton gradeFooterButton" type="button" onClick={() => void runBusyAction("salvar-grade", onSaveSelectedGrade)} disabled={transitionLocked}>
            Salvar
          </button>
          <button className="primaryButton gradeFooterButton" type="button" onClick={() => void runBusyAction("salvar-proxima-grade", onSaveAndNextGrade)} disabled={transitionLocked}>
            Salvar e Proxima Pendencia
          </button>
        </footer>
      </section>
    </div>
  );
}
