import assert from "node:assert/strict";
import test from "node:test";

const filters = await import(new URL("../.tmp-tests/productFilters.js", import.meta.url));

const baseProduct = {
  nome: "Produto",
  codigo: "123",
  codigo_original: null,
  quantidade: 2,
  preco: "10,00",
  categoria: "Feminino",
  marca: "Marca",
  preco_final: null,
  descricao_completa: null,
  grades: null,
  cores: null,
  source_type: null,
  import_batch_id: null,
  import_source_name: null,
  pending_grade_import: false,
  ordering_key: "base",
  timestamp: "2026-06-14",
};

const products = [
  { ...baseProduct, ordering_key: "a" },
  { ...baseProduct, ordering_key: "b", marca: "", codigo: "", pending_grade_import: true, import_batch_id: "batch-1" },
  { ...baseProduct, ordering_key: "c", quantidade: 3, grades: [{ tamanho: "P", quantidade: 1 }] },
  { ...baseProduct, ordering_key: "d", categoria: "", source_type: "local_parser" },
];

test("filters products without changing their relative order", () => {
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "all"), products);
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "needs_review").map((product) => product.ordering_key), ["b", "c", "d"]);
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "recent_imports").map((product) => product.ordering_key), ["b", "d"]);
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "missing_brand").map((product) => product.ordering_key), ["b"]);
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "missing_code").map((product) => product.ordering_key), ["b"]);
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "missing_category").map((product) => product.ordering_key), ["d"]);
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "pending_grades").map((product) => product.ordering_key), ["b"]);
  assert.deepEqual(filters.filterProductsByQuickFilter(products, "grade_mismatch").map((product) => product.ordering_key), ["c"]);
});

test("searches products by visible catalog fields", () => {
  const searchableProducts = [
    { ...baseProduct, ordering_key: "flare", nome: "CALCA FLARE SELENIA", marca: "K2B", codigo: "070570044", categoria: "Feminino" },
    { ...baseProduct, ordering_key: "jaqueta", nome: "JAQUETA SOLIRA", marca: "K2B", codigo: "090840002", categoria: "Feminino" },
    { ...baseProduct, ordering_key: "bolsa", nome: "Bolsa Couro", marca: "Atelie", codigo: "B-300", codigo_original: "ORIG-88", categoria: "Acessorios" },
  ];

  assert.deepEqual(filters.filterProductsBySearch(searchableProducts, ""), searchableProducts);
  assert.deepEqual(filters.filterProductsBySearch(searchableProducts, "k2b").map((product) => product.ordering_key), ["flare", "jaqueta"]);
  assert.deepEqual(filters.filterProductsBySearch(searchableProducts, "calça").map((product) => product.ordering_key), ["flare"]);
  assert.deepEqual(filters.filterProductsBySearch(searchableProducts, "orig 88").map((product) => product.ordering_key), ["bolsa"]);
  assert.deepEqual(filters.filterProductsBySearch(searchableProducts, "feminino solira").map((product) => product.ordering_key), ["jaqueta"]);
});

test("builds quick filter option counts from current products", () => {
  assert.deepEqual(filters.buildProductQuickFilterOptions(products), [
    { key: "all", label: "Todos", count: 4 },
    { key: "needs_review", label: "Revisar", count: 3 },
    { key: "pending_grades", label: "Grades pendentes", count: 1 },
    { key: "recent_imports", label: "Importados", count: 2 },
    { key: "missing_brand", label: "Sem marca", count: 1 },
    { key: "missing_code", label: "Sem codigo", count: 1 },
    { key: "missing_category", label: "Sem categoria", count: 1 },
    { key: "grade_mismatch", label: "Divergencia", count: 1 },
  ]);
});

test("builds readable quick filter button labels for assistive tech", () => {
  assert.equal(
    filters.buildProductQuickFilterButtonLabel({ key: "all", label: "Todos", count: 4 }, true),
    "Filtro ativo: Todos, 4 itens",
  );
  assert.equal(
    filters.buildProductQuickFilterButtonLabel({ key: "missing_code", label: "Sem codigo", count: 1 }, false),
    "Filtro: Sem codigo, 1 item",
  );
  assert.equal(
    filters.buildProductQuickFilterButtonLabel({ key: "pending_grades", label: "Grades pendentes", count: 0 }, false),
    "Filtro: Grades pendentes, 0 itens",
  );
});

