import { buildAutomationStatusDetail, formatAutomationStateLabel, type ExecutionReadinessState } from "./uiFormatting.js";

type ExecutionCenterPanelProps = {
  automationState?: string | null;
  automationMessage?: string | null;
  automationError?: string | null;
  automationProgressWidth: string;
  pendingGradeCount: number;
  executionReadiness: ExecutionReadinessState;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onStartComplete: () => Promise<void>;
  onExecuteGrades: () => Promise<void>;
  onStartCatalog: () => Promise<void>;
  onStopAutomation: () => Promise<void>;
  onJoinGrades: () => Promise<void>;
  onOpenGradeModal: () => Promise<void>;
};

export function ExecutionCenterPanel({
  automationState,
  automationMessage,
  automationError,
  automationProgressWidth,
  pendingGradeCount,
  executionReadiness,
  runBusyAction,
  onStartComplete,
  onExecuteGrades,
  onStartCatalog,
  onStopAutomation,
  onJoinGrades,
  onOpenGradeModal,
}: ExecutionCenterPanelProps) {
  const automationIsRunning = automationState === "running";
  const automationLabel = formatAutomationStateLabel(automationState);
  const automationStatusDetail = buildAutomationStatusDetail({
    automationState,
    automationMessage,
    automationError,
    pendingGradeCount,
  });
  const showExecutionReadiness = !executionReadiness.ready || executionReadiness.items.length > 0;

  return (
    <section className="batchControlsTs" aria-labelledby="execution-center-title" aria-describedby={showExecutionReadiness ? "execution-readiness-detail" : undefined}>
      <div className="executionCenterHeaderTs">
        <h2 className="sectionTag" id="execution-center-title">Centro de execução</h2>
        <span className={`executionStateChipTs ${automationIsRunning ? "executionStateRunningTs" : ""}`}>
          {automationIsRunning ? "Em execução" : "Pronto"}
        </span>
      </div>
      <div className="batchInlineRowTs">
        <aside className="compactAutomationStatusTs" role="status" aria-live="polite" aria-label="Estado da automação">
          <span className="automationStatusLabelTs">Automação</span>
          <strong>{automationLabel}</strong>
          <div className="progressBarTs compactProgressBarTs">
            <div className="progressFillTs" style={{ width: automationProgressWidth }} />
          </div>
          <small>{automationStatusDetail}</small>
        </aside>
        <div className="executionActionClusterTs executionActionClusterPrimaryTs" role="group" aria-label="Ações críticas de execução">
          <button className="actionButtonTs highlight completeActionButton large" type="button" onClick={() => void runBusyAction("cadastro-completo", onStartComplete)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><polygon points="5 3 19 12 5 21 5 3"/></svg>Cadastro completo
          </button>
          <button className="actionButtonTs highlight" type="button" onClick={() => void runBusyAction("executar-grades", onExecuteGrades)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>Executar grades
          </button>
          <button className="actionButtonTs accent large" type="button" onClick={() => void runBusyAction("cadastro-massa", onStartCatalog)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>Executar cadastro
          </button>
          <button
            className="actionButtonTs danger stopActionButtonTs stopActionActiveTs"
            type="button"
            onClick={() => void runBusyAction("parar", onStopAutomation)}
            title="Parar automação"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>Parar
          </button>
        </div>
        <span className="batchInlineDivider" aria-hidden="true" />
        <div className="executionActionClusterTs executionActionClusterSecondaryTs" role="group" aria-label="Ações auxiliares de grade">
          <button className="actionButtonTs secondaryInlineAction" type="button" onClick={() => void runBusyAction("importar-grades", onJoinGrades)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>Importar grades
          </button>
          <button className="actionButtonTs secondaryInlineAction" type="button" onClick={() => void runBusyAction("inserir-grade", onOpenGradeModal)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" ><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>Inserir grade
          </button>
        </div>
      </div>
      {showExecutionReadiness ? (
        <div className={`executionReadinessTs readiness-${executionReadiness.tone}`} role="status" aria-live="polite">
          <div className="executionReadinessMainTs">
            <strong>{executionReadiness.title}</strong>
            <span id="execution-readiness-detail">{executionReadiness.detail}</span>
          </div>
          {executionReadiness.items.length ? (
            <div className="importInsightChipsTs executionReadinessChipsTs">
              {executionReadiness.items.map((item) => (
                <span key={item.label} className={`importInsightChipTs chip-${item.tone}`}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
