import assert from "node:assert/strict";
import test from "node:test";

const appConfig = await import(new URL("../.tmp-tests/appConfig.js", import.meta.url));
const ui = await import(new URL("../.tmp-tests/uiFormatting.js", import.meta.url));

test("allows up to fifty undo redo snapshots", () => {
  assert.equal(appConfig.MAX_UNDO_HISTORY, 50);
});

test("formats singular and plural count labels", () => {
  assert.equal(ui.actionText(1, "item ativo", "itens ativos"), "1 item ativo");
  assert.equal(ui.actionText(2, "item ativo", "itens ativos"), "2 itens ativos");
});

test("formats durations without negative or fractional artifacts", () => {
  assert.equal(ui.formatDuration(0), "0s");
  assert.equal(ui.formatDuration(-30), "0s");
  assert.equal(ui.formatDuration(65), "1min 5s");
  assert.equal(ui.formatDuration(3661), "1h 1min 1s");
});

test("parses prompt integers only when the whole input is a positive integer", () => {
  assert.equal(ui.parsePromptInteger(" 12 "), 12);
  assert.equal(ui.parsePromptInteger("12abc"), null);
  assert.equal(ui.parsePromptInteger("0"), null);
  assert.equal(ui.parsePromptInteger(null), null);
});

test("normalizes target points from finite coordinates only", () => {
  assert.deepEqual(ui.normalizeTargetPoint({ x: "10", y: "20" }), { x: 10, y: 20 });
  assert.deepEqual(ui.normalizeTargetPoint({ x: 0, y: 0 }), { x: 0, y: 0 });
  assert.equal(ui.normalizeTargetPoint({ x: "abc", y: 20 }), null);
  assert.equal(ui.normalizeTargetPoint({ x: 10 }), null);
});

test("formats target points for settings displays", () => {
  assert.equal(ui.formatTargetPoint(null), "Não calibrado");
  assert.equal(ui.formatTargetPoint({ x: 10, y: 20 }), "X: 10 | Y: 20");
});

test("formats caught errors with a fallback message", () => {
  assert.equal(ui.formatCaughtErrorMessage(new Error("Falha real"), "Fallback"), "Falha real");
  assert.equal(ui.formatCaughtErrorMessage("texto solto", "Fallback"), "Fallback");
  assert.equal(ui.formatCaughtErrorMessage(null, "Fallback"), "Fallback");
});

test("coerces import process logs to displayable entries", () => {
  assert.deepEqual(
    ui.coerceImportProcessLog({
      process_log: [
        { index: "2", source: " parser ", level: " warning ", message: "  Ajustado  " },
        { source: "", level: "", message: "" },
        "ignored",
      ],
    }),
    [{ index: 2, source: "parser", level: "warning", message: "Ajustado" }],
  );
});

test("builds import progress messages from the latest job status", () => {
  assert.equal(ui.buildImportProgressMessage(false, "Processando com servico LLM"), null);
  assert.equal(ui.buildImportProgressMessage(true, null), "Importação em andamento...");
  assert.equal(ui.buildImportProgressMessage(true, "  Processando texto 2/3 com servico LLM  "), "Processando texto 2/3 com IA");
});

test("builds import diagnostics chips from existing metrics", () => {
  assert.deepEqual(
    ui.buildImportDiagnosticsChips(
      {
        selected_source: "llm",
        llm_chat_calls: 2,
        llm_chunk_count: 3,
        upload_images: 1,
        llm_chat_calls_details: [{ attempt: "full_page" }, { attempt: "vertical_slices" }],
      },
      ["OCR por pagina inteira sem itens validos"],
    ),
    [
      { label: "Origem", value: "IA", tone: "neutral" },
    ],
  );

  assert.deepEqual(ui.buildImportDiagnosticsChips({ selected_source: "local" }), [
    { label: "Origem", value: "Leitura local", tone: "success" },
  ]);
  assert.deepEqual(ui.buildImportDiagnosticsChips(null), []);
});

