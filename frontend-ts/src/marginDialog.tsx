import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";

import { formatPercentDisplay } from "./productPricing";

type MarginDialogProps = {
  currentPercent: number;
  value: string;
  busy?: boolean;
  error?: string | null;
  onChange: (value: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
};

export function MarginDialog({
  currentPercent,
  value,
  busy = false,
  error,
  onChange,
  onCancel,
  onConfirm,
}: MarginDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const currentPercentDisplay = formatPercentDisplay(currentPercent);

  useEffect(() => {
    const previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const timerId = window.setTimeout(() => {
      inputRef.current?.focus();
      inputRef.current?.select();
    }, 0);

    return () => {
      window.clearTimeout(timerId);
      previousActiveElement?.focus();
    };
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onConfirm();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape" && !busy) {
      event.preventDefault();
      event.stopPropagation();
      onCancel();
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const focusable = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    ).filter((element) => element.offsetParent !== null);

    if (!focusable.length) {
      return;
    }

    const firstElement = focusable[0];
    const lastElement = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  };

  return (
    <div className="marginDialogBackdropTs" onClick={busy ? undefined : onCancel}>
      <section
        ref={dialogRef}
        className="marginDialogTs"
        role="dialog"
        aria-modal="true"
        aria-labelledby="margin-dialog-title"
        aria-describedby="margin-dialog-description"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="marginDialogHeaderTs">
          <div className="marginDialogTitleBlockTs">
            <span className="sectionTag">Financeiro</span>
            <h3 id="margin-dialog-title">Aplicar margem padrão</h3>
            <p id="margin-dialog-description">Atualize a margem da sessão e recalcule os preços de venda da lista ativa.</p>
          </div>
          <span className="marginCurrentChipTs">{currentPercentDisplay}</span>
        </div>

        <form className="marginDialogFormTs" onSubmit={handleSubmit}>
          <label className="marginDialogFieldTs">
            <span>Margem percentual</span>
            <div className="marginInputWrapTs">
              <input
                ref={inputRef}
                value={value}
                onChange={(event) => onChange(event.target.value)}
                inputMode="decimal"
                autoComplete="off"
                aria-invalid={Boolean(error)}
                aria-describedby={error ? "margin-dialog-error" : "margin-dialog-description"}
                disabled={busy}
                placeholder="120,00"
              />
              <span aria-hidden="true">%</span>
            </div>
          </label>
          <small className="marginDialogHintTs">Use ponto ou vírgula para casas decimais. O valor precisa ser maior que zero.</small>
          {error ? <div className="marginDialogErrorTs" id="margin-dialog-error" role="alert">{error}</div> : null}

          <div className="marginDialogActionsTs">
            <button className="ghostButton miniActionButton marginCancelButtonTs" type="button" onClick={onCancel} disabled={busy}>
              Cancelar
            </button>
            <button className="toolButtonTs marginConfirmButtonTs" type="submit" disabled={busy}>
              {busy ? "Aplicando..." : "Aplicar margem"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
