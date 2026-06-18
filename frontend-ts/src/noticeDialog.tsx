import { useEffect, useRef, type KeyboardEvent } from "react";

export type NoticeTone = "info" | "success" | "warning" | "danger";

type NoticeDialogProps = {
  title: string;
  message: string;
  tone?: NoticeTone;
  confirmLabel?: string;
  onClose: () => void;
};

const NOTICE_ICONS: Record<NoticeTone, string> = {
  info: "i",
  success: "✓",
  warning: "!",
  danger: "!",
};

export function NoticeDialog({
  title,
  message,
  tone = "info",
  confirmLabel = "OK",
  onClose,
}: NoticeDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const timerId = window.setTimeout(() => closeButtonRef.current?.focus(), 0);

    return () => {
      window.clearTimeout(timerId);
      previousActiveElement?.focus();
    };
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      onClose();
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
    <div className="noticeDialogBackdropTs" onClick={onClose}>
      <section
        ref={dialogRef}
        className={`noticeDialogTs noticeTone-${tone}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="notice-dialog-title"
        aria-describedby="notice-dialog-message"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="noticeDialogIconTs" aria-hidden="true">{NOTICE_ICONS[tone]}</div>
        <div className="noticeDialogBodyTs">
          <span className="sectionTag">Aviso</span>
          <h3 id="notice-dialog-title">{title}</h3>
          <p id="notice-dialog-message">{message}</p>
        </div>
        <div className="noticeDialogActionsTs">
          <button ref={closeButtonRef} className="toolButtonTs noticeConfirmButtonTs" type="button" onClick={onClose}>
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
