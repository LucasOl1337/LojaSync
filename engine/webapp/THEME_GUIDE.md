# 🎨 Guia do Sistema de Temas LojaSync

## 📁 Arquivos Criados

- **`theme.css`** - Variáveis CSS e estilos base
- **`theme.js`** - Controlador JavaScript para alterações dinâmicas
- **`THEME_GUIDE.md`** - Este guia (você está aqui!)

## ✅ Vantagens do Sistema

✔️ **Não afeta mecânicas** - Zero impacto no funcionamento do programa  
✔️ **Centralizado** - Todas as customizações em um único lugar  
✔️ **Reutilizável** - Variáveis CSS usadas em toda a aplicação  
✔️ **Dinâmico** - Controle via JavaScript em tempo real  
✔️ **Persistente** - Configurações salvas no navegador  

---

## 🎯 Uso Básico

### **1. Alterar Cores Principais**

Edite o arquivo `theme.css`, seção `:root`:

```css
:root {
  /* Mudar cor primária de roxo para azul */
  --color-primary: #3b82f6;  /* Era: #8b5cf6 */
  
  /* Mudar cor de sucesso */
  --color-success: #22c55e;  /* Era: #10b981 */
}
```

💾 **Salve o arquivo** → Recarregue a página (F5)

---

### **2. Ajustar Espaçamento**

Quer um layout mais compacto ou espaçoso?

```css
:root {
  /* Layout compacto (valores menores) */
  --spacing-1: 6px;   /* Era: 8px */
  --spacing-2: 12px;  /* Era: 16px */
  --spacing-3: 18px;  /* Era: 24px */
  
  /* OU Layout espaçoso (valores maiores) */
  --spacing-1: 10px;  /* Era: 8px */
  --spacing-2: 20px;  /* Era: 16px */
  --spacing-3: 30px;  /* Era: 24px */
}
```

---

### **3. Mudar Tamanho de Fonte**

```css
:root {
  /* Fontes maiores */
  --font-size-base: 16px;  /* Era: 14px */
  --font-size-lg: 18px;    /* Era: 16px */
  
  /* Fontes menores */
  --font-size-base: 13px;  /* Era: 14px */
  --font-size-sm: 11px;    /* Era: 12px */
}
```

---

### **4. Alterar Arredondamento (Border Radius)**

```css
:root {
  /* Cantos mais retos */
  --radius-md: 4px;   /* Era: 8px */
  --radius-lg: 6px;   /* Era: 12px */
  
  /* Cantos mais arredondados */
  --radius-md: 12px;  /* Era: 8px */
  --radius-lg: 16px;  /* Era: 12px */
}
```

---

### **5. Customizar Componentes Específicos**

#### Botões
```css
:root {
  /* Botões maiores */
  --button-height-md: 48px;  /* Era: 40px */
  --button-padding-x: 24px;  /* Era: 16px */
}
```

#### Tabela
```css
:root {
  /* Linhas mais altas */
  --table-row-height: 56px;        /* Era: 48px */
  --table-cell-padding: 16px 20px; /* Era: 14px 16px */
}
```

#### Inputs
```css
:root {
  /* Inputs maiores */
  --input-height: 48px;             /* Era: 40px */
  --input-padding: 14px 18px;       /* Era: 12px 16px */
}
```

---

## 🚀 Uso Avançado (JavaScript)

### **Console do Navegador (F12)**

Abra o console do navegador e use os comandos:

#### **Alternar Tema Claro/Escuro**
```javascript
LojaSync.theme.toggleTheme()
```

#### **Aplicar Temas Pré-definidos**
```javascript
// Tema azul
LojaSync.applyThemePreset('blue')

// Tema verde
LojaSync.applyThemePreset('green')

// Tema laranja
LojaSync.applyThemePreset('orange')

// Tema rosa
LojaSync.applyThemePreset('pink')

// Tema ciano
LojaSync.applyThemePreset('cyan')

// Voltar ao padrão (roxo)
LojaSync.applyThemePreset('default')
```

