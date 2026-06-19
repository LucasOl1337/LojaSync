import type { NoticeTone } from "./noticeDialog";

export type NoticeToast = {
  id: number;
  title: string;
  message: string;
  tone: Extract<NoticeTone, "info" | "success">;
};

type NoticeToastStackProps = {
  toasts: NoticeToast[];
  onDismiss: (id: number) => void;
};

const TOAST_ICONS: Record<NoticeToast["tone"], string> = {
  info: "i",
  success: "✓",
};

export function NoticeToastStack({ toasts, onDismiss }: NoticeToastStackProps) {
  if (!toasts.length) {
    return null;
  }

  return (
    <div className="noticeToastRegionTs" role="status" aria-live="polite" aria-label="Atualizações da operação">
      {toasts.map((toast) => (
        <article key={toast.id} className={`noticeToastTs noticeToast-${toast.tone}`}>
          <div className="noticeToastIconTs" aria-hidden="true">{TOAST_ICONS[toast.tone]}</div>
          <div className="noticeToastBodyTs">
            <strong>{toast.title}</strong>
            <p>{toast.message}</p>
          </div>
          <button className="noticeToastCloseTs" type="button" onClick={() => onDismiss(toast.id)} aria-label={`Fechar aviso: ${toast.title}`}>
            ×
          </button>
        </article>
      ))}
    </div>
  );
}
