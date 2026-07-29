from __future__ import annotations

import asyncio
import os
import sys
import types
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("APP_SECRET_KEY", "matter-route-test-secret")


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
        self.routes = []

    def _decorator(self, *args, **kwargs):
        def wrapper(func):
            self.routes.append((args, kwargs, func))
            return func

        return wrapper

    def post(self, *args, **kwargs):
        return self._decorator(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._decorator(*args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._decorator(*args, **kwargs)

    def add_api_route(self, *args, **kwargs):
        if len(args) >= 2 and callable(args[1]):
            path = args[0]
            endpoint = args[1]
            self.routes.append(((path,), kwargs, endpoint))
            return endpoint

        def wrapper(func):
            self.routes.append((args, kwargs, func))
            return func

        return wrapper


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
            data = {
                key: value
                for key, value in data.__dict__.items()
                if not key.startswith("_")
            }
        return cls(**data)

    def model_dump(self):
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        }

    def __getitem__(self, key):
        return self.__dict__[key]


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
fastapi_module.Header = _fake_header
fastapi_module.Query = _fake_query
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


from tllac.app.db.db_client import db_client
from tllac.app.routes import matters as matters_module


def _run(coro):
    return asyncio.run(coro)


class MatterRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        db_client._init_memory_store()
        self.owner = db_client.create_user("owner@example.com", "Matter Owner", "password-123")
        self.other = db_client.create_user("other@example.com", "Other User", "password-456")

    def _route(self, path: str, method: str):
        full_path = f"{matters_module.router.prefix}{path}" if not path.startswith(matters_module.router.prefix) else path
        for route in matters_module.router.routes:
            if (getattr(route, "path", None) in (path, full_path)) and method in getattr(route, "methods", []):
                return route.endpoint
        raise AssertionError(f"Route not found: {method} {path}")

    def test_matter_crud_and_overview(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        create_payload = matters_module.MatterCreateRequest(
            title="State v. Example",
            description="Primary matter",
            case_number="CR-101",
            court="Sample Court",
            jurisdiction="Delhi",
            stage="Pleadings",
            status="open",
            metadata={"source": "unit-test"},
        )
        created = _run(matters_module.create_matter(create_payload, current_user=owner_user))
        matter_id = created["matter_id"]

        fetched = _run(matters_module.get_matter(matter_id, current_user=owner_user))
        self.assertEqual(fetched["matter_id"], matter_id)

        updated = _run(
            matters_module.update_matter(
                matter_id,
                matters_module.MatterUpdateRequest(stage="Evidence", status="active"),
                current_user=owner_user,
            )
        )
        self.assertEqual(updated["stage"], "Evidence")

        party = _run(
            self._route("/{matter_id}/parties", "POST")(
                matter_id,
                matters_module.PartyCreateRequest(
                    name="Senior Counsel",
                    party_role="counsel",
                    details={"bar": "Delhi"},
                ),
                current_user=owner_user,
            )
        )
        hearing = _run(
            self._route("/{matter_id}/hearings", "POST")(
                matter_id,
                matters_module.HearingCreateRequest(
                    title="Status hearing",
                    court="Court 1",
                    status="scheduled",
                ),
                current_user=owner_user,
            )
        )
        task = _run(
            self._route("/{matter_id}/tasks", "POST")(
                matter_id,
                matters_module.TaskCreateRequest(
                    title="Draft affidavit",
                    priority="high",
                ),
                current_user=owner_user,
            )
        )
        note = _run(
            self._route("/{matter_id}/notes", "POST")(
                matter_id,
                matters_module.NoteCreateRequest(content="Client called with instructions."),
                current_user=owner_user,
            )
        )
        event = _run(
            self._route("/{matter_id}/timeline-events", "POST")(
                matter_id,
                matters_module.TimelineEventCreateRequest(
                    event_type="update",
                    title="Client update",
                ),
                current_user=owner_user,
            )
        )
        document = db_client.create_matter_document(
            user_id=self.owner["user_id"],
            matter_id=matter_id,
            title="Evidence bundle",
        )
        research = db_client.create_matter_research(
            user_id=self.owner["user_id"],
            matter_id=matter_id,
            title="Research note",
            query="Recent authority",
            content="Research content",
            verification_status="verified",
        )
        draft = db_client.create_matter_draft(
            user_id=self.owner["user_id"],
            matter_id=matter_id,
            title="Draft one",
            document_type="brief",
        )
        _run(
            self._route("/{matter_id}/tasks/{record_id}", "PATCH")(
                matter_id,
                task["task_id"],
                matters_module.TaskUpdateRequest(status="completed"),
                current_user=owner_user,
            )
        )

        overview = _run(
            matters_module.get_matter_overview(
                matter_id,
                current_user=owner_user,
            )
        )
        self.assertEqual(overview["matter_details"]["matter_id"], matter_id)
        self.assertEqual(overview["parties"][0]["party_id"], party["party_id"])
        self.assertEqual(overview["counsel"][0]["party_id"], party["party_id"])
        self.assertEqual(overview["hearings"][0]["hearing_id"], hearing["hearing_id"])
        self.assertEqual(overview["notes"][0]["note_id"], note["note_id"])
        self.assertEqual(overview["timeline_events"][0]["event_id"], event["event_id"])
        self.assertEqual(overview["documents"][0]["document_id"], document["document_id"])
        self.assertEqual(overview["research"][0]["research_id"], research["research_id"])
        self.assertEqual(overview["drafts"][0]["draft_id"], draft["draft_id"])
        self.assertEqual(overview["open_tasks"], [])

        matters_list = _run(matters_module.list_matters(current_user=owner_user))
        matters_dict = matters_list.model_dump() if hasattr(matters_list, "model_dump") else matters_list.dict()
        self.assertEqual(matters_dict["matters"][0]["matter_id"], matter_id)
        active_list = _run(
            matters_module.list_matters(archive_state="active", current_user=owner_user)
        )
        active_dict = active_list.model_dump() if hasattr(active_list, "model_dump") else active_list.dict()
        self.assertEqual(active_dict["matters"][0]["matter_id"], matter_id)
        recent_list = _run(
            matters_module.list_recent_matters(window="30d", current_user=owner_user)
        )
        recent_dict = recent_list.model_dump() if hasattr(recent_list, "model_dump") else recent_list.dict()
        self.assertEqual(recent_dict["matters"][0]["matter_id"], matter_id)

        archive_response = _run(matters_module.archive_matter(matter_id, current_user=owner_user))
        self.assertTrue(archive_response["is_archived"])
        with self.assertRaises(Exception) as ctx:
            _run(matters_module.get_matter(matter_id, current_user=owner_user))
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)
        res = _run(matters_module.list_matters(current_user=owner_user))
        res_dict = res.model_dump() if hasattr(res, "model_dump") else res.dict()
        self.assertEqual(res_dict["matters"], [])
        archived_list = _run(
            matters_module.list_matters(archive_state="archived", current_user=owner_user)
        )
        archived_dict = archived_list.model_dump() if hasattr(archived_list, "model_dump") else archived_list.dict()
        self.assertEqual(archived_dict["matters"][0]["matter_id"], matter_id)

    def test_ownership_and_structured_errors(self) -> None:
        owner_user = {"user_id": self.owner["user_id"]}
        other_user = {"user_id": self.other["user_id"]}
        created = _run(
            matters_module.create_matter(
                matters_module.MatterCreateRequest(title="Owner matter"),
                current_user=owner_user,
            )
        )
        matter_id = created["matter_id"]

        with self.assertRaises(Exception) as ctx:
            _run(matters_module.get_matter(matter_id, current_user=other_user))
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)
        self.assertEqual(getattr(ctx.exception, "detail", {}).get("error", {}).get("code"), "matter_not_found")

        with self.assertRaises(Exception) as task_ctx:
            _run(
                self._route("/{matter_id}/tasks", "POST")(
                    matter_id,
                    matters_module.TaskCreateRequest(title="Unauthorized task"),
                    current_user=other_user,
                )
            )
        self.assertEqual(getattr(task_ctx.exception, "status_code", None), 404)
        self.assertEqual(getattr(task_ctx.exception, "detail", {}).get("error", {}).get("code"), "task_not_found")


if __name__ == "__main__":
    unittest.main()
