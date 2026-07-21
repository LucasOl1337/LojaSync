import type { CatalogOverview } from "./catalogOverview";
import type { ProductQuickFilter } from "./productFilters";
import { formatCurrency } from "./uiFormatting";

type CatalogOverviewPanelProps = {
  overview: CatalogOverview;
  activeFilter: ProductQuickFilter;
  onSelectFilter: (filter: ProductQuickFilter) => void;
  onOpenSettings?: () => void;
  titleId?: string;
};

function formatPercent(value: number) {
  return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

export function CatalogOverviewPanel({
  overview,
  activeFilter,
  onSelectFilter,
  onOpenSettings,
  titleId = "catalog-overview-title",
}: CatalogOverviewPanelProps) {
  const hasProducts = overview.totalProducts > 0;

  return (
    <section className="catalogOverviewTs" aria-labelledby={titleId}>
      <div className="catalogOverviewHeaderTs">
        <div>
          <span className="sectionTag">Visão comercial</span>
          <h2 id={titleId}>Visão do catálogo</h2>
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

        {activeFilter !== "all" || onOpenSettings ? (
          <div className="catalogOverviewActionsTs">
            {activeFilter !== "all" ? (
              <button className="catalogClearFilterTs" type="button" onClick={() => onSelectFilter("all")} aria-label="Limpar filtro e ver todos os produtos" title="Ver todos">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </svg>
              </button>
            ) : null}
            {onOpenSettings ? (
              <button className="catalogSettingsButtonTs" type="button" onClick={onOpenSettings} aria-label="Abrir configurações" title="Configurações">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 1.55V21h-4v-.09a1.7 1.7 0 0 0-1.08-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1H3v-4h.09A1.7 1.7 0 0 0 4.64 8.9a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.55V3h4v.09a1.7 1.7 0 0 0 1.08 1.55 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.12.61.6 1.08 1.21 1.17H21v4h-.09A1.7 1.7 0 0 0 19.4 15Z" />
                </svg>
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
