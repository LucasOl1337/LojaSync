# 📘 Guia: Como Adicionar Temas Personalizados

## 🎯 Sistema de Temas - Estrutura

O LojaSync possui um sistema completo de temas que permite criar visuais totalmente diferentes para a aplicação.

**Arquivos envolvidos:**
- `themes-complete.css` - Define as variáveis CSS dos temas
- `index.html` - Adiciona os botões no modal de seleção
- `theme.js` - (Opcional) Adiciona atalhos via console

---

## 📝 Passo a Passo: Criar um Novo Tema

### **1. Editar `themes-complete.css`**

Adicione o bloco do seu tema no final do arquivo:

```css
/* ============================================
   TEMA: MEU TEMA PERSONALIZADO
   ============================================ */

[data-complete-theme="meutema"] {
  /* Cores principais */
  --color-primary: #FF6600;              /* Cor primária (botões, destaques) */
  --color-primary-hover: #FF8800;        /* Hover da cor primária */
  --color-primary-light: rgba(255, 102, 0, 0.1);  /* Versão transparente */
  
  /* Cores de estado */
  --color-success: #10b981;              /* Verde para sucesso */
  --color-success-hover: #059669;
  --color-warning: #f59e0b;              /* Laranja para avisos */
  --color-warning-hover: #d97706;
  --color-danger: #ef4444;               /* Vermelho para perigo */
  --color-danger-hover: #dc2626;
  --color-info: #3b82f6;                 /* Azul para informações */
  --color-info-hover: #2563eb;
  
  /* Backgrounds */
  --bg-primary: #1e293b;                 /* Fundo principal */
  --bg-secondary: #0f172a;               /* Fundo de cards */
  --bg-tertiary: #334155;                /* Fundo de inputs */
  --bg-hover: #475569;                   /* Fundo ao passar mouse */
  
  /* Textos */
  --text-primary: #f1f5f9;               /* Texto principal (branco) */
  --text-secondary: #cbd5e1;             /* Texto secundário (cinza claro) */
  --text-muted: #94a3b8;                 /* Texto discreto (cinza) */
  
  /* Bordas */
  --border-color: #334155;               /* Cor de bordas */
  --border-color-hover: #475569;         /* Bordas ao passar mouse */
  
  /* Sombras */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
  --shadow-primary: 0 4px 12px rgba(255, 102, 0, 0.3);
  
  /* Tipografia */
  --font-family-base: 'Space Grotesk', sans-serif;
  --font-size-xs: 12px;
  --font-size-sm: 13px;
  --font-size-base: 14px;
  --font-size-lg: 16px;
  --font-size-xl: 18px;
  --font-size-2xl: 24px;
  
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  
  /* Espaçamento */
  --spacing-1: 4px;
  --spacing-2: 8px;
  --spacing-3: 12px;
  --spacing-4: 16px;
  --spacing-5: 20px;
  --spacing-6: 24px;
  --spacing-8: 32px;
  
  /* Border radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 12px;
  --radius-xl: 16px;
}

/* Efeitos especiais (opcional) */
[data-complete-theme="meutema"] button {
  background: var(--color-primary) !important;
  transition: all 0.2s ease !important;
}

[data-complete-theme="meutema"] button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 4px 12px rgba(255, 102, 0, 0.4) !important;
}
```

---

### **2. Adicionar Botão no `index.html`**

Localize o bloco com `<!-- Adicione novos temas aqui -->` e adicione:

```html
<!-- Tema Meu Tema -->
<button class="theme-card-complete" data-complete-theme="meutema">
  <div class="theme-preview-complete" style="background: linear-gradient(135deg, #FF6600 0%, #000000 100%)">
    <div class="theme-accent" style="background: #FF6600"></div>
  </div>
  <div class="theme-info">
    <span class="theme-name">🔥 Meu Tema</span>
    <span class="theme-desc">Descrição curta</span>
  </div>
</button>
```

**Personalize:**
- `data-complete-theme="meutema"` - Nome do tema (mesmo do CSS)
- `style="background: linear-gradient(...)"` - Preview do gradiente
- `🔥 Meu Tema` - Nome exibido
- `Descrição curta` - Descrição do tema

---

### **3. (Opcional) Adicionar Atalho no `theme.js`**

Localize o bloco `// Atalhos para temas` e adicione:

