import { useEffect, useRef, type KeyboardEvent } from "react";

import {
  AUTOMATION_TARGET_FIELDS,
  GRADE_CAPTURE_FIELDS,
  type AutomationTargetKey,
  type GradeCaptureKey,
} from "./appConfig";
import { parseSizeOrderText } from "./gradeLogic";
import type { AutomationTargets, GradeConfig, TargetPoint } from "./types";
import { formatTargetPoint, normalizeTargetPoint } from "./uiFormatting";

type SettingsModalProps = {
  loading: boolean;
  saving: string | null;
  error: string | null;
  message: string | null;
  targets: AutomationTargets;
  gradeConfig: GradeConfig;
  contextText: string;
  captureLabel: string | null;
  captureCountdown: number | null;
  onClose: () => void;
  onContextRefresh: () => Promise<void>;
  onPrepare: () => Promise<void>;
  onReloadAll: () => Promise<void>;
  onSaveTargets: () => Promise<void>;
  onSaveGradeConfig: () => Promise<void>;
  onTargetChange: (key: keyof AutomationTargets, value: string | TargetPoint | null) => void;
  onGradeConfigChange: (updater: (current: GradeConfig) => GradeConfig) => void;
  onCaptureTarget: (key: AutomationTargetKey, label: string) => Promise<void>;
  onCaptureGradeButton: (key: GradeCaptureKey, label: string) => Promise<void>;
  onCaptureFirstQuantCell: () => Promise<void>;
};

type SettingsTargetsPanelProps = Pick<
  SettingsModalProps,
  "saving" | "targets" | "onSaveTargets" | "onTargetChange" | "onCaptureTarget"
>;

type SettingsGradeConfigPanelProps = Pick<
  SettingsModalProps,
  "saving" | "gradeConfig" | "onSaveGradeConfig" | "onGradeConfigChange" | "onCaptureGradeButton" | "onCaptureFirstQuantCell"
>;

type SettingsDiagnosticsPanelProps = Pick<
  SettingsModalProps,
  "loading" | "saving" | "error" | "message" | "contextText" | "captureLabel" | "captureCountdown" | "onReloadAll"
>;

