import { useEffect, useMemo, useRef, useState } from "react";

import {
  buildAutomaticImportLayout,
  buildImportBatchSummary,
  clampImportRect,
  coerceImportProcessEntries,
  type NormalizedRect,
  type StagedImportDocument,
} from "./importWorkspace";

const TEXT_PREVIEW_LIMIT = 500_000;

type ImportWorkspacePanelProps = {
  documents: StagedImportDocument[];
  busy: boolean;
  activeDocumentId: string | null;
  onDocumentsChange: (documents: StagedImportDocument[]) => void;
  onOpenPicker: (mode: "llm" | "local") => void;
  onRemove: (documentId: string) => void;
  onRetryFailed: () => void;
};

type Interaction = {
  documentId: string;
  mode: "move" | "resize";
  pointerId: number;
  startX: number;
  startY: number;
  startRect: NormalizedRect;
};

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function DocumentPreview({ document, url }: { document: StagedImportDocument; url: string | null }) {
  const [text, setText] = useState("");
  const [textError, setTextError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setText("");
    setTextError(null);
    if (document.previewKind !== "text") return () => { active = false; };
    void document.file.text().then((value) => {
      if (active) setText(value.slice(0, TEXT_PREVIEW_LIMIT));
    }).catch(() => {
      if (active) setTextError("Não foi possível ler a prévia deste texto.");
    });
    return () => { active = false; };
  }, [document.id, document.file, document.previewKind]);

  if (document.previewKind === "image" && url) {
    return <img className="importDocumentImageTs" src={url} alt={`Prévia de ${document.file.name}`} />;
  }
  if (document.previewKind === "pdf" && url) {
    return (
      <object className="importDocumentObjectTs" data={url} type="application/pdf" aria-label={`Prévia de ${document.file.name}`}>
        <p>O navegador não abriu este PDF. <a href={url} target="_blank" rel="noreferrer">Abrir original</a></p>
      </object>
    );
  }
  if (document.previewKind === "text") {
    if (textError) return <div className="importPreviewFallbackTs">{textError}</div>;
    return (
      <div className="importTextPreviewShellTs">
        <pre className="importDocumentTextTs">{text || "Carregando texto..."}</pre>
        {text.length >= TEXT_PREVIEW_LIMIT ? <span>Prévia encurtada; o arquivo original será importado por inteiro.</span> : null}
      </div>
    );
  }
  return (
    <div className="importPreviewFallbackTs">
      <strong>Prévia indisponível</strong>
      <span>O arquivo continua disponível para importação.</span>
      {url ? <a href={url} target="_blank" rel="noreferrer">Abrir original</a> : null}
    </div>
  );
}

