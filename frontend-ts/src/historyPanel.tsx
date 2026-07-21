import type { OperationDiaryEntry } from "./uiFormatting";

type HistoryPanelProps = {
  entries: OperationDiaryEntry[];
  undoSummary: string;
  undoLabel: string;
  redoLabel: string;
  canUndo: boolean;
  canRedo: boolean;
  busy: boolean;
  onUndo: () => Promise<void>;
  onRedo: () => Promise<void>;
};

export function HistoryPanel({
  entries,
  undoSummary,
  undoLabel,
  redoLabel,
  canUndo,
  canRedo,
  busy,
  onUndo,
  onRedo,
}: HistoryPanelProps) {
  return (
    <section className="nexHistoryPanel" aria-labelledby="history-panel-title">
      <header className="nexSectionHead">
        <div>
          <span className="sectionTag">Controle reversível</span>
          <h2 id="history-panel-title">Atividade real da operação</h2>
          <p>Importações, alterações de produto e execuções registradas neste dispositivo.</p>
        </div>
        <span className="nexHistoryCount" aria-label={`${entries.length} registros`}>{entries.length}</span>
      </header>

      <div className="nexHistoryActions" aria-label="Controles do histórico de edições">
        <span>{undoSummary}</span>
        <button className="ghostButton" type="button" disabled={!canUndo || busy} onClick={() => void onUndo()} aria-label={undoLabel}>
          Desfazer
        </button>
        <button className="ghostButton" type="button" disabled={!canRedo || busy} onClick={() => void onRedo()} aria-label={redoLabel}>
          Refazer
        </button>
      </div>

      {entries.length ? (
        <ol className="nexHistoryTimeline">
          {entries.map((entry) => (
            <li key={entry.id} className={`nexHistoryEvent diary-${entry.tone}`}>
              <span className="nexHistoryMark" aria-hidden="true" />
              <div>
                <div className="nexHistoryEventHead">
                  <strong>{entry.title}</strong>
                  <time dateTime={new Date(entry.occurredAt).toISOString()}>
                    {new Date(entry.occurredAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
                  </time>
                </div>
                <p>{entry.detail}</p>
                {entry.meta.length ? <div className="operationDiaryMetaTs">{entry.meta.map((item) => <span key={item}>{item}</span>)}</div> : null}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <div className="nexHistoryEmpty">
          <strong>Nenhuma atividade registrada ainda.</strong>
          <span>As operações reais do catálogo aparecerão aqui quando forem realizadas.</span>
        </div>
      )}
    </section>
  );
}
