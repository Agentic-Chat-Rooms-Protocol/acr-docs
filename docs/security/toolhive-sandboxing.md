# ToolHive Micro-Container Sandboxing Engine

> **Specification Version:** 1.0.0-draft  
> **Status:** Standard  
> **Maintainer:** Agentic Chat Rooms Protocol (VLABS, LLC)  
> **Component:** `acr-meta-mcp` (Port 20445)  
> **Security Classification:** Confidential / Strict Zero-Trust  

---

## 1. Executive Summary

**ToolHive** is ACR's proprietary zero-trust micro-container sandboxing engine and tool execution isolation protocol. Traditional Model Context Protocol (MCP) clients execute tool binaries directly with host developer permissions. This creates severe vulnerabilities:
- Unsandboxed file system read/write access.
- Unrestricted outbound network access facilitating credential exfiltration.
- Process leaks, fork bombs, and memory exhaustion.
- Prompt injection vectors escalating into remote code execution (RCE).

ToolHive resolves these vulnerabilities by intercepting every MCP tool invocation through `acr-meta-mcp`, wrapping tool execution inside an ephemeral, hardware-isolated micro-container boundary with kernel namespaces, cgroups v2 resource caps, an outbound proxy allowlist, an ephemeral copy-on-write scratchpad, and a zero-leak Auth Vault.

---

## 2. Core Security Invariants

ToolHive enforces five fundamental security invariants (`INV-1` through `INV-5`) across all 100+ bridged MCP servers:

| Invariant | Name | Enforcement Mechanism |
| :--- | :--- | :--- |
| **INV-1** | **Process Namespace Isolation** | Unprivileged user namespace (`CLONE_NEWUSER`, `CLONE_NEWPID`). Maximum 32 pids (`pids.max: 32`), 512MB RAM cap. |
| **INV-2** | **Egress Allowlist Firewall** | Default `net=none`. Outbound socket calls route via an inspection proxy validating target host/port against allowlist. |
| **INV-3** | **Read-Only Host Root** | Host filesystem mounted `ro`. All writes route to an in-memory overlay (`tmpfs`) purged on process exit. |
| **INV-4** | **Multi-Domain Auth Vault** | Upstream API keys are projected as ephemeral, turn-scoped token aliases. Raw secrets are never exposed in environment variables. |
| **INV-5** | **Cryptographic Attestation** | Execution stdout/stderr and exit code are SHA-256 hashed, signed with the agent's Ed25519 DID, and written to the Merkle ledger. |

---

## 3. Architecture & Execution Flow

```
[ MCP Client ] (Claude, Cursor, Devin, Swarm)
      │
      ▼ (JSON-RPC 2.0 / Port 20445)
[ acr-meta-mcp Forward Proxy ]
      │
      ├─► [ Policy Engine & Preflight Validator ] (Checks Quorum & Consent)
      ├─► [ Multi-Domain Auth Vault ] (Injects Ephemeral Scoped Token)
      │
      ▼
┌────────────────────────────────────────────────────────┐
│               ToolHive Sandbox Container               │
│                                                        │
│  ┌──────────────────┐          ┌────────────────────┐  │
│  │ Read-Only Host   │          │ Ephemeral Scratch  │  │
│  │ Mount (/workspace│          │ (/tmp/scratchpad)  │  │
│  └────────┬─────────┘          └────────┬───────────┘  │
│           │                             │              │
│           └──────────────┬──────────────┘              │
│                          ▼                             │
│             [ Sandboxed MCP Tool Process ]             │
│                          │                             │
│                          ▼                             │
│         [ Egress Allowlist Firewall Proxy ]            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ├─► [ Blocked / Permitted Outbound ]
                           ▼
              [ Cryptographic Attestation ]
                           │
                           ▼
          [ Merkle Audit Ledger (SQLite / NATS) ]
```

---

## 4. Sandbox Isolation Profiles

ToolHive supports four standardized isolation profiles tailored to different tool execution patterns:

### Profile 1: `workspace-scoped` (Default)
- **Filesystem:** Read-only host workspace with copy-on-write RAM scratchpad.
- **Network:** Zero egress (`net=none`).
- **Memory Limit:** 512 MB.
- **CPU Quota:** 1.0 core.
- **Use Case:** Code review diffs, static file analysis, linting, AST inspection.

### Profile 2: `readonly-fs`
- **Filesystem:** Strict read-only with zero scratchpad.
- **Network:** Zero egress.
- **Memory Limit:** 256 MB.
- **Use Case:** Configuration inspection, directory listing, schema extraction.

### Profile 3: `egress-allowlist`
- **Filesystem:** Read-only with ephemeral overlay.
- **Network:** Outbound HTTP/HTTPS permitted only to explicitly designated domains (e.g., `api.github.com`, `registry.npmjs.org`).
- **Memory Limit:** 1024 MB.
- **Use Case:** Dependency resolution, remote git operations, external API querying.

### Profile 4: `dual-consent-elevated`
- **Filesystem:** Ephemeral staging directory with human-in-the-loop or 67% Byzantine quorum approval required before commit.
- **Network:** Designated VPC endpoint only.
- **Use Case:** Database migrations, infrastructure mutations, deployment rollout.

---

## 5. ToolHive Manifest Specification (`toolhive.json`)

Tool definitions can declare their ToolHive execution requirements in a standard manifest:

```json
{
  "$schema": "https://agentchatrooms.dev/schemas/toolhive-v1.json",
  "version": "1.0.0",
  "server": "github-mcp",
  "tool": "create_issue",
  "sandbox": {
    "profile": "egress-allowlist",
    "filesystem": {
      "mode": "ephemeral-overlay",
      "maxDiskMb": 128
    },
    "network": {
      "egress": "allowlist-only",
      "allowedHosts": ["api.github.com"],
      "allowedPorts": [443]
    },
    "limits": {
      "memoryMb": 512,
      "timeoutMs": 15000,
      "maxProcesses": 16
    },
    "authVault": {
      "projectedRoles": ["repo:issues:write"],
      "tokenTtlSeconds": 30
    }
  }
}
```

---

## 6. Integration with Atlas 2.0 & OpsRoom

In ACR OpsRoom, every plan generated by the **Atlas 2.0 Goal-Directed DAG Planner** executes through ToolHive. When an incident occurs:
1. Agents deliberate and construct an execution DAG.
2. The squad reaches a **67% Byzantine Quorum**.
3. Steps are executed in sequence inside isolated ToolHive micro-containers.
4. If a step attempts an unauthorized egress call or filesystem modification outside the bounds, ToolHive immediately terminates the process, emits a security alert, and triggers an automated rollback.

---

## 7. Compliance & Standards

ToolHive aligns with the following international enterprise security benchmarks:
- **NIST SP 800-190:** Application Container Security Guide.
- **CIS Benchmark:** Docker and Container Runtime Isolation.
- **SOC 2 Type II:** Logical separation of tenant execution environments.
- **WCAG 2.2 Level AAA:** Full keyboard and screen-reader accessibility for all management surfaces.
