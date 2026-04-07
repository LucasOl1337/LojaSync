# LojaSync

Plataforma para cadastro e automacao de produtos em ERP, com foco em fluxo de romaneio e nota fiscal, consolidacao de grades e execucao assistida por backend web com automacao desktop.

---

## Visao Geral

O LojaSync e um sistema desktop-web projetado para lojistas que precisam cadastrar grandes volumes de produtos no Byte Empresa. Ele combina painel web, processamento de documentos e automacao desktop para reduzir trabalho manual.

### O que o sistema faz

- Importacao automatica de romaneios
- Gestao de produtos em lote
- Extracao e consolidacao de grades
- Automacao de cadastro no ERP
- GradeBot para preenchimento de grades
- Metricas operacionais

---

## Estrutura

```text
LojaSync/
|- launcher.py
|- Iniciar LojaSync.bat
|- patchatt.bat
|- app/
|- data/
|- docs/
`- Legacy/
```

### Inicializacao rapida

```bat
Iniciar LojaSync.bat
```

O iniciador tenta usar o Python da maquina; se faltar ambiente, cria uma `.venv` local e instala as dependencias necessarias.

Ou manualmente:

```bat
py launcher.py
```

---

## Como executar manualmente

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python launcher.py
```

---

## URLs padrao

- Frontend principal: `http://127.0.0.1:8800`
- Backend: `http://127.0.0.1:8800`
- Frontend legado: `http://127.0.0.1:8800/legacy/`
- Swagger: `http://127.0.0.1:8800/docs`
- LLM Monitor: `http://127.0.0.1:5174`

---

## Atualizacao rapida

Para atualizar um PC que ja tenha o repositorio clonado:

```bat
patchatt.bat
```

O script valida se a pasta e um repositorio Git, checa se ha alteracoes locais e faz `git pull --ff-only origin main`.

---

## Observacoes

- O projeto deve refletir o estado validado localmente.
- Dados operacionais ficam em `data/`.
- A automacao desktop depende de Windows e PyAutoGUI.
- O frontend novo em TypeScript e o principal da aplicacao. O legado permanece disponivel em `/legacy/`.
