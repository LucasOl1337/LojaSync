export type UndoRedoAction = "undo" | "redo";

type KeyboardShortcutEvent = {
  key?: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  target?: EventTarget | null;
};

export function isTextEntryTarget(target: EventTarget | null | undefined) {
  const node = target as HTMLElement | null | undefined;
  if (!node) return false;
  if (node.isContentEditable) return true;
  const tagName = String(node.tagName || "").toUpperCase();
  return tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT";
}

export function getGlobalUndoRedoAction(event: KeyboardShortcutEvent): UndoRedoAction | null {
  const key = String(event.key || "").toLowerCase();
  if (key !== "z") {
    return null;
  }
  if (!(event.ctrlKey || event.metaKey) || event.altKey) {
    return null;
  }
  if (isTextEntryTarget(event.target)) {
    return null;
  }
  return event.shiftKey ? "redo" : "undo";
}
