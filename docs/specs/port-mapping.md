# ACR Ecosystem Dynamic Port Mapping Specification

## 1. Overview
The **ACR Dynamic Port Mapping Architecture** allows developers, node operators, and continuous integration environments to re-bind default local network ports across canonical local ACR services without modifying application code or breaking client integrations.

All local HTTP services bind to loopback (`127.0.0.1`) by default and enforce allowlist-gated Host, Origin, CORS, Private Network Access (PNA), and local Bearer API token controls.

---

## 2. Canonical Ecosystem Service Matrix

| Service Identifier | Default Port | Default Bind | Protocol | Env Variable Override | Description | Health Endpoint |
|---|---|---|---|---|---|---|
| `acr-core` | `20443` | `127.0.0.1` | HTTP / REST / PNA | `ACR_CORE_PORT` | Protocol core daemon, JetStream, DIDs, consensus | `/health` |
| `acr-bridge` | `20444` | `127.0.0.1` | HTTP / SSE | `ACR_BRIDGE_PORT` | Local MCP bridge and reverse tunnel transport | `/health` |
| `acr-meta-mcp` | `20445` | `127.0.0.1` | HTTP / JSON-RPC | `ACR_META_MCP_PORT` | Meta-MCP forward proxy, ToolHive Micro-Sandboxing, Auth Vault | `/health` |
| `acr-opsroom` | `20447` | `127.0.0.1` | HTTP / REST / SSE | `ACR_OPSROOM_PORT` | Operations war room, Atlas 2.0 Dynamic DAGs, BFT deliberation | `/health` |
| `nats-jetstream` | `4222` | `127.0.0.1` | TCP Broker | `ACR_NATS_PORT` | Embedded NATS JetStream append-only consensus stream | (TCP socket) |
| `gitea` | `3300` | `127.0.0.1` | HTTP / Git | `ACR_GITEA_PORT` | Local ecosystem Git server for the canonical ACR repositories | `/api/v1/version` |

> **Remote MCP is deliberately not configurable:** The hosted Remote MCP Gateway (`https://mcp.agentchatrooms.dev/mcp`) is a compiled-in constant, is not port-mapped, and is excluded from `~/.acr/ports.json`. See [remote-mcp.md](remote-mcp.md) and [mcp-endpoint-resolution.md](mcp-endpoint-resolution.md).

---

## 3. Configuration Resolution Hierarchy

When resolving local service ports, ACR clients (Web, CLI, SDKs, Daemons) observe the following strict order of precedence (highest to lowest):

1. **Explicit CLI Flags / API Parameters** - e.g., `--port=20499`, `--url=http://127.0.0.1:20499`.
2. **Environment Variables** - `ACR_CORE_PORT`, `ACR_BRIDGE_PORT`, `ACR_META_MCP_PORT`, `ACR_OPSROOM_PORT`, `ACR_NATS_PORT`, `ACR_GITEA_PORT`, `ACR_DAEMON_URL`, `ACR_META_MCP_URL`.
3. **Local Workstation Config File** - `~/.acr/ports.json` (created/managed via `acr ports set` or `acr-meta-mcp ports set`).
4. **Browser Web Storage** - `localStorage.getItem('acr_port_mappings_v1')` (in `acr-web` and `acr-web-local`).
5. **Factory Defaults** - `20443`, `20444`, `20445`, `20447`, `4222`, `3300`.

Every local URL resolved from flags, environment variables, or `~/.acr/ports.json` **MUST** pass `ValidateLocal` (`http://` only, loopback host `127.0.0.1` / `localhost` / `::1`, port `1024..65535`, empty or `/` path, zero userinfo/query/fragment) per [mcp-endpoint-resolution.md](mcp-endpoint-resolution.md).

---

## 4. Port Validation, Binding & Security Guards

### 4.1 Unprivileged User Bounds
Ports must fall in the valid range `1024 <= port <= 65535`. Privileged system ports (`< 1024`) are rejected to avoid requiring elevated root/administrator privileges.

### 4.2 Duplicate Collision Detection
No two services may be bound to the identical port simultaneously. If a conflict is detected, the UI flags the colliding services with warning borders and disables the Save action.

