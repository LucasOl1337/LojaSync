from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang=\"pt-BR\">
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>LLM3 Chat</title>
        <style>
          :root {
            color-scheme: light dark;
            font-family: \"Inter\", system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
          }
          body {
            margin: 0;
            padding: 0;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            justify-content: center;
            min-height: 100vh;
          }
          .container {
            width: min(720px, 90vw);
            padding: 32px;
            margin: 48px 0;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            box-shadow: 0 30px 60px rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(18px);
          }
          h1 {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
          }
          .status-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 1.2rem;
            padding: 8px 12px;
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.5);
            font-size: 0.875rem;
          }
          .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ef4444;
          }
          .status-indicator.connected {
            background: #22c55e;
            box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
          }
          .status-text {
            color: #94a3b8;
          }
          .mode-selector {
            margin-bottom: 1rem;
            display: flex;
            gap: 12px;
          }
          .mode-option {
            padding: 10px 14px;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            background: rgba(15, 23, 42, 0.6);
            color: #cbd5f5;
            font-size: 0.95rem;
            cursor: pointer;
            transition: border-color 0.2s ease, background 0.2s ease;
          }
          .mode-option.active {
            border-color: #38bdf8;
            background: rgba(14, 165, 233, 0.2);
            color: #e0f2fe;
          }
          .mode-option input {
            display: none;
          }
          .mode-description {
            font-size: 0.85rem;
            color: #94a3b8;
            margin-top: 4px;
          }
          .attachments {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 1rem;
          }
          .upload-label {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 10px 16px;
            border-radius: 12px;
            background: rgba(148, 163, 184, 0.1);
            border: 1px dashed rgba(148, 163, 184, 0.3);
            cursor: pointer;
            color: #cbd5f5;
            font-size: 0.95rem;
            width: fit-content;
          }
          .upload-label:hover {
            border-color: rgba(148, 163, 184, 0.6);
          }
          .attachment-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
          }
          .attachment-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 12px;
            border-radius: 9999px;
            background: rgba(148, 163, 184, 0.2);
            font-size: 0.85rem;
            color: #e2e8f0;
          }
          .attachment-remove {
            border: none;
            background: transparent;
            color: #94a3b8;
            cursor: pointer;
            padding: 0;
            font-size: 1rem;
          }
          .attachment-remove:hover {
            color: #f87171;
          }
          #chat-log {
            height: 360px;
            overflow-y: auto;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.15);
            padding: 16px;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
            gap: 12px;
            background: rgba(15, 23, 42, 0.6);
          }
          .message {
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 85%;
            white-space: pre-wrap;
            line-height: 1.5;
          }
          .user {
            align-self: flex-end;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
          }
          .assistant {
            align-self: flex-start;
            background: rgba(148, 163, 184, 0.15);
          }
          form {
            display: flex;
            gap: 12px;
          }
          textarea {
            flex: 1;
            border-radius: 12px;
            padding: 14px 16px;
            border: 1px solid rgba(148, 163, 184, 0.25);
            resize: vertical;
            min-height: 72px;
            background: rgba(15, 23, 42, 0.5);
            color: inherit;
          }
          button {
            border: none;
            border-radius: 12px;
            padding: 14px 24px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            background: linear-gradient(135deg, #22d3ee, #0ea5e9);
            color: #0f172a;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
          }
          button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }
          button:not(:disabled):hover {
            transform: translateY(-1px);
            box-shadow: 0 15px 30px rgba(14, 165, 233, 0.35);
          }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>LLM3 · Qwen3.5 Cloud</h1>
          <div class="status-bar">
            <div class="status-indicator" id="status-dot"></div>
            <span class="status-text" id="status-text">Verificando conexão...</span>
          </div>
          <div class="mode-selector" id="mode-selector">
            <label class="mode-option active" data-mode="default">
              <input type="radio" name="mode" value="default" checked>
              Conversa livre
              <div class="mode-description">Envie prompts personalizados.</div>
            </label>
            <label class="mode-option" data-mode="romaneio_extractor">
              <input type="radio" name="mode" value="romaneio_extractor">
              Extrator de romaneio
              <div class="mode-description">Extrai produtos (Código, Descrição, Quantidade, Preço, Total) e salva .txt na área de trabalho.</div>
            </label>
          </div>
          <div class="attachments">
            <label class="upload-label" for="file-input">
              <span>Anexar imagens / textos / PDFs</span>
            </label>
            <input type="file" id="file-input" multiple accept="image/*,.txt,.pdf" hidden>
            <div class="attachment-list" id="attachment-list"></div>
          </div>
          <div id="chat-log"></div>
          <form id="chat-form">
            <textarea id="user-input" placeholder="Digite sua mensagem..." required></textarea>
            <button type="submit">Enviar</button>
          </form>
        </div>
        <script>
          const form = document.getElementById('chat-form');
          const input = document.getElementById('user-input');
          const log = document.getElementById('chat-log');
          const statusDot = document.getElementById('status-dot');
          const statusText = document.getElementById('status-text');
          const fileInput = document.getElementById('file-input');
          const attachmentList = document.getElementById('attachment-list');
          const modeSelector = document.getElementById('mode-selector');

          let uploadedImages = [];
          let uploadedDocuments = [];
          let currentMode = 'default';

          modeSelector.addEventListener('change', (event) => {
            const selected = event.target.closest('.mode-option');
            if (!selected) return;
            currentMode = selected.dataset.mode;
            for (const option of modeSelector.querySelectorAll('.mode-option')) {
              option.classList.toggle('active', option === selected);
            }
            if (currentMode === 'romaneio_extractor') {
              input.placeholder = 'Anexe romaneio e envie observações adicionais (opcional)';
            } else {
              input.placeholder = 'Digite sua mensagem...';
            }
          });

          async function checkStatus() {
            try {
              const response = await fetch('/api/status');
              const data = await response.json();
              if (data.connected) {
                statusDot.classList.add('connected');
                statusText.textContent = `Conectado: ${data.model}`;
              } else if (data.ollama_running) {
                statusDot.classList.remove('connected');
                statusText.textContent = `Ollama ativo, modelo ${data.model} não encontrado`;
              } else {
                statusDot.classList.remove('connected');
                statusText.textContent = 'Ollama não está rodando';
              }
            } catch (error) {
              statusDot.classList.remove('connected');
              statusText.textContent = 'Erro ao verificar status';
            }
          }

          checkStatus();
          setInterval(checkStatus, 10000);

          function renderAttachments() {
            attachmentList.innerHTML = '';
            [...uploadedImages.map((image, index) => ({ ...image, type: 'image', index })),
             ...uploadedDocuments.map((document, index) => ({ ...document, type: 'document', index }))]
              .forEach((file) => {
                const pill = document.createElement('div');
                pill.classList.add('attachment-pill');
                const label = document.createElement('span');
                label.textContent = file.type === 'image' ? `🖼️ ${file.name}` : `📄 ${file.name}`;
                const remove = document.createElement('button');
                remove.type = 'button';
                remove.classList.add('attachment-remove');
                remove.textContent = '×';
                remove.addEventListener('click', () => {
                  if (file.type === 'image') {
                    uploadedImages.splice(file.index, 1);
                  } else {
                    uploadedDocuments.splice(file.index, 1);
                  }
                  renderAttachments();
                });
                pill.appendChild(label);
                pill.appendChild(remove);
                attachmentList.appendChild(pill);
              });
          }

          fileInput.addEventListener('change', async (event) => {
            if (!event.target.files.length) return;

            const formData = new FormData();
            for (const file of event.target.files) {
              formData.append('files', file);
            }

            try {
              const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
              });
              if (!response.ok) {
                throw new Error(await response.text());
              }
              const data = await response.json();
              if (data.images) {
                uploadedImages = uploadedImages.concat(data.images);
              }
              if (data.documents) {
                uploadedDocuments = uploadedDocuments.concat(data.documents);
              }
              renderAttachments();
              if (data.errors && data.errors.length) {
                appendMessage('assistant', 'Upload parcialmente concluído: ' + data.errors.join('; '));
              }
            } catch (error) {
              appendMessage('assistant', 'Erro no upload: ' + error.message);
            } finally {
              fileInput.value = '';
            }
          });

          function appendMessage(role, text) {
            const div = document.createElement('div');
            div.classList.add('message', role);
            div.textContent = text.trim();
            log.appendChild(div);
            log.scrollTop = log.scrollHeight;
          }

          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const text = input.value.trim();
            if (!text) return;

            appendMessage('user', text);
            input.value = '';
            input.disabled = true;
            form.querySelector('button').disabled = true;

            try {
              const payload = {
                message: text,
                mode: currentMode,
                images: uploadedImages,
                documents: uploadedDocuments,
              };

              const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
              });
              if (!response.ok) {
                throw new Error(await response.text());
              }
              const data = await response.json();
              appendMessage('assistant', data.content || '[sem resposta]');
              if (data.saved_file) {
                appendMessage('assistant', `Arquivo salvo em: ${data.saved_file}`);
              }
              uploadedImages = [];
              uploadedDocuments = [];
              renderAttachments();
            } catch (error) {
              appendMessage('assistant', 'Erro: ' + error.message);
              checkStatus();
            } finally {
              input.disabled = false;
              form.querySelector('button').disabled = false;
              input.focus();
            }
          });
        </script>
      </body>
    </html>
    """
