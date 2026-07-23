import type { ChangeEvent, RefObject } from "react";

import type { ImportDiagnosticsChip, ImportHistoryEntry } from "./uiFormatting";
import {
  formatImportHistoryWhen,
  formatImportSourceDisplayName,
  formatImportValidationStatus,
  importValidationStatusTone,
} from "./uiFormatting";
import { ImportDiagnosticsPanel } from "./importDiagnostics";
import { ImportProgressPanel } from "./importProgressPanel";

type ImportStagePanelProps = {
  importing: boolean;
  localExperimentLoading: boolean;
  documentCount: number;
  activeFileName: string | null;
  importProgressMessage: string | null;
  importJobMessage?: string | null;
  importJobStage?: string | null;
  importJobStartedAt?: number | null;
  importProcessLog?: Array<Record<string, unknown>> | null;
  importMode?: "llm" | "local" | null;
  activeDocumentIndex?: number | null;
  importError: string | null;
  importSuccessMessage: string | null;
  validationStatus: string;
  diagnosticsChips: ImportDiagnosticsChip[];
  warnings: string[];
  recentImports: ImportHistoryEntry[];
  inputRef: RefObject<HTMLInputElement>;
  onImportPrimaryClick: () => void;
  onLocalExperimentClick: () => void;
  onFilePickerClick: () => void;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onOpenCatalog?: () => void;
  onClearConference?: () => void;
  canClearConference?: boolean;
  onReopenImport?: (entryId: string) => void;
  onResendImport?: (entryId: string) => void;
  onDeleteImport?: (entryId: string) => void;
  onClearImportHistory?: () => void;
  reopeningImportId?: string | null;
  onAbortImport?: () => void;
  importAborting?: boolean;
  /** Catalog context after import (capital is full list, not only this note). */
  catalogProductCount?: number;
  catalogCapitalLabel?: string | null;
  importNoteItemCount?: number | null;
  importNoteTotalLabel?: string | null;
};

function validationChipClass(status: string): string {
  const tone = importValidationStatusTone(status);
  if (tone === "success") return "recentImportChipTs isSuccess";
  if (tone === "error") return "recentImportChipTs isError";
  if (tone === "warning") return "recentImportChipTs isWarning";
  return "recentImportChipTs";
}

