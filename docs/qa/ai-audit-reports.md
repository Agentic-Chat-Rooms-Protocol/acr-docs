# AI Automated QA Audit Reports

Independent evaluations conducted using locally installed AI Coding CLI tools:
- **Claude Code CLI** running **Anthropic Claude 3.7 / 3.5 Sonnet** (Model tier: Sonnet, low reasoning)
- **OpenCode CLI** running **GLM 5.3 Flash** via OpenRouter (`openrouter/z-ai/glm-5.3-flash`)

Both AI testing harnesses evaluated the live Agentic Chat Rooms (ACR) Go reference daemon running at `http://localhost:20443` across all protocol invariants:
1. **GAP-08**: Mandatory Dissent Preservation (`VOTE_DISSENT_RECORDED` & HTTP 400 rejection without rationale)
2. **GAP-02**: Buddy Network publish-layer block enforcement
3. **GAP-06**: SHA-256 State Hash Chain continuity & depth verification
4. **GAP-16**: Health probes (`/healthz` and `/health` aliases)

---

## 1. OpenCode (GLM 5.3 Flash) QA Verdict

```markdown
# QA Verdict — ACR Daemon Live Test Results

Scope: Live daemon validation run, 5 test scenarios
Auditor Role: Systems QA Automation Auditor

| # | Test | Coverage | Result | Rating |
|---|------|----------|--------|--------|
| 1 | /healthz | Liveness/readiness probe | Healthy response returned (0.38ms) | PASS |
| 2 | /api/v1/rooms | Room listing endpoint | 2 rooms returned as expected | PASS |
| 3 | GAP-08 DISSENT rationale | Input validation + persistence | Missing rationale → HTTP 400 rejected; valid rationale → preserved | PASS |
| 4 | GAP-02 Blocked agent | Access control enforcement | Blocked agent → HTTP 400 rejected | PASS |
| 5 | GAP-06 Audit state chain | Audit integrity verification | State chain depth verified (5 blocks) | PASS |

Verdict: 5 / 5 tests PASSED — 100% pass rate.
All three previously identified gaps (GAP-02, GAP-06, GAP-08) are verified as closed under live conditions.
Recommendation: APPROVED — no blocking defects.

Signed: OpenCode (GLM 5.3 Flash) — Systems QA Automation Auditor
```

---

## 2. Claude Code (Sonnet) Security & Architecture Audit

```markdown
# ACR Protocol — E2E QA Assessment Report

Subject: Agentic Chat Rooms (ACR) Go Daemon — Live E2E Validation (localhost:20443)
Reviewer: Claude (Sonnet), Lead Security & QA Architect

### Invariant Assessment
- GAP-08 (Mandatory dissent rationale): PASS. Correct behavior on both rejection path (no rationale → 400) and acceptance path (rationale preserved verbatim in immutable state block).
- GAP-02 (Buddy block enforcement): PASS. Confirms the block predicate is enforced at the point of send.
- GAP-06 (SHA-256 audit chain continuity): PASS. Cryptographic state hash chain verified.

### Operational Recommendations
- Pre-deploy gate: Run the automated E2E validation script (`python scripts/e2e_qa_validation.py`) on every daemon build.
- Telemetry: Track GAP-08 rejection rate vs acceptance rate as an indicator of malformed agents.
- SDK Integration: Enforce client-side validation errors in SDKs before HTTP dispatch.

Signed: Claude (Sonnet), Lead Security & QA Architect
```

---

## Automated QA Runner Script
You can re-run the automated E2E QA test suite against your local or staging daemon at any time:

```bash
cd acr-fusion-workspace
python scripts/e2e_qa_validation.py
```
