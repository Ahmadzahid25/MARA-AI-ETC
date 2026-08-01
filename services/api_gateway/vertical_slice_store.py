"""Storage backends for vertical-slice API v1.

Provides a single repository interface with two implementations:

1. In-memory store for local/test wiring.
2. AsyncPG store for persistent dev/staging usage.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

import asyncpg

from shared.schemas.vertical_slice import (
    ApplicationStatus,
    OfficerDecisionAction,
    UserRole,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class VerticalSliceStore(Protocol):
    async def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
    ) -> dict[str, Any] | None: ...

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None: ...

    async def create_application(
        self,
        *,
        owner_user_id: str,
        applicant: dict[str, Any],
        business: dict[str, Any],
        financing: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    async def get_application(self, application_id: str) -> dict[str, Any] | None: ...

    async def list_applications(self) -> list[dict[str, Any]]: ...

    async def update_application(
        self,
        application_id: str,
        *,
        status: ApplicationStatus | None = None,
        ai_assessment: dict[str, Any] | None = None,
        stage_log: list[str] | None = None,
        decision_notes: str | None = None,
    ) -> dict[str, Any] | None: ...

    async def record_decision(
        self,
        application_id: str,
        *,
        action: OfficerDecisionAction,
        reason: str,
        decided_by: str,
        status: ApplicationStatus,
    ) -> dict[str, Any] | None: ...

    async def append_audit(
        self,
        *,
        actor: str,
        action: str,
        application_id: str | None,
        payload: dict[str, Any],
    ) -> None: ...

    async def add_document(
        self,
        application_id: str,
        *,
        doc_type: str,
        file_name: str,
        file_path: str,
        mime_type: str,
    ) -> dict[str, Any] | None: ...


class InMemoryVerticalSliceStore:
    def __init__(self) -> None:
        self.users_by_email: dict[str, dict[str, Any]] = {}
        self.applications: dict[str, dict[str, Any]] = {}
        self.audit_log: list[dict[str, Any]] = []
        # Dev bootstrap accounts for officer/admin flows.
        self.users_by_email['officer@mara.local'] = {
            'user_id': str(uuid.uuid4()),
            'full_name': 'MARA Officer',
            'email': 'officer@mara.local',
            'password_hash': _sha256('Officer123!'),
            'role': UserRole.OFFICER,
            'created_at': utc_now(),
        }
        self.users_by_email['admin@mara.local'] = {
            'user_id': str(uuid.uuid4()),
            'full_name': 'MARA Admin',
            'email': 'admin@mara.local',
            'password_hash': _sha256('Admin123!Secure'),
            'role': UserRole.ADMIN,
            'created_at': utc_now(),
        }

    async def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
    ) -> dict[str, Any] | None:
        if email in self.users_by_email:
            return None
        user = {
            'user_id': str(uuid.uuid4()),
            'full_name': full_name,
            'email': email,
            'password_hash': password_hash,
            'role': role,
            'created_at': utc_now(),
        }
        self.users_by_email[email] = user
        return user

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.users_by_email.get(email)

    async def create_application(
        self,
        *,
        owner_user_id: str,
        applicant: dict[str, Any],
        business: dict[str, Any],
        financing: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        application_id = str(uuid.uuid4())
        now = utc_now()
        workflow_meta = {
            'state': 'queued',
            'thread_id': application_id,
            'pending_gate': None,
        }
        app = {
            'application_id': application_id,
            'owner_user_id': owner_user_id,
            'status': ApplicationStatus.SUBMITTED,
            'applicant': applicant,
            'business': business,
            'financing': financing,
            'documents': documents,
            'ai_assessment': {
                'extraction_summary': {},
                'compliance_summary': {},
                'financial_summary': {},
                'risk_summary': {},
                'recommendation': {
                    'decision': None,
                    'withheld_reason': 'Pending workflow execution',
                    'confidence': 0.0,
                    'has_acknowledged_violation': False,
                },
                'citations': [],
                'stage_log': ['submitted'],
                'workflow': workflow_meta,
            },
            'workflow': workflow_meta,
            'stage_log': ['submitted'],
            'decision_notes': '',
            'decided_by': None,
            'decided_at': None,
            'created_at': now,
            'updated_at': now,
        }
        self.applications[application_id] = app
        return app

    async def get_application(self, application_id: str) -> dict[str, Any] | None:
        row = self.applications.get(application_id)
        if row is None:
            return None
        workflow = (row.get('ai_assessment') or {}).get('workflow') or row.get(
            'workflow'
        )
        if workflow is None:
            workflow = {
                'state': 'queued',
                'thread_id': application_id,
                'pending_gate': None,
            }
        row['workflow'] = workflow
        if isinstance(row.get('ai_assessment'), dict):
            row['ai_assessment']['workflow'] = workflow
        return row

    async def list_applications(self) -> list[dict[str, Any]]:
        return list(self.applications.values())

    async def update_application(
        self,
        application_id: str,
        *,
        status: ApplicationStatus | None = None,
        ai_assessment: dict[str, Any] | None = None,
        stage_log: list[str] | None = None,
        decision_notes: str | None = None,
    ) -> dict[str, Any] | None:
        row = self.applications.get(application_id)
        if row is None:
            return None
        if status is not None:
            row['status'] = status
        if ai_assessment is not None:
            row['ai_assessment'] = ai_assessment
            workflow = ai_assessment.get('workflow') if isinstance(ai_assessment, dict) else None
            if workflow is not None:
                row['workflow'] = workflow
        if stage_log is not None:
            row['stage_log'] = stage_log
        if decision_notes is not None:
            row['decision_notes'] = decision_notes
        row['updated_at'] = utc_now()
        return row

    async def record_decision(
        self,
        application_id: str,
        *,
        action: OfficerDecisionAction,
        reason: str,
        decided_by: str,
        status: ApplicationStatus,
    ) -> dict[str, Any] | None:
        row = self.applications.get(application_id)
        if row is None:
            return None
        row['status'] = status
        row['decision_notes'] = reason
        row['decided_by'] = decided_by
        row['decided_at'] = utc_now()
        row['stage_log'] = [*row['stage_log'], f'officer_{action.value}']
        row['updated_at'] = utc_now()
        return row

    async def append_audit(
        self,
        *,
        actor: str,
        action: str,
        application_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        self.audit_log.append(
            {
                'actor': actor,
                'action': action,
                'application_id': application_id,
                'payload_hash': hashlib.sha256(
                    str(sorted(payload.items())).encode('utf-8')
                ).hexdigest(),
                'timestamp': utc_now().isoformat(),
            }
        )

    async def add_document(
        self,
        application_id: str,
        *,
        doc_type: str,
        file_name: str,
        file_path: str,
        mime_type: str,
    ) -> dict[str, Any] | None:
        row = self.applications.get(application_id)
        if row is None:
            return None
        doc = {
            'doc_type': doc_type,
            'file_name': file_name,
            'file_path': file_path,
            'mime_type': mime_type,
        }
        row['documents'] = [*row['documents'], doc]
        row['updated_at'] = utc_now()
        return doc


class AsyncpgVerticalSliceStore:
    """DB-backed store against the per-branch schema
    (infrastructure/compose/init/branch-init.sql).

    ``branch_code`` identifies which branch database this store is writing to —
    it is stamped onto ``mara_users.branch_code`` and every ``audit_memory``
    row, and feeds ``generate_reference_no()`` for application reference
    numbers. Supplied at startup from ``settings.branch.code`` so audit and
    reference numbering stay consistent per branch.
    """

    def __init__(self, pool: asyncpg.Pool, branch_code: str = 'hq') -> None:
        self.pool = pool
        self.branch_code = branch_code

    async def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
    ) -> dict[str, Any] | None:
        user_id = str(uuid.uuid4())
        try:
            row = await self.pool.fetchrow(
                """
                INSERT INTO mara_users (
                    id, full_name, email, password_hash, role, branch_code
                )
                VALUES ($1::uuid, $2, $3, $4, $5, $6)
                RETURNING id::text AS user_id, full_name, email, role, created_at
                """,
                user_id,
                full_name,
                email,
                password_hash,
                role.value,
                self.branch_code,
            )
        except asyncpg.UniqueViolationError:
            return None
        return dict(row) if row else None

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT
                id::text AS user_id,
                full_name,
                email,
                password_hash,
                role,
                created_at
            FROM mara_users
            WHERE email = $1
            """,
            email,
        )
        if row is None:
            return None
        data = dict(row)
        data['role'] = UserRole(data['role'])
        return data

    async def create_application(
        self,
        *,
        owner_user_id: str,
        applicant: dict[str, Any],
        business: dict[str, Any],
        financing: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = utc_now()
        applicant_id = str(uuid.uuid4())
        business_id = str(uuid.uuid4())
        application_id = str(uuid.uuid4())
        ai_assessment = {
            'extraction_summary': {},
            'compliance_summary': {},
            'financial_summary': {},
            'risk_summary': {},
            'recommendation': {
                'decision': None,
                'withheld_reason': 'Pending workflow execution',
                'confidence': 0.0,
                'has_acknowledged_violation': False,
            },
            'citations': [],
            'stage_log': ['submitted'],
            'workflow': {
                'state': 'queued',
                'thread_id': application_id,
                'pending_gate': None,
            },
        }
        stage_log = ['submitted']

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Guna INSERT ... ON CONFLICT supaya satu pemohon boleh hantar
                # berbilang permohonan (cth selepas REJECTED/WITHDRAWN) tanpa
                # UniqueViolation pada ic_number / ssm_number. Profil &
                # perniagaan sedia ada dikemas kini dengan data terkini.
                applicant_id_row = await conn.fetchrow(
                    """
                    INSERT INTO applicants (id, user_id, full_name, ic_number, phone, email, state)
                    VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7)
                    ON CONFLICT (ic_number) DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        phone = EXCLUDED.phone,
                        email = EXCLUDED.email,
                        state = EXCLUDED.state,
                        updated_at = now()
                    RETURNING id
                    """,
                    applicant_id,
                    owner_user_id,
                    applicant['full_name'],
                    applicant['ic_number'],
                    applicant['phone'],
                    applicant['email'],
                    applicant['state'],
                )
                assert applicant_id_row is not None
                applicant_id = str(applicant_id_row['id'])

                business_id_row = await conn.fetchrow(
                    """
                    INSERT INTO businesses (
                        id, applicant_id, business_name, ssm_number, sector,
                        years_operating, monthly_revenue_avg
                    )
                    VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7)
                    ON CONFLICT (ssm_number) DO UPDATE SET
                        business_name = EXCLUDED.business_name,
                        sector = EXCLUDED.sector,
                        years_operating = EXCLUDED.years_operating,
                        monthly_revenue_avg = EXCLUDED.monthly_revenue_avg,
                        updated_at = now()
                    RETURNING id
                    """,
                    business_id,
                    applicant_id,
                    business['business_name'],
                    business['ssm_number'],
                    business['sector'],
                    business['years_operating'],
                    business['monthly_revenue_avg'],
                )
                assert business_id_row is not None
                business_id = str(business_id_row['id'])
                await conn.execute(
                    """
                    INSERT INTO applications (
                        id, reference_no, applicant_id, business_id, scheme,
                        amount_requested, purpose, tenure_months, status,
                        ai_assessment, stage_log, decision_notes,
                        created_at, updated_at
                    )
                    VALUES (
                        $1::uuid, generate_reference_no($2), $3::uuid, $4::uuid,
                        $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12, $13, $14
                    )
                    """,
                    application_id,
                    self.branch_code,
                    applicant_id,
                    business_id,
                    financing['scheme'],
                    financing['amount_requested'],
                    financing['purpose'],
                    financing['tenure_months'],
                    ApplicationStatus.SUBMITTED.value,
                    # asyncpg memerlukan lajur jsonb dihantar sebagai string JSON,
                    # bukan dict/list Python — serialize di sini.
                    json.dumps(ai_assessment),
                    json.dumps(stage_log),
                    '',
                    now,
                    now,
                )
                for doc in documents:
                    await conn.execute(
                        """
                        INSERT INTO application_documents (
                            id, application_id, doc_type, file_name, file_path, mime_type
                        )
                        VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6)
                        """,
                        str(uuid.uuid4()),
                        application_id,
                        doc['doc_type'],
                        doc['file_name'],
                        doc['file_path'],
                        doc['mime_type'],
                    )
        row = await self.get_application(application_id)
        assert row is not None
        return row

    async def get_application(self, application_id: str) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT
                a.id::text AS application_id,
                u.id::text AS owner_user_id,
                a.status,
                a.scheme,
                a.amount_requested,
                a.purpose,
                a.tenure_months,
                a.ai_assessment,
                a.stage_log,
                a.decision_notes,
                a.decided_by::text AS decided_by,
                a.decided_at,
                a.created_at,
                a.updated_at,
                ap.full_name,
                ap.ic_number,
                ap.phone,
                ap.email,
                ap.state,
                b.business_name,
                b.ssm_number,
                b.sector,
                b.years_operating,
                b.monthly_revenue_avg
            FROM applications a
            JOIN applicants ap ON ap.id = a.applicant_id
            JOIN businesses b ON b.id = a.business_id
            JOIN mara_users u ON u.id = ap.user_id
            WHERE a.id = $1::uuid
            """,
            application_id,
        )
        if row is None:
            return None

        docs = await self.pool.fetch(
            """
            SELECT doc_type, file_name, file_path, mime_type
            FROM application_documents
            WHERE application_id = $1::uuid
            ORDER BY created_at ASC
            """,
            application_id,
        )

        data = dict(row)
        # asyncpg mengembalikan lajur jsonb sebagai str mentah — parse semula
        # kepada dict/list Python supaya pemanggil dapat struktur yang konsisten
        # dengan InMemoryVerticalSliceStore.
        ai_assessment = data.get('ai_assessment')
        if isinstance(ai_assessment, str):
            ai_assessment = json.loads(ai_assessment)
        stage_log = data.get('stage_log')
        if isinstance(stage_log, str):
            stage_log = json.loads(stage_log)

        workflow = (ai_assessment or {}).get('workflow') or {
            'state': 'queued',
            'thread_id': application_id,
            'pending_gate': None,
        }
        return {
            'application_id': data['application_id'],
            'owner_user_id': data['owner_user_id'],
            'status': ApplicationStatus(data['status']),
            'applicant': {
                'full_name': data['full_name'],
                'ic_number': data['ic_number'],
                'phone': data['phone'],
                'email': data['email'],
                'state': data['state'],
            },
            'business': {
                'business_name': data['business_name'],
                'ssm_number': data['ssm_number'],
                'sector': data['sector'],
                'years_operating': data['years_operating'],
                'monthly_revenue_avg': float(data['monthly_revenue_avg']),
            },
            'financing': {
                'scheme': data['scheme'],
                'amount_requested': float(data['amount_requested']),
                'purpose': data['purpose'],
                'tenure_months': data['tenure_months'],
            },
            'documents': [dict(d) for d in docs],
            'ai_assessment': ai_assessment or {},
            'workflow': workflow,
            'stage_log': stage_log or [],
            'decision_notes': data['decision_notes'],
            'decided_by': data['decided_by'],
            'decided_at': data['decided_at'],
            'created_at': data['created_at'],
            'updated_at': data['updated_at'],
        }

    async def list_applications(self) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT a.id::text AS application_id
            FROM applications a
            ORDER BY a.updated_at DESC
            """
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            item = await self.get_application(row['application_id'])
            if item is not None:
                results.append(item)
        return results

    async def update_application(
        self,
        application_id: str,
        *,
        status: ApplicationStatus | None = None,
        ai_assessment: dict[str, Any] | None = None,
        stage_log: list[str] | None = None,
        decision_notes: str | None = None,
    ) -> dict[str, Any] | None:
        current = await self.get_application(application_id)
        if current is None:
            return None

        new_status = status.value if status else current['status'].value
        new_ai = ai_assessment if ai_assessment is not None else current['ai_assessment']
        new_stage = stage_log if stage_log is not None else current['stage_log']
        new_notes = decision_notes if decision_notes is not None else current['decision_notes']

        await self.pool.execute(
            """
            UPDATE applications
            SET
                status = $2,
                ai_assessment = $3::jsonb,
                stage_log = $4::jsonb,
                decision_notes = $5,
                updated_at = now()
            WHERE id = $1::uuid
            """,
            application_id,
            new_status,
            json.dumps(new_ai),
            json.dumps(new_stage),
            new_notes,
        )
        return await self.get_application(application_id)

    async def record_decision(
        self,
        application_id: str,
        *,
        action: OfficerDecisionAction,
        reason: str,
        decided_by: str,
        status: ApplicationStatus,
    ) -> dict[str, Any] | None:
        current = await self.get_application(application_id)
        if current is None:
            return None
        stage_log = [*current['stage_log'], f'officer_{action.value}']
        await self.pool.execute(
            """
            UPDATE applications
            SET
                status = $2,
                decision_notes = $3,
                decided_by = $4::uuid,
                decided_at = now(),
                stage_log = $5::jsonb,
                updated_at = now()
            WHERE id = $1::uuid
            """,
            application_id,
            status.value,
            reason,
            decided_by,
            json.dumps(stage_log),
        )
        return await self.get_application(application_id)

    async def append_audit(
        self,
        *,
        actor: str,
        action: str,
        application_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        workflow_id = application_id
        await self.pool.execute(
            """
            INSERT INTO audit_memory (
                workflow_id, actor_id, actor_role, branch_code, event_type, payload
            )
            VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb)
            """,
            workflow_id,
            actor,
            'system',
            self.branch_code,
            action,
            json.dumps(
                {
                    'application_id': application_id,
                    'payload_hash': hashlib.sha256(
                        str(sorted(payload.items())).encode('utf-8')
                    ).hexdigest(),
                    'payload': payload,
                }
            ),
        )

    async def add_document(
        self,
        application_id: str,
        *,
        doc_type: str,
        file_name: str,
        file_path: str,
        mime_type: str,
    ) -> dict[str, Any] | None:
        exists = await self.pool.fetchval(
            "SELECT 1 FROM applications WHERE id = $1::uuid",
            application_id,
        )
        if exists is None:
            return None

        await self.pool.execute(
            """
            INSERT INTO application_documents (
                id, application_id, doc_type, file_name, file_path, mime_type
            )
            VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6)
            """,
            str(uuid.uuid4()),
            application_id,
            doc_type,
            file_name,
            file_path,
            mime_type,
        )
        await self.pool.execute(
            "UPDATE applications SET updated_at = now() WHERE id = $1::uuid",
            application_id,
        )
        return {
            'doc_type': doc_type,
            'file_name': file_name,
            'file_path': file_path,
            'mime_type': mime_type,
        }


async def seed_default_users(store: VerticalSliceStore) -> None:
    """Ensure deterministic officer/admin accounts exist for local slice runs."""

    for full_name, email, password, role in (
        ('MARA Officer', 'officer@mara.local', 'Officer123!', UserRole.OFFICER),
        ('MARA Admin', 'admin@mara.local', 'Admin123!Secure', UserRole.ADMIN),
    ):
        existing = await store.get_user_by_email(email)
        if existing is not None:
            continue
        await store.create_user(
            full_name=full_name,
            email=email,
            password_hash=_sha256(password),
            role=role,
        )
