/**
 * LojaSync Theme Controller
 * ====================================
 * Controle dinâmico do tema e personalizações
 * Permite alternar temas, ajustar cores em tempo real
 */

class ThemeController {
  constructor() {
    this.currentTheme = localStorage.getItem('lojasync-theme') || 'dark';
    this.customColors = this.loadCustomColors();
    this.init();
  }

  init() {
    this.applyTheme(this.currentTheme);
    this.applyCustomColors();
    this.setupEventListeners();
  }

  /**
   * Alterna entre tema claro e escuro
   */
  toggleTheme() {
    this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
    this.applyTheme(this.currentTheme);
    localStorage.setItem('lojasync-theme', this.currentTheme);
  }

  /**
   * Aplica um tema específico
   */
  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    this.currentTheme = theme;
  }

  /**
   * Carrega cores personalizadas do localStorage
   */
  loadCustomColors() {
    const saved = localStorage.getItem('lojasync-custom-colors');
    return saved ? JSON.parse(saved) : {};
  }

  /**
   * Salva cores personalizadas
   */
  saveCustomColors() {
    localStorage.setItem('lojasync-custom-colors', JSON.stringify(this.customColors));
  }

  /**
   * Define uma cor customizada
   * @param {string} variable - Nome da variável CSS (ex: 'color-primary')
   * @param {string} value - Valor da cor (ex: '#8b5cf6')
   */
  setCustomColor(variable, value) {
    this.customColors[variable] = value;
    document.documentElement.style.setProperty(`--${variable}`, value);
    this.saveCustomColors();
  }

  /**
   * Aplica todas as cores customizadas salvas
   */
  applyCustomColors() {
    Object.entries(this.customColors).forEach(([variable, value]) => {
      document.documentElement.style.setProperty(`--${variable}`, value);
    });
  }

  /**
   * Reseta todas as customizações
   */
  resetCustomizations() {
    this.customColors = {};
    localStorage.removeItem('lojasync-custom-colors');
    // Remove estilos inline
    const root = document.documentElement;
    const styles = root.style;
    for (let i = styles.length - 1; i >= 0; i--) {
      const prop = styles[i];
      if (prop.startsWith('--')) {
        root.style.removeProperty(prop);
      }
    }
    // Recarrega página para aplicar temas padrão
    window.location.reload();
  }

  /**
   * Ajusta a escala de todo o layout
   */
  setLayoutScale(scale) {
    document.documentElement.style.fontSize = `${scale}px`;
    localStorage.setItem('lojasync-scale', scale);
  }

  /**
   * Configura listeners para eventos
   */
  setupEventListeners() {
    // Atalho de teclado para alternar tema (Ctrl+Shift+T)
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'T') {
        e.preventDefault();
        this.toggleTheme();
        this.showNotification(`Tema ${this.currentTheme === 'dark' ? 'Escuro' : 'Claro'} ativado`);
      }
    });
  }

  /**
   * Mostra notificação temporária
   */
  showNotification(message) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: var(--color-primary);
      color: white;
      padding: 12px 20px;
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-lg);
      z-index: var(--z-toast);
      animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(notification);
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 2000);
  }

  /**
   * Exporta configurações atuais
   */
  exportSettings() {
    return {
      theme: this.currentTheme,
      customColors: this.customColors,
      scale: localStorage.getItem('lojasync-scale') || 14
    };
  }

  /**
   * Importa configurações
   */
  importSettings(settings) {
    if (settings.theme) {
      this.applyTheme(settings.theme);
    }
    if (settings.customColors) {
      this.customColors = settings.customColors;
      this.applyCustomColors();
      this.saveCustomColors();
    }
    if (settings.scale) {
      this.setLayoutScale(settings.scale);
    }
  }
}

// ============================================
// PRESETS DE CORES PRÉ-DEFINIDOS
// ============================================

