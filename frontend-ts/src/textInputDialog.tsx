import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";

type TextInputDialogProps = {
  title: string;
  description: string;
  label: string;
  value: string;
  confirmLabel: string;
  sectionTag?: string;
  placeholder?: string;
  busy?: boolean;
  error?: string | null;
  onChange: (value: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
};

export function TextInputDialog({
  title,
  description,
  label,
  value,
  confirmLabel,
  sectionTag = "Editar",
  placeholder,
  busy = false,
  error,
  onChange,
  onCancel,
  onConfirm,
}: TextInputDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
    <div className="textInputDialogBackdropTs" onClick={busy ? undefined : onCancel}>
      <section
        ref={dialogRef}
        className="textInputDialogTs"
        role="dialog"
        aria-modal="true"
        aria-labelledby="text-input-dialog-title"
        aria-describedby="text-input-dialog-description"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="textInputDialogHeaderTs">
          <span className="sectionTag">{sectionTag}</span>
          <h3 id="text-input-dialog-title">{title}</h3>
          <p id="text-input-dialog-description">{description}</p>
        </div>

        <form className="textInputDialogFormTs" onSubmit={handleSubmit}>
          <label className="textInputDialogFieldTs">
            <span>{label}</span>
            <input
              ref={inputRef}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              autoComplete="off"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "text-input-dialog-error" : "text-input-dialog-description"}
              disabled={busy}
              placeholder={placeholder}
            />
          </label>
          {error ? <div className="textInputDialogErrorTs" id="text-input-dialog-error" role="alert">{error}</div> : null}

          <div className="textInputDialogActionsTs">
            <button className="ghostButton miniActionButton textInputCancelButtonTs" type="button" onClick={onCancel} disabled={busy}>
              Cancelar
            </button>
            <button className="toolButtonTs textInputConfirmButtonTs" type="submit" disabled={busy}>
              {busy ? "Salvando..." : confirmLabel}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
