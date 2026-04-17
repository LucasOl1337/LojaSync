# LojaSync Crawler - Documentação de Instalação

## Status Atual
MVP funcional rodando com urllib básico. Database criado com 3 leads de teste.

## Para Produção (Chrome CDP + Selenium/Playwright)

### 1. Instalar Dependências
```bash
pip3 install selenium playwright beautifulsoup4 requests
playwright install chromium
```

### 2. Configurar Chrome CDP
```bash
# No Windows, lançar Chrome com debugging:
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9333 --user-data-dir="C:\temp\chrome-cdp-profile-general"
```

### 3. Configurar Variáveis de Ambiente
```bash
export BROWSER_CDP_URL="http://localhost:9333"
export LOJASYNC_LEADS_DB="/mnt/c/Users/user/Desktop/LojaSync/automation/leads.db"
```

### 4. Atualizar o Crawler
Substituir as funções simuladas (crawl_google_maps, crawl_instagram) por implementações reais usando Selenium/Playwright com CDP.

## Arquivos Criados
- `lojasync-crawler.py` - Crawler MVP (3 leads gerados)
- `leads.db` - Database SQLite com schema implementado
- `requirements.txt` - Dependências para produção
- `crawler-setup.md` - Este arquivo

## Próximos Passos
1. Instalar dependências (requer sudo)
2. Implementar crawlers reais com Chrome CDP
3. Integrar LLM real para qualificação
4. Escalar para 50-100 leads/dia
