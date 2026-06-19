import { useEffect, useRef, useState } from "react";

import type { NoticeTone } from "./noticeDialog";
import type { NoticeToast } from "./noticeToastStack";

export type NoticeDialogState = {
  title: string;
  message: string;
  tone?: NoticeTone;
  confirmLabel?: string;
};

export const NOTICE_TOAST_LIMIT = 4;
export const NOTICE_TOAST_TIMEOUT_MS = 9000;

export function buildNoticeToast(id: number, dialog: NoticeDialogState): NoticeToast | null {
  const tone = dialog.tone ?? "info";
  if (tone !== "info" && tone !== "success") {
    return null;
  }

  return {
    id,
    title: dialog.title,
    message: dialog.message,
    tone,
  };
}

export function appendNoticeToast(current: NoticeToast[], toast: NoticeToast, limit = NOTICE_TOAST_LIMIT): NoticeToast[] {
  if (limit <= 0) {
    return [];
  }
  return [...current, toast].slice(-limit);
}

export function dismissNoticeToast(current: NoticeToast[], id: number): NoticeToast[] {
  return current.filter((toast) => toast.id !== id);
}

export function useNoticeCenter() {
  const [noticeDialog, setNoticeDialog] = useState<NoticeDialogState | null>(null);
  const [noticeToasts, setNoticeToasts] = useState<NoticeToast[]>([]);
  const noticeToastSeq = useRef(0);

  useEffect(() => {
    if (!noticeToasts.length) return;

    const timerId = window.setTimeout(() => {
      setNoticeToasts((current) => current.slice(1));
    }, NOTICE_TOAST_TIMEOUT_MS);

    return () => window.clearTimeout(timerId);
  }, [noticeToasts]);

  const showNoticeDialog = (dialog: NoticeDialogState) => {
    const nextToastId = noticeToastSeq.current + 1;
    const toast = buildNoticeToast(nextToastId, dialog);
    if (toast) {
      noticeToastSeq.current = nextToastId;
      setNoticeToasts((current) => appendNoticeToast(current, toast));
      return;
    }

    setNoticeDialog(dialog);
  };

  const showErrorNotice = (title: string, message: string) => {
    showNoticeDialog({ title, message, tone: "danger" });
  };

  const closeNoticeDialog = () => {
    setNoticeDialog(null);
  };

  const dismissNoticeToastById = (id: number) => {
    setNoticeToasts((current) => dismissNoticeToast(current, id));
  };

  return {
    noticeDialog,
    noticeToasts,
    showNoticeDialog,
    showErrorNotice,
    closeNoticeDialog,
    dismissNoticeToast: dismissNoticeToastById,
  };
}
