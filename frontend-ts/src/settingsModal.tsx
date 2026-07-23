import { useEffect, useRef, type KeyboardEvent } from "react";

import {
  AUTOMATION_TARGET_FIELDS,
  GRADE_CAPTURE_FIELDS,
  type AutomationTargetKey,
  type GradeCaptureKey,
} from "./appConfig";
import { parseSizeOrderText } from "./gradeLogic";
import { WALLPAPER_CATALOG } from "./shellAppearance";
import type { ThemeColors, ThemeOpacities } from "./shellTheme";
import { ThemeColorEditor } from "./themeColorEditor";
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
  appearanceWallpaper: string;
  appearanceBrightness: number;
  themeColors: ThemeColors;
  themeOpacities: ThemeOpacities;
  layoutMode?: "modal" | "page";
  onClose?: () => void;
  onContextRefresh: () => Promise<void>;
  onPrepare: () => Promise<void>;
  onReloadAll: () => Promise<void>;
  onSaveTargets: () => Promise<void>;
  onSaveGradeConfig: () => Promise<void>;
  onSaveAppearance: () => Promise<void>;
  onAppearanceWallpaperChange: (path: string) => void;
  onAppearanceBrightnessChange: (value: number) => void;
  onUseAppAppearanceDefault: () => void;
  onThemeColorsChange: (colors: ThemeColors) => void;
  onThemeOpacitiesChange: (opacities: ThemeOpacities) => void;
  onThemeMessage?: (message: string) => void;
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

type SettingsAppearancePanelProps = Pick<
  SettingsModalProps,
  | "saving"
  | "appearanceWallpaper"
  | "appearanceBrightness"
  | "onSaveAppearance"
  | "onAppearanceWallpaperChange"
  | "onAppearanceBrightnessChange"
  | "onUseAppAppearanceDefault"
>;

