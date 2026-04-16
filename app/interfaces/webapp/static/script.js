const API_BASE_URL =
  window.__BACKEND_URL__ ||
  window.location.origin;

const elements = {
  form: document.getElementById("product-form"),
  name: document.getElementById("product-name"),
  code: document.getElementById("product-code"),
  quantity: document.getElementById("product-quantity"),
  price: document.getElementById("product-price"),
  category: document.getElementById("product-category"),
  brand: document.getElementById("product-brand"),
  importRomaneioPrimary: document.getElementById("btn-importar"),
  applyCategory: document.getElementById("btn-aplicar-categoria"),
  applyBrand: document.getElementById("btn-aplicar-marca"),
  joinDuplicates: document.getElementById("btn-juntar"),
  clearList: document.getElementById("btn-limpar-lista"),
  productsBody: document.getElementById("products-body"),
  productsTotal: document.getElementById("products-total"),
  formatCodes: document.getElementById("btn-formatar-codigos"),
  toggleOrdering: document.getElementById("btn-toggle-ordenacao"),
  orderingStatus: document.getElementById("ordering-status"),
  createSets: document.getElementById("btn-criar-conjuntos"),
  totalsQuantity: document.getElementById("totals-quantity"),
  totalsCost: document.getElementById("totals-cost"),
  totalsSale: document.getElementById("totals-sale"),
  totalsGlobalQuantity: document.getElementById("totals-global-quantity"),
  totalsGlobalCost: document.getElementById("totals-global-cost"),
  totalsGlobalSale: document.getElementById("totals-global-sale"),
  totalsGlobalTime: document.getElementById("totals-global-time"),
  totalsGlobalChars: document.getElementById("totals-global-chars"),
  automationStart: document.getElementById("btn-automation-start"),
  automationComplete: document.getElementById("btn-automation-complete"),
  automationStop: document.getElementById("btn-automation-stop"),
  topInsertGrade: document.getElementById("btn-top-inserir-grade"),
  topStopGrades: document.getElementById("btn-top-parar-grades"),
  automationStatus: document.querySelector(".progress-summary .progress-count"),
  improveDescription: document.getElementById("btn-melhorar-descricao"),
  postProcessLlm: document.getElementById("btn-pos-processar-llm"),
  deleteItems: document.getElementById("btn-deletar-itens"),
  editNames: document.getElementById("btn-editar-nomes"),
  allowEdits: document.getElementById("btn-permitir-edicoes"),
  joinGrades: document.getElementById("btn-juntar-grades"),
  calibrate: document.getElementById("btn-calibrar"),
  toggleSimpleMode: document.getElementById("btn-toggle-simple-mode"),
  exportButton: document.getElementById("export-button"),
  descriptionInput: document.getElementById("description-input"),
  insertGrade: document.getElementById("btn-inserir-grade"),
  viewGrades: document.getElementById("btn-ver-grades"),
  clearGrades: document.getElementById("btn-limpar-grades"),
};

let importRomaneioInput = null;
let orderingMode = false;
let orderingSequence = [];
let pendingOrderingKeys = null;
let reorderInFlight = false;
let currentMarginPercentual = 6.0;
let activeCellEditor = null;
const EDITABLE_FIELDS = new Set(["nome", "quantidade", "preco_final"]);
const ALL_INLINE_FIELDS = new Set(["nome", "marca", "codigo", "quantidade", "preco", "preco_final", "categoria"]);
let globalEditMode = false;
let editNamesMode = false;
let simpleModeEnabled = false;
let romaneioStatusModal = null;
let romaneioStatusInterval = null;
let romaneioStatusJobId = null;
let latestImportedKeys = [];
let postProcessStatusModal = null;
let postProcessStatusInterval = null;
let postProcessStatusJobId = null;

const DEFAULT_CATEGORIES = ["Masculino", "Feminino", "Infantil", "Acessórios"];

const AUTOMATION_TARGET_FIELDS = [
  { key: "byte_empresa_posicao", label: "PosiÃ§Ã£o Byte Empresa" },
  { key: "campo_descricao", label: "Campo DescriÃ§Ã£o (Tela 1)" },
  { key: "tres_pontinhos", label: "BotÃ£o 3 pontinhos (Tela 2)" },
  { key: "cadastro_completo_passo_1", label: "Cadastro completo · clique 1" },
  { key: "cadastro_completo_passo_2", label: "Cadastro completo · clique 2" },
  { key: "cadastro_completo_passo_3", label: "Cadastro completo · clique 3" },
  { key: "cadastro_completo_passo_4", label: "Cadastro completo · clique 4" },
];
const AUTOMATION_PHASE_LABELS = {
  catalog: "cadastro",
  transition: "transiÃ§Ã£o",
  grades: "grades",
};
const AUTOMATION_JOB_LABELS = {
  catalog: "cadastro em massa",
  complete: "cadastro completo",
  grades: "inserÃ§Ã£o de grades",
};

const AUTOMATION_RUN_BUTTON_KEYS = ["automationStart", "automationComplete", "topInsertGrade", "insertGrade"];
const AUTOMATION_STOP_BUTTON_KEYS = ["automationStop"];
const GRADE_STOP_BUTTON_KEYS = ["topStopGrades"];

function setButtonsDisabled(keys, disabled) {
  keys.forEach((key) => {
    const element = elements[key];
    if (element) {
      element.disabled = disabled;
    }
  });
}

function setSimpleMode(enabled) {
  simpleModeEnabled = enabled;
  const form = elements.form;
  if (!form) {
    return;
  }

  form.classList.toggle("simple-mode", simpleModeEnabled);
  if (elements.toggleSimpleMode) {
    elements.toggleSimpleMode.classList.toggle("active-simple-mode", simpleModeEnabled);
    elements.toggleSimpleMode.textContent = simpleModeEnabled ? "Modo completo" : "Modo simplificado";
    elements.toggleSimpleMode.title = simpleModeEnabled ? "Voltar ao formulário completo" : "Ativar modo simplificado";
  }
  if (!simpleModeEnabled) {
    void fetchCategories();
  }
  updateDeleteButtonsVisibility();
}

function normalizePointValue(value) {
  if (!value) return null;
  if (Array.isArray(value) && value.length >= 2) {
    return { x: Number(value[0]), y: Number(value[1]) };
  }
  if (typeof value === 'object' && Number.isFinite(Number(value.x)) && Number.isFinite(Number(value.y))) {
    return { x: Number(value.x), y: Number(value.y) };
  }
  return null;
}

function formatCoordsLabel(point, fallback = 'Não calibrado') {
  if (!point) return fallback;
  return `X: ${point.x} | Y: ${point.y}`;
}

async function openGradeCalibrationDialog(existingConfig = {}, options = {}) {
  const { sizesSuggestion = '' } = options;
  const existingButtons = existingConfig.buttons || {};
  const existingGrid = existingConfig.grid || {};
  const existingModel = existingConfig.model || {};

  const state = {
    buttons: Object.fromEntries(
      Object.entries(existingButtons).map(([key, value]) => {
        const normalized = normalizePointValue(value);
        return normalized ? [key, normalized] : null;
      }).filter(Boolean)
    ),
    firstQuantCell: normalizePointValue(existingGrid.first_quant_cell),
    rowHeight: Number(existingGrid.row_height) || '',
    modelHotkey: existingModel.hotkey ? String(existingModel.hotkey) : '',
    modelIndex: Number.isFinite(Number(existingModel.index)) ? Number(existingModel.index) : 0,
    erpOrder: Array.isArray(existingConfig.erp_size_order)
      ? existingConfig.erp_size_order.join(',')
      : sizesSuggestion
  };

  const captureItems = [
    { key: 'focus_app', label: 'Ícone do Byte Empresa (focar aplicativo)', group: 'buttons', optional: false },
    { key: 'alterar_grade', label: "Botão 'Alterar/Definir Grade'", group: 'buttons', optional: false },
    { key: 'modelos', label: "Botão 'Modelos'", group: 'buttons', optional: false },
    { key: 'model_select', label: 'Linha do modelo desejado (clique na lista)', group: 'buttons', optional: false },
    { key: 'model_ok', label: "Botão OK na janela de modelos", group: 'buttons', optional: false },
    { key: 'confirm_sim', label: "Botão 'Sim' na confirmação de importação", group: 'buttons', optional: false },
    { key: 'close_after_import', label: 'Botão Fechar intermediário (se aparecer)', group: 'buttons', optional: true },
    { key: 'save_grade', label: "Botão 'Gravar/OK' final", group: 'buttons', optional: true },
    { key: 'close_grade', label: "Botão 'Fechar' após gravar", group: 'buttons', optional: true },
    { key: 'first_quant_cell', label: '1ª célula Quantidade', group: 'grid-first', optional: false }
  ];

  const dialog = createDialogElement(`
    <h3>Calibração PyAutoGUI - Grades</h3>
    <p class="modal-hint">Capture cada ponto clicando no botão correspondente.</p>
    <div id="grade-calibration-feedback" class="calibration-feedback"></div>
    <div class="calibration-section">
      ${captureItems
        .map((item) => {
          const badge = item.optional ? '<span class="badge optional">Opcional</span>' : '';
          return `
            <div class="calibration-target" data-key="${item.key}" data-group="${item.group}" data-optional="${item.optional ? 'true' : 'false'}">
              <div class="calibration-target-info">
                <strong>${item.label} ${badge}</strong>
                <div class="calibration-coords" data-key="${item.key}">--</div>
              </div>
              <button type="button" class="pill-button secondary" data-action="capture-grade" data-key="${item.key}" data-label="${item.label}">Capturar</button>
            </div>`;
        })
        .join('')}
    </div>
    <div class="calibration-section">
      <label class="modal-input">
        <span>Altura da linha (pixels) — calcula automático com as duas células:</span>
        <input type="number" id="grade-row-height" min="1" step="1" value="${state.rowHeight || ''}" />
      </label>
      <label class="modal-input">
        <span>Ordem do ByteEmpresa para execucao (separados por virgula)</span>
        <textarea id="grade-order-input" rows="3">${state.erpOrder || ''}</textarea>
      </label>
      <div class="two-columns">
        <label class="modal-input">
          <span>Atalho numérico do modelo (opcional)</span>
          <input type="text" id="grade-model-hotkey" value="${state.modelHotkey}" placeholder="Ex.: 4" />
        </label>
        <label class="modal-input">
          <span>Índice do modelo (0 = primeiro)</span>
          <input type="number" id="grade-model-index" min="0" step="1" value="${state.modelIndex}" />
        </label>
      </div>
    </div>
    <div class="modal-actions">
      <button type="button" class="pill-button secondary" data-action="cancel">Cancelar</button>
      <button type="button" class="pill-button primary" data-action="confirm">Salvar</button>
    </div>
  `);

  document.body.appendChild(dialog);

  const coordsEls = dialog.querySelectorAll('.calibration-coords');
  coordsEls.forEach((el) => {
    const key = el.dataset.key;
    if (!key) return;
    if (key === 'first_quant_cell') {
      el.textContent = formatCoordsLabel(state.firstQuantCell);
    } else {
      el.textContent = formatCoordsLabel(state.buttons[key]);
    }
  });

  const feedbackEl = dialog.querySelector('#grade-calibration-feedback');
  const rowHeightInput = dialog.querySelector('#grade-row-height');
  const orderInput = dialog.querySelector('#grade-order-input');
  const hotkeyInput = dialog.querySelector('#grade-model-hotkey');
  const indexInput = dialog.querySelector('#grade-model-index');

  const showFeedback = (msg, tone = 'info') => {
    if (!feedbackEl) return;
    feedbackEl.textContent = msg;
    feedbackEl.dataset.tone = tone;
  };

  const refreshCoords = (key) => {
    const el = dialog.querySelector(`.calibration-coords[data-key="${key}"]`);
    if (!el) return;
    if (key === 'first_quant_cell') {
      el.textContent = formatCoordsLabel(state.firstQuantCell);
    } else {
      el.textContent = formatCoordsLabel(state.buttons[key]);
    }
  };

  if (rowHeightInput) {
    rowHeightInput.addEventListener('input', () => {
      const val = Number(rowHeightInput.value);
      if (Number.isFinite(val) && val > 0) {
        state.rowHeight = val;
      } else {
        state.rowHeight = '';
      }
    });
  }

  let resolver;
  const resultPromise = new Promise((resolve) => {
    resolver = resolve;
  });

  const teardown = () => {
    dialog.remove();
    document.removeEventListener('keydown', escListener);
  };

  const escListener = (event) => {
    if (event.key === 'Escape') {
      teardown();
      resolver(null);
    }
  };

  document.addEventListener('keydown', escListener);

  const handleCapture = (item) => {
    if (!item) return;
    showFeedback(`Capturando ${item.label} em 3 segundos...`, 'info');
    startCaptureCountdown(`grade:${item.key}`, (result, error) => {
      if (error) {
        if (error.message === 'Captura cancelada') {
          showFeedback('Captura cancelada.', 'warning');
          return;
        }
        console.error('Erro na captura de coordenadas:', error);
        showFeedback(`Falha na captura: ${error.message || error}`, 'warning');
        return;
      }
      if (!result) {
        showFeedback('Captura cancelada.', 'warning');
        return;
      }
      if (item.group === 'grid-first') {
        state.firstQuantCell = result;
        refreshCoords('first_quant_cell');
      } else {
        state.buttons[item.key] = result;
        refreshCoords(item.key);
      }
      showFeedback(`Coordenadas registradas para ${item.label}.`, 'success');
    });
  };

  dialog.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    const action = button.dataset.action;
    if (action === 'cancel') {
      teardown();
      resolver(null);
      return;
    }
    if (action === 'capture-grade') {
      const key = button.dataset.key;
      const item = captureItems.find((it) => it.key === key);
      handleCapture(item);
      return;
    }
    if (action === 'confirm') {
      const missingButtons = captureItems.filter(
        (item) => item.group === 'buttons' && !item.optional && !state.buttons[item.key]
      );
      if (missingButtons.length) {
        showFeedback(`Calibre: ${missingButtons.map((i) => i.label).join(', ')}.`, 'warning');
        return;
      }
      if (!state.firstQuantCell) {
        showFeedback('Capture a primeira célula da coluna Quantidade.', 'warning');
        return;
      }
      if (!state.rowHeight || Number(state.rowHeight) <= 0) {
        showFeedback('Informe a altura da linha em pixels.', 'warning');
        return;
      }
      const orderValue = orderInput?.value?.trim();
      if (!orderValue) {
        showFeedback('Informe a ordem dos tamanhos.', 'warning');
        return;
      }
      const payload = {
        buttons: Object.fromEntries(Object.entries(state.buttons).filter(([, v]) => v)),
        firstQuantCell: state.firstQuantCell,
        rowHeight: Number(state.rowHeight) || undefined,
        erpSizeOrder: orderValue.split(',').map((s) => s.trim()).filter(Boolean),
        modelHotkey: hotkeyInput?.value?.trim() || '',
        modelIndex: Number(indexInput?.value || 0) || 0,
      };
      teardown();
      resolver(payload);
    }
  });

  return resultPromise;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function cloneSnapshotItems(items) {
  return JSON.parse(JSON.stringify(items || []));
}

function normalizeSnapshotItems(items) {
  return (items || []).map((item) => ({
    nome: item?.nome ?? "",
    codigo: item?.codigo ?? "",
    codigo_original: item?.codigo_original ?? null,
    quantidade: Number(item?.quantidade ?? 0) || 0,
    preco: item?.preco ?? "",
    categoria: item?.categoria ?? "",
    marca: item?.marca ?? "",
    preco_final: item?.preco_final ?? null,
    descricao_completa: item?.descricao_completa ?? null,
    grades: item?.grades ?? null,
    cores: item?.cores ?? null,
    timestamp: item?.timestamp,
  }));
}

function setCurrentProductsSnapshot(items) {
  currentProductsSnapshot = cloneSnapshotItems(items || []);
}

function pushUndoSnapshot(options = {}) {
  if (isRestoringSnapshot) {
    return;
  }
  const { clearRedo = true } = options;
  const snapshot = cloneSnapshotItems(currentProductsSnapshot);
  undoStack.push(snapshot);
  if (undoStack.length > MAX_HISTORY) {
    undoStack.shift();
  }
  if (clearRedo) {
    redoStack = [];
  }
}

async function applySnapshot(snapshot) {
  isRestoringSnapshot = true;
  try {
    await fetchJSON(`${API_BASE_URL}/actions/restore-snapshot`, {
      method: "POST",
      body: JSON.stringify({ items: normalizeSnapshotItems(snapshot || []) }),
    });
    await refreshProducts();
    await fetchTotals();
  } catch (err) {
    console.error("Erro ao restaurar snapshot:", err);
    window.alert(`Falha ao restaurar estado: ${err.message || err}`);
  } finally {
    isRestoringSnapshot = false;
  }
}

async function undoLastAction() {
  if (!undoStack.length) {
    return;
  }
  const snapshot = undoStack.pop();
  const current = cloneSnapshotItems(currentProductsSnapshot);
  redoStack.push(current);
  if (redoStack.length > MAX_HISTORY) {
    redoStack.shift();
  }
  await applySnapshot(snapshot);
}

async function redoLastAction() {
  if (!redoStack.length) {
    return;
  }
  const snapshot = redoStack.pop();
  const current = cloneSnapshotItems(currentProductsSnapshot);
  undoStack.push(current);
  if (undoStack.length > MAX_HISTORY) {
    undoStack.shift();
  }
  await applySnapshot(snapshot);
}

function shouldIgnoreUndoEvent(event) {
  const target = event?.target;
  if (!target) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

function handleUndoRedoKeydown(event) {
  if (!event) {
    return;
  }
  const key = String(event.key || "").toLowerCase();
  if (key !== "z") {
    return;
  }
  if (!(event.ctrlKey || event.metaKey)) {
    return;
  }
  if (shouldIgnoreUndoEvent(event)) {
    return;
  }
  event.preventDefault();
  if (event.shiftKey) {
    void redoLastAction();
  } else {
    void undoLastAction();
  }
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }

  return response.json().catch(() => ({}));
}

