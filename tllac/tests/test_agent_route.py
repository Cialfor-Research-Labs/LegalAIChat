from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tllac"))

os.environ.setdefault("APP_SECRET_KEY", "agent-route-test-secret")

from app.db.db_client import db_client
from app.main import app
from app.routes.auth import get_current_user


class AgentRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        db_client._init_memory_store()
        db_client._backend = "memory"
        self.user = db_client.create_user("agent@example.com", "Agent User", "password-123")
        self.matter = db_client.create_matter(
            user_id=self.user["user_id"],
            title="Agent Matter",
            description="Matter for route tests",
        )
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": self.user["user_id"],
            "email": self.user["email"],
            "full_name": self.user["full_name"],
        }

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        os.environ.pop("ADVANCED_AGENT_COMMANDS_ENABLED", None)

    def _request(self, method: str, url: str, **kwargs):
        async def runner():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(runner())

    def test_successful_agent_run(self) -> None:
        response = self._request(
            "POST",
            f"/v1/matters/{self.matter['matter_id']}/agent/run",
            json={"command_text": "/next", "conversation_history": []},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["command"], "/next")
        self.assertIn("Next Action Items", payload["output_text"])

    def test_brief_command_is_available_by_default(self) -> None:
        response = self._request(
            "POST",
            f"/v1/matters/{self.matter['matter_id']}/agent/run",
            json={"command_text": "/brief give details about this case", "conversation_history": []},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["command"], "/brief")
        self.assertIn("Matter:", payload["output_text"])

    def test_missing_matter_returns_404(self) -> None:
        response = self._request(
            "POST",
            "/v1/matters/matter-missing/agent/run",
            json={"command_text": "/next", "conversation_history": []},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Matter not found", response.text)

    def test_missing_documents_returns_clear_error(self) -> None:
        os.environ["ADVANCED_AGENT_COMMANDS_ENABLED"] = "1"
        response = self._request(
            "POST",
            f"/v1/matters/{self.matter['matter_id']}/agent/run",
            json={"command_text": "/review missing-document-id", "conversation_history": []},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Document not found", response.text)

    def test_blank_prompt_is_rejected(self) -> None:
        response = self._request(
            "POST",
            f"/v1/matters/{self.matter['matter_id']}/agent/run",
            json={"command_text": "   ", "conversation_history": []},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("command_text is required", response.text)


if __name__ == "__main__":
    unittest.main()
