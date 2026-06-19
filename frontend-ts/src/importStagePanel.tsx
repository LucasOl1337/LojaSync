import type { ChangeEvent, RefObject } from "react";

import type { ImportDiagnosticsChip, ImportHistoryEntry } from "./uiFormatting";
import { formatImportSourceDisplayName, formatImportValidationStatus } from "./uiFormatting";
import { ImportDiagnosticsPanel } from "./importDiagnostics";

type ImportStagePanelProps = {
  importing: boolean;
  localExperimentLoading: boolean;
  selectedFile: File | null;
  importProgressMessage: string | null;
  importJobMessage?: string | null;
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
};

export function ImportStagePanel({
  importing,
  localExperimentLoading,
  selectedFile,
  importProgressMessage,
  importJobMessage,
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
}: ImportStagePanelProps) {
  const disabled = importing || localExperimentLoading;
  const latestImport = recentImports[0] || null;
  const latestImportCompletedAt = latestImport ? new Date(latestImport.completedAt) : null;
  const latestImportTime = latestImportCompletedAt
    ? latestImportCompletedAt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <section className="importStageTs" aria-labelledby="import-stage-title">
      <div className="stageHeaderTs">
        <div className="stageLabelRowTs">
          <span className="stageStepBadgeTs" aria-hidden="true">1</span>
          <span className="sectionTag">Importação</span>
        </div>
        <h2 className="stageTitleTs" id="import-stage-title">Entrada do romaneio</h2>
      </div>
      <button className="primaryButton fullButton importButtonTs" type="button" disabled={disabled} onClick={onImportPrimaryClick}>
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
      <button className="ghostButton fullButton importSecondaryButtonTs" type="button" disabled={disabled} onClick={onLocalExperimentClick}>
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
        className={`fileInput compactFileInput ${disabled ? "fileInputDisabled" : ""}`}
        title={selectedFile ? selectedFile.name : "Selecionar arquivo do romaneio"}
        onClick={disabled ? undefined : (event) => {
          // Programmatic clicks from the parser-local button must keep their selected mode.
          if (event.nativeEvent.isTrusted) onFilePickerClick();
        }}
      >
        <span>
          {selectedFile ? (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              {selectedFile.name}
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
          aria-label="Selecionar arquivo do romaneio"
          disabled={disabled}
          onChange={onFileChange}
        />
      </label>
      {importProgressMessage ? <div className="message subtle">{importProgressMessage}</div> : null}
      {localExperimentLoading ? <div className="message subtle">Processamento local em andamento...</div> : null}
      {!importing && !importSuccessMessage && importJobMessage ? <div className="message subtle">{importJobMessage}</div> : null}
      {importError ? <div className="message error">{importError}</div> : null}
      {importSuccessMessage ? <div className="message success">{importSuccessMessage}</div> : null}
      <ImportDiagnosticsPanel validationStatus={validationStatus} chips={diagnosticsChips} warnings={warnings} />
      {latestImport ? (
        <details className="recentImportsTs">
          <summary
            className="recentImportsSummaryTs"
            aria-label={`Importações recentes, ${recentImports.length} registros. Última origem: ${latestImport.sourceName}`}
          >
            <span className="recentImportsSummaryTextTs">
              <strong>Importações recentes</strong>
              <span className="recentImportPreviewTs" title={latestImport.sourceName}>
                {formatImportSourceDisplayName(latestImport.sourceName)}
              </span>
            </span>
            <span className="recentImportsSummaryMetaTs">
              {latestImportTime && latestImportCompletedAt ? (
                <time dateTime={latestImportCompletedAt.toISOString()} title={latestImportCompletedAt.toLocaleString("pt-BR")}>
                  {latestImportTime}
                </time>
              ) : null}
              <span>{latestImport.totalItems} itens</span>
              <span>{formatImportValidationStatus(latestImport.validationStatus)}</span>
              <span className="recentImportsCountTs">{recentImports.length}</span>
            </span>
          </summary>
          <div className="recentImportsListTs">
            {recentImports.map((entry) => {
              const sourceDisplayName = formatImportSourceDisplayName(entry.sourceName);
              const completedAt = new Date(entry.completedAt);
              const completedTime = completedAt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
              return (
                <div key={entry.id} className="recentImportItemTs">
                  <div className="recentImportMainTs">
                    <strong className="recentImportSourceTs" title={entry.sourceName} aria-label={`Origem: ${entry.sourceName}`}>
                      {sourceDisplayName}
                    </strong>
                  </div>
                  <div className="recentImportMetaTs">
                    <time dateTime={completedAt.toISOString()} title={completedAt.toLocaleString("pt-BR")}>
                      {completedTime}
                    </time>
                    <span>{entry.mode}</span>
                    <span>{entry.totalItems} itens</span>
                    {entry.warningCount ? <span>{entry.warningCount} avisos</span> : null}
                    {entry.gradesAvailable ? <span>grades</span> : null}
                    <span>{formatImportValidationStatus(entry.validationStatus)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </details>
      ) : null}
    </section>
  );
}
