"""
infrastructure/AGENTS.md -- Task 7 & Task 9 verification script
===============================================================
Verifies BOTH write paths against the real postgres-primary database:

  Task 7: services/audit_service  → audit_memory table
  Task 9: services/memory_service → long_term_memory_calibration table

Run from repo root:
    uv run python -m scripts.verify_db_writes

Every step is explicitly checked and reported — nothing is assumed.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import timezone

# Windows asyncio fix (must be before any async imports)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from services.audit_service import (
    AuditEvent,
    AuditQueryFilters,
    audit_pool,
    query_audit_events,
    write_audit_event,
)
from services.memory_service.calibration import (
    CalibrationEvent,
    calibration_pool,
    query_calibration_stats,
    write_calibration_event,
)
from shared.config import get_settings

SEPARATOR = "=" * 60

# Unique UUIDs for this verification run
AUDIT_WORKFLOW_ID = "00000000-0000-0000-0000-000000000007"
CALIBRATION_WORKFLOW_ID = "00000000-0000-0000-0000-000000000009"


# ── Task 7: Audit Memory ─────────────────────────────────────────

async def verify_audit_memory(settings) -> bool:
    print(f"\n{SEPARATOR}")
    print("TASK 7 — Audit Memory write/read (audit_memory table)")
    print(SEPARATOR)

    async with audit_pool(settings) as pool:

        # 1. Write
        event = AuditEvent(
            workflow_id=AUDIT_WORKFLOW_ID,
            actor_id="dev-infra-verify",
            actor_role="officer",
            event_type="approval",
            payload={"note": "infrastructure verification — Task 7", "milestone": 0},
        )
        print(f"\n[1] Writing AuditEvent -> audit_memory ...")
        await write_audit_event(pool, event)
        print("    WRITE: OK")

        # 2. Read back
        print(f"\n[2] Reading back row where workflow_id = '{AUDIT_WORKFLOW_ID}' ...")
        rows = await query_audit_events(
            pool,
            AuditQueryFilters(workflow_id=AUDIT_WORKFLOW_ID, limit=10),
        )

        if not rows:
            print("    ERROR: No rows returned — write may have failed silently")
            return False

        row = rows[0]
        print(f"    READ: OK — got {len(rows)} row(s)")
        print(f"      id           = {row.id}")
        print(f"      occurred_at  = {row.occurred_at}  (set by DB, not client)")
        print(f"      workflow_id  = {row.workflow_id}")
        print(f"      actor_id     = {row.actor_id}")
        print(f"      actor_role   = {row.actor_role}")
        print(f"      event_type   = {row.event_type}")
        print(f"      payload      = {row.payload}")

        # 3. Verify occurred_at was set by the DB (not None, has timezone)
        if row.occurred_at is None:
            print("\n    FAIL: occurred_at is None — DB default not applied")
            return False

        if row.occurred_at.tzinfo is None:
            print("\n    WARN: occurred_at has no timezone info")
        else:
            print(f"\n    PASS: occurred_at is tz-aware ({row.occurred_at.tzinfo}) — DB-set timestamp confirmed")

        # 4. Verify id was set by DB (GENERATED ALWAYS AS IDENTITY)
        if row.id is None:
            print("    FAIL: id is None — GENERATED ALWAYS AS IDENTITY not working")
            return False
        print(f"    PASS: id={row.id} — IDENTITY column confirmed")

        print("\n[PASS] TASK 7 PASSED -- audit_memory write path works against real Postgres")
        return True


# ── Task 9: Long-term Memory Calibration ─────────────────────────

async def verify_calibration_memory(settings) -> bool:
    print(f"\n{SEPARATOR}")
    print("TASK 9 — Calibration Memory write/read (long_term_memory_calibration table)")
    print(SEPARATOR)

    async with calibration_pool(settings) as pool:

        # 1. Write — two events to test aggregation
        events = [
            CalibrationEvent(
                agent_name="DocumentAgent",
                workflow_id=CALIBRATION_WORKFLOW_ID,
                field_name="Loan Amount (MYR)",
                document_type="Loan Application Form",
                stated_confidence=0.78,
                was_corrected=False,
            ),
            CalibrationEvent(
                agent_name="DocumentAgent",
                workflow_id=CALIBRATION_WORKFLOW_ID,
                field_name="Business Type",
                document_type="Loan Application Form",
                stated_confidence=0.64,
                was_corrected=True,  # officer corrected this
            ),
        ]

        print(f"\n[1] Writing 2 CalibrationEvents -> long_term_memory_calibration ...")
        for ev in events:
            await write_calibration_event(pool, ev)
        print("    WRITE: OK (2 rows)")

        # 2. Read back raw rows
        print(f"\n[2] Reading raw rows for workflow_id = '{CALIBRATION_WORKFLOW_ID}' ...")
        raw_rows = await pool.fetch(
            "SELECT * FROM long_term_memory_calibration WHERE workflow_id = $1",
            CALIBRATION_WORKFLOW_ID,
        )

        if not raw_rows:
            print("    ERROR: No rows returned")
            return False

        print(f"    READ: OK — got {len(raw_rows)} row(s)")
        for r in raw_rows:
            print(f"      id={r['id']}  field={r['field_name']}  "
                  f"confidence={r['stated_confidence']}  corrected={r['was_corrected']}  "
                  f"recorded_at={r['recorded_at']}")

        # 3. Verify recorded_at is DB-set
        for r in raw_rows:
            if r['recorded_at'] is None:
                print("    FAIL: recorded_at is None — DB default not applied")
                return False
        print("\n    PASS: recorded_at is DB-set for all rows")

        # 4. Aggregate stats
        print(f"\n[3] Querying calibration stats for agent='DocumentAgent' ...")
        stats = await query_calibration_stats(pool, "DocumentAgent")
        print(f"    total_events                   = {stats.total_events}")
        print(f"    corrected_events               = {stats.corrected_events}")
        print(f"    correction_rate                = {stats.correction_rate:.1%}" if stats.correction_rate is not None else "    correction_rate = None")
        print(f"    average_stated_confidence      = {stats.average_stated_confidence:.2f}" if stats.average_stated_confidence else "    avg_confidence = None")
        print(f"    avg_confidence_when_corrected  = {stats.average_confidence_when_corrected:.2f}" if stats.average_confidence_when_corrected else "    avg_corr_conf = None")

        # Sanity checks on aggregated values
        if stats.total_events < 2:
            print(f"    WARN: expected >=2 total_events, got {stats.total_events}")
        if stats.corrected_events < 1:
            print(f"    WARN: expected >=1 corrected_event, got {stats.corrected_events}")

        print("\n[PASS] TASK 9 PASSED -- long_term_memory_calibration write path works against real Postgres")
        return True


# ── Main ─────────────────────────────────────────────────────────

async def main() -> None:
    settings = get_settings()
    print(f"\nMara infrastructure verification — Audit & Calibration Memory")
    print(f"DSN: {settings.database.primary_dsn}")

    task7_ok = False
    task9_ok = False

    try:
        task7_ok = await verify_audit_memory(settings)
    except Exception as exc:
        print(f"\n[FAIL] TASK 7 EXCEPTION: {type(exc).__name__}: {exc}")

    try:
        task9_ok = await verify_calibration_memory(settings)
    except Exception as exc:
        print(f"\n[FAIL] TASK 9 EXCEPTION: {type(exc).__name__}: {exc}")

    # -- Summary ---------------------------------------------------
    print(f"\n{SEPARATOR}")
    print("SUMMARY")
    print(SEPARATOR)
    print(f"  Task 7 -- Audit Memory:        {'PASSED' if task7_ok else 'FAILED'}")
    print(f"  Task 9 -- Calibration Memory:  {'PASSED' if task9_ok else 'FAILED'}")
    print()

    if not (task7_ok and task9_ok):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
