from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from tools import agent_run


def _index() -> dict[str, object]:
    return {
        "actions": [
            {
                "name": "products.delete",
                "method": "DELETE",
                "path": "/products/{ordering_key}",
                "body": None,
            }
        ]
    }


class AgentRunCliTests(unittest.TestCase):
    def test_placeholder_action_requires_concrete_path(self) -> None:
        with patch("tools.agent_run.request_json") as request_json:
            result = agent_run.cmd_run(
                agent_run.DEFAULT_BASE,
                _index(),
                "products.delete",
                dry_run=False,
                body_json=None,
            )

        self.assertEqual(result, 2)
        request_json.assert_not_called()

    def test_path_override_runs_placeholder_action(self) -> None:
        with patch("tools.agent_run.request_json", return_value=(200, {"deleted": True})) as request_json:
            result = agent_run.cmd_run(
                agent_run.DEFAULT_BASE,
                _index(),
                "products.delete",
                dry_run=False,
                body_json=None,
                path_override="/products/item-1",
            )

        self.assertEqual(result, 0)
        request_json.assert_called_once_with(
            agent_run.DEFAULT_BASE,
            "DELETE",
            "/products/item-1",
            body=None,
            dry_run=False,
        )

    def test_main_accepts_path_override(self) -> None:
        argv = ["agent_run.py", "run", "products.delete", "--path", "/products/item-1"]
        with (
            patch.object(sys, "argv", argv),
            patch("tools.agent_run.load_index", return_value=_index()),
            patch("tools.agent_run.request_json", return_value=(200, {"deleted": True})) as request_json,
        ):
            result = agent_run.main()

        self.assertEqual(result, 0)
        request_json.assert_called_once_with(
            agent_run.DEFAULT_BASE,
            "DELETE",
            "/products/item-1",
            body=None,
            dry_run=False,
        )

    def test_rejects_relative_path_override(self) -> None:
        with patch("tools.agent_run.request_json") as request_json:
            result = agent_run.cmd_run(
                agent_run.DEFAULT_BASE,
                _index(),
                "products.delete",
                dry_run=False,
                body_json=None,
                path_override="products/item-1",
            )

        self.assertEqual(result, 2)
        request_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
