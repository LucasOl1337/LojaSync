import type { ImportDiagnosticsChip, ImportProcessEntry } from "./uiFormatting";

type ImportDiagnosticsPanelProps = {
  validationStatus: string;
  chips: ImportDiagnosticsChip[];
  processLog: ImportProcessEntry[];
  warnings: string[];
};

export function ImportDiagnosticsPanel({
  validationStatus,
  chips,
  processLog,
  warnings,
}: ImportDiagnosticsPanelProps) {
  if (!validationStatus && !chips.length && !processLog.length && !warnings.length) {
    return null;
  }

  return (
    <div className="importDiagnosticsTs">
      {chips.length ? (
        <div className="importInsightChipsTs">
          {chips.map((chip) => (
            <span key={`${chip.label}-${chip.value}`} className={`importInsightChipTs chip-${chip.tone}`}>
              <span>{chip.label}</span>
              <strong>{chip.value}</strong>
            </span>
          ))}
        </div>
      ) : null}
      {validationStatus ? (
        <div className={`importValidationBadge validation-${validationStatus}`}>
          Validation: {validationStatus}
        </div>
      ) : null}
      {processLog.length ? (
        <div className="importLogListTs">
          {processLog.map((entry) => (
            <div key={`${entry.index}-${entry.source}-${entry.message}`} className={`importLogEntryTs log-${entry.level}`}>
              <span className="importLogSourceTs">{entry.source}</span>
              <span>{entry.message}</span>
            </div>
          ))}
        </div>
      ) : null}
      {warnings.length ? (
        <div className="importWarningsTs">
          {warnings.map((warning, index) => (
            <div key={`${index}-${warning}`} className="importWarningEntryTs">
              {warning}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