test("builds operational health chips from runtime, auth, websocket and automation status", () => {
  assert.deepEqual(
    ui.buildOperationalHealthChips({
      backendStatus: "ok",
      authEnabled: true,
      authenticated: true,
      websocketStatus: "connected",
      automationState: "running",
      pendingGrades: 2,
    }),
    [
      { label: "Backend", value: "Ativo", tone: "success" },
      { label: "Auth", value: "Sessão ativa", tone: "success" },
      { label: "Tempo real", value: "Conectado", tone: "success" },
      { label: "Automação", value: "Em execução", tone: "warning" },
      { label: "Grades", value: "2 pendentes", tone: "warning" },
    ],
  );

  assert.deepEqual(
    ui.buildOperationalHealthChips({
      backendStatus: "error",
      backendError: "Falha de rede",
      authEnabled: true,
      authenticated: false,
      websocketStatus: "reconnecting",
      automationError: "ByteEmpresa fechado",
      pendingGrades: 0,
    }),
    [
      { label: "Backend", value: "Indisponível", tone: "error" },
      { label: "Auth", value: "Login pendente", tone: "warning" },
      { label: "Tempo real", value: "Polling API", tone: "neutral" },
      { label: "Automação", value: "ByteEmpresa fechado", tone: "error" },
      { label: "Grades", value: "Sem pendências", tone: "success" },
    ],
  );
});

test("formats automation state labels for operator-facing UI", () => {
  assert.equal(ui.formatAutomationStateLabel(null), "Pronta");
  assert.equal(ui.formatAutomationStateLabel("idle"), "Pronta");
  assert.equal(ui.formatAutomationStateLabel("running"), "Em execução");
  assert.equal(ui.formatAutomationStateLabel("stopping"), "Parando");
  assert.equal(ui.formatAutomationStateLabel("failed"), "Falha");
  assert.equal(ui.formatAutomationStateLabel("queued"), "Na fila");
  assert.equal(ui.formatAutomationStateLabel("paused"), "Pausada");
  assert.equal(ui.formatAutomationStateLabel("custom-state"), "custom-state");
});

test("builds execution readiness from list, grades and automation state", () => {
  assert.deepEqual(
    ui.buildExecutionReadiness({
      productCount: 8,
      pendingGradeCount: 0,
      automationState: "idle",
      automationError: null,
    }),
    {
      ready: true,
      tone: "success",
      title: "Pronto",
      detail: "",
      items: [],
    },
  );

  assert.deepEqual(
    ui.buildExecutionReadiness({
      productCount: 3,
      pendingGradeCount: 2,
      automationState: "idle",
      automationError: "",
    }),
    {
      ready: false,
      tone: "warning",
      title: "2 grades com divergência",
      detail: "Abra Inserir grade para fechar as divergências antes do cadastro completo.",
      items: [
        { label: "Grades", value: "2 divergentes", tone: "warning" },
      ],
    },
  );

  assert.deepEqual(
    ui.buildExecutionReadiness({
      productCount: 0,
      pendingGradeCount: 0,
      automationState: "running",
      automationError: "ByteEmpresa fechado",
    }),
    {
      ready: false,
      tone: "error",
      title: "Revisar automação",
      detail: "Corrija o erro da automação antes de iniciar o cadastro completo.",
      items: [
        { label: "Lista", value: "Sem produtos", tone: "warning" },
        { label: "Automação", value: "ByteEmpresa fechado", tone: "error" },
      ],
    },
  );

  assert.deepEqual(
    ui.buildExecutionReadiness({
      productCount: 5,
      pendingGradeImportCount: 2,
      pendingGradeCount: 0,
      automationState: "idle",
      automationError: null,
    }),
    {
      ready: false,
      tone: "warning",
      title: "2 grades para importar",
      detail: "Use Importar grades para aplicar as grades detectadas antes do cadastro completo.",
      items: [
        { label: "Grades", value: "2 a importar", tone: "warning" },
      ],
    },
  );

  assert.deepEqual(
    ui.buildExecutionReadiness({
      productCount: 5,
      pendingGradeImportCount: 1,
      pendingGradeCount: 1,
      automationState: "idle",
      automationError: null,
    }),
    {
      ready: false,
      tone: "warning",
      title: "2 ajustes de grade pendentes",
      detail: "Importe as grades detectadas e corrija as divergências antes do cadastro completo.",
      items: [
        { label: "Grades", value: "2 ajustes", tone: "warning" },
      ],
    },
  );

  assert.deepEqual(
    ui.buildExecutionReadiness({
      productCount: 5,
      pendingGradeCount: 0,
      automationState: "idle",
      automationError: null,
    }),
    {
      ready: true,
      tone: "success",
      title: "Pronto",
      detail: "",
      items: [],
    },
  );
});