const THEME_PRESETS = {
  // Tema padrão (Roxo)
  default: {
    'color-primary': '#8b5cf6',
    'color-success': '#10b981',
    'color-warning': '#f59e0b',
    'color-danger': '#ef4444',
  },

  // Tema Azul
  blue: {
    'color-primary': '#3b82f6',
    'color-success': '#10b981',
    'color-warning': '#f59e0b',
    'color-danger': '#ef4444',
  },

  // Tema Verde
  green: {
    'color-primary': '#10b981',
    'color-success': '#059669',
    'color-warning': '#f59e0b',
    'color-danger': '#ef4444',
  },

  // Tema Laranja
  orange: {
    'color-primary': '#f97316',
    'color-success': '#10b981',
    'color-warning': '#f59e0b',
    'color-danger': '#ef4444',
  },

  // Tema Rosa
  pink: {
    'color-primary': '#ec4899',
    'color-success': '#10b981',
    'color-warning': '#f59e0b',
    'color-danger': '#ef4444',
  },

  // Tema Ciano
  cyan: {
    'color-primary': '#06b6d4',
    'color-success': '#10b981',
    'color-warning': '#f59e0b',
    'color-danger': '#ef4444',
  }
};

/**
 * Aplica um preset de tema
 */
function applyThemePreset(presetName) {
  const preset = THEME_PRESETS[presetName];
  if (!preset) {
    console.error(`Preset "${presetName}" não encontrado`);
    return;
  }

  Object.entries(preset).forEach(([variable, value]) => {
    window.themeController.setCustomColor(variable, value);
  });

  window.themeController.showNotification(`Tema ${presetName} aplicado!`);
}

// ============================================
// UTILITÁRIOS DE LAYOUT
// ============================================

/**
 * Ajusta o espaçamento global do layout
 * @param {number} multiplier - Multiplicador (0.8 = compacto, 1.0 = normal, 1.2 = espaçoso)
 */
function adjustSpacing(multiplier = 1.0) {
  const baseSpacing = 8;
  for (let i = 1; i <= 6; i++) {
    const value = `${baseSpacing * i * multiplier}px`;
    document.documentElement.style.setProperty(`--spacing-${i}`, value);
  }
  localStorage.setItem('lojasync-spacing', multiplier);
}

/**
 * Ajusta o tamanho dos botões globalmente
 */
function adjustButtonSize(size = 'md') {
  const sizes = {
    sm: { height: '32px', padding: '8px 12px', fontSize: '12px' },
    md: { height: '40px', padding: '10px 16px', fontSize: '14px' },
    lg: { height: '48px', padding: '12px 20px', fontSize: '16px' }
  };

  const config = sizes[size];
  if (!config) return;

  document.documentElement.style.setProperty('--button-height-md', config.height);
  document.documentElement.style.setProperty('--button-padding-x', config.padding.split(' ')[1]);
  document.documentElement.style.setProperty('--font-size-base', config.fontSize);
  
  localStorage.setItem('lojasync-button-size', size);
}

/**
 * Ajusta o raio das bordas (arredondamento)
 */
function adjustBorderRadius(multiplier = 1.0) {
  const base = {
    sm: 6,
    md: 8,
    lg: 12,
    xl: 16
  };

  Object.entries(base).forEach(([size, value]) => {
    document.documentElement.style.setProperty(
      `--radius-${size}`,
      `${value * multiplier}px`
    );
  });

  localStorage.setItem('lojasync-radius', multiplier);
}

// ============================================
// INICIALIZAÇÃO
// ============================================

// Cria instância global do controlador de tema
window.themeController = new ThemeController();

// Adiciona animações CSS necessárias
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Expõe funções globalmente para uso no console ou scripts
window.LojaSync = {
  theme: window.themeController,
  ui: window.themeUI,
  
  // Aplicar temas completos
  applyCompleteTheme: (themeName) => {
    if (window.themeUI) {
      window.themeUI.applyTheme(themeName);
      window.themeUI.savePreferences();
    }
  },
  
  // Atalhos para temas - Adicione os seus aqui
  defaultTheme: () => window.LojaSync.applyCompleteTheme('default'),
  
  // Funções antigas mantidas para compatibilidade
  applyThemePreset,
  adjustSpacing,
  adjustButtonSize,
  adjustBorderRadius,
  
  compactLayout: () => adjustSpacing(0.8),
  normalLayout: () => adjustSpacing(1.0),
  spaciousLayout: () => adjustSpacing(1.2),
  
  smallButtons: () => adjustButtonSize('sm'),
  mediumButtons: () => adjustButtonSize('md'),
  largeButtons: () => adjustButtonSize('lg'),
  
  sharpCorners: () => adjustBorderRadius(0.5),
  normalCorners: () => adjustBorderRadius(1.0),
  roundCorners: () => adjustBorderRadius(1.5)
};

