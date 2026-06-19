import { formatImportValidationStatus, type ImportDiagnosticsChip } from "./uiFormatting";

type ImportDiagnosticsPanelProps = {
  validationStatus: string;
  chips: ImportDiagnosticsChip[];
  warnings: string[];
};

export function ImportDiagnosticsPanel({
  validationStatus,
  chips,
  warnings,
}: ImportDiagnosticsPanelProps) {
  if (!validationStatus && !chips.length && !warnings.length) {
    return null;
  }
  const validationLabel = validationStatus ? formatImportValidationStatus(validationStatus) : "";
  const summaryLabel = [
    ...chips.map((chip) => `${chip.label}: ${chip.value}`),
    validationLabel ? `Validação: ${validationLabel}` : "",
    warnings.length ? `${warnings.length} aviso${warnings.length === 1 ? "" : "s"}` : "",
  ].filter(Boolean).join(". ");

  return (
    <details className="importDiagnosticsTs">
      <summary className="importDiagnosticsSummaryTs" aria-label={`Resultado da importação. ${summaryLabel}. Clique para expandir.`}>
        <span className="importDiagnosticsSummaryMainTs">
          <strong>Resultado da importação</strong>
          <span>Ver detalhes</span>
        </span>
        <span className="importDiagnosticsSummaryMetaTs">
          {chips.map((chip) => (
            <span key={`${chip.label}-${chip.value}`} className={`importInsightChipTs chip-${chip.tone}`}>
              <span>{chip.label}</span>
              <strong>{chip.value}</strong>
            </span>
          ))}
          {validationStatus ? (
            <span className={`importValidationBadge validation-${validationStatus}`}>
              Validação: {validationLabel}
            </span>
          ) : null}
        </span>
      </summary>
      <div className="importDiagnosticsDetailsTs">
        {chips.map((chip) => (
          <div key={`detail-${chip.label}-${chip.value}`} className="importDiagnosticDetailRowTs">
            <span>{chip.label}</span>
            <strong>{chip.value}</strong>
          </div>
        ))}
        {validationStatus ? (
          <div className="importDiagnosticDetailRowTs">
            <span>Validação</span>
            <strong>{validationLabel}</strong>
          </div>
        ) : null}
        {warnings.length ? (
          <div className="importDiagnosticDetailRowTs">
            <span>Avisos</span>
            <strong>{warnings.length}</strong>
          </div>
        ) : null}
      </div>
    </details>
  );
}