test("builds automation status detail without stale idle cancellation messages", () => {
  assert.equal(
    ui.buildAutomationStatusDetail({
      automationState: "idle",
      automationMessage: "Cancelado pelo usuario",
      automationError: null,
      pendingGradeCount: 0,
    }),
    "Sem automação em execução",
  );
  assert.equal(
    ui.buildAutomationStatusDetail({
      automationState: "running",
      automationMessage: "Processando item 3",
      automationError: null,
      pendingGradeCount: 0,
    }),
    "Processando item 3",
  );
  assert.equal(
    ui.buildAutomationStatusDetail({
      automationState: "idle",
      automationMessage: "Processando item 3",
      automationError: "ByteEmpresa fechado",
      pendingGradeCount: 0,
    }),
    "ByteEmpresa fechado",
  );
  assert.equal(
    ui.buildAutomationStatusDetail({
      automationState: "idle",
      automationMessage: null,
      automationError: null,
      pendingGradeCount: 2,
    }),
    "2 grades pendentes",
  );
});

test("builds undo and redo history status from stack sizes", () => {
  assert.deepEqual(ui.buildUndoRedoHistoryState(0, 0), {
    undoCount: 0,
    redoCount: 0,
    canUndo: false,
    canRedo: false,
    summary: "Histórico vazio",
    undoLabel: "Nada para desfazer",
    redoLabel: "Nada para refazer",
  });

  assert.deepEqual(ui.buildUndoRedoHistoryState(2.7, "1"), {
    undoCount: 2,
    redoCount: 1,
    canUndo: true,
    canRedo: true,
    summary: "Histórico: 2 desfazer / 1 refazer",
    undoLabel: "Desfazer 2 ações",
    redoLabel: "Refazer 1 ação",
  });

  assert.deepEqual(ui.buildUndoRedoHistoryState(-5, Number.NaN), {
    undoCount: 0,
    redoCount: 0,
    canUndo: false,
    canRedo: false,
    summary: "Histórico vazio",
    undoLabel: "Nada para desfazer",
    redoLabel: "Nada para refazer",
  });
});

test("builds a safe clear-list confirmation for the full and filtered catalog", () => {
  assert.deepEqual(ui.buildClearProductsConfirmation(12, 12), {
    title: "Limpar toda a lista?",
    message: "12 produtos serão removidos do catálogo ativo.",
    detail: "Esta ação pode ser desfeita pelo histórico da lista.",
    confirmLabel: "Remover 12 produtos",
  });

  assert.deepEqual(ui.buildClearProductsConfirmation(12, 4), {
    title: "Limpar toda a lista?",
    message: "12 produtos serão removidos do catálogo ativo.",
    detail: "A busca atual oculta 8 produtos, que também serão removidos. Esta ação pode ser desfeita pelo histórico da lista.",
    confirmLabel: "Remover 12 produtos",
  });

  assert.deepEqual(ui.buildClearProductsConfirmation(1, 0), {
    title: "Limpar toda a lista?",
    message: "1 produto será removido do catálogo ativo.",
    detail: "A busca atual oculta 1 produto, que também será removido. Esta ação pode ser desfeita pelo histórico da lista.",
    confirmLabel: "Remover produto",
  });
});

