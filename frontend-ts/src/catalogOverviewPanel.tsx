import type { CatalogOverview } from "./catalogOverview";
import type { ProductQuickFilter } from "./productFilters";
import { formatCurrency } from "./uiFormatting";

type CatalogOverviewPanelProps = {
  overview: CatalogOverview;
  activeFilter: ProductQuickFilter;
  onSelectFilter: (filter: ProductQuickFilter) => void;
};

function formatPercent(value: number) {
  return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

export function CatalogOverviewPanel({
  overview,
  activeFilter,
  onSelectFilter,
}: CatalogOverviewPanelProps) {
  const hasProducts = overview.totalProducts > 0;

  return (
    <section className="catalogOverviewTs" aria-labelledby="catalog-overview-title">
      <div className="catalogOverviewHeaderTs">
        <div>
          <span className="sectionTag">Visão comercial</span>
          <h2 id="catalog-overview-title">Visão do catálogo</h2>
          <p>{hasProducts ? `${overview.totalProducts} produtos · ${overview.totalUnits} unidades` : "Cadastre ou importe produtos para formar a visão comercial."}</p>
        </div>
        <div
          className={`catalogReadinessTs ${overview.reviewCount > 0 ? "needsReview" : "ready"}`}
          aria-label={`Prontidão do catálogo: ${overview.readinessPercent}%`}
        >
          <strong>{overview.readinessPercent}%</strong>
          <span>pronto</span>
        </div>
      </div>

      <div className="catalogCommercialGridTs" aria-label="Indicadores comerciais do catálogo">
        <article>
          <span>Capital no lote</span>
          <strong>{formatCurrency(overview.costValue)}</strong>
        </article>
        <article>
          <span>Venda projetada</span>
          <strong>{formatCurrency(overview.saleValue)}</strong>
        </article>
        <article className="catalogGainMetricTs">
          <span>Ganho bruto potencial</span>
          <strong>{formatCurrency(overview.grossPotential)}</strong>
          <small>{formatPercent(overview.grossReturnPercent)} sobre o custo</small>
        </article>
      </div>

      <div className="catalogReviewStripTs">
        <button
          className={`catalogReviewSummaryTs ${activeFilter === "needs_review" ? "active" : ""}`}
          type="button"
          onClick={() => onSelectFilter(overview.reviewCount > 0 ? "needs_review" : "all")}
          disabled={!hasProducts}
          aria-pressed={activeFilter === "needs_review"}
        >
          <span>{overview.reviewCount > 0 ? "Pedem revisão" : "Catálogo revisado"}</span>
          <strong>{overview.reviewCount > 0 ? overview.reviewCount : overview.readyCount}</strong>
        </button>

        <div className="catalogIssueButtonsTs" aria-label="Pendências do catálogo">
          {overview.issues.length ? overview.issues.map((issue) => (
            <button
              key={issue.filter}
              className={`catalogIssueButtonTs ${issue.tone} ${activeFilter === issue.filter ? "active" : ""}`}
              type="button"
              onClick={() => onSelectFilter(issue.filter)}
              aria-pressed={activeFilter === issue.filter}
              aria-label={`${issue.label}: ${issue.count} produtos. Filtrar lista.`}
            >
              <span>{issue.label}</span>
              <strong>{issue.count}</strong>
            </button>
          )) : (
            <span className="catalogNoIssuesTs">Nenhuma pendência estrutural detectada.</span>
          )}
        </div>

        {activeFilter !== "all" ? (
          <button className="catalogClearFilterTs" type="button" onClick={() => onSelectFilter("all")}>Ver todos</button>
        ) : null}
      </div>
    </section>
  );
}
