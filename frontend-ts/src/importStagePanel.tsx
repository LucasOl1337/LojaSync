import type { ChangeEvent, RefObject } from "react";

import type { ImportDiagnosticsChip, ImportHistoryEntry, ImportProcessEntry } from "./uiFormatting";
import { formatImportSourceDisplayName } from "./uiFormatting";
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
  processLog: ImportProcessEntry[];
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
  processLog,
  warnings,
  recentImports,
  inputRef,
  onImportPrimaryClick,
  onLocalExperimentClick,
  onFilePickerClick,
  onFileChange,
}: ImportStagePanelProps) {
  const disabled = importing || localExperimentLoading;

  return (
    <section className="importStageTs" aria-labelledby="import-stage-title">
      <div className="stageHeaderTs">
        <div className="stageLabelRowTs">
          <span className="stageStepBadgeTs" aria-hidden="true">1</span>
          <span className="sectionTag">Importacao</span>
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
            Importar Romaneio
          </>
        )}
      </button>
      <button className="ghostButton fullButton importSecondaryButtonTs" type="button" disabled={disabled} onClick={onLocalExperimentClick}>
        {localExperimentLoading ? (
          "Executando parser local..."
        ) : (
          <>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
            Importar com parser local
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
      {localExperimentLoading ? <div className="message subtle">Parser local em andamento...</div> : null}
      {!importing && importJobMessage ? <div className="message subtle">{importJobMessage}</div> : null}
      {importError ? <div className="message error">{importError}</div> : null}
      {importSuccessMessage ? <div className="message success">{importSuccessMessage}</div> : null}
      <ImportDiagnosticsPanel validationStatus={validationStatus} chips={diagnosticsChips} processLog={processLog} warnings={warnings} />
      {recentImports.length ? (
        <div className="recentImportsTs">
          <div className="recentImportsHeaderTs">
            <strong>Importacoes recentes</strong>
            <span>{recentImports.length}</span>
          </div>
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
                    <span>{entry.validationStatus}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
