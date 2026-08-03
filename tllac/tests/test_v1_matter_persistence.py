import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tllac"))
os.environ.setdefault("APP_SECRET_KEY", "v1-matter-test-secret")

from app.db.db_client import DBClient


class V1MatterPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        with patch.object(DBClient, "_resolve_database_url", return_value=None):
            self.client = DBClient()
        self.owner = self.client.create_user(
            "owner@example.com",
            "Matter Owner",
            "password-123",
        )
        self.other_user = self.client.create_user(
            "other@example.com",
            "Other User",
            "password-456",
        )
        self.matter = self.client.create_matter(
            user_id=self.owner["user_id"],
            title="State v. Example",
            case_number="CR-101",
            court="Sample Court",
        )

    def test_matter_operations_are_scoped_to_owner_and_matter(self) -> None:
        matter_id = self.matter["matter_id"]
        owner_id = self.owner["user_id"]
        other_id = self.other_user["user_id"]

        self.assertEqual(
            self.client.get_matter(owner_id, matter_id)["title"],
            "State v. Example",
        )
        with self.assertRaisesRegex(ValueError, "Matter not found"):
            self.client.get_matter(other_id, matter_id)
        with self.assertRaisesRegex(ValueError, "Matter not found"):
            self.client.update_matter(
                user_id=other_id,
                matter_id=matter_id,
                title="Unauthorized change",
            )
        with self.assertRaisesRegex(ValueError, "Matter not found"):
            self.client.create_matter_note(
                user_id=other_id,
                matter_id=matter_id,
                content="Unauthorized note",
            )

        updated = self.client.update_matter(
            user_id=owner_id,
            matter_id=matter_id,
            stage="Evidence",
        )
        self.assertEqual(updated["stage"], "Evidence")

    def test_archived_matters_are_stored_but_hidden_by_default(self) -> None:
        matter_id = self.matter["matter_id"]
        owner_id = self.owner["user_id"]

        archived = self.client.archive_matter(
            user_id=owner_id,
            matter_id=matter_id,
        )

        self.assertTrue(archived["is_archived"])
        self.assertEqual(self.client.list_matters(owner_id), [])
        self.assertEqual(
            self.client.list_matters(owner_id, include_archived=True)[0]["matter_id"],
            matter_id,
        )
        with self.assertRaisesRegex(ValueError, "Matter not found"):
            self.client.get_matter(owner_id, matter_id)
        self.assertEqual(
            self.client.get_matter(
                owner_id,
                matter_id,
                include_archived=True,
            )["matter_id"],
            matter_id,
        )

    def test_all_v1_matter_record_types_are_persisted_with_ownership(self) -> None:
        matter_id = self.matter["matter_id"]
        owner_id = self.owner["user_id"]

        party = self.client.create_matter_party(
            user_id=owner_id,
            matter_id=matter_id,
            name="Example Party",
            party_role="petitioner",
        )
        hearing = self.client.create_matter_hearing(
            user_id=owner_id,
            matter_id=matter_id,
            title="First hearing",
        )
        task = self.client.create_matter_task(
            user_id=owner_id,
            matter_id=matter_id,
            title="Prepare chronology",
        )
        note = self.client.create_matter_note(
            user_id=owner_id,
            matter_id=matter_id,
            content="Client conference completed.",
        )
        event = self.client.create_matter_event(
            user_id=owner_id,
            matter_id=matter_id,
            event_type="filing",
            title="Petition filed",
        )
        document = self.client.create_matter_document(
            user_id=owner_id,
            matter_id=matter_id,
            title="Petition",
            file_name="petition.pdf",
        )
        research = self.client.create_matter_research(
            user_id=owner_id,
            matter_id=matter_id,
            title="Maintainability research",
            query="Is the petition maintainable?",
            content="Verified research content.",
            verification_status="verified",
        )

        for record in (party, hearing, task, note, event, document, research):
            self.assertEqual(record["user_id"], owner_id)
            self.assertEqual(record["matter_id"], matter_id)
            self.assertFalse(record["is_archived"])
            self.assertIn("created_at", record)
            self.assertIn("updated_at", record)

        self.assertEqual(len(self.client.list_matter_parties(owner_id, matter_id)), 1)
        self.assertEqual(len(self.client.list_matter_hearings(owner_id, matter_id)), 1)
        self.assertEqual(len(self.client.list_matter_tasks(owner_id, matter_id)), 1)
        self.assertEqual(len(self.client.list_matter_notes(owner_id, matter_id)), 1)
        self.assertEqual(len(self.client.list_matter_events(owner_id, matter_id)), 1)
        self.assertEqual(len(self.client.list_matter_documents(owner_id, matter_id)), 1)
        self.assertEqual(len(self.client.list_matter_research(owner_id, matter_id)), 1)

    def test_overview_and_recent_listing_cover_workspace_data(self) -> None:
        matter_id = self.matter["matter_id"]
        owner_id = self.owner["user_id"]

        party = self.client.create_matter_party(
            user_id=owner_id,
            matter_id=matter_id,
            name="Senior Counsel",
            party_role="counsel",
        )
        hearing = self.client.create_matter_hearing(
            user_id=owner_id,
            matter_id=matter_id,
            title="Status hearing",
        )
        task = self.client.create_matter_task(
            user_id=owner_id,
            matter_id=matter_id,
            title="Draft affidavit",
        )
        self.client.update_matter_related_record(
            kind="task",
            user_id=owner_id,
            matter_id=matter_id,
            record_id=task["task_id"],
            status="completed",
        )
        note = self.client.create_matter_note(
            user_id=owner_id,
            matter_id=matter_id,
            content="Workspace note",
        )
        event = self.client.create_matter_event(
            user_id=owner_id,
            matter_id=matter_id,
            event_type="update",
            title="Client updated instructions",
        )
        document = self.client.create_matter_document(
            user_id=owner_id,
            matter_id=matter_id,
            title="Evidence bundle",
        )
        research = self.client.create_matter_research(
            user_id=owner_id,
            matter_id=matter_id,
            title="Research note",
            query="Recent authority on issue",
            content="Research content.",
            verification_status="verified",
        )
        draft = self.client.create_matter_draft(
            user_id=owner_id,
            matter_id=matter_id,
            title="Draft one",
            document_type="brief",
        )

        overview = self.client.get_matter_overview(owner_id, matter_id)
        self.assertEqual(overview["matter_details"]["matter_id"], matter_id)
        self.assertEqual(overview["parties"][0]["party_id"], party["party_id"])
        self.assertEqual(overview["counsel"][0]["party_id"], party["party_id"])
        self.assertEqual(overview["hearings"][0]["hearing_id"], hearing["hearing_id"])
        self.assertEqual(overview["notes"][0]["note_id"], note["note_id"])
        self.assertEqual(overview["timeline_events"][0]["event_id"], event["event_id"])
        self.assertEqual(overview["documents"][0]["document_id"], document["document_id"])
        self.assertEqual(overview["research"][0]["research_id"], research["research_id"])
        self.assertEqual(overview["drafts"][0]["draft_id"], draft["draft_id"])
        self.assertEqual([item["task_id"] for item in overview["open_tasks"]], [])

        recent_matters = self.client.list_matters(owner_id, recent_window="30d")
        self.assertEqual(recent_matters[0]["matter_id"], matter_id)

        archived_task = self.client.archive_matter_related_record(
            kind="task",
            user_id=owner_id,
            matter_id=matter_id,
            record_id=task["task_id"],
        )
        self.assertTrue(archived_task["is_archived"])
        self.assertEqual(
            self.client.get_matter_related_record(
                kind="task",
                user_id=owner_id,
                matter_id=matter_id,
                record_id=task["task_id"],
                include_archived=True,
            )["task_id"],
            task["task_id"],
        )
        with self.assertRaisesRegex(ValueError, "Task not found"):
            self.client.update_matter_related_record(
                kind="task",
                user_id=owner_id,
                matter_id=matter_id,
                record_id=task["task_id"],
                status="open",
            )

    def test_draft_versions_are_append_only_and_preserve_history(self) -> None:
        owner_id = self.owner["user_id"]
        other_id = self.other_user["user_id"]
        matter_id = self.matter["matter_id"]
        draft = self.client.create_matter_draft(
            user_id=owner_id,
            matter_id=matter_id,
            title="Written submission",
            document_type="submission",
        )

        first = self.client.create_draft_version(
            user_id=owner_id,
            matter_id=matter_id,
            draft_id=draft["draft_id"],
            content="Version one",
        )
        second = self.client.create_draft_version(
            user_id=owner_id,
            matter_id=matter_id,
            draft_id=draft["draft_id"],
            content="Version two",
        )
        versions = self.client.list_draft_versions(
            owner_id,
            matter_id,
            draft["draft_id"],
        )

        self.assertEqual(first["version_number"], 1)
        self.assertEqual(second["version_number"], 2)
        self.assertNotEqual(first["version_id"], second["version_id"])
        self.assertEqual(
            [(item["version_number"], item["content"]) for item in versions],
            [(1, "Version one"), (2, "Version two")],
        )
        with self.assertRaisesRegex(ValueError, "Matter not found"):
            self.client.list_draft_versions(
                other_id,
                matter_id,
                draft["draft_id"],
            )
        self.assertFalse(hasattr(self.client, "update_draft_version"))
        self.assertFalse(hasattr(self.client, "delete_draft_version"))

    def test_agent_runs_tool_calls_and_feedback_are_owner_scoped(self) -> None:
        owner_id = self.owner["user_id"]
        other_id = self.other_user["user_id"]
        matter_id = self.matter["matter_id"]
        run = self.client.create_agent_run(
            user_id=owner_id,
            matter_id=matter_id,
            command="/research",
            input_text="Research maintainability",
            context_snapshot={"matter_id": matter_id},
        )
        tool_call = self.client.create_agent_tool_call(
            user_id=owner_id,
            matter_id=matter_id,
            agent_run_id=run["agent_run_id"],
            tool_name="search_legal_corpus",
            input_payload={"query": "maintainability"},
        )
        completed_call = self.client.complete_agent_tool_call(
            user_id=owner_id,
            matter_id=matter_id,
            tool_call_id=tool_call["tool_call_id"],
            status="completed",
            output_payload={"matches": 2},
        )
        feedback = self.client.create_agent_feedback(
            user_id=owner_id,
            matter_id=matter_id,
            agent_run_id=run["agent_run_id"],
            feedback_type="useful",
            rating=5,
            comment="Sources were relevant.",
        )

        self.assertEqual(run["user_id"], owner_id)
        self.assertEqual(completed_call["status"], "completed")
        self.assertEqual(
            self.client.list_agent_tool_calls(
                owner_id,
                matter_id,
                run["agent_run_id"],
            )[0]["tool_call_id"],
            tool_call["tool_call_id"],
        )
        self.assertEqual(
            self.client.list_agent_feedback(owner_id, matter_id)[0]["feedback_id"],
            feedback["feedback_id"],
        )
        with self.assertRaisesRegex(ValueError, "Matter not found"):
            self.client.get_agent_run(
                other_id,
                matter_id,
                run["agent_run_id"],
            )


