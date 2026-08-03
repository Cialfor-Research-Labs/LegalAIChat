import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

os = __import__("os")
os.environ.setdefault("APP_SECRET_KEY", "agent-orchestrator-test-secret")


class _FakeInvalidToken(Exception):
    pass


class _FakeFernet:
    def __init__(self, key: bytes):
        self.key = key

    def encrypt(self, value: bytes) -> bytes:
        return value

    def decrypt(self, value: bytes) -> bytes:
        return value


class _FakeBaseModel:
    def __init__(self, **data):
        annotations = getattr(self.__class__, "__annotations__", {})
        for field in annotations:
            if field in data:
                value = data[field]
            else:
                value = getattr(self.__class__, field, None)
                if value is Ellipsis:
                    raise TypeError(f"{field} is required")
            setattr(self, field, value)
        for key, value in data.items():
            if key not in annotations:
                setattr(self, key, value)

    @classmethod
    def model_validate(cls, data):
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "__dict__") and not isinstance(data, dict):
            data = {key: value for key, value in data.__dict__.items() if not key.startswith("_")}
        return cls(**data)

    def model_dump(self):
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}


def _fake_field(default=None, **kwargs):
    default_factory = kwargs.get("default_factory")
    if default_factory is not None:
        return default_factory()
    return default


pydantic_module = types.ModuleType("pydantic")
pydantic_module.BaseModel = _FakeBaseModel
pydantic_module.Field = _fake_field
sys.modules.setdefault("pydantic", pydantic_module)

dotenv_module = types.ModuleType("dotenv")
dotenv_module.load_dotenv = lambda *args, **kwargs: None
dotenv_module.dotenv_values = lambda *args, **kwargs: {}
sys.modules.setdefault("dotenv", dotenv_module)

cryptography_module = types.ModuleType("cryptography")
fernet_module = types.ModuleType("cryptography.fernet")
fernet_module.Fernet = _FakeFernet
fernet_module.InvalidToken = _FakeInvalidToken
cryptography_module.fernet = fernet_module
sys.modules.setdefault("cryptography", cryptography_module)
sys.modules.setdefault("cryptography.fernet", fernet_module)

psycopg_module = types.ModuleType("psycopg")
psycopg_module.connect = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("psycopg unavailable in tests"))
rows_module = types.ModuleType("psycopg.rows")
rows_module.dict_row = object()
json_module = types.ModuleType("psycopg.types.json")


class _Jsonb:
    def __init__(self, value):
        self.value = value


json_module.Jsonb = _Jsonb
types_module = types.ModuleType("psycopg.types")
types_module.json = json_module
psycopg_module.rows = rows_module
psycopg_module.types = types_module
sys.modules.setdefault("psycopg", psycopg_module)
sys.modules.setdefault("psycopg.rows", rows_module)
sys.modules.setdefault("psycopg.types", types_module)
sys.modules.setdefault("psycopg.types.json", json_module)

boto3_module = types.ModuleType("boto3")
boto3_module.client = lambda *args, **kwargs: types.SimpleNamespace(invoke_model=lambda **kw: (_ for _ in ()).throw(RuntimeError("bedrock unavailable in tests")))
boto3_module.session = types.SimpleNamespace(Session=lambda *args, **kwargs: types.SimpleNamespace(client=lambda service_name: boto3_module.client()))
sys.modules.setdefault("boto3", boto3_module)
botocore_module = types.ModuleType("botocore")
botocore_exceptions = types.ModuleType("botocore.exceptions")


class _FakeClientError(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "Stub"}}


botocore_exceptions.ClientError = _FakeClientError
botocore_module.exceptions = botocore_exceptions
sys.modules.setdefault("botocore", botocore_module)
sys.modules.setdefault("botocore.exceptions", botocore_exceptions)


from tllac.app.db.db_client import db_client
from tllac.app.services.agent_models import AgentRunState
from tllac.app.services.agent_orchestrator import agent_orchestrator


class AgentOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ADVANCED_AGENT_COMMANDS_ENABLED"] = "1"
        db_client._init_memory_store()
        db_client._init_v1_memory_store()
        db_client._backend = "memory"
        self.owner = db_client.create_user("orchestrator@example.com", "Orchestrator Owner", "password-123")
        self.matter = db_client.create_matter(user_id=self.owner["user_id"], title="Orchestrator Matter")

    def tearDown(self) -> None:
        os.environ.pop("ADVANCED_AGENT_COMMANDS_ENABLED", None)

    def test_next_command_remains_read_only(self) -> None:
        user_id = self.owner["user_id"]
        matter_id = self.matter["matter_id"]

        db_client.create_matter_task(
            user_id=user_id,
            matter_id=matter_id,
            title="File appearance",
            due_at="2026-08-01",
        )

        result = agent_orchestrator.run_agent(user_id, matter_id, "/next")

        self.assertEqual(result.status, AgentRunState.COMPLETED)
        self.assertEqual(result.token_count, 0)
        self.assertIn("Next Action Items", result.output_text or "")
        self.assertEqual(len(result.tool_calls), 0)

    def test_timeline_command_remains_read_only(self) -> None:
        user_id = self.owner["user_id"]
        matter_id = self.matter["matter_id"]

        db_client.create_matter_hearing(
            user_id=user_id,
            matter_id=matter_id,
            title="Status Hearing",
            court="Court 2",
        )

        result = agent_orchestrator.run_agent(user_id, matter_id, "/timeline")

        self.assertEqual(result.status, AgentRunState.COMPLETED)
        self.assertEqual(result.token_count, 0)
        self.assertIn("Matter Timeline", result.output_text or "")
        self.assertEqual(len(result.tool_calls), 0)

    def test_failed_draft_path_returns_failed_state(self) -> None:
        user_id = self.owner["user_id"]
        matter_id = self.matter["matter_id"]

        with patch("tllac.app.services.agent_orchestrator.build_draft_preview", side_effect=RuntimeError("bedrock unavailable")):
            result = agent_orchestrator.run_agent(user_id, matter_id, "/draft Prepare draft")

        self.assertEqual(result.status, AgentRunState.FAILED)
        self.assertIn("bedrock unavailable", result.error_text or result.output_text or "")