test("marks zero-count inactive quick filters as visually empty", () => {
  assert.equal(
    filters.getProductQuickFilterVisualState({ key: "pending_grades", label: "Grades pendentes", count: 0 }, false),
    "empty",
  );
  assert.equal(
    filters.getProductQuickFilterVisualState({ key: "pending_grades", label: "Grades pendentes", count: 0 }, true),
    "active",
  );
  assert.equal(
    filters.getProductQuickFilterVisualState({ key: "all", label: "Todos", count: 0 }, false),
    "default",
  );
  assert.equal(
    filters.getProductQuickFilterVisualState({ key: "missing_code", label: "Sem codigo", count: 1 }, false),
    "default",
  );
});

test("hides inactive zero-count quick filters from the primary toolbar", () => {
  const options = [
    { key: "all", label: "Todos", count: 4 },
    { key: "needs_review", label: "Revisar", count: 3 },
    { key: "pending_grades", label: "Grades pendentes", count: 0 },
    { key: "recent_imports", label: "Importados", count: 2 },
    { key: "missing_brand", label: "Sem marca", count: 1 },
    { key: "missing_code", label: "Sem codigo", count: 0 },
    { key: "missing_category", label: "Sem categoria", count: 1 },
    { key: "grade_mismatch", label: "Divergencia", count: 0 },
  ];

  assert.deepEqual(
    filters.getVisibleProductQuickFilterOptions(options, "all").map((option) => option.key),
    ["all", "needs_review", "recent_imports", "missing_brand", "missing_category"],
  );
  assert.deepEqual(
    filters.getVisibleProductQuickFilterOptions(options, "missing_code").map((option) => option.key),
    ["all", "needs_review", "recent_imports", "missing_brand", "missing_code", "missing_category"],
  );
});

test("coerces saved quick filters to known visual presets", () => {
  assert.equal(filters.coerceProductQuickFilter("needs_review"), "needs_review");
  assert.equal(filters.coerceProductQuickFilter("missing_code"), "missing_code");
  assert.equal(filters.coerceProductQuickFilter("missing_category"), "missing_category");
  assert.equal(filters.coerceProductQuickFilter("unknown"), "all");
  assert.equal(filters.coerceProductQuickFilter(null, "recent_imports"), "recent_imports");
  assert.equal(filters.coerceProductQuickFilter("unknown", "missing_brand"), "missing_brand");
});

test("moves stale empty quick filters to the next useful list view", () => {
  const noPendingGradeProducts = products.map((product) => ({ ...product, pending_grade_import: false }));
  const noPendingOptions = filters.buildProductQuickFilterOptions(noPendingGradeProducts);

  assert.equal(filters.resolveStaleProductQuickFilter("pending_grades", noPendingOptions, noPendingGradeProducts.length), "needs_review");
  assert.equal(filters.resolveStaleProductQuickFilter("missing_brand", noPendingOptions, noPendingGradeProducts.length), "missing_brand");
  assert.equal(filters.resolveStaleProductQuickFilter("pending_grades", noPendingOptions, 0), "pending_grades");

  const cleanOptions = filters.buildProductQuickFilterOptions([{ ...baseProduct, ordering_key: "clean" }]);
  assert.equal(filters.resolveStaleProductQuickFilter("pending_grades", cleanOptions, 1), "all");
});

test("builds product review badges from the same conditions used by review filter", () => {
  assert.deepEqual(filters.buildProductReviewBadges(products[0]), []);
  assert.deepEqual(filters.buildProductReviewBadges(products[1]), [
    { key: "pending_grades", filter: "pending_grades", label: "Grade pendente", tone: "warning" },
    { key: "missing_brand", filter: "missing_brand", label: "Sem marca", tone: "warning" },
    { key: "missing_code", filter: "missing_code", label: "Sem codigo", tone: "warning" },
  ]);
  assert.deepEqual(filters.buildProductReviewBadges(products[2]), [
    { key: "grade_mismatch", filter: "grade_mismatch", label: "Grade 1/3", tone: "error" },
  ]);
  assert.deepEqual(filters.buildProductReviewBadges(products[3]), [
    { key: "missing_category", filter: "missing_category", label: "Sem categoria", tone: "warning" },
  ]);

  for (const product of products) {
    assert.equal(filters.productMatchesQuickFilter(product, "needs_review"), filters.buildProductReviewBadges(product).length > 0);
  }
});

test("builds column-level review states for missing catalog fields", () => {
  assert.equal(filters.buildProductReviewFieldStatus(products[0], "marca"), null);
  assert.equal(filters.buildProductReviewFieldStatus(products[0], "codigo"), null);
  assert.equal(filters.buildProductReviewFieldStatus(products[0], "categoria"), null);

  assert.deepEqual(filters.buildProductReviewFieldStatus(products[1], "marca"), {
    field: "marca",
    filter: "missing_brand",
    label: "Sem marca",
    tone: "warning",
  });
  assert.deepEqual(filters.buildProductReviewFieldStatus(products[1], "codigo"), {
    field: "codigo",
    filter: "missing_code",
    label: "Sem codigo",
    tone: "warning",
  });
  assert.deepEqual(filters.buildProductReviewFieldStatus(products[3], "categoria"), {
    field: "categoria",
    filter: "missing_category",
    label: "Sem categoria",
    tone: "warning",
  });
});

