import { prepareImportWarnings } from "./importWarnings.js";
import { formatImportValidationStatus, type ImportDiagnosticsChip } from "./uiFormatting.js";

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
  const warningItems = prepareImportWarnings(warnings);
  if (!validationStatus && !chips.length && !warningItems.length) {
    return null;
  }
  const validationLabel = validationStatus ? formatImportValidationStatus(validationStatus) : "";
  const summaryLabel = [
    ...chips.map((chip) => `${chip.label}: ${chip.value}`),
    validationLabel ? `Validação: ${validationLabel}` : "",
    warningItems.length ? `${warningItems.length} aviso${warningItems.length === 1 ? "" : "s"}` : "",
  ].filter(Boolean).join(". ");

  return (
    <div className="importDiagnosticsGroupTs">
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
          {warningItems.length ? (
            <div className="importDiagnosticDetailRowTs">
              <span>Avisos</span>
              <strong>{warningItems.length}</strong>
            </div>
          ) : null}
        </div>
      </details>
      {warningItems.length ? (
        <section className="importWarningsTs" aria-labelledby="import-warnings-title" aria-live="polite">
          <div className="importWarningsHeaderTs">
            <strong id="import-warnings-title">Revise esta importação</strong>
            <span>{warningItems.length} aviso{warningItems.length === 1 ? "" : "s"}</span>
          </div>
          <ul>
            {warningItems.map((warning, index) => (
              <li key={`${warning}-${index}`}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
