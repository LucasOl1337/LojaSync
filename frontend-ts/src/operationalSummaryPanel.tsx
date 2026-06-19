import type { LoadState } from "./appConfig";

type OperationalSummaryPanelProps = {
  totalsText: LoadState["totalsText"];
  totalsRaw: LoadState["totalsRaw"];
};

export function OperationalSummaryPanel({
  totalsText,
  totalsRaw,
}: OperationalSummaryPanelProps) {
  return (
    <section className="summaryStageTs" aria-labelledby="operational-summary-title">
      <div className="stageHeaderTs">
        <div className="stageLabelRowTs">
          <span className="stageStepBadgeTs" aria-hidden="true">4</span>
          <span className="sectionTag">Totais</span>
        </div>
        <h2 className="stageTitleTs" id="operational-summary-title">Totais da operação</h2>
      </div>

      <div className="totalsBoardTs">
        <article className="totalsSectionTs currentTotalsSectionTs">
          <div className="totalsSectionHeadTs">
            <span className="totalsGroupTitleTs">Sessão atual</span>
            <span className="totalsChipTs live">ao vivo</span>
          </div>
          <div className="totalsRowsTs">
            <div className="totalsRowTs"><span>Quantidade</span><strong>{totalsRaw.atualQuantidade}</strong></div>
            <div className="totalsRowTs"><span>Custo total</span><strong>{totalsText.atualCusto}</strong></div>
            <div className="totalsRowTs"><span>Venda total</span><strong>{totalsText.atualVenda}</strong></div>
          </div>
        </article>

        <article className="totalsSectionTs historicalTotalsTs" aria-label="Acumulado global">
          <div className="totalsSectionHeadTs" title="Acumulado global" aria-label="Acumulado global">
            <span className="totalsGroupTitleTs">Acumulado global</span>
            <span className="totalsChipTs muted">histórico</span>
          </div>
          <div className="totalsRowsTs">
            <div className="totalsRowTs"><span>Quantidade</span><strong>{totalsRaw.historicoQuantidade}</strong></div>
            <div className="totalsRowTs"><span>Custo total</span><strong>{totalsText.historicoCusto}</strong></div>
            <div className="totalsRowTs"><span>Venda total</span><strong>{totalsText.historicoVenda}</strong></div>
            <div className="totalsRowTs"><span>Tempo poupado</span><strong>{totalsText.tempo}</strong></div>
            <div className="totalsRowTs"><span>Caracteres evitados</span><strong>{totalsRaw.caracteres.toLocaleString("pt-BR")}</strong></div>
          </div>
        </article>

      </div>
    </section>
  );
}