```javascript
// Atalhos para temas - Adicione os seus aqui
defaultTheme: () => window.LojaSync.applyCompleteTheme('default'),
meuTema: () => window.LojaSync.applyCompleteTheme('meutema'),  // NOVO
```

E no método `getThemeName`:

```javascript
getThemeName(theme) {
  const names = {
    default: 'Default',
    meutema: 'Meu Tema'  // NOVO
  };
  return names[theme] || theme;
}
```

Agora você pode aplicar via console:
```javascript
LojaSync.meuTema()
```

---

## 🎨 Dicas de Cores

### **Paletas Populares:**

**Tema Oceano:**
```css
--color-primary: #00B4D8;
--bg-primary: #03045E;
--text-primary: #CAF0F8;
```

**Tema Sunset:**
```css
--color-primary: #FF6B6B;
--bg-primary: #2D132C;
--text-primary: #FFEAA7;
```

**Tema Matrix:**
```css
--color-primary: #00FF41;
--bg-primary: #000000;
--text-primary: #00FF41;
```

**Tema Minimal (Claro):**
```css
--color-primary: #000000;
--bg-primary: #FFFFFF;
--text-primary: #000000;
```

---

## 🔧 Efeitos Especiais Avançados

### **Animações de Background:**

```css
[data-complete-theme="meutema"] body::before {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(circle at 20% 50%, rgba(255, 102, 0, 0.15) 0%, transparent 50%);
  animation: pulsar 10s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes pulsar {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### **Glow nos Botões:**

```css
[data-complete-theme="meutema"] button:hover {
  box-shadow: 
    0 0 10px rgba(255, 102, 0, 0.8),
    0 0 20px rgba(255, 102, 0, 0.6),
    0 0 30px rgba(255, 102, 0, 0.4) !important;
}
```

### **Fonte Monospace (Terminal):**

```css
[data-complete-theme="meutema"] * {
  font-family: 'Courier New', monospace !important;
}
```

### **Bordas Neon:**

```css
[data-complete-theme="meutema"] .panel-header {
  border: 2px solid var(--color-primary) !important;
  box-shadow: 
    0 0 20px rgba(255, 102, 0, 0.6),
    inset 0 0 20px rgba(255, 102, 0, 0.1) !important;
}
```

---

## 📊 Estrutura de Seletores

Para customizar elementos específicos:

```css
/* Headers */
[data-complete-theme="meutema"] .panel-header { }

/* Botões */
[data-complete-theme="meutema"] button { }

/* Inputs */
[data-complete-theme="meutema"] input,
[data-complete-theme="meutema"] select { }

/* Tabela */
[data-complete-theme="meutema"] table { }
[data-complete-theme="meutema"] th { }
[data-complete-theme="meutema"] td { }

/* Cards */
[data-complete-theme="meutema"] .totals { }
[data-complete-theme="meutema"] .agents-card { }

/* Textos */
[data-complete-theme="meutema"] h2 { }
[data-complete-theme="meutema"] label { }
```

---

## ✅ Checklist Final

- [ ] Adicionei o tema em `themes-complete.css`
- [ ] Adicionei o botão em `index.html`
- [ ] (Opcional) Adicionei atalho em `theme.js`
- [ ] Testei o tema abrindo o modal (botão 🎨)
- [ ] Verifiquei contraste de cores (texto legível)
- [ ] Testei hover nos botões

---

## 🚀 Aplicar Tema

### **Via Interface:**
1. Clique no botão 🎨 (canto inferior direito)
2. Escolha seu tema
3. Clique em "✓ Aplicar"

### **Via Console (F12):**
```javascript
LojaSync.applyCompleteTheme('meutema')
```

### **Via Atalho (se configurado):**
```javascript
LojaSync.meuTema()
```

---

## 💡 Exemplos Prontos

### **Tema Dark Blue:**
```css
[data-complete-theme="darkblue"] {
  --color-primary: #2563eb;
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --text-primary: #f1f5f9;
}
```

### **Tema Rosé:**
```css
[data-complete-theme="rose"] {
  --color-primary: #f43f5e;
  --bg-primary: #1f1d29;
  --bg-secondary: #2d2a3d;
  --text-primary: #fecdd3;
}
```

---

**Divirta-se criando temas! 🎨**
