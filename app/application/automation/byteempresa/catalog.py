from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Iterable

PRODUCTS_WINDOW_CLASS = "TFormProdutos"
MAIN_WINDOW_CLASS = "TFormPrincipal"
WARNING_WINDOW_CLASS = "#32770"
SEARCH_WINDOW_CLASS = "TFormBuscaPadrao"

CATEGORY_LETTERS = {
    "masculino": "m",
    "feminino": "f",
    "infantil": "i",
    "acessorios": "a",
}


@dataclass(frozen=True, slots=True)
class FieldLayout:
    class_name: str
    center_ratio: tuple[float, float]


FIELD_LAYOUTS: dict[str, FieldLayout] = {
    "descricao": FieldLayout("TDBEdit", (0.2817, 0.2223)),
    "grupo": FieldLayout("TDBLookupComboBox", (0.8204, 0.2223)),
    "cod_fabricante": FieldLayout("TDBEdit", (0.5337, 0.4023)),
    "preco_compra": FieldLayout("TDBEdit", (0.8491, 0.4023)),
    "quantidade": FieldLayout("TDBEdit", (0.8985, 0.3423)),
    "preco_venda": FieldLayout("TDBEdit", (0.5608, 0.4608)),
}


def native_byteempresa_available() -> bool:
    from app.application.automation.byteempresa.session import PYWINAUTO_AVAILABLE

    return bool(PYWINAUTO_AVAILABLE)


def category_letter(categoria: str | None) -> str:
    normalized = str(categoria or "").strip().casefold()
    return CATEGORY_LETTERS.get(normalized, "m")


def normalize_button_title(title: str) -> str:
    return str(title or "").replace("&", "").strip().casefold()


def classify_products_mode(button_states: dict[str, bool | None]) -> str:
    normalized = {normalize_button_title(key): value for key, value in button_states.items()}
    browse = (
        normalized.get("novo") is True
        and normalized.get("alterar") is True
        and normalized.get("excluir") is True
        and normalized.get("busca") is True
        and normalized.get("salvar") is False
        and normalized.get("cancela") is False
    )
    if browse:
        return "browse"
    editing = (
        normalized.get("salvar") is True
        and normalized.get("cancela") is True
        and normalized.get("novo") is False
        and normalized.get("alterar") is False
        and normalized.get("excluir") is False
        and normalized.get("busca") is False
    )
    if editing:
        return "editing"
    return "unknown"


def pick_best_rectangle(
    root_rect: tuple[int, int, int, int],
    center_ratio: tuple[float, float],
    candidate_rects: Iterable[tuple[int, int, int, int]],
) -> tuple[int, int, int, int] | None:
    left, top, right, bottom = root_rect
    width = max(1, right - left)
    height = max(1, bottom - top)
    target_x = left + width * center_ratio[0]
    target_y = top + height * center_ratio[1]
    best_rect: tuple[int, int, int, int] | None = None
    best_distance = math.inf
    for rect in candidate_rects:
        center_x = (rect[0] + rect[2]) / 2
        center_y = (rect[1] + rect[3]) / 2
        distance = math.hypot(center_x - target_x, center_y - target_y)
        if distance < best_distance:
            best_distance = distance
            best_rect = rect
    return best_rect


class ByteEmpresaCatalogError(RuntimeError):
    """Falha na automacao nativa do cadastro ByteEmpresa."""