test("builds and limits recent import history entries", () => {
  const entry = ui.buildImportHistoryEntry(
    {
      status: "ok",
      saved_file: null,
      local_file: "romaneio.pdf",
      content: null,
      warnings: ["Aviso"],
      total_itens: 12,
      grades_disponiveis: true,
      total_grades_disponiveis: 4,
      imported_keys: ["a"],
      metrics: { selected_source: "local", final_validation_status: "approved" },
    },
    {
      job: { job_id: "job-1", updated_at: 1710000000, completed_at: 1710000001 },
      selectedFileName: "upload.pdf",
      mode: "llm",
    },
  );

  assert.deepEqual(entry, {
    id: "job-1",
    completedAt: 1710000001000,
    sourceName: "romaneio.pdf",
    mode: "Leitura local",
    totalItems: 12,
    warningCount: 1,
    validationStatus: "approved",
    gradesAvailable: true,
    status: "ok",
  });

  assert.equal(
    ui.buildImportHistoryEntry(
      {
        status: "ok",
        saved_file: null,
        local_file: "romaneio-ia.pdf",
        content: null,
        warnings: [],
        total_itens: 8,
        grades_disponiveis: false,
        total_grades_disponiveis: 0,
        imported_keys: [],
        metrics: { selected_source: "llm", final_validation_status: "approved" },
      },
      { now: 1710000002000, mode: "llm" },
    ).mode,
    "IA",
  );

  assert.deepEqual(
    ui.updateRecentImportHistory(
      [
        { ...entry, id: "old-1", completedAt: 1 },
        { ...entry, id: "job-1", totalItems: 4, completedAt: 2 },
        { ...entry, id: "old-2", completedAt: 3 },
      ],
      entry,
      2,
    ),
    [entry, { ...entry, id: "old-2", completedAt: 3 }],
  );

  assert.deepEqual(
    ui.coerceImportHistoryEntries([
      { ...entry, id: "valid", completedAt: 9, warningCount: "2" },
      { id: "", completedAt: 10 },
      "ignored",
    ]),
    [{ ...entry, id: "valid", completedAt: 9, warningCount: 2 }],
  );
});

test("formats recent import source names for compact rail display", () => {
  assert.equal(ui.formatImportSourceDisplayName("C:\\Projetos\\LojaSync\\data\\romaneios\\romaneio-final.pdf"), "romaneio-final.pdf");
  assert.equal(ui.formatImportSourceDisplayName("C:\\Projetos\\LojaSync\\data\\romaneios\\romaneio_20260618_182958.txt"), "romaneio_20260618_182958.txt");
  assert.equal(ui.formatImportSourceDisplayName("/data/imports/fornecedor A.txt"), "fornecedor A.txt");
  assert.equal(ui.formatImportSourceDisplayName("upload-avulso.pdf"), "upload-avulso.pdf");
  assert.equal(ui.formatImportSourceDisplayName("   "), "Romaneio importado");
});

test("formats import validation statuses for operator-facing UI", () => {
  assert.equal(ui.formatImportValidationStatus("approved"), "Aprovado");
  assert.equal(ui.formatImportValidationStatus("rejected"), "Rejeitado");
  assert.equal(ui.formatImportValidationStatus("unverified"), "Não validado");
  assert.equal(ui.formatImportValidationStatus("error"), "Erro");
  assert.equal(ui.formatImportValidationStatus(""), "Sem validação");
  assert.equal(ui.formatImportValidationStatus("custom"), "custom");
});

test("builds and protects operation diary entries", () => {
  const entry = ui.buildOperationDiaryEntry({
    kind: "import",
    title: "Importacao concluida",
    detail: "romaneio.pdf",
    tone: "success",
    occurredAt: 1710001000000,
    meta: ["Leitura local", "12 itens", "", null, "1 aviso"],
  });

  assert.deepEqual(entry, {
    id: "import-1710001000000-importacao-concluida",
    occurredAt: 1710001000000,
    kind: "import",
    title: "Importacao concluida",
    detail: "romaneio.pdf",
    tone: "success",
    meta: ["Leitura local", "12 itens", "1 aviso"],
  });

  assert.deepEqual(
    ui.updateOperationDiaryEntries(
      [
        { ...entry, id: "old-1", occurredAt: 1 },
        { ...entry, id: "import-1710001000000-importacao-concluida", detail: "duplicada" },
        { ...entry, id: "old-2", occurredAt: 3 },
      ],
      entry,
      2,
    ),
    [entry, { ...entry, id: "old-2", occurredAt: 3 }],
  );

  assert.deepEqual(
    ui.coerceOperationDiaryEntries([
      { ...entry, id: "valid", occurredAt: 9, tone: "warning", meta: [" A ", 2, ""] },
      { id: "", occurredAt: 10 },
      { id: "bad-tone", occurredAt: 11, title: "Sem tom", detail: "Fallback", tone: "purple" },
      "ignored",
    ]),
    [
      {
        id: "bad-tone",
        occurredAt: 11,
        kind: "system",
        title: "Sem tom",
        detail: "Fallback",
        tone: "neutral",
        meta: [],
      },
      { ...entry, id: "valid", occurredAt: 9, tone: "warning", meta: ["A", "2"] },
    ],
  );
});