#### **Ajustar Layout Dinamicamente**
```javascript
// Layout compacto (menos espaço)
LojaSync.compactLayout()

// Layout normal
LojaSync.normalLayout()

// Layout espaçoso (mais espaço)
LojaSync.spaciousLayout()
```

#### **Tamanho dos Botões**
```javascript
// Botões pequenos
LojaSync.smallButtons()

// Botões médios (padrão)
LojaSync.mediumButtons()

// Botões grandes
LojaSync.largeButtons()
```

#### **Arredondamento**
```javascript
// Cantos retos
LojaSync.sharpCorners()

// Cantos normais
LojaSync.normalCorners()

// Cantos muito arredondados
LojaSync.roundCorners()
```

#### **Customizar Cor Específica**
```javascript
// Mudar cor primária para vermelho
LojaSync.theme.setCustomColor('color-primary', '#ef4444')

// Mudar cor de fundo
LojaSync.theme.setCustomColor('bg-primary', '#1a1a2e')
```

#### **Resetar Customizações**
```javascript
LojaSync.theme.resetCustomizations()
```

---

## 📦 Presets de Layout Prontos

### **Preset 1: Layout Compacto Profissional**
```javascript
LojaSync.compactLayout()
LojaSync.smallButtons()
LojaSync.sharpCorners()
LojaSync.applyThemePreset('blue')
```

### **Preset 2: Layout Espaçoso Moderno**
```javascript
LojaSync.spaciousLayout()
LojaSync.largeButtons()
LojaSync.roundCorners()
LojaSync.applyThemePreset('default')
```

### **Preset 3: Minimalista**
```javascript
LojaSync.compactLayout()
LojaSync.mediumButtons()
LojaSync.sharpCorners()
// Edite theme.css:
// --color-primary: #64748b (cinza)
```

---

## 🎨 Criar Tema Personalizado

### **Método 1: Editar `theme.css` (Recomendado)**

1. Abra `theme.css`
2. Procure a seção `:root { ... }`
3. Altere as variáveis desejadas
4. Salve e recarregue a página

**Exemplo - Tema Verde Escuro:**
```css
:root {
  --color-primary: #22c55e;        /* Verde */
  --color-primary-hover: #16a34a;
  --bg-primary: #0a0f0a;           /* Fundo mais escuro */
  --bg-secondary: #0f1810;
}
```

### **Método 2: Via JavaScript (Temporário)**

```javascript
// Aplica mudanças sem editar arquivos
LojaSync.theme.setCustomColor('color-primary', '#22c55e')
LojaSync.theme.setCustomColor('bg-primary', '#0a0f0a')
LojaSync.theme.setCustomColor('bg-secondary', '#0f1810')
```

💾 As alterações via JS são salvas no navegador automaticamente!

### **Método 3: Criar Preset Permanente**

Edite `theme.js`, seção `THEME_PRESETS`:

```javascript
const THEME_PRESETS = {
  // ... presets existentes ...
  
  // Seu tema customizado
  meuTema: {
    'color-primary': '#ff6b6b',
    'color-success': '#51cf66',
    'color-warning': '#ffd43b',
    'color-danger': '#ff8787',
  }
};
```

Use: `LojaSync.applyThemePreset('meuTema')`

---

## 📊 Tabela de Variáveis Principais

### **Cores**

| Variável | Uso | Padrão |
|----------|-----|--------|
| `--color-primary` | Ações principais, links | `#8b5cf6` (Roxo) |
| `--color-success` | Confirmações, sucesso | `#10b981` (Verde) |
| `--color-warning` | Avisos, atenção | `#f59e0b` (Laranja) |
| `--color-danger` | Erros, deletar | `#ef4444` (Vermelho) |
| `--bg-primary` | Fundo principal | `#0f172a` (Azul escuro) |
| `--bg-secondary` | Cards, painéis | `#1e293b` |
| `--text-primary` | Texto principal | `#f8fafc` (Branco) |

