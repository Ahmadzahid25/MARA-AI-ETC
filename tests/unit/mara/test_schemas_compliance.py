"""Unit tests for shared/schemas/compliance.py."""

from __future__ import annotations

import pytest

from shared.schemas.compliance import (
    ComplianceChecklist,
    ComplianceChecklistItem,
    ComplianceStatus,
)


def _item(status: ComplianceStatus) -> ComplianceChecklistItem:
    return ComplianceChecklistItem(requirement='req', status=status)


class TestComplianceChecklistItem:
    @pytest.mark.parametrize(
        'status',
        [
            ComplianceStatus.PASS,
            ComplianceStatus.EXCEPTION,
            ComplianceStatus.NO_POLICY_FOUND,
        ],
    )
    def test_only_fail_is_a_hard_violation(self, status: ComplianceStatus) -> None:
        assert _item(status).is_hard_violation() is False

    def test_fail_is_a_hard_violation(self) -> None:
        assert _item(ComplianceStatus.FAIL).is_hard_violation() is True

    def test_policy_citation_defaults_to_none(self) -> None:
        item = _item(ComplianceStatus.NO_POLICY_FOUND)
        assert item.policy_citation is None


class TestComplianceChecklist:
    def test_has_hard_violation_true_if_any_item_fails(self) -> None:
        checklist = ComplianceChecklist(
            document_id='doc-1',
            items=[_item(ComplianceStatus.PASS), _item(ComplianceStatus.FAIL)],
        )
        assert checklist.has_hard_violation is True

    def test_has_hard_violation_false_if_no_item_fails(self) -> None:
        checklist = ComplianceChecklist(
            document_id='doc-1',
            items=[_item(ComplianceStatus.PASS), _item(ComplianceStatus.EXCEPTION)],
        )
        assert checklist.has_hard_violation is False

    def test_empty_checklist_has_no_hard_violation(self) -> None:
        checklist = ComplianceChecklist(document_id='doc-1')
        assert checklist.has_hard_violation is False