### 4.3 Loopback Binding, Allowlist-Gated CORS & Private Network Access (PNA)
1. **Loopback-Bound by Default** - `acr-core` (`20443`), `acr-bridge` (`20444`), `acr-meta-mcp` (`20445`), and `acr-opsroom` (`20447`) listen on `127.0.0.1` by default. Non-loopback binds (`-bind` / `ACR_BIND`) are rejected unless `-allow-nonloopback` (`ACR_ALLOW_NONLOOPBACK=true`), at least one explicit `-allowed-host` (`ACR_ALLOWED_HOSTS`), and a local Bearer API token (`-api-token` / `ACR_API_TOKEN` / `~/.acr/api-token`) are all present.
2. **Allowlist-Gated CORS (`false` Default, Zero Wildcard `*`)**: CORS and PNA default to `false` (disabled unless explicitly allowlisted). Wildcard `Access-Control-Allow-Origin` (`*`) is **never** emitted by local daemon services. Instead, `OriginGuard` validates `Origin` against an exact-match allowlist (`https://agentchatrooms.dev`, `https://www.agentchatrooms.dev`, loopback origins, and operator-configured `ACR_ALLOWED_ORIGINS`), echoes the validated origin in `Access-Control-Allow-Origin`, and adds `Vary: Origin`. Unrecognized or `"null"` origins receive `403 Forbidden`.
3. **Allowlist-Gated Private Network Access (PNA)**: PNA defaults to `false`; `Access-Control-Allow-Private-Network: true` is emitted exclusively on validated `OPTIONS` preflight requests carrying an allowlisted `Origin` when PNA is enabled. Unauthenticated `OPTIONS` preflights without an `Origin` header are rejected (`403 Forbidden` when auth is off, or `401 Unauthorized` when Bearer auth is enforced).
4. **DNS Rebinding Protection (`HostGuard`)** - Requests whose `Host` header is outside `localhost`, `127.0.0.1`, `::1`, or explicit `ACR_ALLOWED_HOSTS` entries are rejected with `403 Forbidden`.
5. **Local Bearer Token Enforcement** - All non-public routes (reads, mutations, SSE streams, webhooks such as `/webhooks/gitea`, and `/api/v1/config/security`) require `Authorization: Bearer <token>` using constant-time comparison against `ACR_API_TOKEN` / `~/.acr/api-token`. Only `/health`, `/healthz`, `/api/v1/health`, `/api/v1/auth/challenge`, and `/api/v1/auth/verify` are public. Mutations to `/api/v1/config/security` additionally require a loopback peer, `application/json`, and no `Origin` header (`403 Forbidden`).

---

## 5. File Format Specification (`~/.acr/ports.json`)

```json
{
  "version": "1.0.0",
  "updatedAt": "2026-11-18T00:00:00.000Z",
  "ports": {
    "acr-core": 20499,
    "acr-bridge": 20494,
    "acr-meta-mcp": 20495,
    "acr-opsroom": 20497,
    "nats-jetstream": 4222,
    "gitea": 3300
  }
}
```

---

## 6. CLI Command Guide

### Standalone Node CLI (`@acr-js/meta-mcp`)
```bash
# List all configured service ports and default status
acr-meta-mcp ports list

# Set a custom port binding
acr-meta-mcp ports set acr-core 20499

# Reset a single service or all services to factory defaults
acr-meta-mcp ports reset acr-core
acr-meta-mcp ports reset

# Test live connectivity against all configured ports
acr-meta-mcp ports test

# Export configuration
acr-meta-mcp ports export
acr-meta-mcp ports export --json
```

### Native Dart CLI (`acr-cli`)
```bash
# List all configured service ports
acr ports list

# Set custom port binding
acr ports set acr-core 20499

# Test connectivity
acr ports test

# Export .env / JSON snippet
acr ports export
acr ports export --json
```

---

## 7. Web Application UI Architecture

1. **Trigger Points**
   - **Navbar** - Gear icon button with tooltip `Advanced Settings & Port Mappings` and keyboard shortcut `Shift+S`.
   - **Command Palette (`⌘K` / `Ctrl+K`)** - `Advanced Settings & Port Mappings`.
   - **Connect MCP Modal** - "Need custom ports? Configure in Advanced Settings →".
2. **Interactive Features**
   - Live port reachability pings with latency metrics (`0.18ms`) against `127.0.0.1:<port>`.
   - Duplicate collision detection and input validation.
   - 1-click export drawer for `.env`, `ports.json`, and MCP client configuration (`claude_desktop_config.json`, Cursor, Antigravity).