// ============================================
// CONTROLADOR DE INTERFACE DO MODAL
// ============================================

class ThemeUI {
  constructor() {
    this.modal = null;
    this.selectedTheme = 'default';
    this.init();
  }

  init() {
    // Aguarda DOM carregar
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    this.modal = document.getElementById('theme-modal');
    if (!this.modal) {
      console.warn('Modal de tema não encontrado');
      return;
    }

    this.setupEventListeners();
    this.loadSavedPreferences();
    this.applyTheme(this.selectedTheme);
  }

  setupEventListeners() {
    // Botão de abrir modal
    const btnOpen = document.getElementById('btn-open-theme-menu');
    if (btnOpen) {
      btnOpen.addEventListener('click', () => this.openModal());
    }

    // Botão de fechar modal
    const btnClose = document.getElementById('btn-close-theme-menu');
    if (btnClose) {
      btnClose.addEventListener('click', () => this.closeModal());
    }

    // Fechar ao clicar fora do modal
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.closeModal();
      }
    });

    // Tecla ESC para fechar
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !this.modal.classList.contains('hidden')) {
        this.closeModal();
      }
    });

    // Cards de tema completo
    document.querySelectorAll('.theme-card-complete').forEach(card => {
      card.addEventListener('click', () => {
        const theme = card.dataset.completeTheme;
        this.selectTheme(theme);
      });
    });

    // Botão de reset
    const btnReset = document.getElementById('btn-reset-theme');
    if (btnReset) {
      btnReset.addEventListener('click', () => this.resetToDefaults());
    }

    // Botão de aplicar
    const btnApply = document.getElementById('btn-apply-theme');
    if (btnApply) {
      btnApply.addEventListener('click', () => this.applyChanges());
    }

    // Atalho Ctrl+Shift+T
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'T') {
        e.preventDefault();
        if (this.modal.classList.contains('hidden')) {
          this.openModal();
        } else {
          this.closeModal();
        }
      }
    });
  }

  openModal() {
    if (this.modal) {
      this.modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    }
  }

  closeModal() {
    if (this.modal) {
      this.modal.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  selectTheme(theme) {
    this.selectedTheme = theme;
    // Remove active de todos
    document.querySelectorAll('.theme-card-complete').forEach(card => {
      card.classList.remove('active');
    });
    // Adiciona active no selecionado
    const selected = document.querySelector(`[data-complete-theme="${theme}"]`);
    if (selected) {
      selected.classList.add('active');
    }
  }

  applyTheme(theme) {
    // Aplica o tema completo no documentElement
    document.documentElement.setAttribute('data-complete-theme', theme);
    this.selectedTheme = theme;
    this.selectTheme(theme);
  }

  applyChanges() {
    // Aplica o tema completo
    this.applyTheme(this.selectedTheme);

    // Salva preferências
    this.savePreferences();

    // Mostra notificação
    window.themeController.showNotification(`✨ Tema ${this.getThemeName(this.selectedTheme)} aplicado!`);

    // Fecha modal
    this.closeModal();
  }

  resetToDefaults() {
    this.applyTheme('default');
    this.savePreferences();
    window.themeController.showNotification('🔄 Tema restaurado para o padrão');
  }

  savePreferences() {
    localStorage.setItem('lojasync-complete-theme', this.selectedTheme);
  }

  loadSavedPreferences() {
    const saved = localStorage.getItem('lojasync-complete-theme');
    if (saved) {
      this.selectedTheme = saved;
    }
  }

  getThemeName(theme) {
    const names = {
      default: 'Default'
      // Adicione seus temas aqui
    };
    return names[theme] || theme;
  }
}

// Inicializa UI do modal
window.themeUI = new ThemeUI();

console.log('🎨 LojaSync Theme System carregado!');
console.log('📖 Use window.LojaSync para acessar controles de tema');
console.log('');
console.log('🔧 Para adicionar temas personalizados:');
console.log('   1. Edite themes-complete.css');
console.log('   2. Adicione o botão no modal (index.html)');
console.log('   3. Adicione o atalho em theme.js');
console.log('');
console.log('🎨 Ou use o botão flutuante no canto inferior direito!');
