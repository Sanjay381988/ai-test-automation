"""
E2E Test Suite for AI Test Planner API
Uses FastAPI TestClient to exercise the full request/response cycle.
External services (Jira, Ollama, Groq) are mocked so no live credentials required.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_TICKET = {
    "id": "DEMO-1",
    "key": "DEMO-1",
    "title": "User Login Feature",
    "description": "As a user I want to log in with email and password.",
}

MOCK_CONTENT = {
    "objective": "Validate login flow end-to-end.",
    "scope": "In-scope: login page. Out-of-scope: registration.",
    "test_scenarios": ["Valid credentials login", "Invalid credentials rejection"],
    "risks": "Auth service downtime.",
    "environment": "Staging",
}

MOCK_DOCX_PATH = None  # set during generate tests

# ---------------------------------------------------------------------------
# 1. Health / Root
# ---------------------------------------------------------------------------

class TestRoot:
    def test_docs_reachable(self):
        """OpenAPI docs endpoint should return 200."""
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_schema(self):
        """OpenAPI JSON schema should be valid."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data


# ---------------------------------------------------------------------------
# 2. POST /api/test-alm
# ---------------------------------------------------------------------------

class TestALMConnection:
    def test_jira_success(self):
        with patch("main.test_jira_connection", return_value=True):
            resp = client.post("/api/test-alm", json={
                "provider": "jira",
                "url": "https://example.atlassian.net",
                "email": "user@example.com",
                "token": "fake-token",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_jira_failure(self):
        with patch("main.test_jira_connection", return_value=False):
            resp = client.post("/api/test-alm", json={
                "provider": "jira",
                "url": "https://bad.atlassian.net",
                "email": "user@example.com",
                "token": "wrong-token",
            })
        assert resp.status_code == 400
        assert "ALM Connection Failed" in resp.json()["detail"]

    def test_ado_success(self):
        with patch("main.test_ado_connection", return_value=True):
            resp = client.post("/api/test-alm", json={
                "provider": "ado",
                "url": "https://dev.azure.com/myorg",
                "pat": "fake-pat",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_ado_failure(self):
        with patch("main.test_ado_connection", return_value=False):
            resp = client.post("/api/test-alm", json={
                "provider": "ado",
                "url": "https://dev.azure.com/myorg",
                "pat": "bad-pat",
            })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 3. POST /api/test-llm
# ---------------------------------------------------------------------------

class TestLLMConnection:
    def test_mock_provider_always_passes(self):
        resp = client.post("/api/test-llm", json={
            "provider": "mock",
            "url": "",
            "api_key": "",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_ollama_success(self):
        with patch("main.test_ollama_connection", return_value=True):
            resp = client.post("/api/test-llm", json={
                "provider": "ollama",
                "url": "http://localhost:11434",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_ollama_failure(self):
        with patch("main.test_ollama_connection", return_value=False):
            resp = client.post("/api/test-llm", json={
                "provider": "ollama",
                "url": "http://localhost:11434",
            })
        assert resp.status_code == 400

    def test_groq_success(self):
        with patch("main.test_groq_connection", return_value=True):
            resp = client.post("/api/test-llm", json={
                "provider": "groq",
                "api_key": "gsk_fake",
            })
        assert resp.status_code == 200

    def test_groq_failure(self):
        with patch("main.test_groq_connection", return_value=False):
            resp = client.post("/api/test-llm", json={
                "provider": "groq",
                "api_key": "invalid",
            })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 4. POST /api/generate
# ---------------------------------------------------------------------------

class TestGenerate:
    BASE_PAYLOAD = {
        "alm_provider": "jira",
        "alm_url": "https://example.atlassian.net",
        "alm_email": "user@example.com",
        "alm_token": "fake-token",
        "llm_provider": "mock",
        "llm_model": "mock-model",
        "ticket_id": "DEMO-1",
        "additional_context": "",
    }

    def test_generate_success(self):
        with patch("main.fetch_jira_ticket", return_value=MOCK_TICKET), \
             patch("main.generate_test_plan_docx", return_value=True):
            resp = client.post("/api/generate", json=self.BASE_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "file_name" in data
        assert "html" in data
        assert "data" in data

    def test_generate_alm_error(self):
        with patch("main.fetch_jira_ticket", return_value={"error": "Ticket not found"}):
            resp = client.post("/api/generate", json=self.BASE_PAYLOAD)
        assert resp.status_code == 400
        assert "ALM Error" in resp.json()["detail"]

    def test_generate_docx_failure(self):
        with patch("main.fetch_jira_ticket", return_value=MOCK_TICKET), \
             patch("main.generate_test_plan_docx", return_value=False):
            resp = client.post("/api/generate", json=self.BASE_PAYLOAD)
        assert resp.status_code == 500
        assert "Failed to write docx" in resp.json()["detail"]

    def test_generate_with_ado(self):
        payload = {**self.BASE_PAYLOAD, "alm_provider": "ado", "alm_pat": "fake-pat"}
        with patch("main.fetch_ado_ticket", return_value=MOCK_TICKET), \
             patch("main.generate_test_plan_docx", return_value=True):
            resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 200

    def test_generate_stores_md_file(self):
        with patch("main.fetch_jira_ticket", return_value=MOCK_TICKET), \
             patch("main.generate_test_plan_docx", return_value=True):
            resp = client.post("/api/generate", json=self.BASE_PAYLOAD)
        assert resp.status_code == 200
        md_file = resp.json().get("md_file")
        assert md_file is not None
        assert md_file.endswith(".md")


# ---------------------------------------------------------------------------
# 5. POST /api/preview
# ---------------------------------------------------------------------------

class TestPreview:
    BASE_PAYLOAD = {
        "alm_provider": "jira",
        "alm_url": "https://example.atlassian.net",
        "alm_email": "user@example.com",
        "alm_token": "fake-token",
        "llm_provider": "mock",
        "llm_model": "mock-model",
        "ticket_id": "DEMO-1",
        "additional_context": "",
    }

    def test_preview_success(self):
        with patch("main.fetch_jira_ticket", return_value=MOCK_TICKET):
            resp = client.post("/api/preview", json=self.BASE_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "html" in data
        assert "data" in data

    def test_preview_alm_error(self):
        with patch("main.fetch_jira_ticket", return_value={"error": "Not found"}):
            resp = client.post("/api/preview", json=self.BASE_PAYLOAD)
        assert resp.status_code == 400

    def test_preview_html_not_empty(self):
        with patch("main.fetch_jira_ticket", return_value=MOCK_TICKET):
            resp = client.post("/api/preview", json=self.BASE_PAYLOAD)
        assert len(resp.json()["html"]) > 0


# ---------------------------------------------------------------------------
# 6. GET /api/download/{file_name}
# ---------------------------------------------------------------------------

class TestDownload:
    def test_download_missing_file_returns_404(self):
        resp = client.get("/api/download/nonexistent_file.docx")
        assert resp.status_code == 404
        assert "File not found" in resp.json()["detail"]

    def test_download_docx_after_generate(self):
        with patch("main.fetch_jira_ticket", return_value=MOCK_TICKET), \
             patch("main.generate_test_plan_docx", return_value=True) as mock_docx:
            # Ensure the docx file is actually written so download works
            def write_fake_docx(template, output, content):
                os.makedirs(os.path.dirname(output), exist_ok=True)
                with open(output, "wb") as f:
                    f.write(b"PK\x03\x04fake-docx-content")
                return True
            mock_docx.side_effect = write_fake_docx

            gen_resp = client.post("/api/generate", json={
                "alm_provider": "jira",
                "alm_url": "https://example.atlassian.net",
                "alm_email": "user@example.com",
                "alm_token": "fake-token",
                "llm_provider": "mock",
                "llm_model": "mock-model",
                "ticket_id": "DEMO-1",
            })
        assert gen_resp.status_code == 200
        file_name = gen_resp.json()["file_name"]

        dl_resp = client.get(f"/api/download/{file_name}")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_download_md_after_generate(self):
        with patch("main.fetch_jira_ticket", return_value=MOCK_TICKET), \
             patch("main.generate_test_plan_docx", return_value=True):
            gen_resp = client.post("/api/generate", json={
                "alm_provider": "jira",
                "alm_url": "https://example.atlassian.net",
                "alm_email": "user@example.com",
                "alm_token": "fake-token",
                "llm_provider": "mock",
                "llm_model": "mock-model",
                "ticket_id": "DEMO-1",
            })
        assert gen_resp.status_code == 200
        md_file = gen_resp.json()["md_file"]
        dl_resp = client.get(f"/api/download/{md_file}")
        assert dl_resp.status_code == 200
        assert "text/markdown" in dl_resp.headers["content-type"]


# ---------------------------------------------------------------------------
# 7. Live Integration Tests (real Jira + real GROQ — no mocks)
# Credentials are read from environment variables so secrets are never
# committed to source control.  Set these before running:
#
#   $env:LIVE_JIRA_URL   = "https://<org>.atlassian.net/"
#   $env:LIVE_JIRA_EMAIL = "you@example.com"
#   $env:LIVE_JIRA_TOKEN = "<atlassian-api-token>"
#   $env:LIVE_GROQ_KEY   = "gsk_..."
#   $env:LIVE_TICKET     = "KAN-1"   (optional, defaults to KAN-1)
# ---------------------------------------------------------------------------

LIVE_JIRA_URL   = os.getenv("LIVE_JIRA_URL", "")
LIVE_JIRA_EMAIL = os.getenv("LIVE_JIRA_EMAIL", "")
LIVE_JIRA_TOKEN = os.getenv("LIVE_JIRA_TOKEN", "")
LIVE_GROQ_KEY   = os.getenv("LIVE_GROQ_KEY", "")
LIVE_MODEL      = "llama-3.1-8b-instant"
LIVE_TICKET     = os.getenv("LIVE_TICKET", "KAN-1")

_live_creds_present = all([LIVE_JIRA_URL, LIVE_JIRA_EMAIL, LIVE_JIRA_TOKEN, LIVE_GROQ_KEY])
_live_skip = pytest.mark.skipif(
    not _live_creds_present,
    reason="Live credentials not set — export LIVE_JIRA_URL / LIVE_JIRA_EMAIL / LIVE_JIRA_TOKEN / LIVE_GROQ_KEY"
)


class TestLiveIntegration:
    """
    End-to-end tests against real Jira and GROQ services.
    These tests make real network calls — they verify that the full generate
    pipeline works with actual credentials and that normalize_content() ensures
    all returned fields are plain Python strings / list-of-strings (React-safe).
    """

    @_live_skip
    def test_live_jira_connection(self):
        """Real Jira credentials must connect successfully."""
        resp = client.post("/api/test-alm", json={
            "provider": "jira",
            "url": LIVE_JIRA_URL,
            "email": LIVE_JIRA_EMAIL,
            "token": LIVE_JIRA_TOKEN,
        })
        assert resp.status_code == 200, f"Jira connection failed: {resp.text}"
        assert resp.json()["status"] == "success"

    @_live_skip
    def test_live_groq_connection(self):
        """Real GROQ API key must connect successfully."""
        resp = client.post("/api/test-llm", json={
            "provider": "groq",
            "api_key": LIVE_GROQ_KEY,
        })
        assert resp.status_code == 200, f"GROQ connection failed: {resp.text}"
        assert resp.json()["status"] == "success"

    @_live_skip
    def test_live_generate_full_flow(self):
        """
        Full generate with real Jira + GROQ.
        Verifies:
          - HTTP 200 with status == 'success'
          - docx and md file names are returned
          - html preview is non-empty
          - normalize_content ensured test_scenarios is a list of plain strings
          - all scalar fields (objective, scope, risks, environment) are strings
        """
        resp = client.post("/api/generate", json={
            "alm_provider": "jira",
            "alm_url": LIVE_JIRA_URL,
            "alm_email": LIVE_JIRA_EMAIL,
            "alm_token": LIVE_JIRA_TOKEN,
            "llm_provider": "groq",
            "llm_model": LIVE_MODEL,
            "llm_api_key": LIVE_GROQ_KEY,
            "ticket_id": LIVE_TICKET,
            "additional_context": "",
        })
        assert resp.status_code == 200, f"Generate failed ({resp.status_code}): {resp.text}"
        body = resp.json()
        assert body["status"] == "success", f"Status not success: {body}"
        assert body["file_name"].endswith(".docx"), f"Bad file_name: {body['file_name']}"
        assert body["md_file"].endswith(".md"), f"Bad md_file: {body['md_file']}"
        assert len(body["html"]) > 0, "HTML preview is empty"

        content = body["data"]

        # --- test_scenarios must be a non-empty list of plain strings ---
        scenarios = content.get("test_scenarios", [])
        assert isinstance(scenarios, list), \
            f"test_scenarios must be a list, got {type(scenarios)}: {scenarios}"
        assert len(scenarios) > 0, "test_scenarios must not be empty"
        for i, s in enumerate(scenarios):
            assert isinstance(s, str), \
                f"scenario[{i}] must be a str, got {type(s)}: {s}"

        # --- scalar fields must be plain strings ---
        for field in ["objective", "scope", "risks", "environment"]:
            val = content.get(field, "")
            assert isinstance(val, str), \
                f"'{field}' must be a str, got {type(val)}: {val}"
