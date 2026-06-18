import type { EditableField } from "./productEditing";
import type { AutomationStatus, Product } from "./types";

export const CATEGORIES = ["Masculino", "Feminino", "Infantil", "Acessorios"];
export const MAX_UNDO_HISTORY = 10;

export const AUTOMATION_TARGET_FIELDS = [
  { key: "byte_empresa_posicao", label: "Posicao Byte Empresa" },
  { key: "campo_descricao", label: "Campo Descricao" },
  { key: "tres_pontinhos", label: "Botao 3 pontinhos" },
  { key: "cadastro_completo_passo_1", label: "Cadastro completo passo 1" },
  { key: "cadastro_completo_passo_2", label: "Cadastro completo passo 2" },
  { key: "cadastro_completo_passo_3", label: "Cadastro completo passo 3" },
  { key: "cadastro_completo_passo_4", label: "Cadastro completo passo 4" },
] as const;

export const GRADE_CAPTURE_FIELDS = [
  { key: "focus_app", label: "Focar aplicativo" },
  { key: "alterar_grade", label: "Botao Alterar/Definir Grade" },
  { key: "modelos", label: "Botao Modelos" },
  { key: "model_select", label: "Linha do modelo" },
  { key: "model_ok", label: "Botao OK do modelo" },
  { key: "confirm_sim", label: "Botao Sim da confirmacao" },
  { key: "close_after_import", label: "Fechar intermediario" },
  { key: "save_grade", label: "Salvar grade" },
  { key: "close_grade", label: "Fechar grade" },
] as const;

// Keeps 1920x1080 at 100% unchanged while filling the same physical canvas when Chrome zoom exposes a larger CSS viewport.
export const APP_STAGE_WIDTH = 2144;
export const APP_STAGE_HEIGHT = 1184;
export const APP_STAGE_PADDING = 8;

export type Scope = "products" | "totals" | "brands" | "margin" | "automation";
export type EditingCellState = { orderingKey: string; field: EditableField; value: string };
export type AutomationTargetKey = typeof AUTOMATION_TARGET_FIELDS[number]["key"];
export type GradeCaptureKey = typeof GRADE_CAPTURE_FIELDS[number]["key"];

export type LoadState = {
  products: Product[];
  brands: string[];
  totalsText: {
    atualCusto: string;
    atualVenda: string;
    historicoCusto: string;
    historicoVenda: string;
    tempo: string;
  };
  totalsRaw: {
    atualQuantidade: number;
    historicoQuantidade: number;
    caracteres: number;
  };
  marginPercentual: number;
  automation: AutomationStatus;
};

export const initialState: LoadState = {
  products: [],
  brands: [],
  totalsText: {
    atualCusto: "R$ 0,00",
    atualVenda: "R$ 0,00",
    historicoCusto: "R$ 0,00",
    historicoVenda: "R$ 0,00",
    tempo: "0s",
  },
  totalsRaw: {
    atualQuantidade: 0,
    historicoQuantidade: 0,
    caracteres: 0,
  },
  marginPercentual: 0,
  automation: {},
};
