import assert from "node:assert/strict";
import test from "node:test";

const shortcuts = await import(new URL("../.tmp-tests/keyboardShortcuts.js", import.meta.url));

function event(overrides = {}) {
  return {
    key: "z",
    ctrlKey: true,
    metaKey: false,
    altKey: false,
    shiftKey: false,
    target: null,
    ...overrides,
  };
}

test("detects global undo and redo shortcuts only outside text entry targets", () => {
  assert.equal(shortcuts.getGlobalUndoRedoAction(event()), "undo");
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ shiftKey: true })), "redo");
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ ctrlKey: false, metaKey: true })), "undo");

  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ key: "x" })), null);
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ ctrlKey: false, metaKey: false })), null);
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ altKey: true })), null);
});

test("ignores global undo and redo when focus is in editable controls", () => {
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ target: { tagName: "INPUT" } })), null);
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ target: { tagName: "textarea" } })), null);
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ target: { tagName: "SELECT" } })), null);
  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ target: { isContentEditable: true, tagName: "DIV" } })), null);

  assert.equal(shortcuts.getGlobalUndoRedoAction(event({ target: { tagName: "DIV" } })), "undo");
});
