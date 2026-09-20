"""E02 — Persistence layer regression tests.

Uses SQLite in-memory so no Postgres required in CI.
Tests: ORM models load, CRUD operations, org isolation (ADR-003), soft-delete.
"""
from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import sqlalchemy  # noqa: F401
    SA_AVAILABLE = True
except ImportError:
    SA_AVAILABLE = False


@unittest.skipUnless(SA_AVAILABLE, "sqlalchemy not installed")
class TestOrmModels(unittest.TestCase):
    def setUp(self):
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        from services.api.db.session import create_all_tables, SessionLocal
        create_all_tables()
        self.Session = SessionLocal

    def _session(self):
        return self.Session()

    # ------------------------------------------------------------------
    def test_organization_create(self):
        from services.api.models.orm import Organization
        with self._session() as s:
            org = Organization(name="Test Org", slug="test-org")
            s.add(org)
            s.commit()
            self.assertIsNotNone(org.id)
            self.assertEqual(org.name, "Test Org")

    def test_project_isolation(self):
        """Projects must be scoped to their org — ADR-003."""
        from services.api.models.orm import Organization, Project
        from services.api.repository_sql import SqlProjectRepository
        with self._session() as s:
            org_a = Organization(name="Org A", slug="org-a")
            org_b = Organization(name="Org B", slug="org-b")
            s.add_all([org_a, org_b])
            s.flush()
            proj = Project(organization_id=org_a.id, name="Project A", units="inch")
            s.add(proj)
            s.commit()
            pid = proj.id
            oid_a = org_a.id
            oid_b = org_b.id

        with self._session() as s:
            repo = SqlProjectRepository(s)
            # Org A can see the project
            found = repo.get(pid, oid_a)
            self.assertIsNotNone(found, "Org A should see its own project")
            # Org B cannot see it (isolation)
            not_found = repo.get(pid, oid_b)
            self.assertIsNone(not_found, "Org B must NOT see Org A's project")

    def test_project_soft_delete(self):
        from services.api.models.orm import Organization, Project
        from services.api.repository_sql import SqlProjectRepository
        with self._session() as s:
            org = Organization(name="Del Org", slug="del-org")
            s.add(org)
            s.flush()
            proj = Project(organization_id=org.id, name="To Delete", units="mm")
            s.add(proj)
            s.commit()
            pid = proj.id
            oid = org.id

        with self._session() as s:
            repo = SqlProjectRepository(s)
            repo.soft_delete(pid, oid)
            s.commit()
            deleted = repo.get(pid, oid)
            self.assertIsNone(deleted, "Soft-deleted project should not be returned")

    def test_job_lifecycle(self):
        from services.api.models.orm import Organization, Project
        from services.api.repository_sql import SqlJobRepository, SqlProjectRepository
        with self._session() as s:
            org = Organization(name="Job Org", slug="job-org")
            s.add(org)
            s.flush()
            proj = Project(organization_id=org.id, name="Job Project", units="inch")
            s.add(proj)
            s.commit()
            pid = proj.id

        with self._session() as s:
            job_repo = SqlJobRepository(s)
            job = job_repo.enqueue(
                project_id=pid,
                job_type="validate",
                payload={"test": True},
                created_by_user_id=None,
            )
            s.commit()
            jid = job["id"]

        with self._session() as s:
            job_repo = SqlJobRepository(s)
            job_repo.update_status(jid, "running", progress=50)
            s.commit()
            fetched = job_repo.get(jid)
            self.assertEqual(fetched["status"], "running")
            self.assertEqual(fetched["progress"], 50)

        with self._session() as s:
            job_repo = SqlJobRepository(s)
            job_repo.update_status(jid, "succeeded", progress=100)
            s.commit()
            fetched = job_repo.get(jid)
            self.assertEqual(fetched["status"], "succeeded")
            self.assertIsNotNone(fetched["finished_at"])

    def test_audit_immutable_append(self):
        from services.api.models.orm import Organization
        from services.api.repository_sql import SqlAuditRepository
        org_id = uuid.uuid4()
        with self._session() as s:
            org = Organization(id=org_id, name="Audit Org", slug="audit-org")
            s.add(org)
            s.flush()
            audit = SqlAuditRepository(s)
            audit.record(
                action="project.create",
                resource_type="project",
                resource_id="proj-001",
                organization_id=org_id,
            )
            s.commit()
            events = audit.list_for_org(org_id)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["action"], "project.create")


@unittest.skipUnless(SA_AVAILABLE, "sqlalchemy not installed")
class TestRevisionPointers(unittest.TestCase):
    """Revisions store only SHA-256 pointers — geometry never inline (ADR-001)."""

    def setUp(self):
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        from services.api.db.session import create_all_tables, SessionLocal
        create_all_tables()
        self.Session = SessionLocal

    def test_revision_stores_sha256_pointer_not_geometry(self):
        from services.api.models.orm import Organization, Project
        from services.api.repository_sql import SqlRevisionRepository, SqlProjectRepository
        with self.Session() as s:
            org = Organization(name="Rev Org", slug="rev-org")
            s.add(org)
            s.flush()
            proj = Project(organization_id=org.id, name="Rev Project", units="inch")
            s.add(proj)
            s.commit()
            pid = proj.id

        fake_sha = "a" * 64
        with self.Session() as s:
            repo = SqlRevisionRepository(s)
            rev = repo.create(
                project_id=pid,
                revision_number=1,
                model_sha256=fake_sha,
                model_storage_key="projects/test/rev1.json",
                author_user_id=None,
                reason="initial",
                rule_pack_version="india-preliminary-review@1.0.0",
            )
            s.commit()
            rid = rev["id"]

        with self.Session() as s:
            repo = SqlRevisionRepository(s)
            fetched = repo.get(rid)
            self.assertEqual(fetched["model_sha256"], fake_sha)
            self.assertEqual(fetched["rule_pack_version"], "india-preliminary-review@1.0.0")
            # Confirm no geometry columns exist on the row
            keys = list(fetched.keys())
            self.assertNotIn("walls", keys)
            self.assertNotIn("openings", keys)
            self.assertNotIn("geometry", keys)


if __name__ == "__main__":
    unittest.main()