function SettingsAppearancePanel({
  saving,
  appearanceWallpaper,
  appearanceBrightness,
  onSaveAppearance,
  onAppearanceWallpaperChange,
  onAppearanceBrightnessChange,
  onUseAppAppearanceDefault,
}: SettingsAppearancePanelProps) {
  return (
    <section className="settingsPanel settingsAppearancePanel">
      <div className="settingsPanelHead">
        <div>
          <span className="sectionTag">Visual</span>
          <strong>Plano de fundo do app</strong>
        </div>
        <div className="settingsAppearanceActions">
          <button
            className="ghostButton miniActionButton"
            type="button"
            onClick={onUseAppAppearanceDefault}
            disabled={Boolean(saving)}
          >
            Usar padrão
          </button>
          <button
            className="ghostButton miniActionButton"
            type="button"
            onClick={() => void onSaveAppearance()}
            disabled={saving === "appearance"}
          >
            {saving === "appearance" ? "Salvando..." : "Salvar como padrão global"}
          </button>
        </div>
      </div>
      <p className="settingsAppearanceHint">
        Admin define o default para todos os usuários desta instalação. Cada browser ainda pode
        escolher um fundo pessoal; quem não escolheu usa o padrão global.
      </p>
      <label className="settingsField">
        <span>Brilho do padrão</span>
        <input
          type="range"
          min={0.55}
          max={1}
          step={0.01}
          value={appearanceBrightness}
          onChange={(event) => onAppearanceBrightnessChange(Number(event.target.value))}
        />
        <span>{Math.round(appearanceBrightness * 100)}%</span>
      </label>
      <div className="settingsWallpaperGrid" role="listbox" aria-label="Fundos disponíveis">
        {WALLPAPER_CATALOG.map((wall) => {
          const on = wall.path === appearanceWallpaper;
          return (
            <button
              key={wall.path}
              type="button"
              className={on ? "settingsWallpaperCard is-on" : "settingsWallpaperCard"}
              role="option"
              aria-selected={on}
              onClick={() => onAppearanceWallpaperChange(wall.path)}
            >
              <span
                className="settingsWallpaperThumb"
                style={{ backgroundImage: `url(${wall.path})` }}
              />
              <span className="settingsWallpaperMeta">
                <strong>{wall.label}</strong>
                <em>{wall.blurb}</em>
              </span>
              {on ? <span className="settingsWallpaperCheck">✓</span> : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SettingsTargetsPanel({
  saving,
  targets,
  onSaveTargets,
  onTargetChange,
  onCaptureTarget,
}: SettingsTargetsPanelProps) {
  return (
    <section className="settingsPanel settingsTargetsPanel">
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
        <span>Título da janela</span>
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
    <section className="settingsPanel settingsGradePanel">
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
          <span>Índice do modelo</span>
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
            <strong>Primeira célula da grade</strong>
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
        <span>Ordem ERP usada pela automação</span>
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
    <section className="settingsPanel settingsPanelWide settingsDiagnosticsPanel">
      <div className="settingsPanelHead">
        <div>
          <span className="sectionTag">Diagnóstico</span>
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
      <pre className="settingsContextBlock">{contextText || "Use 'Ver contexto' ou 'Preparar ByteEmpresa' para carregar diagnóstico."}</pre>
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
  appearanceWallpaper,
  appearanceBrightness,
  themeColors,
  themeOpacities,
  layoutMode = "modal",
  onClose,
  onContextRefresh,
  onPrepare,
  onReloadAll,
  onSaveTargets,
  onSaveGradeConfig,
  onSaveAppearance,
  onAppearanceWallpaperChange,
  onAppearanceBrightnessChange,
  onUseAppAppearanceDefault,
  onThemeColorsChange,
  onThemeOpacitiesChange,
  onThemeMessage,
  onTargetChange,
  onGradeConfigChange,
  onCaptureTarget,
  onCaptureGradeButton,
  onCaptureFirstQuantCell,
}: SettingsModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLElement>(null);
  const isPage = layoutMode === "page";

  useEffect(() => {
    if (isPage) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus({ preventScroll: true });

    return () => {
      previousFocus?.focus({ preventScroll: true });
    };
  }, [isPage]);

  const handleShellKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (isPage) return;
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose?.();
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

  const body = (
    <>
      <header className="settingsModalHeader">
        <div>
          <span className="sectionTag">Configurações</span>
          <h3 id="settings-modal-title">{isPage ? "Preferências do app" : "Targets, gradebot e diagnóstico"}</h3>
          {isPage ? <p className="settingsPageLeadTs">Visual, cores, automação e diagnóstico em um só lugar.</p> : null}
        </div>
        <div className="settingsModalHeaderActions">
          <button className="ghostButton miniActionButton" type="button" onClick={() => void onContextRefresh()} disabled={Boolean(saving)}>
            Ver contexto
          </button>
          <button className="ghostButton miniActionButton" type="button" onClick={() => void onPrepare()} disabled={Boolean(saving)}>
            Preparar ByteEmpresa
          </button>
          {!isPage ? (
            <button
              ref={closeButtonRef}
              className="ghostButton miniActionButton settingsModalCloseButton"
              type="button"
              onClick={() => onClose?.()}
              aria-label="Fechar configurações"
            >
              Fechar
            </button>
          ) : null}
        </div>
      </header>

      <div className={isPage ? "settingsPageBodyTs" : "settingsModalBody"}>
        {isPage ? (
          <>
            <div className="settingsPageColTs">
              <SettingsAppearancePanel
                saving={saving}
                appearanceWallpaper={appearanceWallpaper}
                appearanceBrightness={appearanceBrightness}
                onSaveAppearance={onSaveAppearance}
                onAppearanceWallpaperChange={onAppearanceWallpaperChange}
                onAppearanceBrightnessChange={onAppearanceBrightnessChange}
                onUseAppAppearanceDefault={onUseAppAppearanceDefault}
              />
              <ThemeColorEditor
                colors={themeColors}
                opacities={themeOpacities}
                onChange={onThemeColorsChange}
                onOpacitiesChange={onThemeOpacitiesChange}
                onSaved={onThemeMessage}
              />
            </div>
            <div className="settingsPageColTs">
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
          </>
        ) : (
          <>
            <SettingsAppearancePanel
              saving={saving}
              appearanceWallpaper={appearanceWallpaper}
              appearanceBrightness={appearanceBrightness}
              onSaveAppearance={onSaveAppearance}
              onAppearanceWallpaperChange={onAppearanceWallpaperChange}
              onAppearanceBrightnessChange={onAppearanceBrightnessChange}
              onUseAppAppearanceDefault={onUseAppAppearanceDefault}
            />
            <ThemeColorEditor
              colors={themeColors}
              opacities={themeOpacities}
              onChange={onThemeColorsChange}
              onOpacitiesChange={onThemeOpacitiesChange}
              onSaved={onThemeMessage}
            />
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
          </>
        )}
      </div>
    </>
  );

  if (isPage) {
    return (
      <section
        ref={modalRef}
        className="settingsPageShellTs"
        aria-labelledby="settings-modal-title"
      >
        {body}
      </section>
    );
  }

  return (
    <div className="settingsModalBackdrop" onClick={() => onClose?.()}>
      <section
        ref={modalRef}
        className="settingsModalShell"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-modal-title"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleShellKeyDown}
      >
        {body}
      </section>
    </div>
  );
}
