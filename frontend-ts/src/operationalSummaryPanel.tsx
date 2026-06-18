import type { LoadState } from "./appConfig";
import { OperationalHealthPanel } from "./operationalHealthPanel";
import type { OperationDiaryEntry, StatusChip } from "./uiFormatting";

type OperationalSummaryPanelProps = {
  healthChips: StatusChip[];
  checkedAt: number | null;
  totalsText: LoadState["totalsText"];
  totalsRaw: LoadState["totalsRaw"];
  operationDiary: OperationDiaryEntry[];
};

export function OperationalSummaryPanel({
  healthChips,
  checkedAt,
  totalsText,
  totalsRaw,
  operationDiary,
}: OperationalSummaryPanelProps) {
  return (
    <section className="summaryStageTs" aria-labelledby="operational-summary-title">
      <div className="stageHeaderTs">
        <div className="stageLabelRowTs">
          <span className="stageStepBadgeTs" aria-hidden="true">4</span>
          <span className="sectionTag">Resumo operacional</span>
        </div>
        <h2 className="stageTitleTs" id="operational-summary-title">Saude e totais</h2>
      </div>

      <OperationalHealthPanel chips={healthChips} checkedAt={checkedAt} />

      <div className="totalsBoardTs">
        <article className="totalsSectionTs currentTotalsSectionTs">
          <div className="totalsSectionHeadTs">
            <span className="totalsGroupTitleTs">Sessao atual</span>
            <span className="totalsChipTs live">ao vivo</span>
          </div>
          <div className="totalsRowsTs">
            <div className="totalsRowTs"><span>Quantidade</span><strong>{totalsRaw.atualQuantidade}</strong></div>
            <div className="totalsRowTs"><span>Custo total</span><strong>{totalsText.atualCusto}</strong></div>
            <div className="totalsRowTs"><span>Venda total</span><strong>{totalsText.atualVenda}</strong></div>
          </div>
        </article>

        <div className="summaryDetailsRowTs">
          <details className="historicalTotalsTs" aria-label="Acumulado global">
            <summary className="totalsSectionHeadTs" title="Acumulado global" aria-label="Acumulado global">
              <span className="totalsGroupTitleTs">Acumulado</span>
              <span className="totalsChipTs muted">historico</span>
            </summary>
            <div className="totalsRowsTs">
              <div className="totalsRowTs"><span>Quantidade</span><strong>{totalsRaw.historicoQuantidade}</strong></div>
              <div className="totalsRowTs"><span>Custo total</span><strong>{totalsText.historicoCusto}</strong></div>
              <div className="totalsRowTs"><span>Venda total</span><strong>{totalsText.historicoVenda}</strong></div>
              <div className="totalsRowTs"><span>Tempo poupado</span><strong>{totalsText.tempo}</strong></div>
              <div className="totalsRowTs"><span>Caracteres evitados</span><strong>{totalsRaw.caracteres.toLocaleString("pt-BR")}</strong></div>
            </div>
          </details>

          {operationDiary.length ? (
            <details className="operationDiaryTs" aria-label={`Diario de operacao, ${operationDiary.length} registros`}>
              <summary title="Diario de operacao" aria-label={`Diario de operacao, ${operationDiary.length} registros`}>
                <span>Diario</span>
                <strong>{operationDiary.length}</strong>
              </summary>
              <div className="operationDiaryListTs">
                {operationDiary.map((entry) => (
                  <div key={entry.id} className={`operationDiaryItemTs diary-${entry.tone}`}>
                    <div className="operationDiaryMainTs">
                      <strong>{entry.title}</strong>
                      <span>{new Date(entry.occurredAt).toLocaleTimeString("pt-BR")}</span>
                    </div>
                    {entry.detail ? <p>{entry.detail}</p> : null}
                    {entry.meta.length ? (
                      <div className="operationDiaryMetaTs">
                        {entry.meta.map((item) => (
                          <span key={`${entry.id}-${item}`}>{item}</span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </details>
          ) : null}
        </div>
      </div>
    </section>
  );
}
