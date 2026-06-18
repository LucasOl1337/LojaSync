import type { KeyboardEvent, RefObject } from "react";

import type { PostProcessResult, PostProcessStatus } from "./types";
import { formatTimestamp } from "./uiFormatting";

export type FormatCodesOptions = {
  remover_primeiros_numeros: string;
  remover_ultimos_numeros: string;
};

export type DescriptionOptions = {
  remover_especiais: boolean;
  remover_numeros: boolean;
  remover_letras: boolean;
  remover_termos: string;
};

type FormatCodesPanelProps = {
  formatCodesOptions: FormatCodesOptions;
  panelRef?: RefObject<HTMLDivElement>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onFormatCodeOptionChange: (field: keyof FormatCodesOptions, value: string) => void;
  onRestoreOriginalCodes: () => Promise<void>;
  onCloseFormatCodesPanel: () => void;
  onFormatCodes: () => Promise<void>;
  onPanelKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
};

export function FormatCodesPanel({
  formatCodesOptions,
  panelRef,
  runBusyAction,
  onFormatCodeOptionChange,
  onRestoreOriginalCodes,
  onCloseFormatCodesPanel,
  onFormatCodes,
  onPanelKeyDown,
}: FormatCodesPanelProps) {
  return (
    <div className="toolConfigPanel" ref={panelRef} onKeyDown={onPanelKeyDown}>
      <div className="toolConfigIntro">
        <strong>Limpar codigos com menos risco</strong>
        <p>Use apenas estas opcoes para cortar numeros do comeco ou do fim do codigo. Se precisar voltar atras, use Restaurar Originais.</p>
      </div>
      <div className="toolConfigGrid">
        <label className="toolField">
          <span>Quantos numeros apagar do comeco</span>
          <input
            value={formatCodesOptions.remover_primeiros_numeros}
            onChange={(event) => onFormatCodeOptionChange("remover_primeiros_numeros", event.target.value.replace(/[^\d]/g, ""))}
            placeholder="Ex.: 2"
          />
        </label>
        <label className="toolField">
          <span>Quantos numeros apagar do final</span>
          <input
            value={formatCodesOptions.remover_ultimos_numeros}
            onChange={(event) => onFormatCodeOptionChange("remover_ultimos_numeros", event.target.value.replace(/[^\d]/g, ""))}
            placeholder="Ex.: 2"
          />
        </label>
      </div>
      <div className="toolConfigActions">
        <button className="ghostButton miniActionButton" type="button" onClick={() => void runBusyAction("restaurar-codigos", onRestoreOriginalCodes)}>
          Restaurar Originais
        </button>
        <button className="ghostButton miniActionButton" type="button" onClick={onCloseFormatCodesPanel}>
          Fechar
        </button>
        <button className="primaryButton miniPrimaryButton" type="button" onClick={() => void runBusyAction("formatar-codigos", onFormatCodes)}>
          Aplicar
        </button>
      </div>
    </div>
  );
}

type DescriptionPanelProps = {
  descriptionOptions: DescriptionOptions;
  panelRef?: RefObject<HTMLDivElement>;
  runBusyAction: (name: string, action: () => Promise<void>) => Promise<void>;
  onDescriptionOptionChange: (field: keyof DescriptionOptions, value: boolean | string) => void;
  onCloseDescriptionPanel: () => void;
  onImproveDescriptions: () => Promise<void>;
  onPanelKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
};

export function DescriptionPanel({
  descriptionOptions,
  panelRef,
  runBusyAction,
  onDescriptionOptionChange,
  onCloseDescriptionPanel,
  onImproveDescriptions,
  onPanelKeyDown,
}: DescriptionPanelProps) {
  return (
    <div className="toolConfigPanel" ref={panelRef} onKeyDown={onPanelKeyDown}>
      <div className="toolConfigGrid">
        <label className="toolCheck">
          <input
            type="checkbox"
            checked={descriptionOptions.remover_especiais}
            onChange={(event) => onDescriptionOptionChange("remover_especiais", event.target.checked)}
          />
          <span>Remover caracteres especiais</span>
        </label>
        <label className="toolCheck">
          <input
            type="checkbox"
            checked={descriptionOptions.remover_numeros}
            onChange={(event) => onDescriptionOptionChange("remover_numeros", event.target.checked)}
          />
          <span>Remover numeros</span>
        </label>
        <label className="toolCheck">
          <input
            type="checkbox"
            checked={descriptionOptions.remover_letras}
            onChange={(event) => onDescriptionOptionChange("remover_letras", event.target.checked)}
          />
          <span>Remover letras</span>
        </label>
        <label className="toolField toolFieldWide">
          <span>Termos para remover, separados por virgula</span>
          <input value={descriptionOptions.remover_termos} onChange={(event) => onDescriptionOptionChange("remover_termos", event.target.value)} />
        </label>
      </div>
      <div className="toolConfigActions">
        <button className="ghostButton miniActionButton" type="button" onClick={onCloseDescriptionPanel}>
          Fechar
        </button>
        <button className="primaryButton miniPrimaryButton" type="button" onClick={() => void runBusyAction("melhorar-descricao", onImproveDescriptions)}>
          Aplicar
        </button>
      </div>
    </div>
  );
}

type PostProcessMessagesProps = {
  postProcessing: boolean;
  postProcessJob: PostProcessStatus | null;
  postProcessError: string | null;
  postProcessResult: PostProcessResult | null;
};

export function PostProcessMessages({
  postProcessing,
  postProcessJob,
  postProcessError,
  postProcessResult,
}: PostProcessMessagesProps) {
  return (
    <>
      {postProcessing ? <div className="message subtle">Revisao com IA em andamento. {postProcessJob?.message || "Preparando itens da lista..."}</div> : null}
      {!postProcessing && postProcessJob?.message ? <div className="message subtle">{postProcessJob.message}</div> : null}
      {postProcessError ? <div className="message error">{postProcessError}</div> : null}
      {postProcessResult ? (
        <div className="message success">
          {postProcessResult.total_itens} itens revisados as {formatTimestamp(postProcessJob?.updated_at)}.
          {postProcessResult.dry_run ? " Modo inicial: sugestoes capturadas sem aplicar automaticamente." : ""}
        </div>
      ) : null}
    </>
  );
}