test("builds product operation diary entries for relevant edits", () => {
  assert.deepEqual(
    ui.buildProductOperationDiaryEntry({
      action: "inline_edit",
      productName: " Camiseta Azul ",
      fieldLabel: "Preco",
      occurredAt: 1710002000000,
      meta: ["R$ 19,90", "", null],
    }),
    {
      id: "product-1710002000000-produto-editado",
      occurredAt: 1710002000000,
      kind: "product",
      title: "Produto editado",
      detail: "Camiseta Azul",
      tone: "success",
      meta: ["Campo: Preco", "R$ 19,90"],
    },
  );

  assert.deepEqual(
    ui.buildProductOperationDiaryEntry({
      action: "clear",
      productCount: 12,
      occurredAt: 1710002005000,
    }),
    {
      id: "product-1710002005000-lista-limpa",
      occurredAt: 1710002005000,
      kind: "product",
      title: "Lista limpa",
      detail: "12 produtos removidos",
      tone: "warning",
      meta: ["12 itens"],
    },
  );

  assert.deepEqual(
    ui.buildProductOperationDiaryEntry({
      action: "bulk_brand",
      value: "  Nike  ",
      productCount: 0,
      occurredAt: 1710002010000,
    }),
    {
      id: "product-1710002010000-marca-aplicada",
      occurredAt: 1710002010000,
      kind: "product",
      title: "Marca aplicada",
      detail: "Nike",
      tone: "success",
      meta: [],
    },
  );
});

test("builds import completion messages only when grade groups are available", () => {
  assert.equal(ui.buildImportGradesAvailableMessage({ grades_disponiveis: false, total_grades_disponiveis: 0 }), null);
  assert.equal(
    ui.buildImportGradesAvailableMessage({ grades_disponiveis: true, total_grades_disponiveis: 0 }),
    "Grades automáticas disponíveis.\n\nClique em Importar grades para aplicar.",
  );
  assert.equal(
    ui.buildImportGradesAvailableMessage({ grades_disponiveis: true, total_grades_disponiveis: 3 }),
    "Grades automáticas disponíveis.\n\nClique em Importar grades para aplicar.\nGrupos detectados: 3",
  );
});

test("clones product snapshots without sharing nested references", () => {
  const original = [{ ordering_key: "1", grades: [{ tamanho: "P", quantidade: 1 }] }];
  const cloned = ui.cloneSnapshotProducts(original);

  cloned[0].grades[0].quantidade = 3;

  assert.equal(original[0].grades[0].quantidade, 1);
  assert.equal(cloned[0].grades[0].quantidade, 3);
});

test("keeps undo redo history stacks bounded to the newest snapshots", () => {
  const stack = Array.from({ length: 50 }, (_, index) => `snapshot-${index + 1}`);

  ui.pushBoundedHistorySnapshot(stack, "snapshot-51", 50);

  assert.equal(stack.length, 50);
  assert.equal(stack[0], "snapshot-2");
  assert.equal(stack[49], "snapshot-51");

  ui.pushBoundedHistorySnapshot(stack, "snapshot-52", 50);

  assert.equal(stack.length, 50);
  assert.equal(stack[0], "snapshot-3");
  assert.equal(stack[49], "snapshot-52");
});
