type CatalogActionDockProps = {
  manualEntryOpen: boolean;
  onToggleManualEntry: () => void;
  onImport: () => void;
  onOpenGrades: () => void;
  onExecute: () => void;
  onHistory: () => void;
};

function DockIcon({ name }: { name: "add" | "import" | "grade" | "execute" | "history" }) {
  if (name === "add") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>;
  if (name === "import") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 19h16" /></svg>;
  if (name === "grade") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v16H4zM4 10h16M10 4v16" /></svg>;
  if (name === "execute") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7z" /></svg>;
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.3-5.7L4 8.6M4 4v4.6h4.6M12 8v5l3 2" /></svg>;
}

export function CatalogActionDock({
  manualEntryOpen,
  onToggleManualEntry,
  onImport,
  onOpenGrades,
  onExecute,
  onHistory,
}: CatalogActionDockProps) {
  const actions = [
    { key: "add", label: "Novo produto", icon: "add" as const, onClick: onToggleManualEntry, primary: true, pressed: manualEntryOpen },
    { key: "import", label: "Importar arquivo", icon: "import" as const, onClick: onImport, primary: false, pressed: false },
    { key: "grade", label: "Gerenciar grades", icon: "grade" as const, onClick: onOpenGrades, primary: false, pressed: false },
    { key: "execute", label: "Executar catálogo", icon: "execute" as const, onClick: onExecute, primary: false, pressed: false },
    { key: "history", label: "Ver histórico", icon: "history" as const, onClick: onHistory, primary: false, pressed: false },
  ];

  return (
    <nav className="catalogActionDockWrapTs" aria-label="Ações do catálogo">
      <div className="catalogActionDockTs">
        {actions.map((action) => (
          <button
            key={action.key}
            className={`catalogActionDockButtonTs ${action.primary ? "primary" : ""} ${action.pressed ? "active" : ""}`}
            type="button"
            onClick={action.onClick}
            aria-label={action.label}
            title={action.label}
            aria-pressed={action.primary ? action.pressed : undefined}
          >
            <DockIcon name={action.icon} />
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
