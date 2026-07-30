from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

os = __import__("os")
os.environ.setdefault("APP_SECRET_KEY", "v1-research-test-secret")


class _FakeInvalidToken(Exception):
    pass


class _FakeFernet:
    def __init__(self, key: bytes):
        self.key = key

    def encrypt(self, value: bytes) -> bytes:
        return value

    def decrypt(self, value: bytes) -> bytes:
        return value


class _FakeHTTPException(Exception):
    def __init__(self, status_code: int, detail):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class _FakeAPIRouter:
    def __init__(self, *args, **kwargs):
        self.prefix = kwargs.get("prefix", "")
        self.routes = []

    def _register(self, path, endpoint, methods):
        route = types.SimpleNamespace(path=f"{self.prefix}{path}", methods=set(methods), endpoint=endpoint)
        self.routes.append(route)
        return endpoint

    def _decorator(self, method, *args, **kwargs):
        path = args[0]

        def wrapper(func):
            return self._register(path, func, [method])

        return wrapper

    def post(self, *args, **kwargs):
        return self._decorator("POST", *args, **kwargs)

    def get(self, *args, **kwargs):
        return self._decorator("GET", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._decorator("PATCH", *args, **kwargs)


def _fake_body(default=None, **kwargs):
    return default


def _fake_depends(call):
    return call


def _fake_query(default=None, **kwargs):
    return default


def _fake_header(default=None, **kwargs):
    return default


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


fastapi_module = types.ModuleType("fastapi")
fastapi_module.APIRouter = _FakeAPIRouter
fastapi_module.Body = _fake_body
fastapi_module.Depends = _fake_depends
fastapi_module.HTTPException = _FakeHTTPException
fastapi_module.File = lambda *args, **kwargs: None
fastapi_module.Header = _fake_header
fastapi_module.Query = _fake_query
fastapi_module.UploadFile = object
fastapi_status = types.SimpleNamespace(
    HTTP_400_BAD_REQUEST=400,
    HTTP_401_UNAUTHORIZED=401,
    HTTP_404_NOT_FOUND=404,
    HTTP_409_CONFLICT=409,
    HTTP_422_UNPROCESSABLE_ENTITY=422,
    HTTP_500_INTERNAL_SERVER_ERROR=500,
)
fastapi_module.status = fastapi_status
sys.modules.setdefault("fastapi", fastapi_module)

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
from tllac.app.routes import v1 as v1_module


class V1ResearchRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ADVANCED_AGENT_COMMANDS_ENABLED"] = "1"
        db_client._init_memory_store()
        db_client._init_v1_memory_store()
        db_client._backend = "memory"
        v1_module._pending_actions.clear()
        v1_module._idempotency.clear()
        v1_module._feedback.clear()
        self.owner = db_client.create_user("owner@example.com", "Research Owner", "password-123")
        self.other = db_client.create_user("other@example.com", "Other User", "password-123")
        self.matter = db_client.create_matter(user_id=self.owner["user_id"], title="Research Matter")
        self.route_matter_id = self.matter["matter_id"]
        v1_module._matters.setdefault(self.owner["user_id"], {})[self.route_matter_id] = {
            "id": self.route_matter_id,
            "title": "Research Matter",
            "reference": "",
            "description": "",
            "state": "active",
            "created_at": "2026-07-30T00:00:00+00:00",
            "updated_at": "2026-07-30T00:00:00+00:00",
            "tabs": {name: [] for name in ("parties", "hearings", "tasks", "notes", "timeline", "research", "drafts")},
            "documents": [],
        }
        v1_module._matters[self.owner["user_id"]][self.route_matter_id]["documents"].append(
            {
                "id": "doc-1",
                "name": "Owner Document",
                "content_type": "text/plain",
                "size": 20,
                "text": "Confidential owner text",
                "uploaded_at": "2026-07-30T00:00:00+00:00",
            }
        )

    def tearDown(self) -> None:
        os.environ.pop("ADVANCED_AGENT_COMMANDS_ENABLED", None)

    def test_run_research_route_returns_verified_memo(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        fake_result = types.SimpleNamespace(
            query="Section 138 cheque dishonour",
            verification=types.SimpleNamespace(
                verified=True,
                review_required=False,
                memo_title="Cheque Dishonour Memo",
                memo_text="Verified memo text",
                confidence=0.91,
                claims=[types.SimpleNamespace(claim_id="C1", text="Section 138 applies.", source_ids=["LC-1"], source_locations=["section:138"], material=True, confidence=0.9, claim_type="statute")],
                source_mappings=[types.SimpleNamespace(source_id="LC-1", claim_ids=["C1"], support="Statute")],
                rejected_claims=[],
                notes=[],
            ),
            saved_research={"research_id": "R1", "title": "Cheque Dishonour Memo"},
            evidence_sources=[
                types.SimpleNamespace(to_dict=lambda: {"source_id": "LC-1", "title": "BNS"}),
            ],
        )

        with patch("tllac.app.services.research_service.run_research", return_value=fake_result):
            response = v1_module.run_research_endpoint(
                matter_id,
                v1_module.ResearchRunRequest(query="Section 138 cheque dishonour", conversation_history=[]),
                current_user=owner_user,
            )

        self.assertTrue(response.verified)
        self.assertFalse(response.review_required)
        self.assertEqual(response.saved_research["research_id"], "R1")
        self.assertEqual(response.memo_title, "Cheque Dishonour Memo")

    def test_list_research_returns_saved_items(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        db_client.create_matter_research(
            user_id=self.owner["user_id"],
            matter_id=matter_id,
            title="Saved Memo",
            query="query",
            content="content",
            evidence=[{"source_id": "LC-1"}],
            verification_status="verified",
        )

        response = v1_module.list_research(matter_id, current_user=owner_user)

        self.assertEqual(len(response["items"]), 1)
        self.assertEqual(response["items"][0]["title"], "Saved Memo")

    def test_timeline_preview_and_confirm_create_record(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        db_client.create_matter_hearing(
            user_id=self.owner["user_id"],
            matter_id=matter_id,
            title="Mention Hearing",
            court="Court 1",
        )

        preview = v1_module.timeline_preview(matter_id, current_user=owner_user)
        self.assertTrue(preview["read_only"])
        self.assertIn("preview_token", preview)

        before_count = len(v1_module._matter(self.owner["user_id"], self.route_matter_id)["tabs"]["timeline"])
        confirmed = v1_module.timeline_confirm(
            self.route_matter_id,
            payload={"preview_token": preview["preview_token"], "confirmed": True},
            current_user=owner_user,
        )
        after_count = len(v1_module._matter(self.owner["user_id"], self.route_matter_id)["tabs"]["timeline"])

        self.assertEqual(confirmed["status"], "confirmed")
        self.assertEqual(after_count, before_count + 1)

    def test_review_route_requires_source_id(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        with self.assertRaises(v1_module.HTTPException) as ctx:
            v1_module.review_command(
                matter_id,
                payload={"source_type": "document", "source_id": "", "query": "review"},
                current_user=owner_user,
            )

        self.assertEqual(ctx.exception.status_code, 422)

    def test_cross_user_matter_access_is_rejected(self) -> None:
        other_user = {"user_id": self.other["user_id"]}
        with self.assertRaises(v1_module.HTTPException) as ctx:
            v1_module.list_research(self.matter["matter_id"], current_user=other_user)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_cross_user_document_access_is_rejected(self) -> None:
        other_user = {"user_id": self.other["user_id"]}
        with self.assertRaises(v1_module.HTTPException) as ctx:
            v1_module.get_document(self.route_matter_id, "doc-1", current_user=other_user)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_diary_preview_confirm_is_idempotent(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        preview = v1_module.diary_preview(
            self.route_matter_id,
            payload={
                "date": "2026-07-30",
                "duration": "1h",
                "category": "client call",
                "description": "Discussed hearing prep",
                "follow_up_task": "Send draft to client",
            },
            current_user=owner_user,
        )
        first = v1_module.diary_confirm(
            self.route_matter_id,
            payload={
                "preview_token": preview["preview_token"],
                "idempotency_key": "diary-001",
                "confirmed": True,
            },
            current_user=owner_user,
        )
        second = v1_module.diary_confirm(
            self.route_matter_id,
            payload={
                "preview_token": preview["preview_token"],
                "idempotency_key": "diary-001",
                "confirmed": True,
            },
            current_user=owner_user,
        )

        self.assertTrue(first["ok"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(len(db_client.list_matter_tasks(self.owner["user_id"], matter_id)), 1)

    def test_feedback_categories_are_recorded(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        response = v1_module.agent_feedback(
            {
                "matter_id": matter_id,
                "artifact_type": "research",
                "category": "citation issue",
                "value": "not_useful",
                "comment": "Citation points to the wrong page.",
            },
            current_user=owner_user,
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["feedback"]["category"], "citation issue")
        self.assertEqual(v1_module._feedback[self.owner["user_id"]][0]["artifact_type"], "research")

    def test_draft_preview_confirm_preserves_versions(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        db_client.create_matter_research(
            user_id=self.owner["user_id"],
            matter_id=matter_id,
            title="Verified Memo",
            query="query",
            content="Verified content for drafting.",
            evidence=[{"source_id": "LC-1"}],
            verification_status="verified",
        )

        with patch.object(v1_module, "build_draft_preview", return_value=("Draft with verified research", 12)):
            preview_1 = v1_module.draft_preview(
                self.route_matter_id,
                payload={
                    "document_type": "brief",
                    "document_type_label": "Brief",
                    "case_details": "Draft with verified research",
                    "structured_fields": {},
                    "structured_sections": [],
                },
                current_user=owner_user,
            )
            confirmed_1 = v1_module.draft_confirm(
                self.route_matter_id,
                payload={
                    "preview_token": preview_1["preview_token"],
                    "confirmed": True,
                },
                current_user=owner_user,
            )
            preview_2 = v1_module.draft_preview(
                self.route_matter_id,
                payload={
                    "document_type": "brief",
                    "document_type_label": "Brief",
                    "case_details": "Draft with verified research",
                    "structured_fields": {},
                    "structured_sections": [],
                },
                current_user=owner_user,
            )
            v1_module.draft_confirm(
                self.route_matter_id,
                payload={
                    "preview_token": preview_2["preview_token"],
                    "confirmed": True,
                    "draft_id": confirmed_1["draft_id"],
                },
                current_user=owner_user,
            )

        versions = v1_module.list_draft_versions_route(
            matter_id,
            confirmed_1["draft_id"],
            current_user=owner_user,
        )["items"]

        self.assertEqual(len(versions), 2)

    def test_draft_confirm_rejects_unverified_citations(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        matter_id = self.matter["matter_id"]

        db_client.create_matter_research(
            user_id=self.owner["user_id"],
            matter_id=matter_id,
            title="Verified Memo",
            query="query",
            content="Verified content for drafting.",
            evidence=[{"source_id": "LC-1"}],
            verification_status="verified",
        )

        with patch.object(v1_module, "build_draft_preview", return_value=("Draft with verified research", 12)):
            preview = v1_module.draft_preview(
                self.route_matter_id,
                payload={
                    "document_type": "brief",
                    "document_type_label": "Brief",
                    "case_details": "Draft with verified research",
                    "structured_fields": {},
                    "structured_sections": [],
                },
                current_user=owner_user,
            )

        with self.assertRaises(v1_module.HTTPException) as ctx:
            v1_module.draft_confirm(
                self.route_matter_id,
                payload={
                    "preview_token": preview["preview_token"],
                    "confirmed": True,
                    "citations": [{"source_id": "FAKE-1"}],
                },
                current_user=owner_user,
            )

        self.assertEqual(ctx.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
