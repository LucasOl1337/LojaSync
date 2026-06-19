import { useEffect, useRef, type KeyboardEvent } from "react";

export type ConfirmationTone = "danger" | "warning";

type ConfirmationDialogProps = {
  title: string;
  message: string;
  detail?: string;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: ConfirmationTone;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmationDialog({
  title,
  message,
  detail,
  confirmLabel,
  cancelLabel = "Cancelar",
  tone = "danger",
  busy = false,
  error,
  onCancel,
  onConfirm,
}: ConfirmationDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const detailBreakIndex = detail?.indexOf(".");
  const detailLead = detail && detailBreakIndex && detailBreakIndex > 0 ? detail.slice(0, detailBreakIndex + 1) : detail;
  const detailRest = detail && detailBreakIndex && detailBreakIndex > 0 ? detail.slice(detailBreakIndex + 1).trim() : "";

  useEffect(() => {
    const previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const timerId = window.setTimeout(() => cancelButtonRef.current?.focus(), 0);

    return () => {
      window.clearTimeout(timerId);
      previousActiveElement?.focus();
    };
  }, []);

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
    <div className="confirmationBackdropTs" onClick={busy ? undefined : onCancel}>
      <section
        ref={dialogRef}
        className={`confirmationDialogTs confirmationTone-${tone}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirmation-dialog-title"
        aria-describedby="confirmation-dialog-message"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="confirmationIconTs" aria-hidden="true">!</div>
        <div className="confirmationBodyTs">
          <span className="sectionTag">Confirmação</span>
          <h3 id="confirmation-dialog-title">{title}</h3>
          <p id="confirmation-dialog-message">{message}</p>
          {detail ? (
            <small className="confirmationDetailTs">
              {detailLead ? <strong>{detailLead}</strong> : null}
              {detailRest ? <span>{detailRest}</span> : null}
            </small>
          ) : null}
          {error ? <div className="confirmationErrorTs" role="alert">{error}</div> : null}
        </div>
        <div className="confirmationActionsTs">
          <button
            ref={cancelButtonRef}
            className="ghostButton miniActionButton confirmationCancelButtonTs"
            type="button"
            onClick={onCancel}
            disabled={busy}
          >
            {cancelLabel}
          </button>
          <button
            className="toolButtonTs danger confirmationConfirmButtonTs"
            type="button"
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? "Executando..." : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