test("keeps column-level review states out of the product name badges", () => {
  assert.deepEqual(filters.buildProductNameReviewBadges(products[0]), []);
  assert.deepEqual(filters.buildProductNameReviewBadges(products[1]), [
    { key: "pending_grades", filter: "pending_grades", label: "Grade pendente", tone: "warning" },
  ]);
  assert.deepEqual(filters.buildProductNameReviewBadges(products[2]), [
    { key: "grade_mismatch", filter: "grade_mismatch", label: "Grade 1/3", tone: "error" },
  ]);
  assert.deepEqual(filters.buildProductNameReviewBadges(products[3]), []);
  assert.deepEqual(filters.buildProductReviewBadges(products[3]), [
    { key: "missing_category", filter: "missing_category", label: "Sem categoria", tone: "warning" },
  ]);
});

test("builds active quick filter context with reversible actions", () => {
  const options = filters.buildProductQuickFilterOptions(products);

  assert.equal(filters.buildProductQuickFilterContext("all", options, 4, 4), null);
  assert.deepEqual(filters.buildProductQuickFilterContext("missing_brand", options, 1, 4), {
    title: "Filtro ativo: Sem marca",
    detail: "1 de 4 itens visiveis",
    tone: "warning",
    actions: [
      { key: "all", label: "Mostrar todos", targetFilter: "all", tone: "neutral" },
      { key: "needs_review", label: "Voltar para Revisar", targetFilter: "needs_review", tone: "review" },
    ],
  });
  assert.deepEqual(filters.buildProductQuickFilterContext("needs_review", options, 2, 4), {
    title: "Revisao ativa",
    detail: "2 de 4 itens visiveis",
    tone: "review",
    actions: [{ key: "all", label: "Mostrar todos", targetFilter: "all", tone: "neutral" }],
  });
});

test("builds a filtered empty state with recovery actions", () => {
  const options = filters.buildProductQuickFilterOptions(products);

  assert.deepEqual(filters.buildProductQuickFilterEmptyState("all", options, 0, 0), {
    title: "Nenhum produto ativo neste momento.",
    detail: "Importe ou cadastre produtos para iniciar a lista.",
    actions: [],
  });
  assert.deepEqual(filters.buildProductQuickFilterEmptyState("grade_mismatch", options, 0, 4), {
    title: "Nenhum item em Divergencia.",
    detail: "Existem 4 itens na lista fora deste recorte.",
    actions: [
      { key: "all", label: "Mostrar todos", targetFilter: "all", tone: "neutral" },
      { key: "needs_review", label: "Voltar para Revisar", targetFilter: "needs_review", tone: "review" },
    ],
  });
  assert.deepEqual(filters.buildProductQuickFilterEmptyState("needs_review", options, 0, 4), {
    title: "Nenhum item para revisar.",
    detail: "Os 4 itens atuais nao possuem pendencias deste filtro.",
    actions: [{ key: "all", label: "Mostrar todos", targetFilter: "all", tone: "neutral" }],
  });
  assert.deepEqual(filters.buildProductQuickFilterEmptyState("needs_review", options, 0, 1), {
    title: "Nenhum item para revisar.",
    detail: "O item atual nao possui pendencias deste filtro.",
    actions: [{ key: "all", label: "Mostrar todos", targetFilter: "all", tone: "neutral" }],
  });
  assert.deepEqual(filters.buildProductQuickFilterEmptyState("missing_code", options, 0, 1), {
    title: "Nenhum item em Sem codigo.",
    detail: "Existe 1 item na lista fora deste recorte.",
    actions: [
      { key: "all", label: "Mostrar todos", targetFilter: "all", tone: "neutral" },
      { key: "needs_review", label: "Voltar para Revisar", targetFilter: "needs_review", tone: "review" },
    ],
  });
});

test("builds a search empty state with a clear recovery path", () => {
  assert.deepEqual(filters.buildProductSearchEmptyState("solira", 3), {
    title: "Nenhum resultado para solira.",
    detail: "A busca foi aplicada em 3 itens visiveis do recorte atual.",
    actions: [],
    searchActive: true,
    searchQuery: "solira",
  });
  assert.deepEqual(filters.buildProductSearchEmptyState("  ", 1), {
    title: "Nenhum resultado encontrado.",
    detail: "A busca foi aplicada em 1 item visivel do recorte atual.",
    actions: [],
    searchActive: true,
    searchQuery: "",
  });
});