@unittest.skipUnless(
    os.getenv("RUN_V1_POSTGRES_TESTS") == "1",
    "Set RUN_V1_POSTGRES_TESTS=1 to verify the V1 migration against PostgreSQL.",
)
class V1PostgresSchemaTests(unittest.TestCase):
    def test_migration_constraints_and_immutable_versions(self) -> None:
        client = DBClient()
        self.assertEqual(client._backend, "postgres")
        expected_tables = {
            "matters",
            "matter_parties",
            "matter_hearings",
            "matter_tasks",
            "matter_notes",
            "matter_events",
            "matter_documents",
            "matter_document_chunks",
            "matter_research",
            "matter_drafts",
            "draft_versions",
            "agent_runs",
            "agent_tool_calls",
            "agent_feedback",
        }
        owner_id = str(uuid4())
        other_id = str(uuid4())
        matter_id = str(uuid4())
        draft_id = str(uuid4())
        version_id = str(uuid4())

        conn = client._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = current_schema()
                      AND tablename = ANY(%s)
                    """,
                    (list(expected_tables),),
                )
                self.assertEqual(
                    {row["tablename"] for row in cur.fetchall()},
                    expected_tables,
                )
                cur.execute(
                    """
                    SELECT version
                    FROM v1_schema_migrations
                    WHERE version = ANY(%s)
                    """,
                    (
                        [
                            "001_v1_matter_schema",
                            "002_v1_matter_document_storage",
                        ],
                    ),
                )
                self.assertEqual(
                    {row["version"] for row in cur.fetchall()},
                    {
                        "001_v1_matter_schema",
                        "002_v1_matter_document_storage",
                    },
                )
                cur.execute(
                    """
                    SELECT 1
                    FROM pg_trigger
                    WHERE tgname = 'trg_draft_versions_immutable'
                      AND NOT tgisinternal
                    """
                )
                self.assertIsNotNone(cur.fetchone())

                cur.execute(
                    """
                    INSERT INTO app_users (
                        user_id, email, full_name, password_hash
                    )
                    VALUES
                        (%s, %s, 'V1 Owner', 'test-only'),
                        (%s, %s, 'V1 Other', 'test-only')
                    """,
                    (
                        owner_id,
                        f"v1-owner-{owner_id}@example.test",
                        other_id,
                        f"v1-other-{other_id}@example.test",
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO matters (matter_id, user_id, title)
                    VALUES (%s, %s, 'Migration verification matter')
                    """,
                    (matter_id, owner_id),
                )

                cur.execute("SAVEPOINT ownership_check")
                ownership_rejected = False
                try:
                    cur.execute(
                        """
                        INSERT INTO matter_tasks (
                            task_id, user_id, matter_id, title
                        )
                        VALUES (%s, %s, %s, 'Unauthorized task')
                        """,
                        (str(uuid4()), other_id, matter_id),
                    )
                except Exception:
                    ownership_rejected = True
                    cur.execute("ROLLBACK TO SAVEPOINT ownership_check")
                self.assertTrue(ownership_rejected)

                cur.execute(
                    """
                    INSERT INTO matter_drafts (
                        draft_id, user_id, matter_id, title, document_type
                    )
                    VALUES (%s, %s, %s, 'Test draft', 'submission')
                    """,
                    (draft_id, owner_id, matter_id),
                )
                cur.execute(
                    """
                    INSERT INTO draft_versions (
                        version_id, user_id, matter_id, draft_id,
                        version_number, content, created_by
                    )
                    VALUES (%s, %s, %s, %s, 1, 'Immutable content', %s)
                    """,
                    (version_id, owner_id, matter_id, draft_id, owner_id),
                )

                cur.execute("SAVEPOINT immutability_check")
                mutation_rejected = False
                try:
                    cur.execute(
                        """
                        UPDATE draft_versions
                        SET content = 'Mutated content'
                        WHERE user_id = %s
                          AND matter_id = %s
                          AND version_id = %s
                        """,
                        (owner_id, matter_id, version_id),
                    )
                except Exception:
                    mutation_rejected = True
                    cur.execute("ROLLBACK TO SAVEPOINT immutability_check")
                self.assertTrue(mutation_rejected)

                cur.execute(
                    """
                    UPDATE matters
                    SET is_archived = TRUE, archived_at = NOW()
                    WHERE user_id = %s AND matter_id = %s
                    """,
                    (owner_id, matter_id),
                )
                cur.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM matters
                    WHERE user_id = %s
                      AND matter_id = %s
                      AND is_archived = FALSE
                    """,
                    (owner_id, matter_id),
                )
                self.assertEqual(cur.fetchone()["count"], 0)
                cur.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM matters
                    WHERE user_id = %s AND matter_id = %s
                    """,
                    (owner_id, matter_id),
                )
                self.assertEqual(cur.fetchone()["count"], 1)
        finally:
            conn.rollback()
            conn.close()


if __name__ == "__main__":
    unittest.main()
