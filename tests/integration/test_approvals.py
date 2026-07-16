from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from npe.bootstrap import Container, bootstrap
from npe.domain.approval import ApprovalGate
from npe.shared.config import AppPaths, Settings


def project_with_two_buildings(tmp_path: Path) -> tuple[Container, str, str, str]:
    container = bootstrap(
        Settings(paths=AppPaths.under(tmp_path / "data"), minimum_free_disk_bytes=0)
    )
    first = container.workflow.create_job("P", 35.7, 51.4, 100, "B1", 12)
    second_id = "BLD-SECOND"
    now = datetime.now(UTC).isoformat()
    with container.database.connect() as connection:
        connection.execute(
            """INSERT INTO buildings
               (id, project_id, code, target_height_m, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (second_id, first.project_id, "B2", 15, "active", now, now),
        )
    return container, first.project_id, first.building_id, second_id


def test_batch_exceptions_and_targeted_invalidation(tmp_path: Path) -> None:
    container, project_id, first_id, second_id = project_with_two_buildings(tmp_path)
    service = container.approvals

    map_revision = service.create_revision(
        project_id, ApprovalGate.MAP, {"radius": 100}, "reviewer", "map checked"
    )
    map_approval = service.approve(map_revision.id, "reviewer", "map approved")
    for building_id in (first_id, second_id):
        service.create_revision(
            project_id, ApprovalGate.REFERENCE, {"source": building_id},
            "reviewer", building_id, building_id,
        )
        service.create_revision(
            project_id, ApprovalGate.VIEW, {"views": 5},
            "reviewer", "five views", building_id,
        )

    reference_approvals = service.batch_approve(
        project_id, ApprovalGate.REFERENCE, (first_id, second_id), (second_id,),
        "lead", "batch with exception",
    )
    assert [item.building_id for item in reference_approvals] == [first_id]
    first_view = service.approve(
        service.latest_revision(project_id, ApprovalGate.VIEW, first_id).id, "lead"
    )
    second_reference = service.approve(
        service.latest_revision(project_id, ApprovalGate.REFERENCE, second_id).id, "lead"
    )
    second_view = service.approve(
        service.latest_revision(project_id, ApprovalGate.VIEW, second_id).id, "lead"
    )

    service.create_revision(
        project_id, ApprovalGate.REFERENCE, {"source": "corrected"},
        "editor", "source corrected", first_id,
    )
    by_id = {item.id: item for item in service.list_approvals(project_id)}
    assert not by_id[reference_approvals[0].id].valid
    assert not by_id[first_view.id].valid
    assert by_id[map_approval.id].valid
    assert by_id[second_reference.id].valid
    assert by_id[second_view.id].valid


def test_map_change_invalidates_all_and_audit_is_complete(tmp_path: Path) -> None:
    container, project_id, first_id, _ = project_with_two_buildings(tmp_path)
    service = container.approvals
    first = service.create_revision(
        project_id, ApprovalGate.MAP, {"version": 1}, "arya", "initial"
    )
    approval = service.approve(first.id, "arya", "looks good")

    second = service.create_revision(
        project_id, ApprovalGate.MAP, {"version": 2}, "mahdi", "boundary changed"
    )

    assert service.get_revision(first.id).payload_json == '{"version":1}'
    assert service.get_revision(second.id).version == 2
    assert not service.get_approval(approval.id).valid
    timeline = service.audit_timeline(project_id)
    assert [event.event_type for event in timeline] == [
        "revision_created", "approved", "revision_created"
    ]
    assert timeline[-1].actor == "mahdi"
    assert timeline[-1].comment == "boundary changed"
    assert "invalidated_approval_ids" in timeline[-1].changes_json

    # The unrelated building identifier remains valid input scope data.
    assert first_id
