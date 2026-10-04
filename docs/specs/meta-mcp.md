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
│  │ (Manifest Gen)   │ │ (Role/Room)   │ │ (Multiple  │ │
│  │                  │ │               │ │  Ciphers)  │ │
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

### 3.4 Multi-Domain Auth Vault (SQLite3MultipleCiphers Engine)
- Isolated encrypted database file (`vault.db`) with `ACR_MCDB_V1` authenticated header.
- **Supported Ciphers**:
  - `aes-256-gcm`: NIST SP 800-38D AEAD.
  - `chacha20-poly1305`: RFC 8439 AEAD.
  - `sqlcipher-v4`: 256-bit AES-CBC with HMAC-SHA512 record integrity.
- **Key Derivation**: PBKDF2-HMAC-SHA512 (256,000 iterations default) with per-database random salts.
- **Domain Boundaries**: `personal`, `org`, `enterprise`, `ephemeral` prevent credential leakage across unprivileged agent deliberations.
- **Master Key Rotation**: Re-encrypts all database records atomically on demand.

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
| `GET` | `/api/v1/meta-mcp/vault/secrets` | List vaulted secret refs with domain & cipher info |
| `POST` | `/api/v1/meta-mcp/vault/secrets` | Ingest secret into encrypted database |
| `DELETE` | `/api/v1/meta-mcp/vault/secrets/:refId` | Purge secret from database |
| `POST` | `/api/v1/meta-mcp/vault/rotate` | Rotate master passphrase & re-encrypt DB |
| `GET` | `/api/v1/meta-mcp/audit` | Replay cryptographic audit trail |
| `POST` | `/mcp` | Streamable HTTP JSON-RPC 2.0 MCP Gateway |

---

## 5. Ideal Installation Path & Ecosystem Integration

### 5.1 Canonical Deployment Architecture
- **Repository Location**: `http://localhost:3300/ACR/acr-meta-mcp.git`
- **NPM Package**: `@acr-js/meta-mcp`
- **Default Workstation Port**: `20445` (REST: `http://localhost:20445/api/v1/meta-mcp/`, MCP Gateway: `http://localhost:20445/mcp`)
- **Companion Service**: Runs alongside `acr-core` (`http://localhost:20443`) as the dedicated MCP forward proxy and governance control plane.

### 5.2 Real-World MCP Server Integration (Context7 Example)
Context7 provides automated real-time library documentation lookups (`resolve-library-id`, `query-docs`).

**`mcp_config.json` configuration:**
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp", "--api-key", "${CONTEXT7_API_KEY}"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      }
    }
  }
}
```

When imported via `acr meta-mcp import` or the Web Governance Studio:
1. `CONTEXT7_API_KEY` is redacted and vaulted into the MultipleCiphers Auth Vault (`sec_ref_...`).
2. Server is launched within `workspace-scoped` containment profile.
3. Tools are namespaced as `context7__resolve-library-id` and `context7__query-docs`.
4. Governed tool calls are audited with sub-millisecond replay latency.

---

## 6. CLI Management Commands

### Standalone Node CLI
```bash
acr-meta-mcp health
acr-meta-mcp list
acr-meta-mcp import <path/to/mcp_config.json>
acr-meta-mcp enable <serverId>
acr-meta-mcp disable <serverId>
acr-meta-mcp tools [raw|policy|projected]
acr-meta-mcp call <tool_name> [json_args]
acr-meta-mcp vault [list|set|delete|rotate]
acr-meta-mcp audit
```

### Native Dart CLI (`acr-cli`)
```bash
acr meta-mcp list
acr meta-mcp import ./mcp_config.json
acr meta-mcp enable gitee-cloud
acr meta-mcp tools --view=projected
acr meta-mcp call context7__query-docs '{"libraryId":"/vercel/next.js","query":"Server Actions"}'
acr meta-mcp vault list
acr meta-mcp vault set --server=github --key=GITHUB_TOKEN --value="ghp_..." --domain=org
acr meta-mcp audit
```

---

## 7. Deep-Moat Guard Enhancements (PayloadGuard & Wilson Ranking)

### 7.1 PayloadGuard Pre-Flight Inspection
The proxy integrates `PayloadGuard` into the tool execution pipeline:
- Inbound tool arguments are scanned for instruction override and exfiltration patterns before child process dispatch.
- Malicious invocations fail closed with HTTP 422 `Unprocessable Entity` and are recorded in the security audit stream.

### 7.2 Cloakwall Egress PII Sanitization
Responses returned from downstream MCP tools are parsed through recursive sanitization:
- High-entropy tokens, private keys, and sensitive parameters are replaced with `[redacted]`.
- Numeric sequences matching credit cards or medical record numbers are validated and masked.

### 7.3 Wilson 95% Confidence Catalog Ranking
Extensions registered in the catalog and marketplace are ranked using Wilson 95% confidence intervals:
- Eliminates low-sample rank distortion from newly submitted tools.
- Verified tool execution telemetry establishes transparent reliability scores.

