## Verification Report

**Change**: fix-review-findings
**Version**: N/A
**Mode**: Standard

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 13 |
| Tasks complete | 13 |
| Tasks incomplete | 0 |
| Review budget evidence | 177 tracked changed lines (`git diff --stat` before this report), under the 400-line budget |

### Build & Tests Execution

**Build**: ➖ Not configured

```text
openspec/config.yaml has no build, lint, typecheck, or coverage commands configured for this project.
```

**Static check**: ✅ Passed

```text
$ git diff --check
Command executed successfully
```

**Focused tests**: ✅ 22 passed

```text
$ uv run pytest tests/test_pack_routes.py -q
......................                                                   [100%]
22 passed, 1 warning in 1.02s
```

**Full tests**: ✅ 264 passed

```text
$ uv run pytest -q
........................................................................ [ 27%]
........................................................................ [ 54%]
........................................................................ [ 81%]
................................................                         [100%]
264 passed, 1 warning in 37.03s
```

**Coverage**: ➖ Not available / threshold: N/A → ➖ Not configured

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Startup-derived storage root | Publish uses stable startup data directory | `tests/test_pack_routes.py::test_pack_publish_works_with_relative_data_dir` | ✅ COMPLIANT |
| Startup-derived storage root | Request-time drift is ignored | `tests/test_pack_routes.py::test_pack_publish_ignores_request_time_data_dir_drift` | ✅ COMPLIANT |
| Safe orphan final-pack cleanup | Proven orphan is cleaned | `tests/test_pack_routes.py::test_pack_publish_cleans_proven_orphan_final_directory` | ✅ COMPLIANT |
| Safe orphan final-pack cleanup | Ambiguous storage is preserved | `tests/test_pack_routes.py::test_pack_publish_preserves_db_referenced_final_directory` | ✅ COMPLIANT |
| Invalid Content-Length becomes JSON 400 | Malformed header is rejected | `tests/test_pack_routes.py::test_pack_publish_rejects_invalid_content_length_with_json_400` | ✅ COMPLIANT |
| Invalid Content-Length becomes JSON 400 | Non-numeric header is rejected | `tests/test_pack_routes.py::test_pack_publish_rejects_invalid_content_length_with_json_400` | ✅ COMPLIANT |
| Oversized payloads still return 413 | Oversized request remains 413 | `tests/test_pack_routes.py::test_pack_publish_rejects_streamed_body_over_body_cap` | ✅ COMPLIANT |

**Compliance summary**: 7/7 scenarios compliant

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Startup-derived storage root | ✅ Implemented | `agh/server/app.py` resolves and stores `application.state.data_dir`; `agh/server/routes/packs.py` reads publish storage through `_publish_data_dir(request)`. |
| Safe orphan final-pack cleanup | ✅ Implemented | `publish_pack()` checks for existing canonical DB rows before storage preparation; `_prepare_storage_target()` deletes only existing directories with no DB storage-path reference. |
| Ambiguous storage is preserved | ✅ Implemented | `_prepare_storage_target()` rejects non-directories, symlinked path components, and DB-referenced storage paths before deletion. |
| Invalid Content-Length becomes JSON 400 | ✅ Implemented | `_parse_content_length()` rejects empty, signed, decimal, and non-numeric values; middleware returns `{"detail": "invalid content-length header"}` with HTTP 400. |
| Oversized payloads still return 413 | ✅ Implemented | Middleware preserves header-based 413 behavior and `_read_pack_publish_payload()` preserves streamed body-size 413 behavior. |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Store startup `data_dir` in FastAPI app state | ✅ Yes | Implementation stores `application.state.data_dir = data_dir` alongside `application.state.db_path`. |
| Pack routes derive storage from app state | ✅ Yes | `packs.py` no longer imports `get_data_dir()` and publish uses `request.app.state.data_dir`. |
| Conservative orphan recovery | ✅ Yes | Existing final directories are removed only after canonical-version absence and storage-path-reference absence are established. |
| Invalid `Content-Length` returns JSON 400; oversized remains JSON 413 | ✅ Yes | Runtime tests cover invalid values and oversized streamed payloads. |
| Scope remains first-slice only | ✅ Yes | Code changes are limited to `agh/server/app.py`, `agh/server/routes/packs.py`, and focused pack-route tests. Deferred review findings remain out of scope. |

### Issues Found

**CRITICAL**: None

**WARNING**:

- The test suite emits a pre-existing dependency warning: `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` This does not block this change, but should be tracked before dependency upgrades make it noisy or breaking.

**SUGGESTION**:

- Consider adding lint/typecheck/coverage commands to `openspec/config.yaml` so future verification can prove more than runtime tests and whitespace checks.

### Verdict

PASS WITH WARNINGS

All OpenSpec scenarios are covered by passing runtime tests, all tasks are complete, and the implementation follows the design. The only warning is an unrelated TestClient deprecation emitted by the current test stack.
