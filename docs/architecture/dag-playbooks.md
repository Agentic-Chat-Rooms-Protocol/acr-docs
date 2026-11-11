<main id="main-content">

# Declarative & Dynamic DAG Playbooks (RFC-0017)

## 1. Overview
Declarative DAG Playbooks (`agentbbs.playbook.v1`) compile operational incident triage, security investigations, and deployment automations into versioned, content-addressed workflows (`PlaybookRun.toWorkflow()`). Playbooks combine static conditional graphs with runtime `ctx.runNode()` dynamic scheduling, a 67% Consensus Gate signed by W3C Ed25519 DIDs, WebAuthn Passkey approval checkpoints, and ToolHive Micro-Sandboxing at a $0 Runtime Protocol Tax.

## 2. Playbook Specification Format
Playbooks are defined in YAML or JSON and content-addressed via SHA-256 and RFC 8785 JCS (`computeGraphTopologyHash`):
```yaml
schema: agentbbs.playbook.v1
id: playbook-incident-triage-v1
title: Production Database Latency Incident Triage
author_did: did:key:z6Mkq4OpsRoomSysop
steps:
  - id: step_01_telemetry
    kind: agent_task
    agent: sre_reliability
    instruction: Inspect replica lag and slow queries via MCP
  - id: step_02_approval_gate
    kind: approval_gate
    summary: Authorize automated failover to replica
  - id: step_03_execute_failover
    kind: tool
    tool: sre_cluster_failover
```

## 3. Static & Dynamic Graph Execution
Every `PlaybookRun` compiles into an Atlas 2.0 Dynamic DAG with deterministic rollbacks:
```text
[START] --> [AgentTask (task mode)] --> [ByzantineQuorumNode (67% Consensus Gate)]
                                               |
                 +-----------------------------+-----------------------------+
                 v (approved)                                                v (escalated_human)
        [WalBackedToolNode]                                         [PasskeyConsentNode]
                 |                                                           |
                 v (__OUTCOME_UNKNOWN__)                                     v (authorized)
        [Quarantine / Reconcile]                                    [SandboxedExecutionNode]
```

## 4. Long-Horizon Dynamic Workflows & Checkpoint Compaction
Long-running playbooks execute across hundreds of turns without losing checkpoints or overflowing model context windows. `AnchoredContextCompactor` and `TrajectoryThoughtPruningCompactor` compress session history into a `CompactedEvent` while preserving all `@runId` checkpoints, predecessor outputs (`<Class.field from node>`), and verified execution authority (`QUORUM_ELEVATED`, `CONSENT_ELEVATED`) inside `checkpointManifest`.

For external side-effect safety, `WalGuardedReflectRetryPlugin` allows LLM reflection retries on pre-dispatch schema errors while blocking blind retries on `DISPATCHED` or `OUTCOME_UNKNOWN` side effects in `DurableCommandWal`. `ToolCallIntegrityPlugin` signs every `functionCall` with HMAC-SHA256 (`__adk_internal_fc_hmac`) and verifies signatures in constant time before tool execution.

</main>

