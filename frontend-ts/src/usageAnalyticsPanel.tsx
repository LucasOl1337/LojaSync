import type { UsageAnalyticsSummary } from "./usageAnalytics";

type UsageAnalyticsPanelProps = {
  summary: UsageAnalyticsSummary;
};

function activityLabel(count: number) {
  return `${count} ${count === 1 ? "atividade" : "atividades"}`;
}

export function UsageAnalyticsPanel({ summary }: UsageAnalyticsPanelProps) {
  if (!summary.eventCount) {
    return (
      <section className="usageAnalyticsPanelTs empty" aria-labelledby="usage-analytics-title">
        <div className="usageAnalyticsHeadTs">
          <strong id="usage-analytics-title">Pulso de hoje</strong>
          <span>aguardando atividade</span>
        </div>
        <p>Suas ações concluídas aparecerão aqui ao longo do dia.</p>
      </section>
    );
  }

  const visibleCategories = summary.categories.filter((category) => category.count > 0);
  const lastActivityTime = summary.lastActivity
    ? new Date(summary.lastActivity.occurredAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <section className="usageAnalyticsPanelTs" aria-labelledby="usage-analytics-title">
      <div className="usageAnalyticsHeadTs">
        <strong id="usage-analytics-title">Pulso de hoje</strong>
        <span>{activityLabel(summary.eventCount)}</span>
      </div>

      <div className="usageAnalyticsMetricsTs" aria-label="Indicadores de uso de hoje">
        <div><strong>{summary.successCount}</strong><span>conclusões</span></div>
        <div><strong>{summary.assistedFlowCount}</strong><span>fluxos assistidos</span></div>
        <div><strong>{summary.healthyRate}%</strong><span>sem falhas</span></div>
      </div>

      <div className="usageAnalyticsBreakdownTs" aria-label="Distribuição das atividades">
        {visibleCategories.map((category) => (
          <div className="usageAnalyticsCategoryTs" key={category.key}>
            <div>
              <span>{category.label}</span>
              <strong>{category.count}</strong>
            </div>
            <span className="usageAnalyticsTrackTs" aria-hidden="true">
              <span style={{ width: `${Math.max(category.share, 6)}%` }} />
            </span>
          </div>
        ))}
      </div>

      <p className="usageAnalyticsFootTs">
        <span>Ritmo dominante: <strong>{summary.dominantCategory?.label}</strong></span>
        {summary.lastActivity && lastActivityTime ? (
          <span title={summary.lastActivity.title}>Última às {lastActivityTime}</span>
        ) : null}
      </p>
    </section>
  );
}