async function fetchCategories() {
  const select = elements.category;
  if (!select) {
    return DEFAULT_CATEGORIES;
  }

  const seen = new Set(
    Array.from(select.options || []).map((option) => option.value.trim().toLowerCase())
  );

  DEFAULT_CATEGORIES.forEach((category) => {
    const normalized = category.trim().toLowerCase();
    if (seen.has(normalized)) {
      return;
    }
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    select.appendChild(option);
  });

  return DEFAULT_CATEGORIES;
}

function toggleSimpleMode() {
  setSimpleMode(!simpleModeEnabled);
}

function _legacyToggleEditNamesMode(forceValue) {
  const nextValue = typeof forceValue === "boolean" ? forceValue : !editNamesMode;
  editNamesMode = nextValue;
  if (elements.editNames) {
    elements.editNames.textContent = editNamesMode ? "Finalizar Edição" : "Editar Nomes";
    elements.editNames.classList.toggle("active-edit-names", editNamesMode);
  }
  if (!editNamesMode) {
    finalizeActiveEditor(true);
  }
}

function setEditNamesMode(enabled) {
  editNamesMode = enabled;
  document.body.classList.toggle("edit-names-mode", editNamesMode);
  if (elements.editNames) {
    elements.editNames.classList.toggle("active-edit-nomes", editNamesMode);
    elements.editNames.textContent = editNamesMode ? "Finalizar Edição" : "Editar Nomes";
    elements.editNames.title = editNamesMode ? "Clique para encerrar a edição" : "Habilitar edição de nomes";
  }
  setOrderingStatus(editNamesMode ? "Modo edição de nomes ativo" : "");
  if (!editNamesMode) {
    finalizeActiveEditor(true);
  }
}

function toggleEditNamesMode(forceValue) {
  const nextValue = typeof forceValue === "boolean" ? forceValue : !editNamesMode;
  if (nextValue) {
    if (orderingMode) {
      setOrderingMode(false);
    }
    if (createSetsMode) {
      setCreateSetsMode(false);
    }
    if (deleteMode) {
      setDeleteMode(false);
    }
  }
  setEditNamesMode(nextValue);
}

let captureActive = false;
let captureCountdownTimer = null;
let captureCountdownRemaining = 0;
let captureTargetKey = null;
let automationPollTimer = null;
let automationState = "idle";
let automationJobKind = "";
let automationPhase = "";
let deleteMode = false;
let createSetsMode = false;
let createSetKeys = [];
let captureWindow = null;
let captureCallback = null;
const MAX_HISTORY = 10;
let undoStack = [];
let redoStack = [];
let currentProductsSnapshot = [];
let isRestoringSnapshot = false;
let orderingSnapshotTaken = false;

async function _legacyFetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }

  return response.json().catch(() => ({}));
}

