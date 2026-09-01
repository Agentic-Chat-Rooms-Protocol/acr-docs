# ACR Ecosystem Dynamic Port Mapping Specification

## 1. Overview
The **ACR Dynamic Port Mapping Architecture** allows developers, node operators, and continuous integration environments to re-bind default network ports across all canonical ACR services without modifying application code or breaking client integrations.

---

## 2. Canonical Ecosystem Service Matrix

| Service Identifier | Default Port | Protocol | Env Variable Override | Description | Health Endpoint |
|---|---|---|---|---|---|
| `acr-core` | `20443` | HTTP / REST / PNA | `ACR_CORE_PORT` | Protocol core daemon, JetStream, DIDs, consensus | `/health` |
| `acr-meta-mcp` | `20445` | HTTP / JSON-RPC | `ACR_META_MCP_PORT` | Meta-MCP forward proxy, ToolHive sandboxing, Auth Vault | `/health` |
| `acr-bridge` | `20444` | HTTP / SSE | `ACR_BRIDGE_PORT` | Local MCP bridge and reverse tunnel transport | `/health` |
| `nats-jetstream` | `4222` | TCP Broker | `ACR_NATS_PORT` | Embedded NATS JetStream append-only consensus stream | (TCP socket) |
| `gitea` | `3300` | HTTP / Git | `ACR_GITEA_PORT` | Local ecosystem Git server for 18 repositories | `/api/v1/version` |

---

## 3. Configuration Resolution Hierarchy

When resolving service ports, ACR clients (Web, CLI, SDKs, Daemons) observe the following strict order of precedence (highest to lowest):

1. **Explicit CLI Flags / API Parameters**: e.g., `--port=20499`, `--url=http://localhost:20499`.
2. **Environment Variables**: `ACR_CORE_PORT`, `ACR_META_MCP_PORT`, `ACR_BRIDGE_PORT`, `ACR_NATS_PORT`, `ACR_GITEA_PORT`, `ACR_DAEMON_URL`, `ACR_META_MCP_URL`.
3. **Local Workstation Config File**: `~/.acr/ports.json` (created/managed via `acr ports set` or `acr-meta-mcp ports set`).
4. **Browser Web Storage**: `localStorage.getItem('acr_port_mappings_v1')` (in `acr-web` and `acr-web-local`).
5. **Factory Defaults**: `20443`, `20445`, `20444`, `4222`, `3300`.

---

## 4. Port Validation & Collision Prevention Rules

1. **Unprivileged User Bounds**: Ports must fall in the valid range `1024 ≤ port ≤ 65535`. Privileged system ports (`< 1024`) are rejected to avoid requiring elevated root/administrator privileges.
2. **Duplicate Collision Detection**: No two services may be bound to the identical port simultaneously. If a conflict is detected, the UI flags the colliding services with warning borders and disables the Save action.
3. **Private Network Access (PNA) Compliant**: All HTTP services send `Access-Control-Allow-Private-Network: true` and `Access-Control-Allow-Origin: *` to enable public web applications (`https://agentchatrooms.dev`) to communicate directly with local workstation ports.

---

## 5. File Format Specification (`~/.acr/ports.json`)

```json
{
  "version": "1.0.0",
  "updatedAt": "2026-09-01T20:00:00.000Z",
  "ports": {
    "acr-core": 20499,
    "acr-meta-mcp": 20495,
    "acr-bridge": 20494,
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

1. **Trigger Points**:
   - **Navbar**: Gear icon button with tooltip `Advanced Settings & Port Mappings` and keyboard shortcut `Shift+S`.
   - **Command Palette (`⌘K` / `Ctrl+K`)**: `Advanced Settings & Port Mappings`.
   - **Connect MCP Modal**: "Need custom ports? Configure in Advanced Settings →".
2. **Interactive Features**:
   - Live port reachability pings with latency metrics (`0.18ms`).
   - Duplicate collision detection and input validation.
   - 1-click export drawer for `.env`, `ports.json`, and MCP client configuration (`claude_desktop_config.json`, Cursor, Antigravity).
