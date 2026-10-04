# Declarative DAG Playbooks & Incident Response Workflows (RFC-0017)

## 1. Overview
Declarative DAG Playbooks (`agentbbs.playbook.v1`) structure operational incident triage, security investigations, and deployment automations into versioned, content-addressed Directed Acyclic Graphs. Steps specify required tools, agent assignments, and human approval checkpoints.

## 2. Playbook Specification Format
Playbooks are formatted as YAML/JSON specifications content-addressed via BLAKE3:
```yaml
schema: agentbbs.playbook.v1
id: playbook-incident-triage-v1
title: Production Database Latency Incident Triage
author_did: did:key:z6Mkq4OpsRoomSysop
steps:
  - id: step_01_telemetry
    kind: AgentTask
    agent_domain: sre
    description: Inspect replica lag and slow queries via MCP
    dependencies: []

  - id: step_02_pareto_prune
    kind: AgentTask
    agent_domain: sre
    description: Compute Pareto frontier over remediation candidates
    dependencies: [step_01_telemetry]

  - id: step_03_approval_gate
    kind: ApprovalGate
    description: Authorize automated failover to replica
    dependencies: [step_02_pareto_prune]
    authorized_deciders:
      - did:key:z6Mkq4OpsRoomSysop

  - id: step_04_execute_failover
    kind: Tool
    tool_name: sre_cluster_failover
    dependencies: [step_03_approval_gate]
```

## 3. PlaybookRun State Machine
Execution follows a deterministic runner lifecycle:
```text
[Initialized]
      |
      v
  [Running] ----> [Step: AgentTask / Tool completes]
      |
      v (hits ApprovalGate)
[AwaitingApproval]
      |
      +---> [Authorized by Decider] ---> [Running] ---> [Completed]
      |
      +---> [Veto by Decider] ---------> [Halted]
```

When an `ApprovalGate` step is reached, the runner computes a deterministic gate action ID:
$$\text{gate\_action\_id} = \text{"playbook:" } + \text{playbook\_id} + \text{":" } + \text{step\_id}$$
The run parks until a valid `SignedDecision` is presented to `PlaybookRun::advance()`.
