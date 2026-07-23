import type { CatalogOverview } from "./catalogOverview";
import type { ProductQuickFilter } from "./productFilters";
import { formatCurrency } from "./uiFormatting";

type SidebarSectionPanelProps = {
  overview: CatalogOverview;
  activeFilter: ProductQuickFilter;
  marginLabel?: string | null;
  onSelectFilter: (filter: ProductQuickFilter) => void;
};

function formatPercent(value: number) {
  return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

export function SidebarSectionPanel({
  overview,
  activeFilter,
  marginLabel,
  onSelectFilter,
}: SidebarSectionPanelProps) {
  const hasProducts = overview.totalProducts > 0;

  return (
    <section className="nexSidebarSectionTs" aria-labelledby="sidebar-section-title">
      <header className="nexSidebarSectionHeaderTs">
        <div>
          <span className="sectionTag">Seção</span>
          <h2 id="sidebar-section-title">Catálogo</h2>
        </div>
        <div
          className={`catalogReadinessTs sidebarReadinessTs ${overview.reviewCount > 0 ? "needsReview" : "ready"}`}
          aria-label={`Prontidão do catálogo: ${overview.readinessPercent}%`}
        >
          <strong>{overview.readinessPercent}%</strong>
          <span>pronto</span>
        </div>
      </header>

      <div className="nexSidebarMetricsTs" aria-label="Indicadores do catálogo">
        <article>
          <span>Itens</span>
          <strong>{hasProducts ? overview.totalProducts : "—"}</strong>
          <small>{hasProducts ? `${overview.totalUnits} un.` : "vazio"}</small>
        </article>
        <article>
          <span>Capital no lote</span>
          <strong>{formatCurrency(overview.costValue)}</strong>
        </article>
        <article>
          <span>Venda projetada</span>
          <strong>{formatCurrency(overview.saleValue)}</strong>
        </article>
        <article className="sidebarGainMetricTs">
          <span>Ganho bruto</span>
          <strong>{formatCurrency(overview.grossPotential)}</strong>
          <small>{hasProducts ? `${formatPercent(overview.grossReturnPercent)} s/ custo` : "sem base"}</small>
        </article>
        {marginLabel ? (
          <article className="sidebarMarginMetricTs">
            <span>Margem da sessão</span>
            <strong>{marginLabel}</strong>
          </article>
        ) : null}
      </div>

      <div className="nexSidebarReviewTs">
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
            <span className="catalogNoIssuesTs">Sem pendências estruturais.</span>
          )}
        </div>

        {activeFilter !== "all" ? (
          <button className="catalogClearFilterTs sidebarClearFilterTs" type="button" onClick={() => onSelectFilter("all")}>
            Limpar filtro
          </button>
        ) : null}
      </div>
    </section>
  );
}
