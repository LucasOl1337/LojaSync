from __future__ import annotations

import base64
import io
import os
import unittest
from unittest.mock import patch

import httpx

from app.interfaces.api.http.jobs.llm import (
    _raise_zai_for_status,
    allow_local_validation_guard,
    llm_base_url,
    post_llm_chat,
    upload_llm_file,
)
from app.interfaces.api.http.jobs.runtime import _build_no_usable_content_error


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.text = str(payload)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _FakeClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return _FakeResponse(self.payload)


class LlmProviderTests(unittest.TestCase):
    def test_kimi_upload_prepares_image_for_multimodal_chat(self) -> None:
        client = _FakeClient({})

        with patch.dict(
            os.environ,
            {
                "LOJASYNC_LLM_PROVIDER": "kimi",
                "LLM_PROVIDER": "kimi",
                "KIMI_API_KEY": "test-key",
                "KIMI_MODEL": "kimi-for-coding",
            },
            clear=False,
        ):
            result = upload_llm_file(
                client,  # type: ignore[arg-type]
                job_id="job123456",
                contents=b"fake-image",
                filename="nota.png",
                content_type="image/png",
            )

        self.assertEqual(client.calls, [])
        self.assertEqual(result["provider"], "kimi_code_vision")
        self.assertEqual(result["model"], "kimi-for-coding")
        self.assertEqual(result["documents"], [])
        self.assertEqual(result["images"][0]["name"], "nota.png#p1")
        self.assertTrue(result["images"][0]["data"])

    def test_kimi_chat_uses_k27_code_without_incompatible_parameters(self) -> None:
        client = _FakeClient({"choices": [{"message": {"content": '{"items":[]}'}}]})

        with patch.dict(
            os.environ,
            {
                "LOJASYNC_LLM_PROVIDER": "kimi-code",
                "LLM_PROVIDER": "kimi-code",
                "KIMI_API_KEY": "test-key",
                "KIMI_BASE_URL": "https://api.kimi.com/coding/v1",
                "KIMI_MODEL": "kimi-for-coding",
            },
            clear=False,
        ):
            content, saved_file = post_llm_chat(
                client,  # type: ignore[arg-type]
                job_id="job123456",
                message="Extraia produtos em JSON.",
                documents=[{"name": "nota.txt", "content": "Produto A 2 10,00"}],
                images=[{"name": "nota.png#p1", "mime": "image/png", "data": "abc123"}],
            )
            configured_base_url = llm_base_url()
            local_guard_enabled = allow_local_validation_guard()

        self.assertEqual(saved_file, None)
        self.assertEqual(content, '{"items":[]}')
        self.assertEqual(configured_base_url, "https://api.kimi.com/coding/v1")
        self.assertFalse(local_guard_enabled)
        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertEqual(call["url"], "https://api.kimi.com/coding/v1/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-key")  # type: ignore[index]
        self.assertEqual(call["json"]["model"], "kimi-for-coding")  # type: ignore[index]
        self.assertNotIn("temperature", call["json"])  # type: ignore[operator]
        self.assertNotIn("thinking", call["json"])  # type: ignore[operator]
        content_blocks = call["json"]["messages"][0]["content"]  # type: ignore[index]
        self.assertEqual(content_blocks[0]["type"], "image_url")
        self.assertEqual(content_blocks[0]["image_url"]["url"], "data:image/png;base64,abc123")
        self.assertIn("Produto A 2 10,00", content_blocks[1]["text"])

    def test_kimi_can_enable_local_guard_only_with_explicit_opt_in(self) -> None:
        with patch.dict(
            os.environ,
            {"LOJASYNC_LLM_PROVIDER": "kimi", "KIMI_ALLOW_LOCAL_GUARD": "true"},
            clear=False,
        ):
            self.assertTrue(allow_local_validation_guard())

    def test_legacy_upload_slices_rendered_pdf_images_for_ocr(self) -> None:
        try:
            from PIL import Image  # type: ignore
        except Exception:
            self.skipTest("Pillow is required to exercise image slicing")

        buffer = io.BytesIO()
        Image.new("RGB", (4, 8), color="white").save(buffer, format="PNG")
        client = _FakeClient(
            {
                "documents": [],
                "images": [
                    {
                        "name": "romaneio.pdf#p1",
                        "mime": "image/png",
                        "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
                    }
                ],
                "errors": [],
            }
        )

        with patch.dict(
            os.environ,
            {
                "LOJASYNC_LLM_PROVIDER": "legacy",
                "LLM_PROVIDER": "legacy",
                "LLM_BASE_URL": "http://127.0.0.1:8002",
                "LLM_VISION_PAGE_SLICES": "2",
            },
            clear=False,
        ):
            result = upload_llm_file(
                client,  # type: ignore[arg-type]
                job_id="job123456",
                contents=b"%PDF-1.4",
                filename="romaneio.pdf",
                content_type="application/pdf",
            )

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["url"], "http://127.0.0.1:8002/api/upload")
        self.assertEqual(len(result["images"]), 2)
        self.assertEqual(result["images"][0]["name"], "romaneio.pdf#p1#slice1")
        self.assertEqual(result["images"][1]["name"], "romaneio.pdf#p1#slice2")
        self.assertEqual(result["data_info"]["page_slices"], 2)
        self.assertEqual(result["data_info"]["original_images"], 1)

    def test_zai_upload_uses_glm_ocr_layout_parsing(self) -> None:
        client = _FakeClient(
            {
                "model": "GLM-OCR",
                "md_results": "# Nota\nLinha de produto",
                "usage": {"total_tokens": 12},
                "data_info": {"num_pages": 1},
            }
        )

        with patch.dict(
            os.environ,
            {
                "LOJASYNC_LLM_PROVIDER": "zai",
                "LLM_PROVIDER": "zai",
                "ZAI_API_KEY": "test-key",
                "ZAI_UPLOAD_MODE": "ocr",
            },
            clear=False,
        ):
            result = upload_llm_file(
                client,  # type: ignore[arg-type]
                job_id="job123456",
                contents=b"%PDF-1.4",
                filename="nota.pdf",
                content_type="application/pdf",
            )

        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertEqual(call["url"], "https://api.z.ai/api/paas/v4/layout_parsing")
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-key")  # type: ignore[index]
        self.assertEqual(call["json"]["model"], "glm-ocr")  # type: ignore[index]
        self.assertTrue(str(call["json"]["file"]).startswith("data:application/pdf;base64,"))  # type: ignore[index]
        self.assertEqual(result["provider"], "zai")
        self.assertEqual(result["documents"], [{"name": "nota.pdf", "content": "# Nota\nLinha de produto"}])
        self.assertEqual(result["usage"], {"total_tokens": 12})

    def test_zai_upload_defaults_to_coding_vision_for_images(self) -> None:
        client = _FakeClient({})

        with patch.dict(
            os.environ,
            {"LOJASYNC_LLM_PROVIDER": "zai", "LLM_PROVIDER": "zai", "ZAI_API_KEY": "test-key"},
            clear=False,
        ):
            result = upload_llm_file(
                client,  # type: ignore[arg-type]
                job_id="job123456",
                contents=b"fake-image",
                filename="nota.png",
                content_type="image/png",
            )

        self.assertEqual(client.calls, [])
        self.assertEqual(result["provider"], "zai_vision")
        self.assertEqual(result["model"], "glm-4.6v")
        self.assertEqual(result["documents"], [])
        self.assertEqual(result["images"][0]["name"], "nota.png#p1")
        self.assertEqual(result["images"][0]["mime"], "image/png")
        self.assertTrue(result["images"][0]["data"])

    def test_zai_chat_uses_glm_chat_completion_with_document_text(self) -> None:
        client = _FakeClient({"choices": [{"message": {"content": '{"items":[]}'}}]})

        with patch.dict(
            os.environ,
            {"LOJASYNC_LLM_PROVIDER": "zai", "LLM_PROVIDER": "zai", "ZAI_API_KEY": "test-key"},
            clear=False,
        ):
            content, saved_file = post_llm_chat(
                client,  # type: ignore[arg-type]
                job_id="job123456",
                message="Extraia produtos em JSON.",
                documents=[{"name": "nota.md", "content": "Produto A 2 10,00"}],
                images=[],
            )

        self.assertEqual(saved_file, None)
        self.assertEqual(content, '{"items":[]}')
        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertEqual(call["url"], "https://api.z.ai/api/coding/paas/v4/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-key")  # type: ignore[index]
        self.assertEqual(call["json"]["model"], "glm-5.1")  # type: ignore[index]
        self.assertEqual(call["json"]["thinking"], {"type": "disabled"})  # type: ignore[index]
        prompt = call["json"]["messages"][0]["content"]  # type: ignore[index]
        self.assertIn("Extraia produtos em JSON.", prompt)
        self.assertIn("Produto A 2 10,00", prompt)

    def test_zai_chat_sends_image_blocks_to_vision_model(self) -> None:
        client = _FakeClient({"choices": [{"message": {"content": '{"items":[]}'}}]})

        with patch.dict(
            os.environ,
            {"LOJASYNC_LLM_PROVIDER": "zai", "LLM_PROVIDER": "zai", "ZAI_API_KEY": "test-key"},
            clear=False,
        ):
            content, saved_file = post_llm_chat(
                client,  # type: ignore[arg-type]
                job_id="job123456",
                message="Extraia produtos em JSON.",
                documents=[],
                images=[{"name": "nota.png#p1", "mime": "image/png", "data": "abc123"}],
            )

        self.assertEqual(saved_file, None)
        self.assertEqual(content, '{"items":[]}')
        call = client.calls[0]
        self.assertEqual(call["url"], "https://api.z.ai/api/coding/paas/v4/chat/completions")
        self.assertEqual(call["json"]["model"], "glm-4.6v")  # type: ignore[index]
        content_blocks = call["json"]["messages"][0]["content"]  # type: ignore[index]
        self.assertEqual(content_blocks[0]["type"], "image_url")
        self.assertEqual(content_blocks[0]["image_url"]["url"], "data:image/png;base64,abc123")
        self.assertEqual(content_blocks[1]["type"], "text")
        self.assertIn("Extraia produtos em JSON.", content_blocks[1]["text"])

    def test_zai_upload_falls_back_to_local_text_when_paid_ocr_has_no_balance(self) -> None:
        response = httpx.Response(
            429,
            json={"error": {"code": "1113", "message": "Insufficient balance or no resource package. Please recharge."}},
            request=httpx.Request("POST", "https://api.z.ai/api/paas/v4/layout_parsing"),
        )

        class _FailingClient:
            def post(self, url: str, **kwargs: object) -> httpx.Response:
                return response

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "zai",
                "LOJASYNC_LLM_PROVIDER": "zai",
                "ZAI_API_KEY": "test-key",
                "ZAI_UPLOAD_MODE": "ocr",
                "ZAI_ALLOW_LOCAL_TEXT_FALLBACK": "true",
            },
            clear=False,
        ):
            with patch(
                "app.interfaces.api.http.jobs.llm.decode_text_content",
                return_value=("texto local extraido", []),
            ):
                result = upload_llm_file(
                    _FailingClient(),  # type: ignore[arg-type]
                    job_id="job123456",
                    contents=b"%PDF-1.4",
                    filename="nota.pdf",
                    content_type="application/pdf",
                )

        self.assertEqual(result["provider"], "zai_local_text_fallback")
        self.assertEqual(result["documents"], [{"name": "nota.pdf", "content": "texto local extraido"}])
        self.assertTrue(str(result["errors"][0]).startswith("ZAI OCR indisponivel"))

    def test_zai_http_error_preserves_provider_message(self) -> None:
        response = httpx.Response(
            429,
            json={"error": {"code": "1113", "message": "Insufficient balance or no resource package. Please recharge."}},
            request=httpx.Request("POST", "https://api.z.ai/api/paas/v4/layout_parsing"),
        )

        with self.assertRaisesRegex(RuntimeError, "Insufficient balance"):
            _raise_zai_for_status(response)

    def test_zai_balance_error_is_shown_as_actionable_import_error(self) -> None:
        message = _build_no_usable_content_error(
            skip_local_parser=True,
            metrics={"llm_last_error": "ZAI API retornou HTTP 429: Insufficient balance or no resource package. Please recharge."},
        )

        self.assertIn("sem saldo ou pacote ativo", message)

    def test_zai_balance_error_handles_bigmodel_chinese_message(self) -> None:
        message = _build_no_usable_content_error(
            skip_local_parser=True,
            metrics={"llm_last_error": "ZAI API retornou HTTP 429: 余额不足或无可用资源包,请充值。"},
        )

        self.assertIn("sem saldo ou pacote ativo", message)


if __name__ == "__main__":
    unittest.main()
