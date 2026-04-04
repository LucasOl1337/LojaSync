from __future__ import annotations

import unittest

from app.application.automation.byteempresa.catalog import (
    category_letter,
    classify_products_mode,
    pick_best_rectangle,
)


class ByteEmpresaCatalogHelpersTests(unittest.TestCase):
    def test_classifies_browse_mode(self) -> None:
        mode = classify_products_mode(
            {
                "Novo": True,
                "Alterar": True,
                "Excluir": True,
                "Busca": True,
                "Salvar": False,
                "Cancela": False,
            }
        )
        self.assertEqual("browse", mode)

    def test_classifies_editing_mode(self) -> None:
        mode = classify_products_mode(
            {
                "Novo": False,
                "Alterar": False,
                "Excluir": False,
                "Busca": False,
                "Salvar": True,
                "Cancela": True,
            }
        )
        self.assertEqual("editing", mode)

    def test_picks_closest_rect_by_relative_position(self) -> None:
        root = (500, 200, 1400, 800)
        rect = pick_best_rectangle(
            root,
            (0.30, 0.20),
            [
                (520, 320, 580, 340),
                (600, 320, 930, 340),
                (1150, 320, 1360, 340),
            ],
        )
        self.assertEqual((600, 320, 930, 340), rect)

    def test_maps_category_to_expected_letter(self) -> None:
        self.assertEqual("f", category_letter("Feminino"))
        self.assertEqual("m", category_letter("desconhecida"))
