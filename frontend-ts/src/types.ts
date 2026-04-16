export type GradeItem = {
  tamanho: string;
  quantidade: number;
};

export type UiGradeFamily = {
  id: string;
  label: string;
  sizes: string[];
};

export type CorItem = {
  cor: string;
  quantidade: number;
};

export type Product = {
  nome: string;
  codigo: string;
  codigo_original: string | null;
  quantidade: number;
  preco: string;
  categoria: string;
  marca: string;
  preco_final: string | null;
  descricao_completa: string | null;
  grades?: GradeItem[] | null;
  cores?: CorItem[] | null;
  source_type?: string | null;
  import_batch_id?: string | null;
  import_source_name?: string | null;
  pending_grade_import?: boolean;
  ordering_key: string;
  timestamp: string;
};

export type ProductListResponse = {
  items: Product[];
};

export type BrandsResponse = {
  marcas: string[];
};

export type TotalsInfo = {
  quantidade: number;
  custo: number;
  venda: number;
};

export type TotalsResponse = {
  atual: TotalsInfo;
  historico: TotalsInfo;
  tempo_economizado: number;
  caracteres_digitados: number;
};

export type MarginSettingsResponse = {
  margem: number;
  percentual: number;
};

export type ProductPayload = {
  nome: string;
  codigo: string;
  quantidade: number;
  preco: string;
  categoria: string;
  marca: string;
  preco_final?: string | null;
  descricao_completa?: string | null;
  grades?: GradeItem[] | null;
  cores?: CorItem[] | null;
};

export type CatalogSizesResponse = {
  sizes: string[];
};

export type GradeConfig = {
  buttons?: Record<string, unknown> | null;
  first_quant_cell?: { x: number; y: number } | null;
  second_quant_cell?: { x: number; y: number } | null;
  row_height?: number | null;
  model_index?: number | null;
  model_hotkey?: string | null;
  erp_size_order?: string[] | null;
  ui_size_order?: string[] | null;
  ui_families?: UiGradeFamily[] | null;
  ui_family_version?: number | null;
};

export type GradeConfigResponse = {
  config: GradeConfig;
};

export type TargetPoint = {
  x: number;
  y: number;
};

export type AutomationTargets = {
  title?: string | null;
  byte_empresa_posicao?: TargetPoint | null;
  campo_descricao?: TargetPoint | null;
  tres_pontinhos?: TargetPoint | null;
  cadastro_completo_passo_1?: TargetPoint | null;
  cadastro_completo_passo_2?: TargetPoint | null;
  cadastro_completo_passo_3?: TargetPoint | null;
  cadastro_completo_passo_4?: TargetPoint | null;
};

export type TargetCaptureResponse = {
  target: string;
  point: TargetPoint;
};

export type ImportStartResponse = {
  job_id: string;
};

export type ImportStatus = {
  job_id: string;
  stage: string;
  message: string;
  started_at: number;
  updated_at: number;
  completed_at: number | null;
  error: string | null;
  metrics: Record<string, unknown>;
};

export type ImportResult = {
  status: string;
  saved_file: string | null;
  local_file: string | null;
  content: string | null;
  warnings: string[];
  total_itens: number;
  grades_disponiveis: boolean;
  total_grades_disponiveis: number;
  imported_keys: string[];
  metrics: Record<string, unknown>;
};

export type LocalImportExperimentGrade = {
  tamanho: string;
  quantidade: number;
};

export type LocalImportExperimentItem = {
  codigo: string;
  nome: string;
  descricao_completa: string;
  cor: string | null;
  preco: string;
  quantidade: number;
  unidade: string;
  grades: LocalImportExperimentGrade[];
  linhas_originais: number;
};

export type LocalImportExperimentResult = {
  status: string;
  filename: string;
  warnings: string[];
  total_rows: number;
  total_itens: number;
  total_quantity: number;
  remessa_quantity: number | null;
  quantity_matches_remessa: boolean;
  items: LocalImportExperimentItem[];
  metrics: Record<string, unknown>;
};

export type PostProcessStartResponse = {
  job_id: string;
};

export type PostProcessStatus = {
  job_id: string;
  stage: string;
  message: string;
  started_at: number;
  updated_at: number;
  completed_at: number | null;
  error: string | null;
  metrics: Record<string, unknown>;
};

export type PostProcessResult = {
  status: string;
  total_itens: number;
  total_modificados: number;
  dry_run: boolean;
  saved_file: string | null;
  raw_response: string | null;
  warnings: string[];
  metrics: Record<string, unknown>;
};

export type AutomationStatus = {
  estado?: string | null;
  message?: string | null;
  phase?: string | null;
  job_kind?: string | null;
  cancel_requested?: string | null;
  ordering_key_atual?: string | null;
  produto_atual?: string | null;
  codigo_atual?: string | null;
  descricao_digitada?: string | null;
  item_atual?: number | null;
  total_itens?: number | null;
};

export type AuthSessionResponse = {
  auth_enabled: boolean;
  authenticated: boolean;
  bootstrap_required: boolean;
  password_configured: boolean;
  session_ttl_minutes: number;
  user: string | null;
  expires_at: number | null;
};

export type UiConnectedEvent = {
  type: "ui.connected";
  ts: number;
};

export type UiStateChangedEvent = {
  type: "state.changed";
  ts: number;
  scopes: string[];
};

export type UiJobUpdatedEvent = {
  type: "job.updated";
  ts: number;
  job: string;
  job_id: string;
  stage: string;
  message: string;
  error?: string | null;
};

export type UiEvent = UiConnectedEvent | UiStateChangedEvent | UiJobUpdatedEvent;
