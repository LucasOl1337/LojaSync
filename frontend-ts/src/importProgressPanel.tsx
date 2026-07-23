import { useEffect, useMemo, useState } from "react";

import {
  buildImportProgressSteps,
  formatImportElapsed,
  formatImportProgressCopy,
  type ImportProgressStep,
} from "./uiFormatting";

type ImportProgressPanelProps = {
  active: boolean;
  mode: "llm" | "local" | null;
  stage?: string | null;
  message?: string | null;
  startedAt?: number | null;
  fileName?: string | null;
  processLog?: Array<Record<string, unknown>> | null;
  documentIndex?: number | null;
  documentTotal?: number | null;
  onAbort?: () => void;
  aborting?: boolean;
};

function StepList({ steps }: { steps: ImportProgressStep[] }) {
  return (
    <ol className="importProgressStepsTs" aria-label="Etapas da importação">
      {steps.map((step) => (
        <li key={step.id} className={`importProgressStepTs state-${step.state}`}>
          <span className="importProgressStepMarkTs" aria-hidden="true">
            {step.state === "done" ? "✓" : step.state === "active" ? "●" : "○"}
          </span>
          <span className="importProgressStepLabelTs">{step.label}</span>
        </li>
      ))}
    </ol>
  );
}

export function ImportProgressPanel({
  active,
  mode,
  stage,
  message,
  startedAt,
  fileName,
  processLog,
  documentIndex,
  documentTotal,
  onAbort,
  aborting = false,
}: ImportProgressPanelProps) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return;
    setNowMs(Date.now());
    const timerId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timerId);
  }, [active, startedAt]);

  const steps = useMemo(
    () => buildImportProgressSteps({ stage, message, mode, active }),
    [active, message, mode, stage],
  );

  const liveMessage = useMemo(() => {
    if (message) return formatImportProgressCopy(message);
    if (mode === "local") return "Lendo a nota com o parser local...";
    if (active) return "Importação em andamento...";
    return null;
  }, [active, message, mode]);

  const recentLog = useMemo(() => {
    if (!Array.isArray(processLog)) return [];
    return processLog
      .map((entry, index) => {
        const text = formatImportProgressCopy(String(entry?.message || "").trim());
        if (!text) return null;
        return {
          key: `${index}-${text}`,
          text,
          level: String(entry?.level || "info"),
        };
      })
      .filter((item): item is { key: string; text: string; level: string } => Boolean(item))
      .slice(-4);
  }, [processLog]);

  if (!active && !liveMessage) return null;

  const startedMs = Number(startedAt || 0) > 0
    ? (Number(startedAt) > 1e12 ? Number(startedAt) : Number(startedAt) * 1000)
    : null;
  const elapsedLabel = startedMs ? formatImportElapsed(Math.max(0, nowMs - startedMs)) : null;
  const batchLabel =
    documentTotal && documentTotal > 1 && documentIndex
      ? `Documento ${documentIndex} de ${documentTotal}`
      : null;
  const modeLabel = mode === "local" ? "Leitura local" : mode === "llm" ? "IA" : "Importação";
  const activeStep = steps.find((step) => step.state === "active");
  const progressPercent = Math.max(
    8,
    Math.round((steps.filter((step) => step.state === "done").length / Math.max(steps.length, 1)) * 100)
      + (activeStep ? 12 : 0),
  );

  return (
    <section
      className={`importProgressPanelTs ${active ? "isActive" : ""}`}
      aria-live="polite"
      aria-busy={active}
      aria-label="Progresso da importação"
    >
      <header className="importProgressHeaderTs">
        <div>
          <span className="sectionTag">{modeLabel}</span>
          <strong>{active ? (aborting ? "Cancelando importação..." : "Importação em andamento") : "Último status"}</strong>
          {fileName ? <span className="importProgressFileTs" title={fileName}>{fileName}</span> : null}
        </div>
        <div className="importProgressMetaTs">
          {batchLabel ? <span>{batchLabel}</span> : null}
          {elapsedLabel ? <span className="importProgressElapsedTs">{elapsedLabel}</span> : null}
          {active && onAbort ? (
            <button
              className="ghostButton compactButton importProgressAbortTs"
              type="button"
              disabled={aborting}
              onClick={onAbort}
              title="Abortar a importação agora (cancela IA e libera a interface)"
            >
              {aborting ? "Cancelando..." : "Abortar"}
            </button>
          ) : null}
        </div>
      </header>

      <div className="importProgressBarTrackTs" aria-hidden="true">
        <div className="importProgressBarFillTs" style={{ width: `${Math.min(progressPercent, 96)}%` }} />
      </div>

      <p className="importProgressLiveTs">
        {liveMessage || activeStep?.label || "Preparando..."}
      </p>

      <StepList steps={steps} />

      {recentLog.length ? (
        <ul className="importProgressLogTs" aria-label="Passos recentes">
          {recentLog.map((entry) => (
            <li key={entry.key} className={`level-${entry.level}`}>{entry.text}</li>
          ))}
        </ul>
      ) : (
        <p className="importProgressHintTs">
          Notas grandes ou com foto podem demorar mais na etapa da IA. O progresso atualiza a cada passo do servidor.
        </p>
      )}
    </section>
  );
}
