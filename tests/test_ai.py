"""Pruebas sintéticas del Rol A: sin red ni consumo de cuota."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from reciclaclaro.ai import identify
from reciclaclaro.contracts import AnalysisRequest, ReciclaClaroError


# Cabecera sintética para probar transporte; no es una foto ni prueba de visión.
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic"
PROPOSAL = {"items": [{
    "description": "Envase sin símbolo", "proposed_material": "desconocido",
    "visible_evidence": "No se distingue el símbolo", "proposed_presentation": "botella",
    "pending_questions": [{"attribute": "resin_code", "question": "¿Qué número aparece?"}],
}]}


def response(text=None, *, reason="STOP", parts=None):
    return io.BytesIO(json.dumps({"candidates": [{
        "finishReason": reason,
        "content": {"parts": parts if parts is not None else [
            {"text": text if text is not None else json.dumps(PROPOSAL)},
        ]},
    }]}).encode())


class IdentificationTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"GEMINI_API_KEY": "test-only", "GEMMA_MODEL": "gemma-4-26b-a4b-it"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.req = AnalysisRequest(image_bytes=PNG, mime_type="image/png")

    @patch("reciclaclaro.ai.client.urlopen")
    def test_success_keeps_uncertainty_generates_ids_and_sends_image(self, send):
        send.return_value = response()
        result = identify(self.req)
        self.assertFalse(result.is_mock)
        self.assertEqual(result.model_id, "gemma-4-26b-a4b-it")
        self.assertGreaterEqual(result.latency_ms, 0)
        item = result.items[0]
        self.assertEqual(item.analysis_id, result.analysis_id)
        self.assertTrue(item.item_id.startswith(result.analysis_id))
        self.assertEqual(item.proposed_material.value, "desconocido")
        self.assertEqual(item.pending_question, item.pending_questions[0].question)
        request = send.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["contents"][0]["parts"][1]["inlineData"]["mimeType"], "image/png")
        self.assertNotIn("test-only", request.full_url)
        self.assertEqual(send.call_args.kwargs["timeout"], 30)

    @patch("reciclaclaro.ai.client.urlopen")
    def test_mock_is_explicit_and_never_uses_network(self, send):
        result = identify(self.req, mock=True)
        self.assertTrue(result.is_mock)
        self.assertIn("sintética", result.items[0].visible_evidence)
        send.assert_not_called()

    @patch("reciclaclaro.ai.client.urlopen")
    def test_invalid_schema_is_retried_once_with_validation_error(self, send):
        send.side_effect = [response('{"items":[{"proposed_material":"inventado"}]}'), response()]
        result = identify(self.req)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(send.call_count, 2)
        second_prompt = json.loads(send.call_args.args[0].data)["contents"][0]["parts"][0]["text"]
        self.assertIn("Error de validación", second_prompt)
        self.assertIn("enum", second_prompt)

    @patch("reciclaclaro.ai.client.urlopen")
    def test_repeated_invalid_json_returns_controlled_error(self, send):
        send.side_effect = [response("not json"), response("not json")]
        with self.assertRaises(ReciclaClaroError) as caught:
            identify(self.req)
        self.assertEqual(caught.exception.error.category, "formato_invalido")
        self.assertEqual(send.call_count, 2)

    @patch("reciclaclaro.ai.client.urlopen")
    def test_empty_scene_is_valid(self, send):
        send.return_value = response('{"items":[]}')
        self.assertEqual(identify(self.req).items, [])

    @patch("reciclaclaro.ai.client.urlopen")
    def test_fenced_json_is_accepted_and_thoughts_are_excluded(self, send):
        send.return_value = response(parts=[
            {"thought": True, "text": "Internal reasoning"},
            {"text": "```json\n" + json.dumps(PROPOSAL) + "\n```"},
        ])
        self.assertEqual(len(identify(self.req).items), 1)

    @patch("reciclaclaro.ai.client.urlopen")
    def test_api_errors_are_classified_without_leaking_details(self, send):
        for status, retryable in [(400, False), (403, False), (429, True), (503, True)]:
            with self.subTest(status=status):
                send.reset_mock()
                send.side_effect = HTTPError("https://secret.invalid", status, "secret", {}, None)
                with self.assertRaises(ReciclaClaroError) as caught:
                    identify(self.req)
                self.assertEqual(caught.exception.error.category, "api")
                self.assertEqual(caught.exception.error.retryable, retryable)
                self.assertNotIn("secret", str(caught.exception))
                self.assertEqual(send.call_count, 1)

    @patch("reciclaclaro.ai.client.urlopen")
    def test_timeouts_and_connection_failures_are_controlled(self, send):
        for error, category in [(TimeoutError(), "timeout"), (URLError(TimeoutError()), "timeout"),
                                (URLError("offline"), "api")]:
            with self.subTest(category=category):
                send.side_effect = error
                with self.assertRaises(ReciclaClaroError) as caught:
                    identify(self.req)
                self.assertEqual(caught.exception.error.category, category)
                self.assertTrue(caught.exception.error.retryable)

    @patch("reciclaclaro.ai.client.urlopen")
    def test_invalid_input_and_local_backend_do_not_use_network(self, send):
        for data, mime, backend in [(b"", "image/png", "gemini_api"),
                                    (b"invalid", "image/png", "gemini_api"),
                                    (PNG, "image/jpeg", "gemini_api"),
                                    (PNG + b"x" * (5 * 1024 * 1024), "image/png", "gemini_api"),
                                    (PNG, "image/png", "local")]:
            with self.subTest(mime=mime, backend=backend):
                with self.assertRaises(ReciclaClaroError) as caught:
                    identify(AnalysisRequest(image_bytes=data, mime_type=mime, backend=backend))
                self.assertEqual(caught.exception.error.category, "entrada_invalida")
        send.assert_not_called()

    @patch("reciclaclaro.ai.client.urlopen")
    def test_missing_key_does_not_use_network(self, send):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            with self.assertRaises(ReciclaClaroError) as caught:
                identify(self.req)
        self.assertEqual(caught.exception.error.category, "api")
        send.assert_not_called()

    @patch("reciclaclaro.ai.client.urlopen")
    def test_disallowed_model_is_not_sent(self, send):
        with patch.dict("os.environ", {"GEMMA_MODEL": "other-model"}):
            with self.assertRaises(ReciclaClaroError):
                identify(self.req)
        send.assert_not_called()

    @patch("reciclaclaro.ai.client.urlopen")
    def test_new_analysis_has_new_identity(self, send):
        first = identify(self.req, mock=True)
        second = identify(self.req, mock=True)
        self.assertNotEqual(first.analysis_id, second.analysis_id)
        self.assertNotEqual(first.items[0].item_id, second.items[0].item_id)

    @patch("reciclaclaro.ai.client.urlopen")
    def test_truncated_or_blocked_response_is_not_presented_as_valid(self, send):
        send.side_effect = [response(reason="MAX_TOKENS"), response(reason="SAFETY")]
        with self.assertRaises(ReciclaClaroError) as caught:
            identify(self.req)
        self.assertEqual(caught.exception.error.category, "formato_invalido")

    @patch("reciclaclaro.ai.client.urlopen")
    def test_model_cannot_supply_ids_or_metadata(self, send):
        invented = {"items": [{**PROPOSAL["items"][0], "item_id": "invented"}], "model_id": "fake"}
        send.side_effect = [response(json.dumps(invented)), response()]
        result = identify(self.req)
        self.assertNotEqual(result.items[0].item_id, "invented")
        self.assertEqual(send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
