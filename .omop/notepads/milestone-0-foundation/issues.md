## [2026-07-23] Environment Assessment

### BLOCKER: Docker Not Available
Docker is not installed on this dev machine. Step 1 cannot be executed here.

### BLOCKER: Python Dependency Conflict
openhands-sdk==1.36.0 -> lmnr -> opentelemetry-semantic-conventions==0.60b1
but opentelemetry-instrumentation-fastapi>=0.60 needs >=0.61b0. Incompatible.

### BLOCKER: System Python broken
Python 3.14/3.13 pick up site-packages from Python 3.11 at C:\ZKBioWDMS\Python311.

### NOTE: event-stream-client missing
packages/event-stream-client/ does not exist yet (migration plan Phase 3).

### ISSUE: test_auth.py key format mismatch
test_auth.py uses pyjwt.encode() with PEM keys but authlib.jose expects JWK format.
Tests need to use authlib for key generation/signing, not pyjwt, for compatibility.
Cannot verify in this environment (Python broken). Fix before CI run.

### KNOWN CONFLICT: opentelemetry-instrumentation-fastapi vs lmnr
openhands-sdk==1.36.0 -> lmnr>=0.7.47 -> opentelemetry-semantic-conventions==0.60b1
but opentelemetry-instrumentation-fastapi>=0.60 (MARA addition) -> >=0.61b0.
These are fundamentally incompatible while lmnr pins semantic-conventions at 0.60b1.
Resolution options: (a) update openhands-sdk to use lmnr with relaxed pin, (b) make fastapi instrumentation optional, (c) pin to compatible versions. pyproject.toml was reverted to original state since fix could not be verified.

### BLOCKER: No disk space on dev machine
npm install and bun install both fail with ENOSPC. Cannot verify officer-workspace dependencies or build openhands-ui. This machine needs disk space cleared before any package installation can succeed.

### RESOLVED: ENOSPC was misdiagnosed (round 3)
npm install with --cache E:/npm-cache-tmp succeeds (95 packages, 0 vulns). 
Root cause of earlier failure was D: drive being full, not E: drive.
tsc --noEmit now passes after removing broken TS project-references from tsconfig.json.
test_auth.py encoding fixed (Windows-1252 -> UTF-8), all 5 test files pass py_compile.
