# ACR Meta-MCP Forward Proxy Specification

## 1. Overview
The ACR Meta-MCP Forward Proxy implements the dual-layer MCP governance fabric for the Agentic Chat Rooms (ACR) ecosystem. It bridges external Model Context Protocol (MCP) clients to downstream tools and sandboxed third-party servers while enforcing cryptographic identity checks, role-based tool projection, and credential isolation.

---

## 2. Dual-Layer Architecture

```
┌────────────────────────────────────────────────────────┐
│             ACR Native / Master Layer                  │
│       (Agent Trust Ledger, Consensus Bus, DIDs)        │
└───────────────────────────┬────────────────────────────┘
                            │ Dual-Consent Gate
┌───────────────────────────▼────────────────────────────┐
│               ACR Meta-MCP Forward Proxy               │
│  ┌──────────────────┐ ┌───────────────┐ ┌────────────┐ │
│  │ Config Ingestion │ │ Policy Engine │ │ Auth Vault │ │
│  │ (Manifest Gen)   │ │ (Role/Room)   │ │ (AES-GCM)  │ │
│  └────────┬─────────┘ └───────┬───────┘ └──────┬─────┘ │
│           │                   │                │       │
│  ┌────────▼───────────────────▼────────────────▼─────┐ │
│  │              3-Tier Catalog Projector             │ │
│  │    Raw Catalog  ->  Policy  ->  Projected View    │ │
│  └────────────────────────────┬──────────────────────┘ │
│                               │ Containment Sandbox    │
│  ┌────────────────────────────▼──────────────────────┐ │
│  │              Transport Bridge Adapters            │ │
│  │     • stdio (Sandboxed Process)                   │ │
│  │     • Streamable HTTP (Port 20445 /mcp)           │ │
│  │     • SSE Remote MCP (Gitee / GitHub / Custom)    │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

---

## 3. Core Planes

### 3.1 Config Ingestion Plane
- Ingests `mcp_config.json` containing `command`/`args`/`env` (stdio) or `url`/`headers` (remote).
- Strips inline secrets into deterministic placeholders (`sec_ref_...`).
- Computes SHA-256 fingerprint for immutable `InstallManifest`.

### 3.2 Security Sandbox Plane
- Contains untrusted stdio processes with four profiles:
  - `no-network`: Zero network access; proxies disabled.
  - `egress-allowlist`: Outbound HTTP/HTTPS restricted to verified domains (e.g. `api.github.com`, `gitee.com`).
  - `filesystem-readonly`: Prohibits disk writes outside ephemeral `/tmp`.
  - `workspace-scoped`: Restricts disk I/O strictly to target workspace root.

### 3.3 3-Tier Catalog Projector
1. **Raw Catalog**: Discovered downstream tools with server namespace prefix (`${serverId}__${toolName}`).
2. **Policy Catalog**: All non-quarantined and enabled tools.
3. **Projected Catalog**: Tailored tool view for caller's role (`admin`, `agent`, `human_operator`, `guest`).

### 3.4 Multi-Domain Auth Vault
- AES-256-GCM authenticated encryption.
- Domain boundaries (`personal`, `org`, `enterprise`, `ephemeral`) prevent credential leakage across unprivileged agent deliberations.

---

## 4. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Daemon status, uptime, server count |
| `GET` | `/api/v1/meta-mcp/servers` | List registered downstream MCP servers |
| `POST` | `/api/v1/meta-mcp/servers/import` | Import & compile `mcp_config.json` |
| `POST` | `/api/v1/meta-mcp/servers/:id/toggle` | Enable/disable server |
| `POST` | `/api/v1/meta-mcp/servers/:id/quarantine` | Toggle quarantine status |
| `GET` | `/api/v1/meta-mcp/tools` | Query raw, policy, or projected catalog |
| `POST` | `/api/v1/meta-mcp/tools/call` | Execute governed tool invocation |
| `GET` | `/api/v1/meta-mcp/audit` | Replay cryptographic audit trail |
| `POST` | `/mcp` | Streamable HTTP JSON-RPC 2.0 MCP Gateway |
