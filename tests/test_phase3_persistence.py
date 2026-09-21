"""Dependency-free tests for the Phase 3 persistent revision boundary."""

from __future__ import annotations

import hashlib
import unittest

from packages.geometry.persistence import (
    IdempotencyConflict,
    IntegrityError,
    ProjectNotFound,
    RevisionCommitRequest,
    RevisionConflict,
    RevisionTransactionCoordinator,
    revision_storage_key,
)


class MemoryObjects:
    def __init__(self, digest_override: str | None = None) -> None:
        self.values: dict[str, bytes] = {}
        self.digest_override = digest_override

    def put(self, key: str, data: bytes) -> str:
        self.values[key] = data
        return self.digest_override or hashlib.sha256(data).hexdigest()


class MemoryProjects:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], dict[str, object]] = {}
        self.force_cas_failure = False

    def get(self, project_id: str, org_id: str) -> dict[str, object] | None:
        value = self.values.get((project_id, org_id))
        return dict(value) if value else None

    def advance_current_revision(
        self,
        project_id: str,
        org_id: str,
        expected_current_revision_id: str | None,
        new_revision_id: str,
    ) -> bool:
        value = self.values.get((project_id, org_id))
        if self.force_cas_failure:
            return False
        if value is None or value.get("current_revision_id") != expected_current_revision_id:
            return False
        value["current_revision_id"] = new_revision_id
        return True


class MemoryRevisions:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, object]] = {}
        self.next_id = 1

    def get(self, revision_id: str | None) -> dict[str, object] | None:
        return dict(self.values[revision_id]) if revision_id in self.values else None

    def get_by_idempotency(self, project_id: str, idempotency_key: str) -> dict[str, object] | None:
        return next(
            (
                dict(value)
                for value in self.values.values()
                if value["project_id"] == project_id
                and value.get("idempotency_key") == idempotency_key
            ),
            None,
        )

    def create(self, project_id: str, revision_number: int, model_sha256: str, model_storage_key: str, author_user_id: str | None, reason: str, rule_pack_version: str | None = None, parent_revision_id: str | None = None, command_id: str | None = None, idempotency_key: str | None = None, command_fingerprint: str | None = None, engine_version: str = "phase2.command-engine.v1", validation_state: str = "DRAFT") -> dict[str, object]:
        revision = {
            "id": f"rev-{self.next_id}",
            "project_id": project_id,
            "revision_number": revision_number,
            "model_sha256": model_sha256,
            "model_storage_key": model_storage_key,
            "author_user_id": author_user_id,
            "reason": reason,
            "rule_pack_version": rule_pack_version,
            "parent_revision_id": parent_revision_id,
            "command_id": command_id,
            "idempotency_key": idempotency_key,
            "command_fingerprint": command_fingerprint,
            "engine_version": engine_version,
            "validation_state": validation_state,
        }
        self.next_id += 1
        self.values[revision["id"]] = revision
        return dict(revision)

    def set_validation_report_sha256(self, revision_id: str, digest: str) -> None:
        self.values[revision_id]["validation_report_sha256"] = digest


class MemoryAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record(self, **kwargs: object) -> None:
        self.events.append(kwargs)


def request(**kwargs: object) -> RevisionCommitRequest:
    base_revision = kwargs.pop("base_revision", 0)
    idempotency_key = kwargs.pop("idempotency_key", "idem-0001")
    command_fingerprint = kwargs.pop("command_fingerprint", "f" * 64)
    return RevisionCommitRequest(
        organization_id="org-1",
        project_id="proj-1",
        base_revision=base_revision,
        model_bytes=b'{"schemaVersion":"advocate-chambers.project.v2"}',
        author_user_id="user-1",
        command_id="cmd-1",
        idempotency_key=idempotency_key,
        command_fingerprint=command_fingerprint,
        **kwargs,
    )


class Phase3PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projects = MemoryProjects()
        self.projects.values[("proj-1", "org-1")] = {"current_revision_id": None}
        self.revisions = MemoryRevisions()
        self.objects = MemoryObjects()
        self.audit = MemoryAudit()
        self.coordinator = RevisionTransactionCoordinator(
            self.projects, self.revisions, self.objects, self.audit
        )

    def test_first_revision_stores_bytes_and_advances_pointer(self) -> None:
        result = self.coordinator.commit(request())
        self.assertFalse(result.replayed)
        self.assertEqual(result.revision["revision_number"], 1)
        self.assertEqual(
            self.projects.values[("proj-1", "org-1")]["current_revision_id"],
            result.revision["id"],
        )
        self.assertEqual(len(self.objects.values), 1)
        self.assertEqual(len(self.audit.events), 1)

    def test_revision_storage_key_is_content_addressed_and_stable(self) -> None:
        digest = hashlib.sha256(b"model").hexdigest()
        self.assertEqual(
            revision_storage_key("org-1", "proj-1", digest),
            f"orgs/org-1/projects/proj-1/revisions/{digest}/model.json",
        )

    def test_unsafe_storage_components_are_rejected(self) -> None:
        digest = hashlib.sha256(b"model").hexdigest()
        with self.assertRaises(ValueError):
            revision_storage_key("../org", "proj-1", digest)

    def test_replay_returns_original_revision_without_new_row(self) -> None:
        first = self.coordinator.commit(request())
        replay = self.coordinator.commit(request())
        self.assertTrue(replay.replayed)
        self.assertEqual(first.revision, replay.revision)
        self.assertEqual(len(self.revisions.values), 1)

    def test_idempotency_collision_is_rejected(self) -> None:
        self.coordinator.commit(request())
        with self.assertRaises(IdempotencyConflict):
            self.coordinator.commit(request(command_fingerprint="e" * 64))

    def test_stale_base_revision_is_rejected(self) -> None:
        self.coordinator.commit(request())
        with self.assertRaises(RevisionConflict) as context:
            self.coordinator.commit(request(base_revision=0, idempotency_key="idem-0002"))
        self.assertEqual(context.exception.actual, 1)

    def test_missing_project_is_rejected(self) -> None:
        with self.assertRaises(ProjectNotFound):
            self.coordinator.commit(
                RevisionCommitRequest(
                    organization_id="org-1",
                    project_id="missing",
                    base_revision=0,
                    model_bytes=b"model",
                )
            )

    def test_store_digest_mismatch_is_rejected(self) -> None:
        self.coordinator.objects = MemoryObjects("0" * 64)
        with self.assertRaises(IntegrityError):
            self.coordinator.commit(request())
        self.assertEqual(len(self.revisions.values), 0)

    def test_validation_report_is_stored_and_linked(self) -> None:
        result = self.coordinator.commit(request())
        key, digest = self.coordinator.attach_validation_report(
            result.revision, b'{"findings":[]}', organization_id="org-1"
        )
        self.assertTrue(key.endswith("/validation.json"))
        self.assertEqual(digest, hashlib.sha256(b'{"findings":[]}').hexdigest())
        self.assertEqual(self.revisions.values[result.revision["id"]]["validation_report_sha256"], digest)

    def test_optimistic_pointer_cas_blocks_second_writer(self) -> None:
        first = self.coordinator.commit(request())
        self.projects.force_cas_failure = True
        with self.assertRaises(RevisionConflict):
            self.coordinator.commit(request(idempotency_key="idem-0002"))
        self.assertEqual(first.revision["revision_number"], 1)


if __name__ == "__main__":
    unittest.main()