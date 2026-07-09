from __future__ import annotations

from unittest.mock import patch

from tools import agent_run


def test_main_accepts_path_override_for_placeholder_action() -> None:
    index = {
        "actions": [
            {
                "name": "products.delete",
                "method": "DELETE",
                "path": "/products/{ordering_key}",
                "body": None,
            }
        ]
    }

    with (
        patch.object(agent_run.sys, "argv", ["agent_run.py", "run", "products.delete", "--path", "/products/abc123"]),
        patch.object(agent_run, "load_index", return_value=index),
        patch.object(agent_run, "request_json", return_value=(200, {"status": "deleted"})) as request_json,
    ):
        assert agent_run.main() == 0

    request_json.assert_called_once_with(
        agent_run.DEFAULT_BASE,
        "DELETE",
        "/products/abc123",
        body=None,
        dry_run=False,
    )


def test_cmd_run_requires_path_override_for_placeholder_action() -> None:
    index = {
        "actions": [
            {
                "name": "products.delete",
                "method": "DELETE",
                "path": "/products/{ordering_key}",
                "body": None,
            }
        ]
    }

    with patch.object(agent_run, "request_json") as request_json:
        assert agent_run.cmd_run(agent_run.DEFAULT_BASE, index, "products.delete", False, None) == 2

    request_json.assert_not_called()