export function ImportWorkspacePanel({
  documents,
  busy,
  activeDocumentId,
  onDocumentsChange,
  onOpenPicker,
  onRemove,
  onRetryFailed,
}: ImportWorkspacePanelProps) {
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const interactionRef = useRef<Interaction | null>(null);
  const keyboardStartRectsRef = useRef<Record<string, NormalizedRect>>({});
  const urlsRef = useRef<Record<string, string>>({});
  const [canvasSize, setCanvasSize] = useState({ width: 1, height: 1 });
  const [urls, setUrls] = useState<Record<string, string>>({});
  const summary = buildImportBatchSummary(documents);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const update = () => setCanvasSize({ width: Math.max(canvas.clientWidth, 1), height: Math.max(canvas.clientHeight, 1) });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setUrls((current) => {
      const next: Record<string, string> = {};
      for (const document of documents) {
        if (document.previewKind === "text") continue;
        next[document.id] = current[document.id] || URL.createObjectURL(document.file);
      }
      for (const [id, url] of Object.entries(current)) {
        if (!next[id]) URL.revokeObjectURL(url);
      }
      urlsRef.current = next;
      return next;
    });
  }, [documents]);

  useEffect(() => () => {
    for (const url of Object.values(urlsRef.current)) URL.revokeObjectURL(url);
    urlsRef.current = {};
  }, []);

  const failedCount = useMemo(() => documents.filter((document) => document.state === "failed").length, [documents]);

  const updateRect = (documentId: string, nextRect: NormalizedRect, bringForward = false) => {
    const minimumWidth = Math.min(280 / canvasSize.width, 0.92);
    const minimumHeight = Math.min(180 / canvasSize.height, 0.92);
    const nextZ = bringForward ? Math.max(0, ...documents.map((document) => document.zIndex)) + 1 : 0;
    onDocumentsChange(documents.map((document) => document.id === documentId
      ? { ...document, rect: clampImportRect(nextRect, minimumWidth, minimumHeight), zIndex: nextZ || document.zIndex }
      : document));
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLElement>, document: StagedImportDocument, mode: "move" | "resize") => {
    if (busy || window.matchMedia("(max-width: 720px)").matches) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    interactionRef.current = {
      documentId: document.id,
      mode,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startRect: document.rect,
    };
    updateRect(document.id, document.rect, true);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLElement>) => {
    const interaction = interactionRef.current;
    if (!interaction || interaction.pointerId !== event.pointerId) return;
    const dx = (event.clientX - interaction.startX) / canvasSize.width;
    const dy = (event.clientY - interaction.startY) / canvasSize.height;
    updateRect(interaction.documentId, interaction.mode === "move"
      ? { ...interaction.startRect, x: interaction.startRect.x + dx, y: interaction.startRect.y + dy }
      : { ...interaction.startRect, width: interaction.startRect.width + dx, height: interaction.startRect.height + dy });
  };

  const stopInteraction = (event: React.PointerEvent<HTMLElement>) => {
    if (interactionRef.current?.pointerId === event.pointerId) interactionRef.current = null;
  };

  const handleGeometryKeyDown = (event: React.KeyboardEvent<HTMLElement>, document: StagedImportDocument, mode: "move" | "resize") => {
    const interactionKey = `${document.id}:${mode}`;
    if (event.key === "Escape" && keyboardStartRectsRef.current[interactionKey]) {
      event.preventDefault();
      updateRect(document.id, keyboardStartRectsRef.current[interactionKey], true);
      delete keyboardStartRectsRef.current[interactionKey];
      return;
    }
    const directions: Record<string, [number, number]> = {
      ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1],
    };
    const direction = directions[event.key];
    if (!direction || busy) return;
    event.preventDefault();
    keyboardStartRectsRef.current[interactionKey] ||= document.rect;
    const step = event.shiftKey ? 0.05 : 0.012;
    updateRect(document.id, mode === "move"
      ? { ...document.rect, x: document.rect.x + direction[0] * step, y: document.rect.y + direction[1] * step }
      : { ...document.rect, width: document.rect.width + direction[0] * step, height: document.rect.height + direction[1] * step }, true);
  };

  const stopKeyboardInteraction = (documentId: string, mode: "move" | "resize") => {
    delete keyboardStartRectsRef.current[`${documentId}:${mode}`];
  };

  const resetLayout = () => {
    const layout = buildAutomaticImportLayout(documents.length);
    onDocumentsChange(documents.map((document, index) => ({ ...document, rect: layout[index], zIndex: index + 1 })));
  };

  return (
    <section className="importWorkspaceTs" aria-labelledby="import-workspace-title">
      <header className="importWorkspaceHeaderTs">
        <div>
          <span className="sectionTag">Conferência visual</span>
          <h2 id="import-workspace-title">Notas da importação</h2>
          <p role="status" aria-live="polite">{busy && activeDocumentId ? `Processando ${documents.findIndex((document) => document.id === activeDocumentId) + 1} de ${documents.length}.` : summary.message}</p>
        </div>
        <div className="importWorkspaceActionsTs">
          <button className="ghostButton" type="button" disabled={!documents.length || busy} onClick={resetLayout}>Organizar automaticamente</button>
          <button className="ghostButton" type="button" disabled={busy} onClick={() => onOpenPicker("llm")}>Adicionar com IA</button>
          <button className="ghostButton" type="button" disabled={busy} onClick={() => onOpenPicker("local")}>Adicionar com leitura local</button>
          {failedCount ? <button className="primaryButton" type="button" disabled={busy} onClick={onRetryFailed}>Tentar falhas novamente</button> : null}
        </div>
      </header>
      <div ref={canvasRef} className={`importWorkspaceCanvasTs ${documents.length ? "hasDocuments" : ""}`}>
        {!documents.length ? (
          <div className="importWorkspaceEmptyTs">
            <span className="importWorkspaceEmptyIconTs" aria-hidden="true">⌁</span>
            <strong>Use esta área para conferir a nota</strong>
            <span>Uma nota ocupa todo o painel. Várias notas se dividem automaticamente.</span>
            <small>PDF, imagem ou TXT</small>
            <span className="importWorkspaceEmptyActionsTs">
              <button className="primaryButton" type="button" disabled={busy} onClick={() => onOpenPicker("llm")}>Escolher e importar com IA</button>
              <button className="ghostButton" type="button" disabled={busy} onClick={() => onOpenPicker("local")}>Escolher e usar leitura local</button>
            </span>
          </div>
        ) : documents.map((document) => {
          const processEntries = coerceImportProcessEntries(document.status?.metrics);
          const style = {
            "--document-x": `${document.rect.x * 100}%`,
            "--document-y": `${document.rect.y * 100}%`,
            "--document-width": `${document.rect.width * 100}%`,
            "--document-height": `${document.rect.height * 100}%`,
            zIndex: document.zIndex,
          } as React.CSSProperties;
          return (
            <article key={document.id} className={`importDocumentCardTs state-${document.state} ${document.id === activeDocumentId ? "active" : ""}`} style={style} aria-label={`${document.file.name}, ${document.state}`}>
              <header
                className="importDocumentHeaderTs"
                tabIndex={0}
                aria-label={`Mover ${document.file.name}. Use as setas; Shift e setas movem mais rápido.`}
                onPointerDown={(event) => handlePointerDown(event, document, "move")}
                onPointerMove={handlePointerMove}
                onPointerUp={stopInteraction}
                onPointerCancel={stopInteraction}
                onKeyDown={(event) => handleGeometryKeyDown(event, document, "move")}
                onBlur={() => stopKeyboardInteraction(document.id, "move")}
              >
                <div><strong title={document.file.name}>{document.file.name}</strong><span>{formatFileSize(document.file.size)}</span></div>
                <span className="importDocumentStateTs">{document.state === "processing" ? "Importando" : document.state === "succeeded" ? "Importada" : document.state === "failed" ? "Bloqueada" : document.state === "queued" ? "Na fila" : "Pronta"}</span>
                <button type="button" disabled={busy} onClick={(event) => { event.stopPropagation(); onRemove(document.id); }} aria-label={`Remover ${document.file.name}`}>×</button>
              </header>
              <div className="importDocumentBodyTs"><DocumentPreview document={document} url={urls[document.id] || null} /></div>
              {document.errorReasons.length ? (
                <section className="importDocumentErrorTs" role="alert">
                  <strong>Importação bloqueada</strong>
                  <ul>{document.errorReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                  <span>Este documento não alterou o catálogo.</span>
                  {processEntries.length ? <details><summary>Detalhes técnicos</summary><ol>{processEntries.map((entry) => <li key={`${entry.index}-${entry.message}`}>{entry.message}</li>)}</ol></details> : null}
                </section>
              ) : null}
              <span
                className="importDocumentResizeTs"
                role="separator"
                tabIndex={0}
                aria-label={`Redimensionar ${document.file.name}. Use as setas; Shift e setas redimensionam mais rápido.`}
                onPointerDown={(event) => handlePointerDown(event, document, "resize")}
                onPointerMove={handlePointerMove}
                onPointerUp={stopInteraction}
                onPointerCancel={stopInteraction}
                onKeyDown={(event) => handleGeometryKeyDown(event, document, "resize")}
                onBlur={() => stopKeyboardInteraction(document.id, "resize")}
              />
            </article>
          );
        })}
      </div>
    </section>
  );
}
