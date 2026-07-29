# 2026-07-29 Vertical Slice Recovery Handoff

Purpose: this file is the restart point after machine reset / PC format.

## Source of truth

1. Remote repository: `origin/main`
2. Latest verified backup commit at handoff time: `47ada06`
3. Commit message: `Implement vertical-slice API flow and officer workspace integration`

If the local machine is wiped, clone the repository again and start from this
commit or any later commit on `main`.

## What is already completed

### Backend / vertical slice

1. Phase 17 execution directive added and linked.
2. v1 contracts added for applicant/officer vertical slice.
3. `/api/v1` endpoints implemented for:
   - register/login
   - create application
   - upload application document
   - application detail
   - application status
   - officer queue
   - officer decision
4. In-memory + AsyncPG vertical-slice store abstraction implemented.
5. Workflow status mapping implemented:
   - `queued` -> `SUBMITTED`
   - `running` -> `PROCESSING`
   - `paused@recommendation_approval` -> `UNDER_REVIEW`
   - `completed` -> `APPROVED`
   - `failed` / `resume_failed` -> `NEEDS_INFO`
6. Upload can retrigger workflow for waiting / retry-required states.
7. Unit tests verified for:
   - vertical slice router
   - recommendation agent
   - loan assessment workflow

### Frontend / officer workspace

1. `src/services/api.ts` contains typed `/api/v1/*` contracts.
2. `src/services/data.ts` maps officer queue data into dashboard/review models.
3. Review Console now shows live vertical-slice officer queue.
4. Officer queue actions verified live:
   - `approve`
   - `reject`
   - `request_more_info`
5. Dev-mode login patched to obtain a real backend JWT when backend is up.
6. `apps/officer-workspace/AGENTS.md` expanded with phased frontend delivery guidance.

## Files to read first when resuming

1. `docs/architecture/00-INDEX.md`
2. `docs/architecture/17-vertical-slice-execution-directive.md`
3. `overallPlan.md`
4. `apps/officer-workspace/AGENTS.md`

## Verified tests at handoff

Run from repo root:

```powershell
uv run --directory . python -m pytest tests/unit/mara/test_vertical_slice_router.py tests/unit/mara/test_recommendation_agent.py tests/unit/mara/test_loan_assessment_workflow.py -q
```

Last known result before handoff:

```text
24 passed in 5.59s
```

## Local startup recipes

### Officer workspace frontend

Run from `apps/officer-workspace`:

```powershell
npm run build
npm run dev
```

Expected URL:

```text
http://localhost:4000/
```

### API Gateway real/default path

Vite proxy currently points `/api` to:

```text
http://localhost:8051
```

If running the real gateway entrypoint:

```powershell
uv run --directory . python -m services.api_gateway.main
```

### API Gateway local stub path used during UI validation

This was used to demo the queue/UI without full infra:

```powershell
Set-Location -LiteralPath 'e:\Production\Contribution[MARA]\OpenHands-main\MARA aiETC'
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$code = @'
import uvicorn
from services.api_gateway.app import create_app

class W:
    async def ainvoke(self, input, config=None):
        return {"stage_log": ["submitted"]}

app = create_app(workflow=W(), loan_workflow=W())
uvicorn.run(app, host="0.0.0.0", port=8052, log_level="info")
'@
$code | uv run --directory . python -
```

If the frontend should talk to this stub backend instead of port 8051, start
Vite with:

```powershell
$env:VITE_API_GATEWAY_URL='http://localhost:8052'
npm run dev
```

## Known local issues at handoff

1. On this machine, a polluted Python environment (`PYTHONHOME` / `PYTHONPATH`
   pointing to `C:\ZKBioWDMS\Python311`) caused `SRE module mismatch`.
   Clearing those env vars fixed local Python execution.
2. Earlier Vite errors mentioning `ECONNREFUSED` were caused by the frontend
   running while no backend process was listening on the configured target port.
3. If the officer queue shows 401 in dev mode, ensure mock login obtains a
   backend token and that the backend seed user exists:
   - `officer@mara.local` / `Officer123!`
4. OCR/document-classifier path is still incomplete by design; some non-v1
   assessment flows may still return 503 until that tool path is wired.

## Immediate next work after restart

### Highest priority

1. Frontend Lane C: applicant portal path
   - register/login
   - application form
   - document upload
   - status timeline

2. Frontend Lane D continuation: officer case detail page
   - load `GET /api/v1/applications/{application_id}`
   - render extraction/compliance/finance/risk/recommendation outputs
   - show `has_acknowledged_violation`

3. Smoke-path stabilization
   - applicant submits
   - officer reviews
   - status reflects decision

### Lower priority until vertical slice is fully closed

1. extra dashboards
2. voice expansion
3. broad UI refactors unrelated to R2/R4/R5

## Frontend ownership note

Frontend continuation instructions are intentionally captured in:

1. `apps/officer-workspace/AGENTS.md`

That file now acts as the execution brief for frontend developers so the core
team can focus on architecture, system integration, and agentic behavior.

## Recovery checklist after PC format

1. Clone repo.
2. Checkout `main`.
3. Read the four files listed in "Files to read first when resuming".
4. Run the three backend unit test files.
5. Start backend on either 8051 (real entrypoint) or 8052 (stub mode).
6. Start officer workspace frontend.
7. Continue from Phase 17 R2/R4 items only.