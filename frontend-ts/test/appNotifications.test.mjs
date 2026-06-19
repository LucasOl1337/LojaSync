import assert from "node:assert/strict";
import test from "node:test";

const notifications = await import(new URL("../.tmp-tests/appNotifications.js", import.meta.url));

test("builds toasts only for transient notice tones", () => {
  assert.deepEqual(notifications.buildNoticeToast(1, { title: "Sincronizado", message: "Lista atualizada." }), {
    id: 1,
    title: "Sincronizado",
    message: "Lista atualizada.",
    tone: "info",
  });
  assert.deepEqual(notifications.buildNoticeToast(2, { title: "Pronto", message: "Cadastro concluido.", tone: "success" }), {
    id: 2,
    title: "Pronto",
    message: "Cadastro concluido.",
    tone: "success",
  });

  assert.equal(notifications.buildNoticeToast(3, { title: "Atencao", message: "Revise os itens.", tone: "warning" }), null);
  assert.equal(notifications.buildNoticeToast(4, { title: "Erro", message: "Falha na operacao.", tone: "danger" }), null);
});

test("appends notice toasts with immutable limit trimming", () => {
  const current = [
    { id: 1, title: "A", message: "1", tone: "info" },
    { id: 2, title: "B", message: "2", tone: "info" },
    { id: 3, title: "C", message: "3", tone: "success" },
  ];
  const toast = { id: 4, title: "D", message: "4", tone: "info" };

  const next = notifications.appendNoticeToast(current, toast, 2);

  assert.deepEqual(next.map((entry) => entry.id), [3, 4]);
  assert.deepEqual(current.map((entry) => entry.id), [1, 2, 3]);
  assert.deepEqual(notifications.appendNoticeToast(current, toast, 0), []);
});

test("dismisses notice toasts by id without mutating the source list", () => {
  const current = [
    { id: 1, title: "A", message: "1", tone: "info" },
    { id: 2, title: "B", message: "2", tone: "success" },
  ];

  assert.deepEqual(notifications.dismissNoticeToast(current, 1).map((entry) => entry.id), [2]);
  assert.deepEqual(current.map((entry) => entry.id), [1, 2]);
});