function _legacyEscapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function startAutomationFlow(endpoint, optimisticStatus = {}) {
  const data = await fetchJSON(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  console.log("AutomaÃ§Ã£o disparada:", data);
  updateAutomationStatus({
    estado: "running",
    message: data?.message || optimisticStatus.message || "Em andamento",
    job_kind: data?.job_kind || optimisticStatus.job_kind || "",
    phase: optimisticStatus.phase || "",
  });
  if (!automationPollTimer) {
    automationPollTimer = window.setInterval(pollAutomationStatus, 1000);
  }
}

async function handleAutomationStart() {
  if (!elements.automationStart) {
    return;
  }
  elements.automationStart.disabled = true;
  try {
    const result = await fetchJSON(`${API_BASE_URL}/automation/execute`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    console.log("Automação disparada:", result);
    automationState = "running";
    updateAutomationStatus({ estado: "running", message: "Em andamento" });
    if (!automationPollTimer) {
      automationPollTimer = window.setInterval(pollAutomationStatus, 1000);
    }
  } catch (err) {
    window.alert(`Não foi possível iniciar automação: ${err.message || err}`);
  } finally {
    syncAutomationShortcutButtons();
  }
}

async function handleAutomationComplete() {
  if (!elements.automationComplete) {
    return;
  }
  elements.automationComplete.disabled = true;
  try {
    await startAutomationFlow("/automation/execute-complete", {
      job_kind: "complete",
      phase: "catalog",
      message: "Cadastro completo em andamento",
    });
  } catch (err) {
    window.alert(`NÃ£o foi possÃ­vel iniciar o cadastro completo: ${err.message || err}`);
  } finally {
    syncAutomationShortcutButtons();
  }
}

async function handleTopExecuteGrades() {
  if (!elements.topInsertGrade) {
    return;
  }
  elements.topInsertGrade.disabled = true;
  try {
    await startAutomationFlow("/automation/grades/execute-products", {
      job_kind: "grades",
      phase: "grades",
      message: "Execucao de grades em andamento",
    });
  } catch (err) {
    window.alert(`Nao foi possivel iniciar a execucao de grades: ${err.message || err}`);
  } finally {
    syncAutomationShortcutButtons();
  }
}

async function handleAutomationStop() {
  if (!elements.automationStop) {
    return;
  }
  elements.automationStop.disabled = true;
  try {
    const result = await fetchJSON(`${API_BASE_URL}/automation/cancel`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    console.log("Cancelamento solicitado:", result);
    automationState = "stopping";
    updateAutomationStatus({
      estado: "stopping",
      job_kind: automationJobKind,
      phase: automationPhase,
      message: "Cancelando...",
    });
  } catch (err) {
    window.alert(`Não foi possível cancelar: ${err.message || err}`);
  } finally {
    syncAutomationShortcutButtons();
  }
}

async function handleTopStopGrades() {
  if (!elements.topStopGrades) {
    return;
  }
  elements.topStopGrades.disabled = true;
  try {
    const result = await fetchJSON(`${API_BASE_URL}/automation/grades/stop`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    console.log("Parada de grades solicitada:", result);
    updateAutomationStatus({ estado: "stopping", job_kind: "grades", phase: "grades", message: "Parando grades..." });
  } catch (err) {
    window.alert(`Não foi possível parar as grades: ${err.message || err}`);
  } finally {
    syncAutomationShortcutButtons({ estado: "stopping", job_kind: "grades", phase: "grades" });
  }
}

function syncAutomationShortcutButtons(data = {}) {
  const estado = data.estado || automationState;
  const jobKind = data.job_kind || automationJobKind || "";
  const phase = data.phase || automationPhase || "";
  const anyRunning = estado === "running" || estado === "stopping";
  const gradesRunning = anyRunning && (jobKind === "grades" || phase === "grades");

  setButtonsDisabled(AUTOMATION_RUN_BUTTON_KEYS, anyRunning);
  setButtonsDisabled(AUTOMATION_STOP_BUTTON_KEYS, !anyRunning);
  setButtonsDisabled(GRADE_STOP_BUTTON_KEYS, !gradesRunning);
}

function updateAutomationStatus(data = {}) {
  if (!elements.automationStatus) {
    return;
  }
  const estado = data.estado || automationState;
  automationState = estado;
  automationJobKind = Object.prototype.hasOwnProperty.call(data, "job_kind")
    ? data.job_kind || ""
    : automationJobKind || "";
  automationPhase = Object.prototype.hasOwnProperty.call(data, "phase")
    ? data.phase || ""
    : automationPhase || "";
  const mensagem = data.message || data.detail || data.status || data.sucesso || "";
  const cancelRequested = data.cancel_requested === "True" ? " (cancelando)" : "";

  const linhas = [];
  linhas.push(`Estado: ${estado}${cancelRequested}`);
  if (automationJobKind) {
    const fluxoLabels = {
      catalog: "cadastro em massa",
      complete: "cadastro completo",
      grades: "insercao de grades",
    };
    const faseLabels = {
      catalog: "cadastro",
      transition: "transicao",
      grades: "grades",
    };
    const fluxo = fluxoLabels[automationJobKind] || AUTOMATION_JOB_LABELS[automationJobKind] || automationJobKind;
    const fase = automationPhase
      ? faseLabels[automationPhase] || AUTOMATION_PHASE_LABELS[automationPhase] || automationPhase
      : "";
    linhas.push(fase ? `Fluxo: ${fluxo} · ${fase}` : `Fluxo: ${fluxo}`);
  }
  if (mensagem) {
    linhas.push(mensagem);
  }
  if (data.sucesso) {
    linhas.push(`Sucesso: ${data.sucesso}`);
  }
  if (data.sucesso_catalogo) {
    linhas.push(`Cadastro: ${data.sucesso_catalogo}`);
  }
  if (data.sucesso_grades) {
    linhas.push(`Grades: ${data.sucesso_grades}`);
  }
  if (data.falhas) {
    linhas.push(`Falhas: ${data.falhas}`);
  }
  if (data.duration) {
    linhas.push(`Duração: ${data.duration}`);
  }
  if (data.tempo_economizado) {
    linhas.push(`Tempo manual evitado: ${formatDuration(data.tempo_economizado)}`);
  }
  if (data.caracteres_digitados) {
    const charsFormatted = Number(data.caracteres_digitados || 0).toLocaleString("pt-BR");
    linhas.push(`Caracteres digitados: ${charsFormatted}`);
  }
  elements.automationStatus.textContent = linhas.join(" | ") || "—";
  const resumo = [];
  resumo.push(`Estado: ${estado}${cancelRequested}`);
  if (automationJobKind && estado !== "idle") {
    const fluxoLabelsCompact = {
      catalog: "cadastro",
      complete: "completo",
      grades: "grades",
    };
    const faseLabelsCompact = {
      catalog: "cadastro",
      transition: "transicao",
      grades: "grades",
    };
    const fluxoCompact =
      fluxoLabelsCompact[automationJobKind] || AUTOMATION_JOB_LABELS[automationJobKind] || automationJobKind;
    const faseCompact = automationPhase
      ? faseLabelsCompact[automationPhase] || AUTOMATION_PHASE_LABELS[automationPhase] || automationPhase
      : "";
    resumo.push(faseCompact && faseCompact !== fluxoCompact ? `${fluxoCompact} · ${faseCompact}` : fluxoCompact);
  }
  if (resumo.length) {
    resumo[resumo.length - 1] = resumo[resumo.length - 1].replace("Â·", "-");
  }
  if (data.duration && estado === "running") {
    resumo.push(data.duration);
  }
  elements.automationStatus.textContent = resumo.join(" | ") || "—";
  elements.automationStatus.title = linhas.join(" | ") || "";
  syncAutomationShortcutButtons({ ...data, estado });
}

async function pollAutomationStatus() {
  try {
    const previousState = automationState;
    const data = await fetchJSON(`${API_BASE_URL}/automation/status`);
    updateAutomationStatus(data);
    if (automationState === "running" && !automationPollTimer) {
      automationPollTimer = window.setInterval(pollAutomationStatus, 1000);
    }
    if (automationState !== "running" && automationPollTimer) {
      window.clearInterval(automationPollTimer);
      automationPollTimer = null;
      automationJobKind = data?.job_kind || "";
      automationPhase = data?.phase || "";
    }
    if (previousState === "running" && automationState !== "running") {
      void fetchTotals();
    }
  } catch (err) {
    console.error("Erro ao consultar status de automação:", err);
    if (automationPollTimer) {
      window.clearInterval(automationPollTimer);
      automationPollTimer = null;
    }
    updateAutomationStatus({ estado: "erro", job_kind: "", phase: "", message: err.message || err });
  }
}

async function refreshProducts() {
  try {
    const data = await fetchJSON(`${API_BASE_URL}/products`);
    renderProducts(data.items || []);
  } catch (err) {
    console.error("Erro ao carregar produtos:", err);
  }
}

function resetForm() {
  elements.form.reset();
  elements.name.focus();
}

function formatTimestamp(timestamp) {
  if (!timestamp) return "--";
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch (err) {
    return "--";
  }
}

function renderProducts(items = []) {
  setCurrentProductsSnapshot(items);
  elements.productsBody.innerHTML = "";
  const existingKeys = new Set();
  items.forEach((item, index) => {
    const tr = document.createElement("tr");
    tr.dataset.orderingKey = item.ordering_key;
    existingKeys.add(item.ordering_key);
    const qtyValue = Number.isFinite(Number(item.quantidade)) ? Number(item.quantidade) : "";
    const saleValue = item.preco_final ? escapeHtml(item.preco_final) : "";
    tr.innerHTML = `
      <td>${index + 1}</td>
      <td data-field="nome" data-ordering-key="${item.ordering_key}">${escapeHtml(item.nome || "")}</td>
      <td data-field="marca" data-ordering-key="${item.ordering_key}">${escapeHtml(item.marca || "")}</td>
      <td data-field="codigo" data-ordering-key="${item.ordering_key}">${escapeHtml(item.codigo || "")}</td>
      <td data-field="quantidade" data-ordering-key="${item.ordering_key}">${qtyValue}</td>
      <td data-field="preco" data-ordering-key="${item.ordering_key}">${escapeHtml(item.preco || "")}</td>
      <td data-field="preco_final" data-ordering-key="${item.ordering_key}">${saleValue}</td>
      <td data-field="categoria" data-ordering-key="${item.ordering_key}">${escapeHtml(item.categoria || "")}</td>
    `;

    const actionsTd = document.createElement("td");
    actionsTd.className = "actions-cell";
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "icon-button delete-row-btn";
    deleteBtn.title = "Remover item";
    deleteBtn.dataset.orderingKey = item.ordering_key;
    deleteBtn.textContent = "🗑️";
    deleteBtn.addEventListener("click", handleDeleteButtonClick);
    actionsTd.appendChild(deleteBtn);
    tr.appendChild(actionsTd);
    elements.productsBody.appendChild(tr);
  });

  orderingSequence = orderingSequence.filter((key) => existingKeys.has(key));

  elements.productsTotal.textContent = `Total de produtos: ${items.length}`;
  updateOrderingBadges();
  updateDeleteButtonsVisibility();
  updateCreateSetHighlights();
}

function createDialogElement(content) {
  const wrapper = document.createElement("div");
  wrapper.className = "modal-backdrop";
  wrapper.innerHTML = `
    <div class="modal">
      <div class="modal-body">
        ${content}
      </div>
      <div class="modal-actions">
        <button type="button" class="pill-button secondary" data-action="cancel">Cancelar</button>
        <button type="button" class="pill-button accent" data-action="confirm">Aplicar</button>
      </div>
    </div>
  `;
  return wrapper;
}

async function fetchSizesCatalog() {
  try {
    const data = await fetchJSON(`${API_BASE_URL}/catalog/sizes`);
    const sizes = Array.isArray(data?.sizes) ? data.sizes.map((s) => String(s).trim()).filter(Boolean) : [];
    return sizes;
  } catch (err) {
    console.error("Erro ao carregar catálogo de tamanhos:", err);
    return [];
  }
}

async function openInsertGradesDialog() {
  // Modal com lista de produtos à esquerda e editor à direita
  const wrapper = document.createElement("div");
  wrapper.className = "modal-backdrop";
  wrapper.innerHTML = `
    <div class="modal grades-modal">
      <div class="modal-body">
        <h3>Inserir Grade</h3>
        <div class="grades-layout">
          <div class="grades-products" id="grades-products">
            <p class="modal-hint">Carregando produtos...</p>
          </div>
          <div class="grades-editor" id="grades-editor">
            <p class="modal-hint">Carregando tamanhos...</p>
          </div>
          <div class="grades-actions" id="grades-actions">
            <div class="actions-inner">
              <div class="actions-title">Automação</div>
              <div class="actions-buttons">
                <button type="button" class="pill-button secondary" data-action="calibrate-grades">Calibrar Grades</button>
                <button type="button" class="pill-button secondary" data-action="manage-grade-sizes">Tamanhos</button>
                <button type="button" class="pill-button secondary" data-action="clear-grades">Limpar Grades</button>
                <button type="button" class="pill-button accent" data-action="execute-grades">Executar Grades</button>
                <button type="button" class="pill-button danger" data-action="stop-grades" disabled>Parar</button>
              </div>
            </div>
            <p class="modal-hint" id="grades-status-text"></p>
          </div>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" class="pill-button secondary" data-action="cancel">Fechar</button>
        <button type="button" class="pill-button secondary" data-action="export-grade">Exportar grade</button>
        <button type="button" class="pill-button accent" data-action="save" disabled>Salvar</button>
        <button type="button" class="pill-button accent" data-action="save-next" disabled>Salvar & Próximo</button>
      </div>
    </div>
  `;
  document.body.appendChild(wrapper);

  const listEl = wrapper.querySelector('#grades-products');
  const editorEl = wrapper.querySelector('#grades-editor');
  const saveBtn = wrapper.querySelector('[data-action="save"]');
  const saveNextBtn = wrapper.querySelector('[data-action="save-next"]');
  let selected = null;
  let selectedIndex = -1;
  let products = [];
  let sizes = [];
  let gradeConfig = {};
  let saveTimer = null;
  let wheelHandler = null;
  let gradeExecutionPollTimer = null;

  function normalizeSizeLabel(v) {
    return String(v || "").trim().toLowerCase();
  }

  function getConfiguredSizeOrder() {
    return normalizeGradeSizeList(gradeConfig?.erp_size_order || []);
  }

  function getVisualSizeOrder() {
    const visualOrder = normalizeGradeSizeList(gradeConfig?.ui_size_order || []);
    return visualOrder.length ? visualOrder : getConfiguredSizeOrder();
  }

  const SMART_PATTERNS = {
    PMG: { seq: ['P','M','G'], weights: [3,5,4] },
    PMG_GG: { seq: ['P','M','G','GG'], weights: [2,4,4,2] },
    JEANS_32_42: { seq: ['32','34','36','38','40','42'], weights: [1,2,3,3,2,1] },
    JEANS_34_44: { seq: ['34','36','38','40','42','44'], weights: [1,2,3,3,2,1] },
    JEANS_36_46: { seq: ['36','38','40','42','44','46'], weights: [1,2,3,3,2,1] },
  };

  function applySmartFill(patternId) {
    if (!selected || !editorEl) return;
    const total = Number(selected.quantidade || 0);
    if (!Number.isFinite(total) || total <= 0) {
      window.alert('Quantidade do produto é 0.');
      return;
    }

    const inputs = Array.from(editorEl.querySelectorAll('input[data-size]'));
    if (!inputs.length) return;

    const byNorm = new Map();
    inputs.forEach((inp) => byNorm.set(normalizeSizeLabel(inp.dataset.size), inp));

    let seqNorm = [];
    let weights = [];
    if (patternId === 'UNIFORME') {
      seqNorm = inputs.map((inp) => normalizeSizeLabel(inp.dataset.size));
      weights = new Array(seqNorm.length).fill(1);
    } else {
      const def = SMART_PATTERNS[patternId];
      if (!def) return;
      const desired = def.seq.map(normalizeSizeLabel);
      // Mantém somente tamanhos presentes na tela
      seqNorm = desired.filter((s) => byNorm.has(s));
      weights = def.weights.filter((_, i) => byNorm.has(desired[i]));
      // Se nenhum tamanho do padrão existir na grade, cai no uniforme em todos os tamanhos visíveis
      if (!seqNorm.length) {
        seqNorm = inputs.map((inp) => normalizeSizeLabel(inp.dataset.size));
        weights = new Array(seqNorm.length).fill(1);
      }
    }

    if (!seqNorm.length) return;

    const sumW = weights.reduce((a, b) => a + (Number(b) || 0), 0) || 1;
    const base = weights.map((w) => Math.floor((Number(w) || 0) * total / sumW));
    let leftover = total - base.reduce((a, b) => a + b, 0);
    // distribui o restante começando nos maiores pesos
    const order = weights
      .map((w, i) => ({ i, w: Number(w) || 0 }))
      .sort((a, b) => b.w - a.w || a.i - b.i)
      .map((o) => o.i);
    for (let k = 0; k < leftover; k++) {
      const idx = order[k % order.length];
      base[idx] += 1;
    }

    // zera tudo antes de aplicar, para não somar com valores anteriores
    inputs.forEach((inp) => {
      inp.value = '0';
    });

    // aplica nos inputs e garante soma exata
    seqNorm.forEach((norm, idx) => {
      const input = byNorm.get(norm);
      if (!input) return;
      input.value = String(base[idx] || 0);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });

    computeSumAndDiff(selected.quantidade, inputs);
    scheduleSaveCurrent(150);

    // foco no primeiro tamanho com valor > 0
    const firstNonZero = seqNorm
      .map((norm) => byNorm.get(norm))
      .find((inp) => inp && Number(inp.value) > 0);
    (firstNonZero || inputs[0])?.focus();
  }

  function getNextIndexPreferUnsaved(fromIndex) {
    if (!Array.isArray(products) || !products.length) return -1;
    const n = products.length;
    for (let i = 1; i <= n; i++) {
      const idx = (fromIndex + i) % n;
      const p = products[idx];
      const unsaved = !Array.isArray(p?.grades) || p.grades.length === 0;
      if (unsaved) return idx;
    }
    return (fromIndex + 1) % n;
  }

  function selectProductByIndex(index) {
    if (index < 0 || index >= products.length) return;
    if (saveTimer) { window.clearTimeout(saveTimer); saveTimer = null; }
    selectedIndex = index;
    selected = products[index];
    renderProductsList(selected.ordering_key);
    const active = listEl.querySelector('.product-item.active');
    active?.scrollIntoView({ block: 'nearest' });
    renderEditor(selected);
  }

  async function saveCurrentGrades() {
    if (!selected) return;
    const inputs = Array.from(editorEl.querySelectorAll('input[data-size]'));
    const grades = inputs
      .map((inp) => ({ tamanho: String(inp.dataset.size), quantidade: Number(inp.value) || 0 }))
      .filter((g) => g.quantidade > 0);
    await fetchJSON(`${API_BASE_URL}/products/${encodeURIComponent(selected.ordering_key)}`, {
      method: 'PATCH',
      body: JSON.stringify({ grades }),
    });
    selected.grades = grades;
    // Update local data immediately for real-time UI
    const productIndex = loadedProducts.findIndex(p => p.ordering_key === selected.ordering_key);
    if (productIndex !== -1) {
      loadedProducts[productIndex].grades = grades;
      renderProducts();
      await fetchTotals();
    }
  }

  async function clearAllGrades() {
    const loadedProducts = Array.isArray(products) ? products.filter((product) => product?.ordering_key) : [];
    if (!loadedProducts.length) {
      return 0;
    }

    if (saveTimer) {
      window.clearTimeout(saveTimer);
      saveTimer = null;
    }

    await Promise.all(
      loadedProducts.map((product) =>
        fetchJSON(`${API_BASE_URL}/products/${encodeURIComponent(product.ordering_key)}`, {
          method: 'PATCH',
          body: JSON.stringify({ grades: [] }),
        })
      )
    );

    loadedProducts.forEach((product) => {
      product.grades = [];
    });

    if (selected) {
      const inputs = Array.from(editorEl.querySelectorAll('input[data-size]'));
      inputs.forEach((inp) => {
        inp.value = '';
      });
      computeSumAndDiff(selected.quantidade, inputs);
      renderProductsList(selected.ordering_key);
    }

    await refreshProducts();
    await fetchTotals();
    return loadedProducts.length;
  }

  async function saveAndNext() {
    try {
      await saveCurrentGrades();
      const nextIndex = getNextIndexPreferUnsaved(selectedIndex);
      selectProductByIndex(nextIndex);
    } catch (err) {
      console.error('Erro ao salvar grade:', err);
      window.alert(`Falha ao salvar grade: ${err.message || err}`);
    }
  }

  function scheduleSaveCurrent(delay = 350) {
    if (!selected) return;
    if (saveTimer) {
      window.clearTimeout(saveTimer);
      saveTimer = null;
    }
    saveTimer = window.setTimeout(() => {
      void saveCurrentGrades().catch((err) => console.error('Autosave falhou:', err));
    }, delay);
  }

  function attachSizeInputInteractions(inputs, product) {
    inputs.forEach((inp, idx) => {
      // Navegação de teclado
      inp.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const isLast = idx === inputs.length - 1;
          if (!isLast) {
            // Vai para o próximo tamanho
            const next = inputs[idx + 1];
            next.focus();
            next.select?.();
            next.scrollIntoView({ block: 'nearest' });
            scheduleSaveCurrent(0);
          } else {
            // Último tamanho: salvar e ir para próximo produto
            void saveAndNext();
          }
          return;
        }
        if (e.key === 'Tab') {
          // TAB = Salvar & Próximo (Shift+Tab volta um tamanho)
          e.preventDefault();
          if (e.shiftKey) {
            const prev = inputs[Math.max(0, idx - 1)];
            if (prev) {
              scheduleSaveCurrent(0);
              prev.focus();
              prev.select?.();
              prev.scrollIntoView({ block: 'nearest' });
            }
            return;
          }
          if (saveTimer) { window.clearTimeout(saveTimer); saveTimer = null; }
          void saveAndNext();
          return;
        }
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          const next = inputs[Math.min(inputs.length - 1, idx + 1)];
          if (next) {
            scheduleSaveCurrent(0);
            next.focus();
            next.select?.();
            next.scrollIntoView({ block: 'nearest' });
          }
          return;
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault();
          const prev = inputs[Math.max(0, idx - 1)];
          if (prev) {
            scheduleSaveCurrent(0);
            prev.focus();
            prev.select?.();
            prev.scrollIntoView({ block: 'nearest' });
          }
          return;
        }
      });

      // Salva ao perder foco e ao digitar (debounced)
      inp.addEventListener('blur', () => scheduleSaveCurrent(100));
      inp.addEventListener('input', () => scheduleSaveCurrent(350));
    });
  }

  function renderEditor(product) {
    if (!editorEl) return;
    const editorSizes = buildGradeSizeCatalog([product], sizes, getVisualSizeOrder());
    const gradesMap = new Map();
    if (Array.isArray(product.grades)) {
      product.grades.forEach((g) => {
        if (g && typeof g.tamanho !== 'undefined') {
          gradesMap.set(normalizeGradeSizeLabel(g.tamanho), Number(g.quantidade) || 0);
        }
      });
    }
    const cells = editorSizes
      .map((size) => {
        const val = gradesMap.get(normalizeGradeSizeLabel(size)) ?? '';
        return `
          <div class="size-cell">
            <label>${escapeHtml(size)}</label>
            <input type="number" min="0" step="1" inputmode="numeric" data-size="${escapeHtml(size)}" value="${val}">
          </div>
        `;
      })
      .join('');

    editorEl.innerHTML = `
      <div class="grades-header">
        <div class="grades-title"><strong>${escapeHtml(product.nome || '')}</strong> <span class="muted">${escapeHtml(product.codigo || '')}</span></div>
        <div class="grades-summary">
          <span>Qtd produto: <strong>${product.quantidade ?? 0}</strong></span>
          <span>Somatório da grade: <strong id="grades-sum">0</strong></span>
          <span>Diferença: <strong id="grades-diff">0</strong></span>
        </div>
      </div>
      <div class="smart-fill">
        <div class="smart-fill-actions" style="display:flex;flex-wrap:wrap;gap:6px;align-items:center">
          <span class="muted" style="font-size:0.85rem">Preenchimento inteligente:</span>
          <button type="button" class="pill-button secondary" data-smart="PMG">PMG</button>
          <button type="button" class="pill-button secondary" data-smart="PMG_GG">PMG + GG</button>
          <button type="button" class="pill-button secondary" data-smart="JEANS_32_42">Jeans 32–42</button>
          <button type="button" class="pill-button secondary" data-smart="JEANS_34_44">Jeans 34–44</button>
          <button type="button" class="pill-button secondary" data-smart="JEANS_36_46">Jeans 36–46</button>
          <button type="button" class="pill-button accent" data-smart="UNIFORME">Uniforme</button>
        </div>
      </div>
      <p class="modal-hint">Ordem atual: ${escapeHtml(editorSizes.join(" • "))}</p>
      <div class="sizes-grid">${cells}</div>
      <p class="modal-hint">Dica: deixe em branco ou zero para tamanhos que não existem.</p>
    `;

    const sizesGridEl = editorEl.querySelector('.sizes-grid');
    if (sizesGridEl) {
      sizesGridEl.style.display = 'grid';
      sizesGridEl.style.gridTemplateColumns = '1fr';
    }

    const inputs = Array.from(editorEl.querySelectorAll('input[data-size]'));
    inputs.forEach((inp) => {
      inp.addEventListener('input', () => {
        computeSumAndDiff(product.quantidade, inputs);
        scheduleSaveCurrent(350);
      });
      inp.addEventListener('blur', () => scheduleSaveCurrent(100));
    });
    attachSizeInputInteractions(inputs, product);
    // Handler global de scroll baseado no campo focado
    if (wheelHandler) {
      wrapper.removeEventListener('wheel', wheelHandler);
      wheelHandler = null;
    }
    wheelHandler = (e) => {
      const active = document.activeElement;
      if (!active || !active.matches?.('input[data-size]')) return; // só intercepta se estiver num campo da grade
      e.preventDefault();
      const all = Array.from(editorEl.querySelectorAll('input[data-size]'));
      const idx = all.indexOf(active);
      if (idx < 0) return;
      const goingDown = e.deltaY > 0;
      const nextIdx = goingDown ? Math.min(all.length - 1, idx + 1) : Math.max(0, idx - 1);
      const next = all[nextIdx];
      if (next && next !== active) {
        scheduleSaveCurrent(200);
        next.focus();
        next.select?.();
        next.scrollIntoView({ block: 'nearest' });
      }
    };
    wrapper.addEventListener('wheel', wheelHandler, { passive: false });
    computeSumAndDiff(product.quantidade, inputs);

    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.dataset.key = product.ordering_key;
    }
    if (saveNextBtn) {
      saveNextBtn.disabled = false;
      saveNextBtn.dataset.key = product.ordering_key;
    }

    // Foco inicial no primeiro campo vazio/zero para agilizar a digitação
    const firstEmpty = inputs.find((el) => !el.value || Number(el.value) === 0) || inputs[0];
    firstEmpty?.focus();
    firstEmpty?.select?.();
  }

  function renderProductsList(selectedKey = null) {
    if (!listEl) return;
    listEl.innerHTML = '';
    products.forEach((p) => {
      const hasGrades = Array.isArray(p.grades) && p.grades.length > 0;
      const item = document.createElement('div');
      item.className = 'product-item' + (selectedKey === p.ordering_key ? ' active' : '');
      const title = escapeHtml(p.nome || 'Produto');
      const code = escapeHtml(p.codigo || '');
      const marca = escapeHtml(p.marca || '');
      const chip = hasGrades ? '<span class="chip">✓</span>' : '';
      item.innerHTML = `
        <div class="product-item-main">
          <div class="product-item-title">${title}</div>
          <div class="product-item-meta">${code}${marca ? ' · ' + marca : ''}</div>
        </div>
        <div class="product-item-side">${chip}</div>
      `;
      item.dataset.key = p.ordering_key;
      item.tabIndex = 0;
      listEl.appendChild(item);
    });
  }

  function computeSumAndDiff(qty, inputs) {
    const sum = inputs.reduce((acc, input) => acc + (Number(input.value) || 0), 0);
    const diff = (Number(qty) || 0) - sum;
    const sumEl = editorEl?.querySelector('#grades-sum');
    const diffEl = editorEl?.querySelector('#grades-diff');
    if (sumEl) sumEl.textContent = String(sum);
    if (diffEl) diffEl.textContent = String(diff);
  }

  function scheduleSaveCurrent(delay = 350) {
    if (!selected) return;
    if (saveTimer) {
      window.clearTimeout(saveTimer);
      saveTimer = null;
    }
    saveTimer = window.setTimeout(() => {
      void saveCurrentGrades().catch((err) => console.error('Autosave falhou:', err));
    }, delay);
  }

  const updateAutomationUI = (running, message = "") => {
    automationRunning = running;
    const execBtn = wrapper.querySelector('button[data-action="execute-grades"]');
    const stopBtn = wrapper.querySelector('button[data-action="stop-grades"]');
    const statusEl = wrapper.querySelector('#grades-status-text');
    if (execBtn) {
      execBtn.disabled = running;
    }
    if (stopBtn) {
      stopBtn.disabled = !running;
    }
    if (statusEl) {
      statusEl.textContent = message;
    }
  };

  const stopGradeExecutionPolling = () => {
    if (gradeExecutionPollTimer) {
      window.clearInterval(gradeExecutionPollTimer);
      gradeExecutionPollTimer = null;
    }
  };

  const pollGradeExecutionStatus = async () => {
    try {
      const data = await fetchJSON(`${API_BASE_URL}/automation/status`);
      const isRunningGrades = data?.estado === 'running' && data?.job_kind === 'grades';
      if (isRunningGrades) {
        automationState = 'running';
        updateAutomationStatus(data);
        updateAutomationUI(true, data?.message || 'Execução em andamento... Verifique o ERP.');
        return;
      }

      stopGradeExecutionPolling();
      if (data?.job_kind === 'grades' || automationRunning) {
        updateAutomationStatus(data || {});
        updateAutomationUI(false, data?.message || '');
        if (data?.status === 'success') {
          await refreshProducts();
          await fetchTotals();
        }
      } else {
        updateAutomationUI(false, '');
      }
    } catch (err) {
      console.error('Erro ao consultar execução de grades:', err);
      stopGradeExecutionPolling();
      updateAutomationUI(false, '');
    }
  };

  wrapper.addEventListener('click', async (event) => {
    const target = event.target;
    if (target.dataset?.action === 'cancel' || target === wrapper) {
      if (saveTimer) {
        window.clearTimeout(saveTimer);
        saveTimer = null;
      }
      stopGradeExecutionPolling();
      if (wheelHandler) wrapper.removeEventListener('wheel', wheelHandler);
      document.removeEventListener('keydown', escListener);
      wrapper.remove();
      return;
    }

    const item = target.closest?.('.product-item');
    if (item && listEl.contains(item)) {
      const key = item.dataset.key;
      const idx = products.findIndex((p) => p.ordering_key === key);
      if (idx >= 0) {
        selectProductByIndex(idx);
      }
      return;
    }

    if (target.dataset?.action === 'save') {
      if (!selected) {
        window.alert('Selecione um produto primeiro.');
        return;
      }
      try {
        await saveCurrentGrades();
        window.alert('Grade salva com sucesso.');
      } catch (err) {
        console.error('Erro ao salvar grade:', err);
        window.alert(`Falha ao salvar grade: ${err.message || err}`);
      }
      return;
    }
    if (target.dataset?.action === 'save-next') {
      if (!selected) {
        window.alert('Selecione um produto primeiro.');
        return;
      }
      await saveAndNext();
      return;
    }
    if (target.dataset?.action === 'export-grade') {
      try {
        const inputs = Array.from(editorEl.querySelectorAll('input[data-size]'));
        const map = {};
        inputs.forEach((inp) => {
          const k = String(inp.dataset.size);
          const v = Number(inp.value) || 0;
          map[k] = v;
        });
        const json = JSON.stringify(map, null, 2);
        const a = document.createElement('a');
        const blob = new Blob([json], { type: 'application/json' });
        a.href = URL.createObjectURL(blob);
        const code = selected?.codigo || 'produto';
        const ts = new Date().toISOString().replace(/[:.]/g, '-');
        a.download = `grade-${code}-${ts}.json`;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(a.href);
        a.remove();
      } catch (e) {
        console.error('Falha ao exportar grade', e);
        window.alert('Falha ao exportar grade.');
      }
      return;
    }
    if (target.dataset?.action === 'calibrate-grades') {
      if (target.disabled) {
        return;
      }
      target.disabled = true;
      try {
        const sizesSuggestion = Array.from(editorEl.querySelectorAll('input[data-size]'))
          .map((i) => String(i.dataset.size))
          .join(',');
        const existingConfig = await fetchGradeConfig();
        const dialogResult = await openGradeCalibrationDialog(existingConfig, { sizesSuggestion });
        if (!dialogResult) {
          return;
        }

        const payload = buildGradeConfigPayload(dialogResult);
        await saveGradeConfig(payload);
        window.alert('Calibração salva.');
      } catch (e) {
        console.error('Calibração falhou', e);
        window.alert(`Falha ao calibrar: ${e?.message || e}`);
      } finally {
        target.disabled = false;
      }
      return;
    }
    if (target.dataset?.action === 'manage-grade-sizes') {
      if (target.disabled) {
        return;
      }
      target.disabled = true;
      try {
        const currentCatalog = buildGradeSizeCatalog(products, sizes, getVisualSizeOrder());
        const updatedOrder = await openGradeOrderDialog(currentCatalog);
        if (!updatedOrder) {
          return;
        }
        const nextErpOrder = mergeNewSizesIntoErpOrder(getConfiguredSizeOrder(), updatedOrder);
        gradeConfig = await saveGradeConfig({
          ui_size_order: updatedOrder,
          erp_size_order: nextErpOrder,
        });
        sizes = buildGradeSizeCatalog(products, sizes, getVisualSizeOrder());
        if (selected) {
          renderEditor(selected);
        }
        window.alert('Ordem visual atualizada. A ordem antiga do ByteEmpresa foi mantida, com novos tamanhos adicionados no final.');
      } catch (e) {
        console.error('Falha ao atualizar tamanhos', e);
        window.alert(`Falha ao salvar tamanhos: ${e?.message || e}`);
      } finally {
        target.disabled = false;
      }
      return;
    }
    if (target.dataset?.action === 'clear-grades') {
      const totalProducts = Array.isArray(products) ? products.length : 0;
      if (!totalProducts) {
        window.alert('Nenhum produto carregado para limpar.');
        return;
      }
      const confirmed = window.confirm(`Limpar as grades de todos os ${totalProducts} produtos carregados? Essa ação zera os preenchimentos atuais.`);
      if (!confirmed) {
        return;
      }
      target.disabled = true;
      try {
        const clearedCount = await clearAllGrades();
        window.alert(`Grades limpas com sucesso em ${clearedCount} produto(s).`);
      } catch (e) {
        console.error('Falha ao limpar grade', e);
        window.alert(`Falha ao limpar grade: ${e?.message || e}`);
      } finally {
        target.disabled = false;
      }
      return;
    }
    if (target.dataset?.action === 'stop-grades') {
      if (!automationRunning) {
        return;
      }
      try {
        updateAutomationUI(true, 'Enviando pedido de parada...');
        const res = await fetch(`${API_BASE_URL}/automation/grades/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (!res.ok) throw new Error(await res.text());
        updateAutomationUI(true, 'Parada solicitada. Aguarde o GradeBot finalizar o item atual.');
      } catch (e) {
        console.error('Falha ao parar grades', e);
        window.alert(`Falha ao enviar parada: ${e?.message || e}`);
      }
      return;
    }
    if (target.dataset?.action === 'execute-grades') {
      try {
        const inputs = Array.from(editorEl.querySelectorAll('input[data-size]'));
        if (!inputs.length) {
          window.alert('Nenhum tamanho carregado.');
          return;
        }

        const buildMapFromInputs = () => {
          const map = {};
          inputs.forEach((inp) => {
            const k = String(inp.dataset.size);
            const v = Number(inp.value) || 0;
            if (v > 0) {
              map[k] = v;
            }
          });
          return Object.keys(map).length ? map : null;
        };

        const mapFromProduct = (product) => {
          if (!product || !Array.isArray(product.grades) || !product.grades.length) {
            return null;
          }
          const map = {};
          product.grades.forEach((item) => {
            const size = String(item?.tamanho || '').trim();
            const qty = Number(item?.quantidade) || 0;
            if (size && qty > 0) {
              map[size] = qty;
            }
          });
          return Object.keys(map).length ? map : null;
        };

        const selectedKey = selected?.ordering_key;
        const tasks = [];
        const currentMap = buildMapFromInputs();
        if (selectedKey && currentMap) {
          tasks.push({ key: selectedKey, grades: currentMap });
        }

        products.forEach((product) => {
          const map = mapFromProduct(product);
          if (!map) return;
          if (product.ordering_key === selectedKey) {
            if (!currentMap) {
              tasks.push({ key: product.ordering_key, grades: map });
            }
            return;
          }
          tasks.push({ key: product.ordering_key, grades: map });
        });

        if (!tasks.length) {
          window.alert('Nenhum produto possui grade com quantidades > 0.');
          return;
        }

        const endpoint = tasks.length > 1 ? `${API_BASE_URL}/automation/grades/batch` : `${API_BASE_URL}/automation/grades/run`;
        const payload = tasks.length > 1
          ? { tasks: tasks.map(({ grades }) => ({ grades })) }
          : { grades: tasks[0].grades };

        updateAutomationUI(true, tasks.length > 1 ? `Executando ${tasks.length} produtos...` : 'Executando grade...');
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        automationState = 'running';
        updateAutomationStatus({
          estado: 'running',
          message: tasks.length > 1 ? `Inserção de grades em lote iniciada (${tasks.length} produtos)` : 'Inserção de grade iniciada'
        });
        updateAutomationUI(true, 'Execução em andamento... Verifique o ERP.');
        if (!automationPollTimer) {
          automationPollTimer = window.setInterval(pollAutomationStatus, 1000);
        }
        stopGradeExecutionPolling();
        void pollGradeExecutionStatus();
        gradeExecutionPollTimer = window.setInterval(() => {
          void pollGradeExecutionStatus();
        }, 1000);
        window.alert(tasks.length > 1 ? `Execução de grades disparada para ${tasks.length} produtos. Acompanhe no ERP.` : 'Execução de grades iniciada. Verifique o ERP.');
      } catch (e) {
        console.error('Falha ao executar grades', e);
        window.alert(`Falha ao executar grades: ${e?.message || e}`);
        updateAutomationUI(false, '');
      }
      return;
    }
    if (target.dataset?.smart) {
      if (!selected) {
        window.alert('Selecione um produto primeiro.');
        return;
      }
      applySmartFill(String(target.dataset.smart));
      return;
    }
  });

  const escListener = (ev) => {
    if (ev.key === 'Escape') {
      if (saveTimer) {
        window.clearTimeout(saveTimer);
        saveTimer = null;
      }
      if (wheelHandler) wrapper.removeEventListener('wheel', wheelHandler);
      wrapper.remove();
      document.removeEventListener('keydown', escListener);
    }
  };
  document.addEventListener('keydown', escListener);

  // Busca assíncrona de dados
  try {
    const [productsPayload, sizesData, gradeConfigData] = await Promise.all([
      fetchJSON(`${API_BASE_URL}/products`).catch(() => ({ items: [] })),
      fetchSizesCatalog(),
      fetchGradeConfig(),
    ]);
    products = Array.isArray(productsPayload?.items) ? productsPayload.items : [];
    gradeConfig = gradeConfigData || {};
    sizes = buildGradeSizeCatalog(products, Array.isArray(sizesData) ? sizesData : [], getVisualSizeOrder());
    renderProductsList();

    // Seleciona automaticamente o primeiro produto sem grade (ou o primeiro)
    const firstUnsavedIdx = products.findIndex((p) => !Array.isArray(p?.grades) || p.grades.length === 0);
    selectProductByIndex(firstUnsavedIdx >= 0 ? firstUnsavedIdx : 0);
  } catch (err) {
    console.error('Falha ao carregar dados da grade:', err);
    if (listEl) listEl.innerHTML = '<p class="modal-hint">Erro ao carregar produtos.</p>';
    if (editorEl) editorEl.innerHTML = '<p class="modal-hint">Erro ao carregar tamanhos.</p>';
  }
}

function openMarginDialog(percentualAtual) {
  const dialog = createDialogElement(`
    <h3>Configurar Margem de Venda</h3>
    <label class="modal-input">
      <span>Margem desejada (%):</span>
      <input type="number" id="opt-margin-percentual" min="0.01" step="0.01" value="${percentualAtual.toFixed(2)}" />
    </label>
    <p class="modal-hint">A margem será salva como padrão e aplicada a todos os produtos.</p>
  `);

  document.body.appendChild(dialog);

  return new Promise((resolve) => {
    const cleanup = () => {
      dialog.remove();
      document.removeEventListener("keydown", escListener);
    };

    const escListener = (event) => {
      if (event.key === "Escape") {
        cleanup();
        resolve(null);
      }
    };

    dialog.addEventListener("click", (event) => {
      const target = event.target;
      if (target.dataset?.action === "cancel") {
        cleanup();
        resolve(null);
      }
      if (target.dataset?.action === "confirm") {
        const valor = dialog.querySelector("#opt-margin-percentual").value;
        const percentual = Number(valor);
        if (!Number.isFinite(percentual) || percentual <= 0) {
          window.alert("Informe um percentual de margem válido.");
          return;
        }
        cleanup();
        resolve(percentual);
      }
      if (target === dialog) {
        cleanup();
        resolve(null);
      }
    });

    document.addEventListener("keydown", escListener);
  });
}

function updateMarginBadge() {
  const badge = document.getElementById("margin-current-value");
  if (badge) {
    badge.textContent = `${currentMarginPercentual.toFixed(2)}%`;
  }
}

async function fetchMarginSettings() {
  try {
    const data = await fetchJSON(`${API_BASE_URL}/settings/margin`);
    if (data && typeof data.percentual === "number") {
      currentMarginPercentual = data.percentual;
      updateMarginBadge();
    }
  } catch (err) {
    console.error("Erro ao carregar margem:", err);
  }
}

async function handleOpenMargin() {
  const percentual = await openMarginDialog(currentMarginPercentual);
  if (percentual == null) {
    return;
  }

  try {
    pushUndoSnapshot();
    const payload = { percentual };
    const response = await fetchJSON(`${API_BASE_URL}/settings/margin`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (response && typeof response.percentual === "number") {
      currentMarginPercentual = response.percentual;
      updateMarginBadge();
    }

    const applyResponse = await fetchJSON(`${API_BASE_URL}/actions/apply-margin`, {
      method: "POST",
      body: JSON.stringify({ percentual: currentMarginPercentual }),
    });

    await refreshProducts();
    await fetchTotals();

    const atualizado = applyResponse?.total_atualizados ?? 0;
    const pct = applyResponse?.percentual_utilizado ?? currentMarginPercentual;
    window.alert(`Margem aplicada com sucesso.\nPercentual: ${pct.toFixed(2)}%\nProdutos atualizados: ${atualizado}`);
  } catch (err) {
    console.error("Erro ao atualizar margem:", err);
    window.alert(`Falha ao atualizar margem: ${err.message || err}`);
  }
}

function openBrandDialog() {
  const dialog = createDialogElement(`
    <h3>Cadastrar Nova Marca</h3>
    <label class="modal-input">
      <span>Nome da marca</span>
      <input type="text" id="opt-brand-nome" placeholder="Ex.: Nova Marca" />
    </label>
  `);

  document.body.appendChild(dialog);

  return new Promise((resolve) => {
    const cleanup = () => {
      dialog.remove();
      document.removeEventListener("keydown", escListener);
    };

    const escListener = (event) => {
      if (event.key === "Escape") {
        cleanup();
        resolve(null);
      }
    };

    dialog.addEventListener("click", (event) => {
      const target = event.target;
      if (target.dataset?.action === "cancel") {
        cleanup();
        resolve(null);
      }
      if (target.dataset?.action === "confirm") {
        const nome = dialog.querySelector("#opt-brand-nome").value.trim();
        if (!nome) {
          window.alert("Informe um nome de marca válido.");
          return;
        }
        cleanup();
        resolve(nome);
      }
      if (target === dialog) {
        cleanup();
        resolve(null);
      }
    });

    document.addEventListener("keydown", escListener);
  });
}

function renderBrandOptions(marcas = []) {
  const select = elements.brand;
  if (!select) {
    return;
  }
  const atual = select.value;
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Selecionar...";
  select.appendChild(placeholder);
  marcas.forEach((marca) => {
    const option = document.createElement("option");
    option.value = marca;
    option.textContent = marca;
    select.appendChild(option);
  });
  if (marcas.includes(atual)) {
    select.value = atual;
  } else {
    select.value = "";
  }
}

async function fetchBrands() {
  try {
    const data = await fetchJSON(`${API_BASE_URL}/brands`);
    if (Array.isArray(data?.marcas)) {
      renderBrandOptions(data.marcas);
    }
  } catch (err) {
    console.error("Erro ao carregar marcas:", err);
  }
}

async function handleNewBrand() {
  const nome = await openBrandDialog();
  if (!nome) {
    return;
  }

  try {
    const data = await fetchJSON(`${API_BASE_URL}/brands`, {
      method: "POST",
      body: JSON.stringify({ nome }),
    });
    if (Array.isArray(data?.marcas)) {
      renderBrandOptions(data.marcas);
      elements.brand.value = nome;
      window.alert(`Marca "${nome}" cadastrada com sucesso.`);
    }
  } catch (err) {
    console.error("Erro ao criar nova marca:", err);
    window.alert(`Falha ao criar nova marca: ${err.message || err}`);
  }
}

function formatCurrency(value) {
  try {
    return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  } catch (err) {
    return `R$ ${Number(value || 0).toFixed(2)}`;
  }
}

function formatDuration(seconds) {
  const value = Number(seconds || 0);
  if (!Number.isFinite(value) || value <= 0) {
    return "0s";
  }
  const totalSeconds = Math.floor(value);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  const parts = [];
  if (hours) {
    parts.push(`${hours}h`);
  }
  if (minutes) {
    parts.push(`${minutes}min`);
  }
  if (secs || !parts.length) {
    parts.push(`${secs}s`);
  }
  return parts.join(" ");
}

function updateTotalsDisplay(totals) {
  if (!totals) {
    return;
  }

  const atual = totals.atual || {};
  const historico = totals.historico || {};

  if (elements.totalsQuantity) {
    elements.totalsQuantity.textContent = atual.quantidade ?? 0;
  }
  if (elements.totalsCost) {
    elements.totalsCost.textContent = formatCurrency(atual.custo ?? 0);
  }
  if (elements.totalsSale) {
    elements.totalsSale.textContent = formatCurrency(atual.venda ?? 0);
  }

  if (elements.totalsGlobalQuantity) {
    elements.totalsGlobalQuantity.textContent = historico.quantidade ?? 0;
  }
  if (elements.totalsGlobalCost) {
    elements.totalsGlobalCost.textContent = formatCurrency(historico.custo ?? 0);
  }
  if (elements.totalsGlobalSale) {
    elements.totalsGlobalSale.textContent = formatCurrency(historico.venda ?? 0);
  }
  if (elements.totalsGlobalTime) {
    const tempo = totals.tempo_economizado ?? historico.tempo_economizado ?? 0;
    elements.totalsGlobalTime.textContent = formatDuration(tempo);
  }
  if (elements.totalsGlobalChars) {
    const caracteres = totals.caracteres_digitados ?? historico.caracteres_digitados ?? 0;
    elements.totalsGlobalChars.textContent = caracteres.toLocaleString("pt-BR");
  }
}

async function fetchTotals() {
  try {
    const data = await fetchJSON(`${API_BASE_URL}/totals`);
    updateTotalsDisplay(data);
  } catch (err) {
    console.error("Erro ao carregar totais:", err);
  }
}

function openFormatDialog() {
  const dialog = createDialogElement(`
    <h3>Formatação de Códigos</h3>
    <p class="modal-hint">Combine as opções abaixo para padronizar os códigos sem afetar dados originais.</p>
    <div class="format-options">
      <div class="format-option-block">
        <label class="format-option-toggle">
          <input type="checkbox" id="opt-remover-prefixo" />
          <div class="format-option-text">
            <span class="format-option-title">Remover prefixo repetido</span>
            <span class="format-option-description">
              Remove automaticamente o prefixo numérico de 5 dígitos quando houver padrão forte na lista.
            </span>
          </div>
        </label>
      </div>
      <div class="format-option-block">
        <label class="format-option-toggle">
          <input type="checkbox" id="opt-remover-zeros" />
          <div class="format-option-text">
            <span class="format-option-title">Remover zeros à esquerda</span>
            <span class="format-option-description">Limpa zeros extras no início dos códigos.</span>
          </div>
        </label>
      </div>
      <div class="format-option-block format-option-with-extra">
        <label class="format-option-toggle">
          <input type="checkbox" id="opt-remover-ultimos" />
          <div class="format-option-text">
            <span class="format-option-title">Remover últimos N números</span>
            <span class="format-option-description">
              Exclui os últimos dígitos numéricos de cada código, ideal para retirar sufixos de grade.
            </span>
          </div>
        </label>
        <div class="format-option-extra">
          <input type="number" id="opt-remover-ultimos-valor" min="1" max="50" placeholder="Quantidade" disabled />
          <span class="modal-input-hint">Informe quantos dígitos finais devem ser removidos.</span>
        </div>
      </div>
      <div class="format-option-block format-option-with-extra">
        <label class="format-option-toggle">
          <input type="checkbox" id="opt-remover-primeiros" />
          <div class="format-option-text">
            <span class="format-option-title">Remover primeiros N números</span>
            <span class="format-option-description">
              Descarte dígitos numéricos iniciais mantendo o restante do código intacto.
            </span>
          </div>
        </label>
        <div class="format-option-extra">
          <input type="number" id="opt-remover-primeiros-valor" min="1" max="50" placeholder="Quantidade" disabled />
          <span class="modal-input-hint">Defina quantos dígitos iniciais serão removidos.</span>
        </div>
      </div>
    </div>
    <div class="modal-input-group modal-input-grid">
      <label class="modal-input" for="opt-ultimos">
        <span class="modal-input-title">Manter apenas últimos N dígitos</span>
        <input type="number" id="opt-ultimos" min="1" placeholder="Opcional" />
        <span class="modal-input-hint">Ex.: digite 8 para preservar apenas os 8 últimos dígitos de cada código.</span>
      </label>
      <label class="modal-input" for="opt-primeiros">
        <span class="modal-input-title">Manter apenas primeiros N dígitos</span>
        <input type="number" id="opt-primeiros" min="1" placeholder="Opcional" />
        <span class="modal-input-hint">Use quando desejar truncar códigos longos mantendo o início.</span>
      </label>
    </div>
  `);

  document.body.appendChild(dialog);

  const modalElement = dialog.querySelector(".modal");
  modalElement?.classList.add("format-codes-modal");

  const actions = dialog.querySelector(".modal-actions");
  if (actions) {
    const cancelButton = actions.querySelector('[data-action="cancel"]');
    const confirmButton = actions.querySelector('[data-action="confirm"]');
    if (confirmButton) {
      confirmButton.textContent = "Aplicar formatação";
    }

    const restoreButton = document.createElement("button");
    restoreButton.type = "button";
    restoreButton.className = "pill-button secondary modal-restore-btn";
    restoreButton.dataset.action = "restore";
    restoreButton.textContent = "Restaurar códigos originais";

    if (confirmButton) {
      actions.insertBefore(restoreButton, confirmButton);
    } else if (cancelButton) {
      cancelButton.insertAdjacentElement("afterend", restoreButton);
    } else {
      actions.appendChild(restoreButton);
    }
  }

  const optionInputs = [
    { checkbox: "#opt-remover-ultimos", input: "#opt-remover-ultimos-valor" },
    { checkbox: "#opt-remover-primeiros", input: "#opt-remover-primeiros-valor" },
  ];

  optionInputs.forEach(({ checkbox, input }) => {
    const checkboxEl = dialog.querySelector(checkbox);
    const inputEl = dialog.querySelector(input);
    if (!checkboxEl || !inputEl) {
      return;
    }
    const toggle = () => {
      const enabled = checkboxEl.checked;
      inputEl.disabled = !enabled;
      inputEl.classList.toggle("modal-input-disabled", !enabled);
    };
    toggle();
    checkboxEl.addEventListener("change", toggle);
  });

  return new Promise((resolve) => {
    const cleanup = () => {
      dialog.remove();
      document.removeEventListener("keydown", escListener);
    };

    const escListener = (event) => {
      if (event.key === "Escape") {
        cleanup();
        resolve(null);
      }
    };

    dialog.addEventListener("click", (event) => {
      const target = event.target;
      if (target.dataset?.action === "cancel") {
        cleanup();
        resolve(null);
      }
      if (target.dataset?.action === "confirm") {
        const removerPrefixo = dialog.querySelector("#opt-remover-prefixo").checked;
        const removerZeros = dialog.querySelector("#opt-remover-zeros").checked;
        const removerUltimos = dialog.querySelector("#opt-remover-ultimos").checked;
        const removerPrimeiros = dialog.querySelector("#opt-remover-primeiros").checked;
        const removerUltimosValor = dialog.querySelector("#opt-remover-ultimos-valor")?.value;
        const removerPrimeirosValor = dialog.querySelector("#opt-remover-primeiros-valor")?.value;
        const ultimosValor = dialog.querySelector("#opt-ultimos").value;
        const primeirosValor = dialog.querySelector("#opt-primeiros").value;
        const removerUltimosNumeros = removerUltimosValor ? parseInt(removerUltimosValor, 10) : null;
        const removerPrimeirosNumeros = removerPrimeirosValor ? parseInt(removerPrimeirosValor, 10) : null;
        const ultimosDigitos = ultimosValor ? parseInt(ultimosValor, 10) : null;
        const primeirosDigitos = primeirosValor ? parseInt(primeirosValor, 10) : null;
        if (removerUltimos && (!Number.isFinite(removerUltimosNumeros) || removerUltimosNumeros <= 0)) {
          window.alert("Informe a quantidade de dígitos a remover no final do código.");
          return;
        }
        if (removerPrimeiros && (!Number.isFinite(removerPrimeirosNumeros) || removerPrimeirosNumeros <= 0)) {
          window.alert("Informe a quantidade de dígitos a remover no início do código.");
          return;
        }
        const hasOptions =
          removerPrefixo ||
          removerZeros ||
          removerUltimos ||
          removerPrimeiros ||
          (Number.isFinite(ultimosDigitos) && ultimosDigitos > 0) ||
          (Number.isFinite(primeirosDigitos) && primeirosDigitos > 0);
        if (!hasOptions) {
          window.alert("Selecione pelo menos uma opção de formatação antes de aplicar.");
          return;
        }
        cleanup();
        resolve({
          remover_prefixo5: removerPrefixo,
          remover_zeros_a_esquerda: removerZeros,
          remover_ultimos_numeros:
            removerUltimos && Number.isFinite(removerUltimosNumeros) && removerUltimosNumeros > 0
              ? removerUltimosNumeros
              : null,
          remover_primeiros_numeros:
            removerPrimeiros &&
            Number.isFinite(removerPrimeirosNumeros) &&
            removerPrimeirosNumeros > 0
              ? removerPrimeirosNumeros
              : null,
          ultimos_digitos:
            Number.isFinite(ultimosDigitos) && ultimosDigitos > 0 ? ultimosDigitos : null,
          primeiros_digitos:
            Number.isFinite(primeirosDigitos) && primeirosDigitos > 0 ? primeirosDigitos : null,
        });
      }
      if (target.dataset?.action === "restore") {
        cleanup();
        resolve({ restoreOriginal: true });
      }
      if (target === dialog) {
        cleanup();
        resolve(null);
      }
    });

    document.addEventListener("keydown", escListener);
  });
}

async function handleFormatCodes() {
  const options = await openFormatDialog();
  if (!options) {
    return;
  }

  try {
    pushUndoSnapshot();
    if (options.restoreOriginal) {
      const result = await fetchJSON(`${API_BASE_URL}/actions/restore-original-codes`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refreshProducts();
      const detalhes = [`Total analisado: ${result.total}`, `Códigos restaurados: ${result.restaurados}`];
      window.alert(detalhes.join("\n"));
      return;
    }

    const payload = {
      remover_prefixo5: Boolean(options.remover_prefixo5),
      remover_zeros_a_esquerda: Boolean(options.remover_zeros_a_esquerda),
      remover_ultimos_numeros: options.remover_ultimos_numeros ?? null,
      remover_primeiros_numeros: options.remover_primeiros_numeros ?? null,
      ultimos_digitos: options.ultimos_digitos ?? null,
      primeiros_digitos: options.primeiros_digitos ?? null,
    };

    const result = await fetchJSON(`${API_BASE_URL}/actions/format-codes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await refreshProducts();
    const detalhes = [`Total analisado: ${result.total}`, `Alterados: ${result.alterados}`];
    if (result.prefixo) {
      detalhes.push(`Prefixo removido: ${result.prefixo}`);
    }
    window.alert(detalhes.join("\n"));
  } catch (err) {
    console.error("Erro ao formatar códigos:", err);
    window.alert(`Falha ao formatar códigos: ${err.message || err}`);
  }
}

function openImproveDescriptionDialog() {
  const dialog = createDialogElement(`
    <h3>Melhorar Descrições</h3>
    <p class="modal-hint">Selecione os elementos que deseja remover das descrições atuais.</p>
    <label class="modal-checkbox">
      <input type="checkbox" id="opt-remover-numeros" checked /> Remover números
    </label>
    <label class="modal-checkbox">
      <input type="checkbox" id="opt-remover-especiais" checked /> Remover caracteres especiais
    </label>
    <div class="modal-input-group">
      <label class="modal-input" for="opt-remover-termos">
        <span class="modal-input-title">Remover termos específicos</span>
        <textarea id="opt-remover-termos" rows="3" placeholder="Digite termos separados por vírgula ou quebra de linha"></textarea>
        <span class="modal-input-hint">Ex.: Tam, Tam Cor, B. Letras isoladas são removidas apenas quando aparecem sozinhas.</span>
      </label>
    </div>
  `);

  document.body.appendChild(dialog);

  return new Promise((resolve) => {
    const cleanup = () => {
      dialog.remove();
      document.removeEventListener("keydown", escListener);
    };

    const escListener = (event) => {
      if (event.key === "Escape") {
        cleanup();
        resolve(null);
      }
    };

    dialog.addEventListener("click", (event) => {
      const target = event.target;
      if (target.dataset?.action === "cancel") {
        cleanup();
        resolve(null);
      }
      if (target.dataset?.action === "confirm") {
        const removeNumbers = dialog.querySelector("#opt-remover-numeros").checked;
        const removeSpecial = dialog.querySelector("#opt-remover-especiais").checked;
        const rawTerms = dialog.querySelector("#opt-remover-termos")?.value ?? "";
        const customTerms = Array.from(
          new Set(
            rawTerms
              .split(/[\n,]/)
              .map((term) => term.trim())
              .filter(Boolean)
          )
        );
        const hasOptions = removeNumbers || removeSpecial || customTerms.length > 0;
        if (!hasOptions) {
          window.alert("Selecione uma opção ou informe termos para remover.");
          return;
        }
        cleanup();
        resolve({
          remover_numeros: removeNumbers,
          remover_especiais: removeSpecial,
          remover_termos: customTerms,
        });
      }
      if (target === dialog) {
        cleanup();
        resolve(null);
      }
    });

    document.addEventListener("keydown", escListener);
  });
}

async function handleImproveDescription() {
  const options = await openImproveDescriptionDialog();
  if (!options) {
    return;
  }

  try {
    pushUndoSnapshot();
    const result = await fetchJSON(`${API_BASE_URL}/actions/improve-descriptions`, {
      method: "POST",
      body: JSON.stringify({
        remover_numeros: Boolean(options.remover_numeros),
        remover_especiais: Boolean(options.remover_especiais),
        remover_termos: Array.isArray(options.remover_termos) ? options.remover_termos : [],
      }),
    });
    await refreshProducts();
    await fetchTotals();
    window.alert(
      [`Descrições analisadas: ${result.total}`, `Descrições modificadas: ${result.modificados}`].join("\n")
    );
  } catch (err) {
    console.error("Erro ao melhorar descrições:", err);
    window.alert(`Falha ao melhorar descrições: ${err.message || err}`);
  }
}

function setOrderingStatus(message) {
  if (elements.orderingStatus) {
    elements.orderingStatus.textContent = message || "";
  }
}

function updateCreateSetsUI() {
  if (!elements.createSets) return;
  const ready = createSetKeys.length === 2;
  elements.createSets.classList.toggle("active-create-sets", createSetsMode);
  if (!createSetsMode) {
    elements.createSets.textContent = "Criar Conjuntos";
    elements.createSets.title = "Ativar modo de criação de conjuntos";
    if (!orderingMode && !editNamesMode) {
      setOrderingStatus("");
    }
    return;
  }
  elements.createSets.textContent = ready ? "Confirmar Conjunto" : "Cancelar Conjunto";
  elements.createSets.title = ready
    ? "Clique para criar o conjunto com os 2 itens selecionados"
    : "Clique para sair do modo conjunto";
  setOrderingStatus(`Conjunto: ${createSetKeys.length}/2 selecionados`);
}

function updateCreateSetHighlights() {
  const rows = elements.productsBody?.querySelectorAll("tr") || [];
  rows.forEach((row) => {
    const key = row.dataset.orderingKey;
    row.classList.toggle("set-selected", createSetKeys.includes(key));
  });
}

function setCreateSetsMode(enabled) {
  createSetsMode = !!enabled;
  createSetKeys = createSetsMode ? [] : [];
  document.body.classList.toggle("create-sets-mode", createSetsMode);
  updateCreateSetsUI();
  updateCreateSetHighlights();
}

async function confirmCreateSet() {
  if (createSetKeys.length !== 2) {
    return;
  }
  const [keyA, keyB] = createSetKeys;
  try {
    pushUndoSnapshot();
    await fetchJSON(`${API_BASE_URL}/actions/create-set`, {
      method: "POST",
      body: JSON.stringify({ key_a: keyA, key_b: keyB }),
    });
    await refreshProducts();
    await fetchTotals();
    setCreateSetsMode(false);
  } catch (err) {
    console.error("Erro ao criar conjunto:", err);
    window.alert(`Falha ao criar conjunto: ${err.message || err}`);
  }
}

function toggleCreateSetSelection(key) {
  if (!key) return;
  if (createSetKeys.includes(key)) {
    createSetKeys = createSetKeys.filter((entry) => entry !== key);
  } else if (createSetKeys.length < 2) {
    createSetKeys = [...createSetKeys, key];
  }
  updateCreateSetsUI();
  updateCreateSetHighlights();
}

function setOrderingMode(enabled) {
  orderingMode = enabled;
  orderingSequence = enabled ? [] : [];
  pendingOrderingKeys = null;
  orderingSnapshotTaken = false;
  document.body.classList.toggle("ordering-mode", orderingMode);
  if (orderingMode) {
    setCreateSetsMode(false);
  }
  if (elements.toggleOrdering) {
    elements.toggleOrdering.classList.toggle("active-ordering", orderingMode);
    elements.toggleOrdering.textContent = orderingMode ? "Finalizar Ordenação" : "Ordenar Lista";
    elements.toggleOrdering.title = orderingMode ? "Clique para encerrar a ordenação" : "Ativar ordenação";
  }
  setOrderingStatus(orderingMode ? "Posições definidas: 0" : "");
  updateOrderingBadges();
}

function updateOrderingBadges() {
  const rows = elements.productsBody?.querySelectorAll("tr") || [];
  rows.forEach((row, index) => {
    const orderPosition = index + 1;
    row.dataset.orderIndex = String(orderPosition);
    const firstCell = row.querySelector("td");
    if (firstCell) {
      firstCell.textContent = orderPosition;
    }
    const key = row.dataset.orderingKey;
    const isPinned = orderingSequence.includes(key);
    row.classList.toggle("ordering-picked", isPinned);
  });
}

function handleRowClick(event) {
  if (event.target.closest(".delete-row-btn")) {
    return;
  }
  if (event.target.closest(".inline-editor")) {
    return;
  }
  const row = event.target.closest("tr");
  if (createSetsMode) {
    if (row && row.dataset.orderingKey) {
      toggleCreateSetSelection(row.dataset.orderingKey);
    }
    return;
  }
  const cell = event.target.closest("td[data-field]");
  if (cell) {
    if (!deleteMode) {
      const field = cell.dataset.field;
      let canEdit = false;
      if (globalEditMode) {
        canEdit = ALL_INLINE_FIELDS.has(field ?? "");
      } else {
        canEdit = field === "nome" ? editNamesMode : EDITABLE_FIELDS.has(field ?? "");
      }
      if (canEdit) {
        beginInlineEdit(cell);
      }
    }
    return;
  }
  if (!orderingMode) {
    return;
  }
  if (!row || !row.dataset.orderingKey) {
    return;
  }

  const key = row.dataset.orderingKey;
  if (orderingSequence.includes(key)) {
    return;
  }

  if (!orderingSnapshotTaken) {
    pushUndoSnapshot();
    orderingSnapshotTaken = true;
  }

  orderingSequence.push(key);
  moveRowToPosition(row, orderingSequence.length - 1);
  setOrderingStatus(`Posições definidas: ${orderingSequence.length}`);
  updateOrderingBadges();
  persistOrderingSequence();
}

function moveRowToPosition(row, targetIndex) {
  const body = elements.productsBody;
  if (!body) {
    return;
  }

  const currentRows = Array.from(body.children);
  const clampedIndex = Math.max(0, Math.min(targetIndex, currentRows.length));
  if (!currentRows.includes(row)) {
    return;
  }

  body.removeChild(row);
  const referenceNode = body.children[clampedIndex] ?? null;
  body.insertBefore(row, referenceNode);
}

function persistOrderingSequence() {
  if (!orderingSequence.length) {
    pendingOrderingKeys = null;
    return;
  }
  pendingOrderingKeys = [...orderingSequence];
  if (!reorderInFlight) {
    void sendOrderingRequest();
  }
}

function handleToggleOrdering() {
  if (!orderingMode) {
    setOrderingMode(true);
  } else {
    setOrderingMode(false);
  }
}

function handleCreateSetsClick() {
  if (!createSetsMode) {
    setOrderingMode(false);
    if (editNamesMode) {
      setEditNamesMode(false);
    }
    if (deleteMode) {
      setDeleteMode(false);
    }
    if (globalEditMode) {
      setGlobalEditMode(false);
    }
    setCreateSetsMode(true);
    return;
  }
  if (createSetKeys.length === 2) {
    void confirmCreateSet();
    return;
  }
  setCreateSetsMode(false);
}

function setDeleteMode(enabled) {
  if (enabled) {
    setOrderingMode(false);
    setCreateSetsMode(false);
    if (editNamesMode) {
      toggleEditNamesMode(false);
    }
  }
  deleteMode = enabled;
  if (elements.deleteItems) {
    elements.deleteItems.textContent = enabled ? "Cancelar Exclusão" : "Deletar Itens";
    elements.deleteItems.classList.toggle("active-delete", enabled);
  }
  document.body.classList.toggle("delete-mode", enabled);
  updateDeleteButtonsVisibility();
}

function handleDeleteItemsClick() {
  setDeleteMode(!deleteMode);
}

function updateDeleteButtonsVisibility() {
  const buttons = document.querySelectorAll(".delete-row-btn");
  buttons.forEach((button) => {
    button.hidden = !deleteMode;
  });
}

function beginInlineEdit(cell) {
  if (!cell || !cell.dataset.field) {
    return;
  }
  const field = cell.dataset.field;
  if (!ALL_INLINE_FIELDS.has(field)) {
    return;
  }
  const orderingKey = cell.dataset.orderingKey || cell.closest("tr")?.dataset.orderingKey;
  if (!orderingKey) {
    return;
  }

  if (activeCellEditor?.cell === cell && activeCellEditor.input?.isConnected) {
    activeCellEditor.input.focus();
    return;
  }

  finalizeActiveEditor(true);

  const originalValue = cell.textContent || "";
  const input = document.createElement("input");
  if (field === "quantidade") {
    input.type = "number";
    input.min = "0";
    input.step = "1";
  } else if (field === "preco_final" || field === "preco") {
    input.type = "text";
    input.inputMode = "decimal";
    input.placeholder = "Ex.: 99,90";
  } else {
    input.type = "text";
  }
  input.value = originalValue;
  input.className = "inline-editor";
  input.dataset.field = field;
  input.dataset.orderingKey = orderingKey;
  input.addEventListener("keydown", handleEditorKeydown);
  input.addEventListener("blur", () => {
    if (!activeCellEditor || activeCellEditor.input !== input) {
      return;
    }
    finalizeActiveEditor(false, true);
  });
  cell.classList.add("editing");
  cell.textContent = "";
  cell.appendChild(input);
  input.focus();
  const caretPosition = input.value.length;
  if (typeof input.setSelectionRange === "function" && input.type !== "number") {
    input.setSelectionRange(caretPosition, caretPosition);
  }
  activeCellEditor = { cell, input, originalValue, field, orderingKey };
}

function handleEditorKeydown(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    event.stopPropagation();
    finalizeActiveEditor(false, true);
  } else if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    finalizeActiveEditor(true);
  }
}

function finalizeActiveEditor(cancel = false, submit = false) {
  if (!activeCellEditor) {
    return;
  }
  const { cell, input, originalValue, field, orderingKey } = activeCellEditor;
  activeCellEditor = null;
  const newValue = input.value;
  cell.classList.remove("editing");
  cell.textContent = cancel ? originalValue : newValue;

  if (submit && !cancel && field && orderingKey) {
    const trimmed = newValue.trim();
    if (trimmed === originalValue.trim()) {
      cell.textContent = originalValue;
      return;
    }
    void submitInlineUpdate(orderingKey, field, trimmed).catch((err) => {
      console.error("Erro ao atualizar produto:", err);
      window.alert(`Falha ao atualizar produto: ${err.message || err}`);
      void refreshProducts();
    });
  }
}

async function submitInlineUpdate(orderingKey, field, value) {
  let payload = null;
  if (field === "nome") {
    payload = { nome: String(value ?? "").trim() };
  } else if (field === "quantidade") {
    const qty = Number.parseInt(value, 10);
    if (!Number.isFinite(qty) || qty < 0) {
      window.alert("Informe uma quantidade válida (>= 0).");
      return;
    }
    payload = { quantidade: qty };
  } else if (field === "preco_final") {
    const trimmed = String(value ?? "").trim();
    if (!trimmed) {
      payload = { preco_final: null };
    } else {
      payload = { preco_final: trimmed };
    }
  } else if (field === "preco") {
    const trimmed = String(value ?? "").trim();
    payload = { preco: trimmed };
  } else if (field === "marca") {
    payload = { marca: String(value ?? "").trim() };
  } else if (field === "categoria") {
    payload = { categoria: String(value ?? "").trim() };
  } else if (field === "codigo") {
    const trimmed = String(value ?? "").trim();
    payload = { codigo: trimmed };
  }
  if (!payload) {
    return;
  }

  pushUndoSnapshot();

  const response = await fetchJSON(`${API_BASE_URL}/products/${encodeURIComponent(orderingKey)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (response && response.item) {
    await Promise.all([refreshProducts(), fetchTotals()]);
  }
}

function setGlobalEditMode(enabled) {
  globalEditMode = !!enabled;
  document.body.classList.toggle("global-edit-mode", globalEditMode);
  if (elements.allowEdits) {
    elements.allowEdits.textContent = globalEditMode ? "Finalizar Edições" : "Permitir Edições";
    elements.allowEdits.classList.toggle("active-edit", globalEditMode);
  }
  if (globalEditMode) {
    setOrderingMode(false);
    setCreateSetsMode(false);
    setDeleteMode(false);
    if (typeof setEditNamesMode === "function") {
      setEditNamesMode(false);
    }
    setOrderingStatus("Modo edição global ativo");
  } else {
    setOrderingStatus("");
    finalizeActiveEditor(true);
  }
}

function toggleGlobalEditMode(forceValue) {
  const nextValue = typeof forceValue === "boolean" ? forceValue : !globalEditMode;
  setGlobalEditMode(nextValue);
}

async function handleDeleteButtonClick(event) {
  event.stopPropagation();
  const button = event.currentTarget;
  const key = button.dataset.orderingKey;
  if (!key) {
    return;
  }

  try {
    pushUndoSnapshot();
    await fetchJSON(`${API_BASE_URL}/products/${encodeURIComponent(key)}`, {
      method: "DELETE",
    });
    await refreshProducts();
    await fetchTotals();
  } catch (err) {
    console.error("Erro ao remover produto:", err);
    window.alert(`Falha ao remover produto: ${err.message || err}`);
  }
}

async function sendOrderingRequest() {
  if (!pendingOrderingKeys || !pendingOrderingKeys.length) {
    reorderInFlight = false;
    return;
  }
  reorderInFlight = true;
  const payloadKeys = pendingOrderingKeys;
  pendingOrderingKeys = null;
  try {
    await fetchJSON(`${API_BASE_URL}/actions/reorder`, {
      method: "POST",
      body: JSON.stringify({ keys: payloadKeys }),
    });
  } catch (err) {
    console.error("Erro ao reordenar produtos:", err);
    window.alert(`Falha ao reordenar produtos: ${err.message || err}`);
    orderingSequence = [];
    await refreshProducts();
    setOrderingMode(false);
  } finally {
    reorderInFlight = false;
    if (pendingOrderingKeys) {
      void sendOrderingRequest();
    }
  }
}

function isElementVisible(element) {
  if (!element) {
    return false;
  }
  return element.offsetParent !== null && !element.disabled;
}

function focusProductField(element) {
  if (!element) {
    return;
  }
  element.focus();
  if (typeof element.select === "function") {
    element.select();
  }
}

function getProductFormFieldOrder() {
  const order = [];
  if (elements.name) order.push(elements.name);
  if (!simpleModeEnabled && isElementVisible(elements.code)) order.push(elements.code);
  if (elements.quantity) order.push(elements.quantity);
  if (elements.price) order.push(elements.price);
  return order;
}

function getFirstMissingProductField() {
  if (elements.name && !String(elements.name.value || "").trim()) {
    return elements.name;
  }

  if (!simpleModeEnabled && isElementVisible(elements.code)) {
    if (!String(elements.code.value || "").trim()) {
      return elements.code;
    }
  }

  if (elements.quantity) {
    const raw = String(elements.quantity.value || "").trim();
    if (raw) {
      const parsed = Number(raw);
      if (!Number.isFinite(parsed) || parsed < 1) {
        return elements.quantity;
      }
    }
  }

  if (elements.price && !String(elements.price.value || "").trim()) {
    return elements.price;
  }

  return null;
}

function getNextProductField(current) {
  const order = getProductFormFieldOrder();
  const currentIndex = order.indexOf(current);
  if (currentIndex < 0) {
    return order[0] || null;
  }
  return order[currentIndex + 1] || null;
}

async function submitProduct() {
  const missing = getFirstMissingProductField();
  if (missing) {
    focusProductField(missing);
    return;
  }

  const rawQuantity = String(elements.quantity?.value || "").trim();
  const quantityValue = rawQuantity ? Number(rawQuantity) : 1;

  const payload = {
    nome: elements.name.value,
    codigo: simpleModeEnabled ? "" : elements.code.value,
    quantidade: quantityValue,
    preco: elements.price.value,
    categoria: elements.category.value,
    marca: simpleModeEnabled ? "" : elements.brand.value,
  };

  try {
    pushUndoSnapshot();
    await fetchJSON(`${API_BASE_URL}/products`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    resetForm();
    await refreshProducts();
    await fetchTotals();
  } catch (err) {
    console.error("Erro ao adicionar produto:", err);
  }
}

function handleSubmit(event) {
  event.preventDefault();
  void submitProduct();
}

function handleProductFormKeydown(event) {
  if (event.key !== "Enter" || event.isComposing) {
    return;
  }
  if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) {
    return;
  }

  const targets = [elements.name, elements.code, elements.quantity, elements.price].filter(Boolean);
  if (!targets.includes(event.target)) {
    return;
  }

  event.preventDefault();

  const missing = getFirstMissingProductField();
  if (missing) {
    if (
      missing === elements.price &&
      elements.quantity &&
      String(elements.quantity.value || "").trim() === "" &&
      event.target !== elements.quantity
    ) {
      const order = getProductFormFieldOrder();
      const targetIndex = order.indexOf(event.target);
      const quantityIndex = order.indexOf(elements.quantity);
      const priceIndex = order.indexOf(elements.price);
      if (targetIndex >= 0 && quantityIndex > targetIndex && priceIndex > quantityIndex) {
        focusProductField(elements.quantity);
        return;
      }
    }

    focusProductField(missing);
    return;
  }

  void submitProduct();
}

async function handleApplyCategory() {
  try {
    pushUndoSnapshot();
    await fetchJSON(`${API_BASE_URL}/actions/apply-category`, {
      method: "POST",
      body: JSON.stringify({ valor: elements.category.value }),
    });
    await refreshProducts();
    await fetchTotals();
  } catch (err) {
    console.error("Erro ao aplicar categoria:", err);
  }
}

async function handleApplyBrand() {
  try {
    pushUndoSnapshot();
    await fetchJSON(`${API_BASE_URL}/actions/apply-brand`, {
      method: "POST",
      body: JSON.stringify({ valor: elements.brand.value }),
    });
    await refreshProducts();
    await fetchTotals();
  } catch (err) {
    console.error("Erro ao aplicar marca:", err);
  }
}

async function handleJoinDuplicates() {
  try {
    pushUndoSnapshot();
    await fetchJSON(`${API_BASE_URL}/actions/join-duplicates`, {
      method: "POST",
    });
    await refreshProducts();
    await fetchTotals();
  } catch (err) {
    console.error("Erro ao juntar repetidos:", err);
  }
}

const GRADE_SIZE_PRIORITY = [
  "1",
  "2",
  "3",
  "4",
  "6",
  "8",
  "10",
  "12",
  "14",
  "16",
  "18",
  "U",
  "PP",
  "P",
  "M",
  "G",
  "GG",
  "XG",
  "XXG",
  "G1",
  "G2",
  "G3",
  "34",
  "36",
  "38",
  "40",
  "42",
  "44",
  "46",
  "48",
  "50",
  "52",
  "54",
  "56",
];
const GRADE_SIZE_PRIORITY_INDEX = new Map(GRADE_SIZE_PRIORITY.map((size, index) => [size, index]));

function normalizeGradeSizeLabel(value) {
  const label = String(value || "").trim().toUpperCase().replace(/[^A-Z0-9]+/g, "");
  if (!label) {
    return "";
  }
  if (/^\d+$/.test(label)) {
    const number = Number.parseInt(label, 10);
    return Number.isFinite(number) && number > 0 ? String(number) : "";
  }
  return label;
}

function compareGradeSizeLabels(a, b) {
  const left = normalizeGradeSizeLabel(a);
  const right = normalizeGradeSizeLabel(b);
  const leftRank = GRADE_SIZE_PRIORITY_INDEX.has(left) ? GRADE_SIZE_PRIORITY_INDEX.get(left) : Number.POSITIVE_INFINITY;
  const rightRank = GRADE_SIZE_PRIORITY_INDEX.has(right) ? GRADE_SIZE_PRIORITY_INDEX.get(right) : Number.POSITIVE_INFINITY;
  if (leftRank !== rightRank) {
    return leftRank - rightRank;
  }
  return left.localeCompare(right, "pt-BR");
}

function normalizeGradeSizeList(values) {
  const unique = new Map();
  (Array.isArray(values) ? values : []).forEach((value) => {
    const label = normalizeGradeSizeLabel(value);
    if (!label || unique.has(label)) {
      return;
    }
    unique.set(label, label);
  });
  return Array.from(unique.values());
}

function buildGradeSizeCatalog(products, catalogSizes, preferredOrder = []) {
  const merged = new Map();

  const pushValue = (value) => {
    const label = normalizeGradeSizeLabel(value);
    if (!label || merged.has(label)) {
      return;
    }
    merged.set(label, label);
  };

  normalizeGradeSizeList(preferredOrder).forEach(pushValue);
  (Array.isArray(catalogSizes) ? catalogSizes : []).forEach(pushValue);
  (Array.isArray(products) ? products : []).forEach((product) => {
    if (!Array.isArray(product?.grades)) {
      return;
    }
    product.grades.forEach((grade) => pushValue(grade?.tamanho));
  });

  const preferredIndex = new Map(
    normalizeGradeSizeList(preferredOrder).map((size, index) => [normalizeGradeSizeLabel(size), index])
  );

  return Array.from(merged.values()).sort((a, b) => {
    const left = normalizeGradeSizeLabel(a);
    const right = normalizeGradeSizeLabel(b);
    const leftPreferred = preferredIndex.has(left) ? preferredIndex.get(left) : Number.POSITIVE_INFINITY;
    const rightPreferred = preferredIndex.has(right) ? preferredIndex.get(right) : Number.POSITIVE_INFINITY;
    if (leftPreferred !== rightPreferred) {
      return leftPreferred - rightPreferred;
    }
    return compareGradeSizeLabels(left, right);
  });
}

function openGradeOrderDialog(currentSizes = []) {
  const normalizedSizes = normalizeGradeSizeList(currentSizes);
  const dialog = createDialogElement(`
    <h3>Personalizar Tamanhos</h3>
    <label class="modal-input">
      <span>Ordem visual dos tamanhos no webapp</span>
      <textarea id="grade-order-manager-input" rows="6" placeholder="Ex.: PP, P, M, G, GG, XG">${normalizedSizes.join(", ")}</textarea>
    </label>
    <p class="modal-hint">Adicione novos tamanhos e reorganize a ordem separando por virgula. O visual do webapp muda, mas a ordem antiga do ByteEmpresa fica preservada; tamanhos novos entram no fim da automacao.</p>
  `);

  document.body.appendChild(dialog);

  return new Promise((resolve) => {
    const cleanup = () => {
      dialog.remove();
      document.removeEventListener("keydown", escListener);
    };

    const escListener = (event) => {
      if (event.key === "Escape") {
        cleanup();
        resolve(null);
      }
    };

    document.addEventListener("keydown", escListener);

    dialog.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) {
        return;
      }
      const action = button.dataset.action;
      if (action === "cancel") {
        cleanup();
        resolve(null);
        return;
      }
      if (action === "confirm") {
        const input = dialog.querySelector("#grade-order-manager-input");
        const values = String(input?.value || "")
          .split(",")
          .map((item) => normalizeGradeSizeLabel(item))
          .filter(Boolean);
        const normalized = normalizeGradeSizeList(values);
        if (!normalized.length) {
          window.alert("Informe pelo menos um tamanho.");
          return;
        }
        cleanup();
        resolve(normalized);
      }
    });
  });
}

async function handleJoinGrades() {
  if (!elements.joinGrades) {
    return;
  }

  const button = elements.joinGrades;
  const previousLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Importando...";

  try {
    pushUndoSnapshot();
    const result = await fetchJSON(`${API_BASE_URL}/actions/join-grades`, {
      method: "POST",
      body: JSON.stringify({ keys: [] }),
    });
    await refreshProducts();
    await fetchTotals();
    if (!Number(result?.lotes_processados || 0)) {
      window.alert("Nao ha lotes com grades pendentes para importar.");
      return;
    }

    window.alert(
      [
        `Lotes processados: ${Number(result?.lotes_processados || 0)}`,
        `Produtos finais: ${Number(result?.resultantes || 0)}`,
        `Grades importadas: ${Number(result?.atualizados_grades || 0)}`,
        `Linhas unificadas: ${Number(result?.removidos || 0)}`,
      ].join("\n")
    );
  } catch (err) {
    console.error("Erro ao juntar grades:", err);
    window.alert(`Falha ao importar grades: ${err.message || err}`);
  } finally {
    button.disabled = false;
    button.textContent = previousLabel;
  }
}

async function handleClearList() {
  try {
    pushUndoSnapshot();
    await fetchJSON(`${API_BASE_URL}/products`, {
      method: "DELETE",
    });
    await refreshProducts();
    await fetchTotals();
  } catch (err) {
    console.error("Erro ao limpar lista:", err);
  }
}

function ensureImportRomaneioInput() {
  if (!importRomaneioInput) {
    importRomaneioInput = document.createElement("input");
    importRomaneioInput.type = "file";
    importRomaneioInput.accept = "image/*,.pdf,.txt";
    importRomaneioInput.style.display = "none";
    document.body.appendChild(importRomaneioInput);
  }
  return importRomaneioInput;
}

function toggleImportButtons(disabled) {
  if (elements.importRomaneioPrimary) {
    elements.importRomaneioPrimary.disabled = disabled;
  }
  if (elements.importRomaneioSecondary) {
    elements.importRomaneioSecondary.disabled = disabled;
  }
}

function toggleGradeButtons(disabled) {
  if (elements.insertGrade) {
    elements.insertGrade.disabled = disabled;
  }
  if (elements.topInsertGrade) {
    elements.topInsertGrade.disabled = disabled;
  }
}

function createRomaneioStatusModal() {
  if (romaneioStatusModal) {
    return romaneioStatusModal;
  }

  const overlay = document.createElement("div");
  overlay.className = "romaneio-status-overlay";

  const panel = document.createElement("div");
  panel.className = "romaneio-status-panel";

  const title = document.createElement("h3");
  title.textContent = "Importando romaneio";

  const stage = document.createElement("div");
  stage.className = "romaneio-status-stage";
  stage.textContent = "Preparando...";

  const progressBar = document.createElement("div");
  progressBar.className = "romaneio-progress";
  const progressInner = document.createElement("div");
  progressInner.className = "romaneio-progress-inner";
  progressBar.appendChild(progressInner);

  const logs = document.createElement("ul");
  logs.className = "romaneio-status-logs";

  panel.appendChild(title);
  panel.appendChild(stage);
  panel.appendChild(progressBar);
  panel.appendChild(logs);
  overlay.appendChild(panel);

  const closeModal = () => {
    overlay.classList.remove("visible");
  };

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      closeModal();
    }
  });

  document.body.appendChild(overlay);

  romaneioStatusModal = {
    overlay,
    stage,
    progressInner,
    logs,
    lastMessage: null,
    show(message) {
      if (message) {
        stage.textContent = message;
      }
      overlay.classList.add("visible");
    },
    hide() {
      overlay.classList.remove("visible");
    },
    update(message, progress) {
      if (message) {
        stage.textContent = message;
        if (message !== this.lastMessage) {
          const listItem = document.createElement("li");
          listItem.textContent = `${new Date().toLocaleTimeString()} · ${message}`;
          logs.appendChild(listItem);
          logs.scrollTop = logs.scrollHeight;
          this.lastMessage = message;
        }
      }
      if (typeof progress === "number") {
        progressInner.style.width = `${progress * 100}%`;
      }
    },
    reset() {
      stage.textContent = "Preparando...";
      progressInner.style.width = "10%";
      logs.innerHTML = "";
      this.lastMessage = null;
    },
  };

  return romaneioStatusModal;
}

function createPostProcessStatusModal() {
  if (postProcessStatusModal) {
    return postProcessStatusModal;
  }

  const overlay = document.createElement("div");
  overlay.className = "romaneio-status-overlay";

  const panel = document.createElement("div");
  panel.className = "romaneio-status-panel";

  const title = document.createElement("h3");
  title.textContent = "Pos-processamento LLM";

  const stage = document.createElement("div");
  stage.className = "romaneio-status-stage";
  stage.textContent = "Preparando...";

  const progressBar = document.createElement("div");
  progressBar.className = "romaneio-progress";
  const progressInner = document.createElement("div");
  progressInner.className = "romaneio-progress-inner";
  progressBar.appendChild(progressInner);

  const logs = document.createElement("ul");
  logs.className = "romaneio-status-logs";

  panel.appendChild(title);
  panel.appendChild(stage);
  panel.appendChild(progressBar);
  panel.appendChild(logs);
  overlay.appendChild(panel);

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      overlay.classList.remove("visible");
    }
  });

  document.body.appendChild(overlay);

  postProcessStatusModal = {
    overlay,
    stage,
    progressInner,
    logs,
    lastMessage: null,
    show(message) {
      if (message) {
        stage.textContent = message;
      }
      overlay.classList.add("visible");
    },
    hide() {
      overlay.classList.remove("visible");
    },
    update(message, progress) {
      if (message) {
        stage.textContent = message;
        if (message !== this.lastMessage) {
          const listItem = document.createElement("li");
          listItem.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
          logs.appendChild(listItem);
          logs.scrollTop = logs.scrollHeight;
          this.lastMessage = message;
        }
      }
      if (typeof progress === "number") {
        progressInner.style.width = `${progress * 100}%`;
      }
    },
    reset() {
      stage.textContent = "Preparando...";
      progressInner.style.width = "10%";
      logs.innerHTML = "";
      this.lastMessage = null;
    },
  };

  return postProcessStatusModal;
}

function stopRomaneioStatusPolling() {
  if (romaneioStatusInterval) {
    window.clearInterval(romaneioStatusInterval);
    romaneioStatusInterval = null;
  }
  romaneioStatusJobId = null;
}

function startRomaneioStatusPolling(jobId) {
  stopRomaneioStatusPolling();
  romaneioStatusJobId = jobId;
  const modal = createRomaneioStatusModal();
  modal.reset();
  modal.show("Enviando arquivo para serviço LLM");
  modal.update("Enviando arquivo para serviço LLM", 0.2);

  const STAGE_PROGRESS = {
    pending: 0.1,
    uploading: 0.3,
    processing: 0.6,
    parsing: 0.85,
    completed: 1,
    error: 1,
  };

  const fetchStatus = async () => {
    if (!romaneioStatusJobId) {
      return;
    }
    try {
      const status = await fetchJSON(
        `${API_BASE_URL}/actions/import-romaneio/status/${romaneioStatusJobId}`
      );
      const { stage, message, error } = status || {};
      const progress = STAGE_PROGRESS[String(stage)] ?? 0.1;
      modal.update(message || "Processando...", progress);

      if (stage === "completed") {
        const jobId = romaneioStatusJobId;
        stopRomaneioStatusPolling();
        modal.update("Processamento concluído", 1);
        let result;
        try {
          result = await fetchJSON(
            `${API_BASE_URL}/actions/import-romaneio/result/${jobId}`
          );
        } catch (fetchErr) {
          console.error("Falha ao obter resultado do romaneio:", fetchErr);
          window.alert(
            `Processo finalizou, mas não foi possível carregar o resultado: ${fetchErr.message || fetchErr}`
          );
        }
        setTimeout(() => {
          modal.hide();
          modal.reset();
        }, 1500);
        if (result) {
          latestImportedKeys = result.grades_disponiveis && Array.isArray(result.imported_keys)
            ? result.imported_keys.filter(Boolean)
            : [];
          const lines = [`Itens importados: ${result.total_itens || 0}`]
            .concat(result.local_file ? [`Arquivo salvo: ${result.local_file}`] : [])
            .concat(
              Array.isArray(result.warnings) && result.warnings.length
                ? [`Avisos: ${result.warnings.join(" | ")}`]
                : []
            );
          if (result.grades_disponiveis) {
            lines.push("Grades automaticas disponiveis.");
            lines.push("Clique em Importar Grades para aplicar.");
          }
          window.alert(lines.join("\n"));
          void refreshProducts();
        }
        try {
          await fetch(`${API_BASE_URL}/actions/import-romaneio/status/${jobId}`, {
            method: "DELETE",
          });
        } catch (cleanupErr) {
          console.warn("Falha ao limpar job de romaneio:", cleanupErr);
        }
        romaneioStatusJobId = null;
        return;
      }

      if (stage === "error") {
        stopRomaneioStatusPolling();
        modal.update(error || "Falha ao importar romaneio", 1);
        setTimeout(() => {
          modal.hide();
          modal.reset();
        }, 2000);
        throw new Error(error || "Falha ao importar romaneio");
      }
    } catch (err) {
      console.error("Erro ao consultar status do romaneio:", err);
      stopRomaneioStatusPolling();
      createRomaneioStatusModal().hide();
      window.alert(`Falha ao importar romaneio: ${err.message || err}`);
    }
  };

  fetchStatus();
  romaneioStatusInterval = window.setInterval(fetchStatus, 5000);
}

function stopPostProcessStatusPolling() {
  if (postProcessStatusInterval) {
    window.clearInterval(postProcessStatusInterval);
    postProcessStatusInterval = null;
  }
  postProcessStatusJobId = null;
}

function startPostProcessStatusPolling(jobId) {
  stopPostProcessStatusPolling();
  postProcessStatusJobId = jobId;
  const modal = createPostProcessStatusModal();
  modal.reset();
  modal.show("Enviando itens para pos-processamento");
  modal.update("Enviando itens para pos-processamento", 0.2);

  const STAGE_PROGRESS = {
    pending: 0.1,
    processing: 0.35,
    reviewing: 0.75,
    completed: 1,
    error: 1,
  };

  const fetchStatus = async () => {
    if (!postProcessStatusJobId) {
      return;
    }
    try {
      const status = await fetchJSON(
        `${API_BASE_URL}/actions/post-process-products/status/${postProcessStatusJobId}`
      );
      const { stage, message, error } = status || {};
      const progress = STAGE_PROGRESS[String(stage)] ?? 0.1;
      modal.update(message || "Processando...", progress);

      if (stage === "completed") {
        const currentJobId = postProcessStatusJobId;
        stopPostProcessStatusPolling();
        modal.update("Pos-processamento concluido", 1);
        let result;
        try {
          result = await fetchJSON(
            `${API_BASE_URL}/actions/post-process-products/result/${currentJobId}`
          );
        } catch (fetchErr) {
          console.error("Falha ao obter resultado do pos-processamento:", fetchErr);
          window.alert(
            `O pos-processamento terminou, mas o resultado nao foi carregado: ${fetchErr.message || fetchErr}`
          );
        }
        setTimeout(() => {
          modal.hide();
          modal.reset();
        }, 1500);
        if (result) {
          const lines = [
            `Itens analisados: ${result.total_itens || 0}`,
            `Alteracoes aplicadas nesta fase: ${result.total_modificados || 0}`,
          ];
          if (result.dry_run) {
            lines.push("Skeleton ativo: a resposta do LLM foi capturada, mas ainda nao aplicamos as sugestoes.");
          }
          if (Array.isArray(result.warnings) && result.warnings.length) {
            lines.push(`Avisos: ${result.warnings.join(" | ")}`);
          }
          window.alert(lines.join("\n"));
        }
        try {
          await fetch(`${API_BASE_URL}/actions/post-process-products/status/${currentJobId}`, {
            method: "DELETE",
          });
        } catch (cleanupErr) {
          console.warn("Falha ao limpar job de pos-processamento:", cleanupErr);
        }
        return;
      }

      if (stage === "error") {
        stopPostProcessStatusPolling();
        modal.update(error || "Falha ao executar pos-processamento", 1);
        setTimeout(() => {
          modal.hide();
          modal.reset();
        }, 2000);
        throw new Error(error || "Falha ao executar pos-processamento");
      }
    } catch (err) {
      console.error("Erro ao consultar status do pos-processamento:", err);
      stopPostProcessStatusPolling();
      createPostProcessStatusModal().hide();
      window.alert(`Falha no pos-processamento: ${err.message || err}`);
    }
  };

  fetchStatus();
  postProcessStatusInterval = window.setInterval(fetchStatus, 5000);
}

async function handleImportRomaneio() {
  const input = ensureImportRomaneioInput();
  const file = await new Promise((resolve) => {
    const handler = () => {
      resolve(input.files && input.files.length ? input.files[0] : null);
    };
    input.addEventListener("change", handler, { once: true });
    input.click();
  });

  if (!file) {
    input.value = "";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  latestImportedKeys = [];

  toggleImportButtons(true);
  const modal = createRomaneioStatusModal();
  modal.reset();
  modal.show("Iniciando importação...");
  modal.update("Iniciando importação...", 0.15);
  pushUndoSnapshot();

  try {
    const response = await fetch(`${API_BASE_URL}/actions/import-romaneio`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || response.statusText);
    }

    const data = await response.json();
    const jobId = data?.job_id;
    if (!jobId) {
      throw new Error("Resposta inválida do servidor");
    }
    startRomaneioStatusPolling(jobId);
  } catch (err) {
    console.error("Erro ao importar romaneio:", err);
    window.alert(`Falha ao importar romaneio: ${err.message || err}`);
    createRomaneioStatusModal().hide();
    stopRomaneioStatusPolling();
  } finally {
    toggleImportButtons(false);
    input.value = "";
  }
}

async function handlePostProcessLlm() {
  if (elements.postProcessLlm) {
    elements.postProcessLlm.disabled = true;
  }

  const modal = createPostProcessStatusModal();
  modal.reset();
  modal.show("Preparando pos-processamento...");
  modal.update("Preparando pos-processamento...", 0.15);
  pushUndoSnapshot();

  try {
    const response = await fetch(`${API_BASE_URL}/actions/post-process-products`, {
      method: "POST",
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || response.statusText);
    }

    const data = await response.json();
    const jobId = data?.job_id;
    if (!jobId) {
      throw new Error("Resposta invalida do servidor");
    }
    startPostProcessStatusPolling(jobId);
  } catch (err) {
    console.error("Erro ao iniciar pos-processamento:", err);
    window.alert(`Falha ao iniciar pos-processamento: ${err.message || err}`);
    createPostProcessStatusModal().hide();
    stopPostProcessStatusPolling();
  } finally {
    if (elements.postProcessLlm) {
      elements.postProcessLlm.disabled = false;
    }
  }
}

async function fetchTargets() {
  try {
    const data = await fetchJSON(`${API_BASE_URL}/automation/targets`);
    return normalizeTargets(data || {});
  } catch (err) {
    console.error("Erro ao carregar targets:", err);
    return {};
  }
}

function normalizeTargets(raw) {
  const normalized = {};
  AUTOMATION_TARGET_FIELDS.forEach(({ key }) => {
    const entry = raw?.[key];
    if (entry && Number.isFinite(Number(entry.x)) && Number.isFinite(Number(entry.y))) {
      normalized[key] = { x: Number(entry.x), y: Number(entry.y) };
    }
  });
  if (typeof raw?.title === "string") {
    normalized.title = raw.title;
  }
  return normalized;
}

async function fetchGradeConfig() {
  try {
    const data = await fetchJSON(`${API_BASE_URL}/automation/grades/config`);
    return data?.config || {};
  } catch (err) {
    console.error("Erro ao carregar configuracao de grades:", err);
    return {};
  }
}

async function saveTargets(payload) {
  try {
    const response = await fetchJSON(`${API_BASE_URL}/automation/targets`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return normalizeTargets(response || {});
  } catch (err) {
    console.error("Erro ao salvar targets:", err);
    throw err;
  }
}

function buildGradeConfigPayload(dialogResult) {
  const payload = {
    buttons: dialogResult.buttons,
    erp_size_order: dialogResult.erpSizeOrder,
  };
  if (dialogResult.firstQuantCell) {
    payload.first_quant_cell = dialogResult.firstQuantCell;
  }
  if (dialogResult.secondQuantCell) {
    payload.second_quant_cell = dialogResult.secondQuantCell;
  }
  if (dialogResult.rowHeight) {
    payload.row_height = dialogResult.rowHeight;
  }
  if (dialogResult.modelIndex !== undefined) {
    payload.model_index = dialogResult.modelIndex;
  }
  if (dialogResult.modelHotkey !== undefined) {
    payload.model_hotkey = dialogResult.modelHotkey;
  }
  return payload;
}

async function saveGradeConfig(payload) {
  try {
    const response = await fetchJSON(`${API_BASE_URL}/automation/grades/config`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return response?.config || {};
  } catch (err) {
    console.error("Erro ao salvar configuracao de grades:", err);
    throw err;
  }
}

function mergeNewSizesIntoErpOrder(erpOrder, uiOrder) {
  const merged = normalizeGradeSizeList(erpOrder);
  normalizeGradeSizeList(uiOrder).forEach((size) => {
    if (!merged.includes(size)) {
      merged.push(size);
    }
  });
  return merged;
}

function openTargetPickerDialog(existingTargets = {}) {
  const titleValue = existingTargets.title || "";
  const makeCoordsText = (key) => {
    const entry = existingTargets[key];
    if (!entry) {
      return "Não calibrado";
    }
    return `X: ${entry.x} | Y: ${entry.y}`;
  };

  const dialog = createDialogElement(`
    <h3>Calibração PyAutoGUI</h3>
    <div class="calibration-section">
      <label class="modal-input">
        <span>Título da janela alvo (opcional)</span>
        <input type="text" id="calibration-window-title" value="${titleValue}" placeholder="Ex.: Byte Empresa" />
      </label>
      <div class="calibration-target" data-target="byte_empresa_posicao">
        <div class="calibration-info">
          <strong>Posição Byte Empresa</strong>
          <span class="calibration-coords">${makeCoordsText("byte_empresa_posicao")}</span>
        </div>
        <button type="button" class="pill-button accent" data-action="capture" data-target="byte_empresa_posicao">Capturar</button>
      </div>
      <div class="calibration-target" data-target="campo_descricao">
        <div class="calibration-info">
          <strong>Campo Descrição (Tela 1)</strong>
          <span class="calibration-coords">${makeCoordsText("campo_descricao")}</span>
        </div>
        <button type="button" class="pill-button accent" data-action="capture" data-target="campo_descricao">Capturar</button>
      </div>
      <div class="calibration-target" data-target="tres_pontinhos">
        <div class="calibration-info">
          <strong>Botão 3 pontinhos (Tela 2)</strong>
          <span class="calibration-coords">${makeCoordsText("tres_pontinhos")}</span>
        </div>
        <button type="button" class="pill-button accent" data-action="capture" data-target="tres_pontinhos">Capturar</button>
      </div>
      <div id="calibration-capture-feedback" class="calibration-feedback"></div>
    </div>
  `);

  const confirmButton = dialog.querySelector(".modal-actions [data-action=confirm]");
  if (confirmButton) {
    confirmButton.textContent = "Salvar";
  }
  const feedbackEl = dialog.querySelector("#calibration-capture-feedback");
  if (feedbackEl) {
    const hint = document.createElement("p");
    hint.className = "modal-hint";
    hint.textContent = "Os 4 cliques de Cadastro completo sÃ£o usados na transiÃ§Ã£o entre cadastro em massa e grades.";
    hint.textContent = "Os 4 cliques de Cadastro completo sao usados na transicao entre cadastro em massa e grades.";
    feedbackEl.insertAdjacentElement("beforebegin", hint);

    AUTOMATION_TARGET_FIELDS.filter(({ key }) => key.startsWith("cadastro_completo_passo_")).forEach(({ key }) => {
      const row = document.createElement("div");
      row.className = "calibration-target";
      row.dataset.target = key;
      row.innerHTML = `
        <div class="calibration-info">
          <strong>${labelForTarget(key)}</strong>
          <span class="calibration-coords">${makeCoordsText(key)}</span>
        </div>
        <button type="button" class="pill-button accent" data-action="capture" data-target="${key}">Capturar</button>
      `;
      feedbackEl.insertAdjacentElement("beforebegin", row);
    });
  }

  let currentTargets = { ...existingTargets };

  const teardown = () => {
    stopCaptureCountdown();
    dialog.remove();
    document.removeEventListener("keydown", escListener);
  };

  const escListener = (event) => {
    if (event.key === "Escape") {
      teardown();
      resolvePromise(null);
    }
  };

  document.addEventListener("keydown", escListener);
  document.body.appendChild(dialog);

  let resolvePromise;
  const promise = new Promise((resolve) => {
    resolvePromise = resolve;
  });

  const showFeedback = (message, tone = "info") => {
    const feedbackEl = dialog.querySelector("#calibration-capture-feedback");
    if (!feedbackEl) return;
    feedbackEl.textContent = message || "";
    feedbackEl.dataset.tone = tone;
  };

  const updateTargetDisplay = (key, value) => {
    const wrapper = dialog.querySelector(`.calibration-target[data-target="${key}"]`);
    if (!wrapper) return;
    const coordsEl = wrapper.querySelector(".calibration-coords");
    if (!coordsEl) return;
    coordsEl.textContent = value ? `X: ${value.x} | Y: ${value.y}` : "Não calibrado";
  };

  const handleCaptureClick = (targetKey) => {
    if (captureActive) {
      return;
    }
    showFeedback("Clique no ponto desejado em 3 segundos...", "info");
    startCaptureCountdown(targetKey, (result, error) => {
      if (error) {
        if (error.message === "Captura cancelada") {
          showFeedback("Captura cancelada.", "warning");
          return;
        }
        console.error("Erro na captura de coordenadas:", error);
        showFeedback(`Falha ao capturar coordenadas: ${error.message || error}`, "warning");
        return;
      }
      if (!result) {
        showFeedback("Captura cancelada.", "warning");
        return;
      }
      currentTargets[targetKey] = result;
      updateTargetDisplay(targetKey, result);
      showFeedback(`Coordenadas registradas para ${labelForTarget(targetKey)}.`, "success");
    });
  };

  dialog.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) {
      return;
    }

    const action = button.dataset.action;
    if (action === "cancel") {
      teardown();
      resolvePromise(null);
      return;
    }

    if (action === "confirm") {
      const payload = { ...currentTargets };
      const titleInput = dialog.querySelector("#calibration-window-title");
      if (titleInput) {
        const title = titleInput.value.trim();
        if (title) {
          payload.title = title;
        } else {
          delete payload.title;
        }
      }
      teardown();
      resolvePromise(payload);
      return;
    }

    if (action === "capture") {
      const targetKey = button.dataset.target;
      if (!targetKey) {
        return;
      }
      handleCaptureClick(targetKey);
    }
  });

  return promise;
}

function labelForTarget(key) {
  const safeLabels = {
    byte_empresa_posicao: "Posicao Byte Empresa",
    campo_descricao: "Campo Descricao",
    tres_pontinhos: "Botao 3 pontinhos",
    cadastro_completo_passo_1: "Cadastro completo - clique 1",
    cadastro_completo_passo_2: "Cadastro completo - clique 2",
    cadastro_completo_passo_3: "Cadastro completo - clique 3",
    cadastro_completo_passo_4: "Cadastro completo - clique 4",
  };
  if (safeLabels[key]) {
    return safeLabels[key];
  }
  const item = AUTOMATION_TARGET_FIELDS.find((entry) => entry.key === key);
  if (item?.label) {
    return item.label;
  }
  switch (key) {
    case "byte_empresa_posicao":
      return "Posição Byte Empresa";
    case "campo_descricao":
      return "Campo Descrição";
    case "tres_pontinhos":
      return "Botão 3 pontinhos";
    default:
      return key;
  }
}

function startCaptureCountdown(targetKey, callback) {
  stopCaptureCountdown();
  captureActive = true;
  captureTargetKey = targetKey;
  captureCountdownRemaining = 3;
  captureCallback = callback;

  captureWindow = document.createElement("div");
  captureWindow.className = "capture-overlay";
  captureWindow.innerHTML = `
    <div class="capture-card">
      <h4>Captura de coordenadas</h4>
      <p>Posicione o mouse. Capturando em <span id="capture-countdown">${captureCountdownRemaining}</span>...</p>
      <button type="button" class="pill-button secondary" data-action="cancel-capture">Cancelar</button>
    </div>
  `;
  document.body.appendChild(captureWindow);

  const completeCapture = async () => {
    const callbackRef = captureCallback;
    stopCaptureCountdown(false);
    try {
      const coords = await captureTargetCoordinates(targetKey);
      if (callbackRef) {
        callbackRef(coords, null);
      }
    } catch (err) {
      if (callbackRef) {
        callbackRef(null, err);
      }
    } finally {
      captureActive = false;
      captureTargetKey = null;
      captureCallback = null;
    }
  };

  const tick = () => {
    captureCountdownRemaining -= 1;
    const countdownEl = captureWindow?.querySelector("#capture-countdown");
    if (countdownEl) {
      countdownEl.textContent = String(Math.max(captureCountdownRemaining, 0));
    }
    if (captureCountdownRemaining <= 0) {
      void completeCapture();
      return;
    }
    captureCountdownTimer = window.setTimeout(tick, 1000);
  };

  captureWindow.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (button && button.dataset.action === "cancel-capture") {
      stopCaptureCountdown();
    }
  });

  captureCountdownTimer = window.setTimeout(tick, 1000);
}

function stopCaptureCountdown(cancel = true) {
  if (captureCountdownTimer) {
    window.clearTimeout(captureCountdownTimer);
    captureCountdownTimer = null;
  }
  if (captureWindow) {
    captureWindow.remove();
    captureWindow = null;
  }
  if (cancel) {
    const callbackRef = captureCallback;
    captureActive = false;
    captureTargetKey = null;
    captureCallback = null;
    if (callbackRef) {
      callbackRef(null, new Error("Captura cancelada"));
    }
  }
}

async function captureTargetCoordinates(targetKey) {
  if (!targetKey) {
    throw new Error("Target inválido");
  }
  const payload = { target: targetKey };
  const response = await fetchJSON(`${API_BASE_URL}/automation/targets/capture`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const point = response?.point || response;
  if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
    throw new Error("Resposta de captura inválida");
  }
  return { x: Number(point.x), y: Number(point.y) };
}

async function handleCalibrationClick() {
  if (!elements.calibrate) {
    return;
  }

  if (elements.calibrate.disabled) {
    return;
  }

  elements.calibrate.disabled = true;
  try {
    const currentTargets = await fetchTargets();
    const result = await openTargetPickerDialog(currentTargets);
    if (!result) {
      return;
    }
    const toPersist = {};
    if (result.title) {
      toPersist.title = result.title;
    }
    AUTOMATION_TARGET_FIELDS.forEach(({ key }) => {
      if (result[key]) {
        toPersist[key] = result[key];
      }
    });
    if (!Object.keys(toPersist).length) {
      window.alert("Nenhuma coordenada nova para salvar.");
      return;
    }
    await saveTargets(toPersist);
    window.alert("Coordenadas atualizadas com sucesso.");
  } catch (err) {
    console.error("Erro durante calibração:", err);
    window.alert(`Falha na calibração: ${err.message || err}`);
  } finally {
    elements.calibrate.disabled = false;
  }
}

async function handleFullAutomationCalibrationClick() {
  if (!elements.calibrate) {
    return;
  }

  if (elements.calibrate.disabled) {
    return;
  }

  elements.calibrate.disabled = true;
  try {
    const currentTargets = await fetchTargets();
    const targetResult = await openTargetPickerDialog(currentTargets);
    if (!targetResult) {
      return;
    }

    const targetPayload = {};
    if (targetResult.title) {
      targetPayload.title = targetResult.title;
    }
    AUTOMATION_TARGET_FIELDS.forEach(({ key }) => {
      if (targetResult[key]) {
        targetPayload[key] = targetResult[key];
      }
    });

    let savedTargets = false;
    if (Object.keys(targetPayload).length) {
      await saveTargets(targetPayload);
      savedTargets = true;
    }

    const currentGradeConfig = await fetchGradeConfig();
    const gradeResult = await openGradeCalibrationDialog(currentGradeConfig, {});

    let savedGrades = false;
    if (gradeResult) {
      const gradePayload = buildGradeConfigPayload(gradeResult);
      if (Object.keys(gradePayload).length) {
        await saveGradeConfig(gradePayload);
        savedGrades = true;
      }
    }

    if (!savedTargets && !savedGrades) {
      window.alert("Nenhuma coordenada nova para salvar.");
      return;
    }
    if (savedTargets && savedGrades) {
      window.alert("Calibracao completa salva com sucesso.");
      return;
    }
    if (savedTargets) {
      window.alert("Coordenadas do cadastro salvas com sucesso.");
      return;
    }
    window.alert("Coordenadas das grades salvas com sucesso.");
  } catch (err) {
    console.error("Erro durante calibracao completa:", err);
    window.alert(`Falha na calibracao: ${err.message || err}`);
  } finally {
    elements.calibrate.disabled = false;
  }
}

function registerEvents() {
  elements.form?.addEventListener("submit", handleSubmit);
  elements.applyCategory?.addEventListener("click", handleApplyCategory);
  elements.applyBrand?.addEventListener("click", handleApplyBrand);
  elements.joinDuplicates?.addEventListener("click", handleJoinDuplicates);
  elements.clearList?.addEventListener("click", handleClearList);
  elements.importRomaneioPrimary?.addEventListener("click", handleImportRomaneio);
  elements.importRomaneioSecondary?.addEventListener("click", handleImportRomaneio);
  elements.formatCodes?.addEventListener("click", handleFormatCodes);
  elements.calibrate?.addEventListener("click", handleFullAutomationCalibrationClick);
  elements.improveDescription?.addEventListener("click", handleImproveDescription);
  elements.postProcessLlm?.addEventListener("click", handlePostProcessLlm);
  elements.deleteItems?.addEventListener("click", handleDeleteItemsClick);
  elements.toggleOrdering?.addEventListener("click", handleToggleOrdering);
  elements.createSets?.addEventListener("click", handleCreateSetsClick);
  elements.joinGrades?.addEventListener("click", handleJoinGrades);
  elements.editNames?.addEventListener("click", toggleEditNamesMode);
  elements.allowEdits?.addEventListener("click", () => toggleGlobalEditMode());
  elements.toggleSimpleMode?.addEventListener("click", toggleSimpleMode);
  elements.insertGrade?.addEventListener("click", () => {
    void openInsertGradesDialog();
  });
  elements.topInsertGrade?.addEventListener("click", handleTopExecuteGrades);
  document.getElementById("btn-nova-marca")?.addEventListener("click", handleNewBrand);
  elements.automationStart?.addEventListener("click", handleAutomationStart);
  elements.automationComplete?.addEventListener("click", handleAutomationComplete);
  elements.automationStop?.addEventListener("click", handleAutomationStop);
  elements.topStopGrades?.addEventListener("click", handleTopStopGrades);

  const marginPrimary = document.getElementById("btn-open-margin");
  [marginPrimary]
    .filter(Boolean)
    .forEach((button) =>
      button.addEventListener("click", () => {
        handleOpenMargin();
      })
    );

  [elements.name, elements.code, elements.quantity, elements.price]
    .filter(Boolean)
    .forEach((input) => input.addEventListener("keydown", handleProductFormKeydown));
}

async function init() {
  elements.productsBody?.addEventListener("click", handleRowClick);
  document.addEventListener("keydown", handleUndoRedoKeydown);
  registerEvents();

  try {
    await Promise.all([
      refreshProducts(),
      fetchTotals(),
      fetchBrands(),
      pollAutomationStatus(),
      fetchCategories(),
    ]);
  } catch (err) {
    console.error("Falha durante inicialização:", err);
  }

  try {
    await fetchMarginSettings();
    await fetchTotals();
    await refreshProducts();
  } catch (err) {
    console.error("Falha ao atualizar dados iniciais:", err);
  }

  startUIRealtime();
}

document.addEventListener("DOMContentLoaded", init);

const UI_WS_PATH = "/ws/ui";
const UI_WS_PING_INTERVAL_MS = 20000;
const UI_WS_REFRESH_DEBOUNCE_MS = 150;
const UI_FALLBACK_POLL_INTERVAL_MS = 5000;

const ROMANEIO_STAGE_PROGRESS = {
  pending: 0.1,
  uploading: 0.3,
  processing: 0.6,
  parsing: 0.85,
  completed: 1,
  error: 1,
};

const POST_PROCESS_STAGE_PROGRESS = {
  pending: 0.1,
  processing: 0.35,
  reviewing: 0.75,
  completed: 1,
  error: 1,
};


let uiWs = null;
let uiWsConnected = false;
let uiWsPingTimer = null;
let uiWsReconnectTimer = null;
let uiWsReconnectDelayMs = 1000;
let uiFallbackPollTimer = null;
let uiPendingRefreshTimer = null;
let uiRealtimeStarted = false;
const uiPendingScopes = new Set();

function buildWsUrl(path) {
  try {
    const url = new URL(API_BASE_URL);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = path;
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch (err) {
    return null;
  }
}

function scheduleUiScopesRefresh(scopes) {
  const list = Array.isArray(scopes) ? scopes : [];
  list.forEach((scope) => {
    if (scope) {
      uiPendingScopes.add(String(scope));
    }
  });
  if (uiPendingRefreshTimer) {
    return;
  }
  uiPendingRefreshTimer = window.setTimeout(() => {
    uiPendingRefreshTimer = null;
    void flushUiScopesRefresh();
  }, UI_WS_REFRESH_DEBOUNCE_MS);
}

async function flushUiScopesRefresh() {
  if (!uiPendingScopes.size) {
    return;
  }
  const scopes = Array.from(uiPendingScopes);
  uiPendingScopes.clear();

  const tasks = [];
  if (scopes.includes("products")) {
    tasks.push(refreshProducts());
  }
  if (scopes.includes("totals")) {
    tasks.push(fetchTotals());
  }
  if (scopes.includes("brands")) {
    tasks.push(fetchBrands());
  }
  if (scopes.includes("automation")) {
    tasks.push(pollAutomationStatus());
  }
  if (scopes.includes("margin")) {
    tasks.push(fetchMarginSettings());
  }
  await Promise.allSettled(tasks);
}

function startUiFallbackPolling() {
  if (uiFallbackPollTimer) {
    return;
  }
  uiFallbackPollTimer = window.setInterval(() => {
    if (document.visibilityState === "visible") {
      scheduleUiScopesRefresh(["products", "totals", "brands", "automation", "margin"]);
    }
  }, UI_FALLBACK_POLL_INTERVAL_MS);
}

function stopUiFallbackPolling() {
  if (uiFallbackPollTimer) {
    window.clearInterval(uiFallbackPollTimer);
    uiFallbackPollTimer = null;
  }
}

function stopUiWsPing() {
  if (uiWsPingTimer) {
    window.clearInterval(uiWsPingTimer);
    uiWsPingTimer = null;
  }
}

function startUiWsPing() {
  stopUiWsPing();
  uiWsPingTimer = window.setInterval(() => {
    if (uiWs && uiWs.readyState === WebSocket.OPEN) {
      try {
        uiWs.send("ping");
      } catch (err) {
        stopUiWsPing();
      }
    }
  }, UI_WS_PING_INTERVAL_MS);
}

function scheduleUiWsReconnect() {
  if (uiWsReconnectTimer) {
    return;
  }
  const delay = uiWsReconnectDelayMs;
  uiWsReconnectDelayMs = Math.min(Math.round(uiWsReconnectDelayMs * 1.5), 30000);
  uiWsReconnectTimer = window.setTimeout(() => {
    uiWsReconnectTimer = null;
    connectUiWs();
  }, delay);
}

function handleUiJobUpdated(payload) {
  const job = payload?.job;
  const jobId = payload?.job_id;
  const stage = payload?.stage;
  const message = payload?.message;

  if (job === "import_romaneio" && romaneioStatusJobId && jobId === romaneioStatusJobId) {
    const modal = createRomaneioStatusModal();
    const progress = ROMANEIO_STAGE_PROGRESS[String(stage)] ?? 0.1;
    modal.update(message || "Processando...", progress);
    return;
  }

  if (job === "post_process_products" && postProcessStatusJobId && jobId === postProcessStatusJobId) {
    const modal = createPostProcessStatusModal();
    const progress = POST_PROCESS_STAGE_PROGRESS[String(stage)] ?? 0.1;
    modal.update(message || "Processando...", progress);
    return;
  }

}

function handleUiWsMessage(raw) {
  if (!raw) {
    return;
  }
  let payload;
  try {
    payload = typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch (err) {
    return;
  }

  const type = payload?.type;
  if (type === "state.changed") {
    scheduleUiScopesRefresh(payload?.scopes);
    return;
  }
  if (type === "job.updated") {
    handleUiJobUpdated(payload);
  }
}

function connectUiWs() {
  if (!window.WebSocket) {
    startUiFallbackPolling();
    return;
  }

  if (uiWs && (uiWs.readyState === WebSocket.OPEN || uiWs.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const wsUrl = buildWsUrl(UI_WS_PATH);
  if (!wsUrl) {
    startUiFallbackPolling();
    scheduleUiWsReconnect();
    return;
  }

  try {
    uiWs = new WebSocket(wsUrl);
  } catch (err) {
    startUiFallbackPolling();
    scheduleUiWsReconnect();
    return;
  }

  uiWs.addEventListener("open", () => {
    uiWsConnected = true;
    uiWsReconnectDelayMs = 1000;
    stopUiFallbackPolling();
    scheduleUiScopesRefresh(["products", "totals", "brands", "automation", "margin"]);
    startUiWsPing();
  });

  uiWs.addEventListener("message", (event) => {
    handleUiWsMessage(event.data);
  });

  uiWs.addEventListener("close", () => {
    uiWsConnected = false;
    stopUiWsPing();
    startUiFallbackPolling();
    scheduleUiWsReconnect();
  });

  uiWs.addEventListener("error", () => {
    uiWsConnected = false;
  });
}

function startUIRealtime() {
  if (uiRealtimeStarted) {
    return;
  }
  uiRealtimeStarted = true;

  startUiFallbackPolling();
  connectUiWs();

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      connectUiWs();
      if (uiPendingScopes.size) {
        scheduleUiScopesRefresh([]);
      }
    }
  });
}