class ByteEmpresaCatalogDriver:
    def __init__(self, backend: str = "win32") -> None:
        if not native_byteempresa_available():
            raise ByteEmpresaCatalogError(
                "pywinauto nao esta disponivel neste ambiente. Instale pywinauto/comtypes para usar a automacao nativa."
            )
        from app.application.automation.byteempresa.session import ByteEmpresaSession

        self._backend = backend
        self._session = ByteEmpresaSession.attach(backend=backend)

    def inspect_context(self) -> dict[str, Any]:
        self._refresh()
        interaction = self._session.interaction_candidate()
        context: dict[str, Any] = {
            "main_window": self._session.candidate.to_dict(),
            "interaction_window": interaction.to_dict(),
            "top_level_windows": [item.to_dict() for item in self._session.significant_windows()],
            "findings": [item.to_dict() for item in self._session.health_findings()],
        }
        if interaction.class_name == PRODUCTS_WINDOW_CLASS:
            context["products_mode"] = self._products_mode()
        return context

    def prepare_catalog_window(self) -> dict[str, Any]:
        self._ensure_products_window()
        self._dismiss_known_modal_if_present()
        self._select_tab("Cadastro")
        self._ensure_browse_mode()
        return self.inspect_context()

    def submit_product(self, payload: dict[str, Any], cancel_event: Any | None = None) -> bool:
        self._check_cancel(cancel_event)
        self.prepare_catalog_window()
        self._click_products_button("Novo")
        self._wait_for_products_mode("editing")
        self._select_tab("Cadastro")
        self._fill_text_field("descricao", str(payload.get("descricao_completa") or payload.get("nome") or ""))
        self._fill_combo_with_letter("grupo", category_letter(str(payload.get("categoria") or "")))
        self._fill_text_field("cod_fabricante", str(payload.get("codigo") or ""))
        self._fill_text_field("preco_compra", str(payload.get("preco") or ""))
        self._fill_text_field("quantidade", str(payload.get("quantidade") or ""))
        self._fill_text_field("preco_venda", str(payload.get("preco_final") or payload.get("preco") or ""))
        self._check_cancel(cancel_event)
        self._click_products_button("Salvar")
        return self._wait_for_save_result()

    def _refresh(self) -> None:
        self._session.refresh()

    def _check_cancel(self, cancel_event: Any | None) -> None:
        if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
            raise KeyboardInterrupt("Automacao cancelada pelo usuario")

    def _ensure_products_window(self) -> None:
        self._refresh()
        interaction = self._session.interaction_candidate()
        if interaction.class_name == PRODUCTS_WINDOW_CLASS:
            return
        self._open_products_from_main()
        self._wait_for_products_window()

    def _wait_for_products_window(self, timeout: float = 6.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._refresh()
            if self._session.interaction_candidate().class_name == PRODUCTS_WINDOW_CLASS:
                return
            time.sleep(0.2)
        raise ByteEmpresaCatalogError("Nao foi possivel abrir a tela 'Cadastro de Mercadorias'.")

    def _open_products_from_main(self) -> None:
        main_wrapper = None
        for item in self._session.significant_windows():
            if item.class_name == MAIN_WINDOW_CLASS or item.title.startswith("Byte Empresa - "):
                main_wrapper = self._session.app.window(handle=item.handle)
                break
        if main_wrapper is None:
            raise ByteEmpresaCatalogError("Janela principal do ByteEmpresa nao encontrada para abrir o cadastro.")

        menu_bars = self._find_descendants(main_wrapper, class_name="TRibbonApplicationMenuBar")
        if not menu_bars:
            raise ByteEmpresaCatalogError("Nao foi possivel localizar o menu principal do ByteEmpresa.")
        self._invoke(menu_bars[0])
        time.sleep(0.4)

        self._refresh()
        popup_wrapper = None
        for item in self._session.significant_windows():
            if item.class_name == "TRibbonApplicationPopupMenu":
                popup_wrapper = self._session.app.window(handle=item.handle)
                break
        if popup_wrapper is None:
            popup_wrapper = main_wrapper

        estoque = self._find_by_title(popup_wrapper, "Estoque")
        if estoque is None:
            raise ByteEmpresaCatalogError("Nao foi possivel localizar o item 'Estoque' para abrir o cadastro.")
        self._invoke(estoque)
        time.sleep(0.6)

    def _dismiss_known_modal_if_present(self) -> None:
        self._refresh()
        interaction = self._session.interaction_candidate()
        if interaction.class_name == WARNING_WINDOW_CLASS:
            self._dismiss_warning()
        elif interaction.class_name == SEARCH_WINDOW_CLASS:
            self._dismiss_search()

    def _dismiss_warning(self) -> None:
        wrapper = self._session.interaction_window()
        ok_button = self._find_by_title(wrapper, "OK", class_name="Button")
        if ok_button is None:
            raise ByteEmpresaCatalogError("Modal 'Warning' detectado, mas o botao OK nao foi localizado.")
        self._invoke(ok_button)
        time.sleep(0.3)

    def _dismiss_search(self) -> None:
        wrapper = self._session.interaction_window()
        cancel_button = self._find_by_title(wrapper, "Cancela", class_name="TBitBtn") or self._find_by_title(
            wrapper, "&Cancela", class_name="TBitBtn"
        )
        if cancel_button is None:
            raise ByteEmpresaCatalogError("Modal 'Pesquisar' detectado, mas o botao Cancela nao foi localizado.")
        self._invoke(cancel_button)
        time.sleep(0.3)

    def _ensure_browse_mode(self) -> None:
        mode = self._products_mode()
        if mode == "browse":
            return
        if mode == "editing":
            self._click_products_button("Cancela")
            self._wait_for_products_mode("browse")
            return
        raise ByteEmpresaCatalogError("A tela de produtos nao esta em um estado reconhecido para iniciar a automacao.")

    def _products_mode(self) -> str:
        wrapper = self._current_products_window()
        states = {
            "Novo": self._button_enabled(wrapper, "Novo"),
            "Alterar": self._button_enabled(wrapper, "Alterar"),
            "Excluir": self._button_enabled(wrapper, "Excluir"),
            "Salvar": self._button_enabled(wrapper, "Salvar"),
            "Cancela": self._button_enabled(wrapper, "Cancela"),
            "Busca": self._button_enabled(wrapper, "Busca"),
        }
        return classify_products_mode(states)

    def _button_enabled(self, wrapper, title: str) -> bool | None:
        button = self._find_by_title(wrapper, title, class_name="TBitBtn")
        if button is None:
            return None
        try:
            return bool(button.is_enabled())
        except Exception:
            return None

    def _wait_for_products_mode(self, expected_mode: str, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._refresh()
            interaction = self._session.interaction_candidate()
            if interaction.class_name == WARNING_WINDOW_CLASS:
                message = self._extract_modal_message(self._session.interaction_window())
                self._dismiss_warning()
                raise ByteEmpresaCatalogError(f"ByteEmpresa bloqueou o salvamento: {message or 'Warning sem mensagem.'}")
            if interaction.class_name == PRODUCTS_WINDOW_CLASS and self._products_mode() == expected_mode:
                return
            time.sleep(0.2)
        raise ByteEmpresaCatalogError(f"O cadastro nao entrou no estado esperado: {expected_mode}.")

    def _wait_for_save_result(self, timeout: float = 6.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._refresh()
            interaction = self._session.interaction_candidate()
            if interaction.class_name == WARNING_WINDOW_CLASS:
                message = self._extract_modal_message(self._session.interaction_window())
                self._dismiss_warning()
                raise ByteEmpresaCatalogError(f"Falha ao salvar produto: {message or 'Warning sem mensagem.'}")
            if interaction.class_name == PRODUCTS_WINDOW_CLASS and self._products_mode() == "browse":
                return True
            time.sleep(0.2)
        raise ByteEmpresaCatalogError("O ByteEmpresa nao confirmou o retorno ao modo browse apos salvar o produto.")

    def _current_products_window(self):
        self._refresh()
        interaction = self._session.interaction_candidate()
        if interaction.class_name != PRODUCTS_WINDOW_CLASS:
            raise ByteEmpresaCatalogError("A janela interativa atual nao e 'Cadastro de Mercadorias'.")
        return self._session.interaction_window()

    def _click_products_button(self, title: str) -> None:
        wrapper = self._current_products_window()
        button = self._find_by_title(wrapper, title, class_name="TBitBtn")
        if button is None:
            raise ByteEmpresaCatalogError(f"Botao '{title}' nao encontrado na tela de produtos.")
        self._invoke(button)
        time.sleep(0.2)

    def _select_tab(self, title: str) -> None:
        products = self._current_products_window()
        handle = int(products.handle)
        from app.application.automation.byteempresa.session import ByteEmpresaSession

        try:
            uia_session = ByteEmpresaSession.attach(backend="uia", handle=handle)
            root = uia_session.window
        except Exception as exc:
            raise ByteEmpresaCatalogError(f"Nao foi possivel anexar UIA para selecionar a aba '{title}': {exc}") from exc

        tab_title = normalize_button_title(title)
        for wrapper in self._find_descendants(root, control_type="TabItem"):
            if normalize_button_title(self._text(wrapper)) != tab_title:
                continue
            try:
                wrapper.select()
                time.sleep(0.15)
                return
            except Exception as exc:
                raise ByteEmpresaCatalogError(f"Falha ao selecionar a aba '{title}': {exc}") from exc
        raise ByteEmpresaCatalogError(f"Aba '{title}' nao localizada na tela de produtos.")

    def _fill_text_field(self, field_name: str, value: str) -> None:
        text = str(value or "").strip()
        if not text:
            return
        control = self._resolve_field_control(field_name)
        self._type_text(control, text)

    def _fill_combo_with_letter(self, field_name: str, letter: str) -> None:
        combo = self._resolve_field_control(field_name)
        self._type_text(combo, str(letter or "").strip().lower(), clear=False)
        try:
            combo.type_keys("{ENTER}", set_foreground=True)
        except Exception:
            pass
        time.sleep(0.15)

    def _resolve_field_control(self, field_name: str):
        layout = FIELD_LAYOUTS.get(field_name)
        if layout is None:
            raise ByteEmpresaCatalogError(f"Layout do campo '{field_name}' nao configurado.")
        root = self._current_products_window()
        root_rect = self._rect_tuple(root)
        if root_rect is None:
            raise ByteEmpresaCatalogError("Nao foi possivel obter o retangulo da tela de produtos.")
        controls = [
            wrapper
            for wrapper in self._find_descendants(root, class_name=layout.class_name)
            if self._rect_tuple(wrapper) is not None and self._is_visible(wrapper)
        ]
        if not controls:
            raise ByteEmpresaCatalogError(
                f"Nenhum controle da classe '{layout.class_name}' encontrado para o campo '{field_name}'."
            )
        candidate_rects = [self._rect_tuple(wrapper) for wrapper in controls if self._rect_tuple(wrapper) is not None]
        best_rect = pick_best_rectangle(root_rect, layout.center_ratio, candidate_rects)
        if best_rect is None:
            raise ByteEmpresaCatalogError(f"Nao foi possivel resolver o campo '{field_name}' pela geometria da tela.")
        for wrapper in controls:
            if self._rect_tuple(wrapper) == best_rect:
                return wrapper
        raise ByteEmpresaCatalogError(f"Nao foi possivel resolver o controle do campo '{field_name}'.")

    def _extract_modal_message(self, wrapper) -> str:
        texts: list[str] = []
        for candidate in [wrapper, *self._find_descendants(wrapper)]:
            text = self._text(candidate)
            if not text:
                continue
            normalized = normalize_button_title(text)
            if normalized in {"warning", "ok"}:
                continue
            texts.append(text.strip())
        unique: list[str] = []
        seen: set[str] = set()
        for text in texts:
            if text in seen:
                continue
            seen.add(text)
            unique.append(text)
        return " | ".join(unique)

    def _type_text(self, control, text: str, *, clear: bool = True) -> None:
        try:
            control.set_focus()
        except Exception as exc:
            raise ByteEmpresaCatalogError(f"Controle localizado, mas nao foi possivel focar: {exc}") from exc
        try:
            if clear:
                control.type_keys("^a{BACKSPACE}", set_foreground=True)
                time.sleep(0.05)
            control.type_keys(text, with_spaces=True, set_foreground=True)
        except Exception:
            try:
                control.set_edit_text(text)
            except Exception as exc:
                raise ByteEmpresaCatalogError(f"Falha ao digitar no ByteEmpresa: {exc}") from exc
        time.sleep(0.12)

    @staticmethod
    def _invoke(control) -> None:
        last_error: Exception | None = None
        for action in ("click_input", "click", "invoke"):
            try:
                getattr(control, action)()
                return
            except Exception as exc:
                last_error = exc
        raise ByteEmpresaCatalogError(f"Falha ao acionar controle da UI: {last_error}")

    @staticmethod
    def _text(wrapper) -> str:
        try:
            return str(wrapper.window_text() or "")
        except Exception:
            return ""

    @staticmethod
    def _rect_tuple(wrapper) -> tuple[int, int, int, int] | None:
        try:
            rect = wrapper.rectangle()
            return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            return None

    @staticmethod
    def _is_visible(wrapper) -> bool:
        try:
            return bool(wrapper.is_visible())
        except Exception:
            return False

    @staticmethod
    def _find_descendants(wrapper, *, class_name: str | None = None, control_type: str | None = None) -> list:
        matches: list[Any] = []
        seen: set[int] = set()
        try:
            descendants = wrapper.descendants()
        except Exception:
            return matches
        for candidate in descendants:
            try:
                handle = int(candidate.handle)
            except Exception:
                handle = id(candidate)
            if handle in seen:
                continue
            seen.add(handle)
            if class_name is not None:
                try:
                    if candidate.class_name() != class_name:
                        continue
                except Exception:
                    continue
            if control_type is not None:
                if getattr(candidate.element_info, "control_type", None) != control_type:
                    continue
            matches.append(candidate)
        return matches

    def _find_by_title(self, wrapper, title: str, *, class_name: str | None = None):
        target = normalize_button_title(title)
        for candidate in self._find_descendants(wrapper, class_name=class_name):
            if normalize_button_title(self._text(candidate)) == target:
                return candidate
        return None