export function ImportStagePanel({
  importing,
  localExperimentLoading,
  documentCount,
  activeFileName,
  importProgressMessage,
  importJobMessage,
  importJobStage,
  importJobStartedAt,
  importProcessLog,
  importMode = null,
  activeDocumentIndex = null,
  importError,
  importSuccessMessage,
  validationStatus,
  diagnosticsChips,
  warnings,
  recentImports,
  inputRef,
  onImportPrimaryClick,
  onLocalExperimentClick,
  onFilePickerClick,
  onFileChange,
  onOpenCatalog,
  onClearConference,
  canClearConference = false,
  onReopenImport,
  onResendImport,
  onDeleteImport,
  onClearImportHistory,
  reopeningImportId = null,
  onAbortImport,
  importAborting = false,
  catalogProductCount = 0,
  catalogCapitalLabel = null,
  importNoteItemCount = null,
  importNoteTotalLabel = null,
}: ImportStagePanelProps) {
  const pipelineBusy = importing || localExperimentLoading;
  const historyBusyId = reopeningImportId;
  const primaryDisabled = pipelineBusy || Boolean(historyBusyId);
  const progressActive = pipelineBusy;
  const resolvedMode = importMode || (localExperimentLoading ? "local" : importing ? "llm" : null);
  const historyCount = recentImports.length;
  const noteItems = Math.max(0, Math.floor(Number(importNoteItemCount || 0)));
  const catalogItems = Math.max(0, Math.floor(Number(catalogProductCount || 0)));
  const showCatalogContext =
    Boolean(importSuccessMessage) &&
    catalogItems > 0 &&
    (catalogItems > noteItems || Boolean(catalogCapitalLabel && importNoteTotalLabel && catalogCapitalLabel !== importNoteTotalLabel));

  return (
    <section className="importStageTs" aria-labelledby="import-stage-title">
      <div className="stageHeaderTs">
        <div className="stageLabelRowTs">
          <span className="stageStepBadgeTs" aria-hidden="true">
            1
          </span>
          <span className="sectionTag">Importação</span>
        </div>
        <h2 className="stageTitleTs" id="import-stage-title">
          Entrada do romaneio
        </h2>
      </div>
      <button className="primaryButton fullButton importButtonTs" type="button" disabled={primaryDisabled} onClick={onImportPrimaryClick}>
        {importing ? (
          <>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            Importando...
          </>
        ) : (
          <>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Importar com IA
          </>
        )}
      </button>
      <button
        className="ghostButton fullButton importSecondaryButtonTs"
        type="button"
        disabled={primaryDisabled}
        onClick={onLocalExperimentClick}
        aria-label="Importar com leitura local"
      >
        {localExperimentLoading ? (
          "Executando leitura local..."
        ) : (
          <>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
            Importar com leitura local
          </>
        )}
      </button>
      <label
        className={`fileInput compactFileInput ${primaryDisabled ? "fileInputDisabled" : ""}`}
        title={activeFileName || (documentCount ? `${documentCount} documentos selecionados` : "Selecionar arquivos do romaneio")}
        onClick={
          primaryDisabled
            ? undefined
            : (event) => {
                // Programmatic clicks from the parser-local button must keep their selected mode.
                if (event.nativeEvent.isTrusted) onFilePickerClick();
              }
        }
      >
        <span>
          {documentCount ? (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              {activeFileName || `${documentCount} documento${documentCount === 1 ? "" : "s"}`}
            </>
          ) : (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Selecionar arquivo
            </>
          )}
        </span>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.jpg,.jpeg,.png"
          multiple
          aria-label="Selecionar arquivos do romaneio"
          disabled={primaryDisabled}
          onChange={onFileChange}
        />
      </label>
      {canClearConference && onClearConference ? (
        <button className="ghostButton fullButton importClearConferenceTs" type="button" disabled={primaryDisabled} onClick={onClearConference}>
          Limpar conferência e importar outra nota
        </button>
      ) : null}
      {progressActive || importProgressMessage || importJobMessage ? (
        <ImportProgressPanel
          active={progressActive}
          mode={resolvedMode}
          stage={importJobStage || (localExperimentLoading ? "processing" : null)}
          message={
            progressActive
              ? importProgressMessage ||
                importJobMessage ||
                (localExperimentLoading ? "Lendo a nota com o parser local..." : null)
              : importJobMessage
          }
          startedAt={importJobStartedAt}
          fileName={activeFileName}
          processLog={importProcessLog}
          documentIndex={activeDocumentIndex}
          documentTotal={documentCount || null}
          onAbort={progressActive ? onAbortImport : undefined}
          aborting={importAborting}
        />
      ) : null}
      {importError ? <div className="message error">{importError}</div> : null}
      {importSuccessMessage ? <div className="message success">{importSuccessMessage}</div> : null}
      <ImportDiagnosticsPanel validationStatus={validationStatus} chips={diagnosticsChips} warnings={warnings} />
      {importSuccessMessage && onOpenCatalog ? (
        <button className="primaryButton fullButton importOpenCatalogTs" type="button" onClick={onOpenCatalog}>
          Ver produtos no catálogo
        </button>
      ) : null}

      {showCatalogContext ? (
        <aside className="importCatalogContextTs" aria-label="Diferença entre esta nota e o catálogo">
          <strong>Catálogo ≠ só esta nota</strong>
          <p>
            Esta importação trouxe <b>{noteItems}</b> item{noteItems === 1 ? "" : "s"}
            {importNoteTotalLabel ? <> · total da nota <b>{importNoteTotalLabel}</b></> : null}.
            O catálogo tem agora <b>{catalogItems}</b> item{catalogItems === 1 ? "" : "s"}
            {catalogCapitalLabel ? <> · capital no lote <b>{catalogCapitalLabel}</b></> : null}.
            {catalogItems > noteItems
              ? " Há itens de importações anteriores ou cadastro manual na lista — o capital soma tudo."
              : " Confira se o capital do lote bate com o total da nota."}
          </p>
        </aside>
      ) : null}

      {historyCount > 0 ? (
        <details className="recentImportsTs" open={!progressActive && documentCount === 0}>
          <summary className="recentImportsSummaryTs" aria-label={`Histórico de importações, ${historyCount} registro(s)`}>
            <span className="recentImportsSummaryTextTs">
              <strong>Histórico de importações</strong>
              <span className="recentImportPreviewTs">
                {historyCount} {historyCount === 1 ? "nota neste navegador" : "notas neste navegador"}
                {progressActive ? " · disponível durante a importação" : ""}
              </span>
            </span>
            <span className="recentImportsCountTs">{historyCount}</span>
          </summary>

          <div className="recentImportsToolbarTs">
            <span className="recentImportsToolbarHintTs">
              Reabrir conferência, reenviar ao catálogo ou excluir do histórico.
            </span>
            {onClearImportHistory ? (
              <button
                className="ghostButton compactButton recentImportClearAllButtonTs"
                type="button"
                disabled={Boolean(historyBusyId)}
                onClick={onClearImportHistory}
                title="Apaga todo o histórico e as sessões salvas neste navegador"
              >
                Limpar histórico
              </button>
            ) : null}
          </div>

          <div className="recentImportsListTs">
            {recentImports.map((entry) => {
              const sourceDisplayName = formatImportSourceDisplayName(entry.sourceName);
              const when = formatImportHistoryWhen(entry.completedAt);
              const busyThis = historyBusyId === entry.id;
              const canReopen = entry.canReopen !== false && Boolean(onReopenImport);
              const validationLabel = formatImportValidationStatus(entry.validationStatus);
              const reopenDisabled = pipelineBusy || Boolean(historyBusyId);
              const resendDisabled = pipelineBusy || Boolean(historyBusyId);
              const deleteDisabled = busyThis || Boolean(historyBusyId && historyBusyId !== entry.id);
              return (
                <article key={entry.id} className="recentImportItemTs" aria-label={`Importação ${sourceDisplayName}`}>
                  <header className="recentImportHeaderTs">
                    <div className="recentImportTitleBlockTs">
                      <strong className="recentImportSourceTs" title={entry.sourceName}>
                        {sourceDisplayName}
                      </strong>
                      <time className="recentImportWhenTs" dateTime={when.iso || undefined} title={when.fullLabel}>
                        {when.dateLabel} · {when.timeLabel}
                      </time>
                    </div>
                    <span className={validationChipClass(entry.validationStatus)} title={`Validação: ${validationLabel}`}>
                      {validationLabel}
                    </span>
                  </header>

                  <dl className="recentImportDetailsTs">
                    <div>
                      <dt>Modo</dt>
                      <dd>{entry.mode || "Importação"}</dd>
                    </div>
                    <div>
                      <dt>Itens</dt>
                      <dd>{entry.totalItems}</dd>
                    </div>
                    <div>
                      <dt>Valor</dt>
                      <dd>{entry.totalValueLabel || "—"}</dd>
                    </div>
                    <div>
                      <dt>Avisos</dt>
                      <dd>{entry.warningCount > 0 ? entry.warningCount : "Nenhum"}</dd>
                    </div>
                    <div>
                      <dt>Grades</dt>
                      <dd>{entry.gradesAvailable ? "Sim" : "Não"}</dd>
                    </div>
                    <div className="recentImportDetailsFullTs">
                      <dt>Sessão</dt>
                      <dd className={canReopen ? "isOk" : "isMuted"}>
                        {canReopen ? "Arquivo e extração disponíveis para reabrir" : "Só histórico (sem arquivo para reabrir)"}
                      </dd>
                    </div>
                  </dl>

                  <div className="recentImportActionsTs" role="group" aria-label={`Ações de ${sourceDisplayName}`}>
                    {canReopen ? (
                      <button
                        className="primaryButton compactButton recentImportReopenButtonTs"
                        type="button"
                        disabled={reopenDisabled}
                        onClick={() => onReopenImport?.(entry.id)}
                        title={
                          pipelineBusy
                            ? "Aguarde a importação em andamento terminar para reabrir outra nota"
                            : "Reabrir a nota e o resultado da extração na conferência"
                        }
                      >
                        {busyThis ? "Abrindo..." : "Reabrir"}
                      </button>
                    ) : null}
                    {onResendImport ? (
                      <button
                        className="ghostButton compactButton recentImportResendButtonTs"
                        type="button"
                        disabled={resendDisabled}
                        onClick={() => onResendImport(entry.id)}
                        title={
                          pipelineBusy
                            ? "Aguarde a importação em andamento terminar para reenviar"
                            : "Enviar ao catálogo o resultado já processado, sem nova leitura por IA"
                        }
                      >
                        {busyThis ? "..." : "Enviar ao catálogo"}
                      </button>
                    ) : null}
                    {onDeleteImport ? (
                      <button
                        className="ghostButton compactButton recentImportDeleteButtonTs"
                        type="button"
                        disabled={deleteDisabled}
                        onClick={() => onDeleteImport(entry.id)}
                        title="Apagar este item do histórico e da sessão salva neste navegador, para sempre. Não remove produtos do catálogo."
                      >
                        {busyThis ? "Excluindo..." : "Excluir"}
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </details>
      ) : null}
    </section>
  );
}