function SettingsTargetsPanel({
  saving,
  targets,
  onSaveTargets,
  onTargetChange,
  onCaptureTarget,
}: SettingsTargetsPanelProps) {
  return (
    <section className="settingsPanel">
      <div className="settingsPanelHead">
        <div>
          <span className="sectionTag">Cadastro</span>
          <strong>Targets do PyAutoGUI</strong>
        </div>
        <button className="ghostButton miniActionButton" type="button" onClick={() => void onSaveTargets()} disabled={saving === "targets"}>
          {saving === "targets" ? "Salvando..." : "Salvar targets"}
        </button>
      </div>
      <label className="settingsField">
        <span>Titulo da janela</span>
        <input
          value={targets.title || ""}
          onChange={(event) => onTargetChange("title", event.target.value)}
          placeholder="Byte Empresa - 1 - NAPASSARELA"
        />
      </label>
      <div className="settingsTargetList">
        {AUTOMATION_TARGET_FIELDS.map((field) => (
          <div key={field.key} className="settingsTargetRow">
            <div>
              <strong>{field.label}</strong>
              <span>{formatTargetPoint((targets[field.key] as TargetPoint | null | undefined) || null)}</span>
            </div>
            <button
              className="ghostButton miniActionButton"
              type="button"
              onClick={() => void onCaptureTarget(field.key, field.label)}
              disabled={Boolean(saving)}
            >
              {saving === `capture-target-${field.key}` ? "Capturando..." : "Capturar"}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function SettingsGradeConfigPanel({
  saving,
  gradeConfig,
  onSaveGradeConfig,
  onGradeConfigChange,
  onCaptureGradeButton,
  onCaptureFirstQuantCell,
}: SettingsGradeConfigPanelProps) {
  return (
    <section className="settingsPanel">
      <div className="settingsPanelHead">
        <div>
          <span className="sectionTag">Gradebot</span>
          <strong>Coordenadas e ordem ERP</strong>
        </div>
        <button className="ghostButton miniActionButton" type="button" onClick={() => void onSaveGradeConfig()} disabled={saving === "grade-config"}>
          {saving === "grade-config" ? "Salvando..." : "Salvar grades"}
        </button>
      </div>
      <div className="settingsFormGrid">
        <label className="settingsField">
          <span>Altura da linha</span>
          <input
            value={gradeConfig.row_height ?? ""}
            onChange={(event) => onGradeConfigChange((current) => ({
              ...current,
              row_height: Number.parseInt(event.target.value.replace(/[^\d]/g, ""), 10) || null,
            }))}
            placeholder="44"
          />
        </label>
        <label className="settingsField">
          <span>Indice do modelo</span>
          <input
            value={gradeConfig.model_index ?? ""}
            onChange={(event) => onGradeConfigChange((current) => ({
              ...current,
              model_index: Number.parseInt(event.target.value.replace(/[^\d]/g, ""), 10) || null,
            }))}
            placeholder="1"
          />
        </label>
        <label className="settingsField">
          <span>Hotkey do modelo</span>
          <input
            value={gradeConfig.model_hotkey || ""}
            onChange={(event) => onGradeConfigChange((current) => ({ ...current, model_hotkey: event.target.value }))}
            placeholder="f6"
          />
        </label>
        <div className="settingsTargetRow compact">
          <div>
            <strong>Primeira celula da grade</strong>
            <span>{formatTargetPoint(gradeConfig.first_quant_cell)}</span>
          </div>
          <button className="ghostButton miniActionButton" type="button" onClick={() => void onCaptureFirstQuantCell()} disabled={Boolean(saving)}>
            {saving === "capture-first-quant" ? "Capturando..." : "Capturar"}
          </button>
        </div>
      </div>
      <div className="settingsTargetList">
        {GRADE_CAPTURE_FIELDS.map((field) => (
          <div key={field.key} className="settingsTargetRow">
            <div>
              <strong>{field.label}</strong>
              <span>{formatTargetPoint(normalizeTargetPoint(gradeConfig.buttons?.[field.key]))}</span>
            </div>
            <button
              className="ghostButton miniActionButton"
              type="button"
              onClick={() => void onCaptureGradeButton(field.key, field.label)}
              disabled={Boolean(saving)}
            >
              {saving === `capture-grade-${field.key}` ? "Capturando..." : "Capturar"}
            </button>
          </div>
        ))}
      </div>
      <label className="settingsField">
        <span>Ordem ERP usada pela automacao</span>
        <textarea
          value={(gradeConfig.erp_size_order || []).join(", ")}
          onChange={(event) => onGradeConfigChange((current) => ({
            ...current,
            erp_size_order: parseSizeOrderText(event.target.value),
          }))}
          placeholder="P, M, G, GG, 34, 36, 38"
        />
      </label>
    </section>
  );
}

function SettingsDiagnosticsPanel({
  loading,
  saving,
  error,
  message,
  contextText,
  captureLabel,
  captureCountdown,
  onReloadAll,
}: SettingsDiagnosticsPanelProps) {
  return (
    <section className="settingsPanel settingsPanelWide">
      <div className="settingsPanelHead">
        <div>
          <span className="sectionTag">Diagnostico</span>
          <strong>Contexto atual do ByteEmpresa</strong>
        </div>
        <button className="ghostButton miniActionButton" type="button" onClick={() => void onReloadAll()} disabled={loading || Boolean(saving)}>
          {loading ? "Atualizando..." : "Recarregar tudo"}
        </button>
      </div>
      {captureCountdown ? (
        <div className="message subtle">
          Capturando <strong>{captureLabel}</strong> em {captureCountdown}s...
        </div>
      ) : null}
      {message ? <div className="message success">{message}</div> : null}
      {error ? <div className="message error">{error}</div> : null}
      <pre className="settingsContextBlock">{contextText || "Use 'Ver contexto' ou 'Preparar ByteEmpresa' para carregar diagnostico."}</pre>
    </section>
  );
}

export function SettingsModal({
  loading,
  saving,
  error,
  message,
  targets,
  gradeConfig,
  contextText,
  captureLabel,
  captureCountdown,
  onClose,
  onContextRefresh,
  onPrepare,
  onReloadAll,
  onSaveTargets,
  onSaveGradeConfig,
  onTargetChange,
  onGradeConfigChange,
  onCaptureTarget,
  onCaptureGradeButton,
  onCaptureFirstQuantCell,
}: SettingsModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus({ preventScroll: true });

    return () => {
      previousFocus?.focus({ preventScroll: true });
    };
  }, []);

  const handleShellKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const focusable = Array.from(
      modalRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    ).filter((element) => element.offsetParent !== null);

    if (focusable.length === 0) {
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
    <div className="settingsModalBackdrop" onClick={onClose}>
      <section
        ref={modalRef}
        className="settingsModalShell"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-modal-title"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleShellKeyDown}
      >
        <header className="settingsModalHeader">
          <div>
            <span className="sectionTag">Configuracoes</span>
            <h3 id="settings-modal-title">Targets, gradebot e diagnostico</h3>
          </div>
          <div className="settingsModalHeaderActions">
            <button className="ghostButton miniActionButton" type="button" onClick={() => void onContextRefresh()} disabled={Boolean(saving)}>
              Ver contexto
            </button>
            <button className="ghostButton miniActionButton" type="button" onClick={() => void onPrepare()} disabled={Boolean(saving)}>
              Preparar ByteEmpresa
            </button>
            <button
              ref={closeButtonRef}
              className="ghostButton miniActionButton settingsModalCloseButton"
              type="button"
              onClick={onClose}
              aria-label="Fechar configuracoes"
            >
              Fechar
            </button>
          </div>
        </header>

        <div className="settingsModalBody">
          <SettingsTargetsPanel
            saving={saving}
            targets={targets}
            onSaveTargets={onSaveTargets}
            onTargetChange={onTargetChange}
            onCaptureTarget={onCaptureTarget}
          />
          <SettingsGradeConfigPanel
            saving={saving}
            gradeConfig={gradeConfig}
            onSaveGradeConfig={onSaveGradeConfig}
            onGradeConfigChange={onGradeConfigChange}
            onCaptureGradeButton={onCaptureGradeButton}
            onCaptureFirstQuantCell={onCaptureFirstQuantCell}
          />
          <SettingsDiagnosticsPanel
            loading={loading}
            saving={saving}
            error={error}
            message={message}
            contextText={contextText}
            captureLabel={captureLabel}
            captureCountdown={captureCountdown}
            onReloadAll={onReloadAll}
          />
        </div>
      </section>
    </div>
  );
}
