import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tllac"))

from app.routes.chat import ChatRequest


class ChatRequestTests(unittest.TestCase):
    def test_accepts_optional_context_fields(self):
        request = ChatRequest(
            query="What remedy is available?",
            session_id="session-1",
            matter_id="matter-1",
            personalization={"baseStyle": "Concise", "memoryEnabled": True},
        )

        self.assertEqual(request.matter_id, "matter-1")
        self.assertEqual(
            request.personalization,
            {"baseStyle": "Concise", "memoryEnabled": True},
        )

    def test_context_fields_are_optional(self):
        request = ChatRequest(query="Explain bail")

        self.assertIsNone(request.matter_id)
        self.assertIsNone(request.personalization)


if __name__ == "__main__":
    unittest.main()