### **Espaçamento**

| Variável | Valor | Uso |
|----------|-------|-----|
| `--spacing-1` | `8px` | Pequeno |
| `--spacing-2` | `16px` | Médio |
| `--spacing-3` | `24px` | Grande |
| `--spacing-4` | `32px` | Extra grande |

### **Tipografia**

| Variável | Valor | Uso |
|----------|-------|-----|
| `--font-size-sm` | `12px` | Legendas |
| `--font-size-base` | `14px` | Texto normal |
| `--font-size-lg` | `16px` | Destaque |
| `--font-size-2xl` | `24px` | Títulos |

---

## 🔧 Troubleshooting

### **Mudanças não aparecem?**

1. ✅ Certifique-se de salvar o arquivo
2. ✅ Recarregue a página (F5 ou Ctrl+R)
3. ✅ Limpe o cache (Ctrl+Shift+R)
4. ✅ Verifique o console (F12) por erros

### **Tema bagunçado?**

```javascript
// Reset completo
LojaSync.theme.resetCustomizations()
```

### **Como saber quais variáveis existem?**

Abra `theme.css` e veja todas na seção `:root { ... }`

### **Atalho de teclado**

**Ctrl + Shift + T** = Alternar tema claro/escuro

---

## 💡 Dicas Pro

### **1. Testar Antes de Aplicar**

Use o console para testar:
```javascript
// Teste temporário
LojaSync.theme.setCustomColor('color-primary', '#3b82f6')

// Gostou? Aplique no theme.css permanentemente
```

### **2. Exportar/Importar Configurações**

```javascript
// Exportar suas configurações
const config = LojaSync.theme.exportSettings()
console.log(JSON.stringify(config, null, 2))

// Importar
LojaSync.theme.importSettings(config)
```

### **3. Modo Desenvolvimento**

Adicione no console:
```javascript
// Mostra valores de todas as variáveis CSS
getComputedStyle(document.documentElement).getPropertyValue('--color-primary')
```

### **4. Criar Variações de Cor Automaticamente**

```javascript
// Gera hover automaticamente (cor mais escura)
function darkenColor(hex, percent) {
  // ... implementação ...
}
```

---

## 📚 Exemplos Práticos

### **Exemplo 1: Site para Cliente - Tema Corporativo Azul**

```css
/* No theme.css */
:root {
  --color-primary: #0066cc;
  --color-success: #28a745;
  --font-size-base: 15px;
  --radius-md: 6px;
}
```

### **Exemplo 2: Uso Pessoal - Dark Mode Intenso**

```css
:root {
  --bg-primary: #000000;
  --bg-secondary: #0a0a0a;
  --color-primary: #00ff88;
}
```

### **Exemplo 3: Apresentação/Demo - Alto Contraste**

```javascript
LojaSync.spaciousLayout()
LojaSync.largeButtons()
LojaSync.theme.setCustomColor('font-size-base', '16px')
```

---

## 🎬 Workflow Recomendado

1. **Planejamento** - Defina paleta de cores
2. **Edite `theme.css`** - Altere variáveis principais
3. **Teste no navegador** - F5 e verifique
4. **Ajuste fino** - Use console para tweaks rápidos
5. **Permanentize** - Copie valores do console para `theme.css`
6. **Commit** - Salve suas alterações

---

## 🚀 Quick Start

**Quero mudar TUDO agora! Como faço?**

1. Abra `theme.css`
2. Procure `:root {`
3. Mude estas 3 linhas:
```css
--color-primary: #SEU_COR_FAVORITA;
--bg-primary: #SEU_FUNDO;
--font-size-base: 15px; /* ou outro tamanho */
```
4. Salve, F5, pronto! 🎉

---

## 📞 Suporte

**Dúvidas?** Abra o console (F12) e digite:
```javascript
LojaSync
```

Verá todos os comandos disponíveis!

---

**Desenvolvido para facilitar customizações sem quebrar funcionalidades! 🚀**
