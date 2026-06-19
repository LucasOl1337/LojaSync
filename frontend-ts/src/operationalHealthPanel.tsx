import type { StatusChip } from "./uiFormatting";

type OperationalHealthPanelProps = {
  chips: StatusChip[];
  checkedAt?: number | null;
};

function getCompactHealthCopy(chip: StatusChip): { label: string; value: string } {
  const label = chip.label === "Backend"
    ? "API"
    : chip.label === "Automação"
        ? "Auto"
        : chip.label;
  let value = chip.value;
  if (chip.label === "Backend") {
    value = chip.value === "Ativo" ? "OK" : chip.value === "Indisponível" ? "Erro" : chip.value;
  } else if (chip.label === "Auth") {
    value = chip.value === "Sessão ativa" ? "Ativa" : chip.value === "Login pendente" ? "Login" : chip.value;
  } else if (chip.label === "Tempo real") {
    value = chip.value === "Conectado" ? "OK" : chip.value;
  } else if (chip.label === "Automação") {
    value = chip.value === "idle" ? "Idle" : chip.value === "running" ? "Run" : chip.value;
  } else if (chip.label === "Grades") {
    value = chip.value === "Sem pendências" ? "OK" : chip.value.replace("pendentes", "pend.").replace("pendente", "pend.");
  }
  return { label, value };
}

export function OperationalHealthPanel({ chips, checkedAt }: OperationalHealthPanelProps) {
  const updatedAt = checkedAt ? new Date(checkedAt).toLocaleTimeString("pt-BR") : null;

  return (
    <div className="operationalHealthPanelTs">
      <div className="operationalHealthPanelHeaderTs">
        <strong>Saúde operacional</strong>
        {updatedAt ? <span>{updatedAt}</span> : null}
      </div>
      <div className="importInsightChipsTs">
        {chips.map((chip) => {
          const compactCopy = getCompactHealthCopy(chip);
          const visibleLabel = compactCopy.label;
          const visibleValue = compactCopy.value;
          const fullText = `${chip.label}: ${chip.value}`;

          return (
            <div
              key={`${chip.label}-${chip.value}`}
              className={`importInsightChipTs chip-${chip.tone} ${chip.label === "Tempo real" ? "healthRealtimeChipTs" : ""}`}
              aria-label={fullText}
              title={fullText}
            >
              <span>{visibleLabel}</span>
              <strong>{visibleValue}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}
