import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const { ExecutionCenterPanel } = await import(new URL("../.tmp-tests/executionCenterPanel.js", import.meta.url));

const noopAsync = async () => {};

function renderExecutionCenter(overrides = {}) {
  const props = {
    automationState: "idle",
    automationMessage: null,
    automationError: null,
    automationProgressWidth: "0%",
    pendingGradeCount: 0,
    executionReadiness: {
      ready: true,
      tone: "success",
      title: "Pronto para cadastro completo",
      detail: "Lista com produtos, grades fechadas e automação sem erro ativo.",
      items: [],
    },
    runBusyAction: async (_name, action) => action(),
    onStartComplete: noopAsync,
    onExecuteGrades: noopAsync,
    onStartCatalog: noopAsync,
    onStopAutomation: noopAsync,
    onJoinGrades: noopAsync,
    onOpenGradeModal: noopAsync,
    ...overrides,
  };

  return renderToStaticMarkup(React.createElement(ExecutionCenterPanel, props));
}

test("keeps the emergency stop button visible when automation status is idle", () => {
  const html = renderExecutionCenter({ automationState: "idle" });

  const cadastroIndex = html.indexOf("Executar cadastro");
  const pararIndex = html.indexOf("Parar", cadastroIndex);
  const stopButton = html.match(/<button[^>]*class="[^"]*stopActionButtonTs[^"]*"[^>]*>[\s\S]*?<\/button>/)?.[0] || "";

  assert.ok(cadastroIndex >= 0, "expected cadastro action to render");
  assert.ok(pararIndex > cadastroIndex, "expected Parar next to the cadastro action even while idle");
  assert.ok(stopButton, "expected the stop button to use the emergency stop styling hook");
  assert.equal(stopButton.includes("disabled"), false, "expected Parar to stay clickable as a failsafe");
});
