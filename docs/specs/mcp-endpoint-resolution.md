# MCP Endpoint Resolution & Daemon Routing Specification

## 1. Purpose & Architectural Boundary

This specification defines how ACR clients (`acr-core/pkg/mcpendpoint`, `acr-mcp-server`, `acr-cli`, `acr-bridge`, and the `@acr-js/sdk` / Python SDKs) choose between the **local** MCP stack and the hosted **remote** gateway (`https://mcp.agentchatrooms.dev/mcp`).

### Design Invariants
1. **The daemon stays local-only and subscription-agnostic.** `acr-core` never holds Cloud OAuth tokens, never tracks billing tiers, and never proxies requests to the remote gateway.
2. **Entitlement enforcement is server-side.** The hosted Remote MCP gateway resolves paid Cloud Pro / Enterprise entitlement via the verified Clerk `sub` on every request (`401 invalid_token`, `403 subscription_required`). Client-side routing is a UX selector, not an authorization boundary.
3. **Remote URL is a compiled-in constant.** Mode (`local` | `remote`) may be selected; the remote URL (`https://mcp.agentchatrooms.dev/mcp`) is **never** configurable via flags, environment variables, `~/.acr/ports.json`, or daemon responses.
4. **Default to local.** Absent credentials, free-tier accounts, or unverified entitlements resolve to `local`.
5. **Never cross tiers silently.** Local rooms (`chat.*` / local daemon) and Cloud rooms (`acr_*` / Remote MCP) are separate stores. Failures on `remote` return an explicit error naming the active endpoint and never silently fall back to `local`.
6. **Two credentials, never interchangeable.** The local API token (`~/.acr/api-token` or `ACR_API_TOKEN`) never leaves the workstation; a Clerk OAuth token (audience `https://mcp.agentchatrooms.dev/mcp`, scopes `["profile", "email"]`) is never sent to `127.0.0.1`.

Machine-readable test vectors live in [`fixtures/endpoint-vectors.json`](fixtures/endpoint-vectors.json). Go, Dart, and TypeScript implementations **MUST** validate against the same vectors.

---

## 2. Endpoint Validation Rules

### 2.1 `ValidateLocal(raw)`
Local daemon URLs come from CLI flags, `ACR_DAEMON_URL`, `~/.acr/ports.json`, or the default `http://127.0.0.1:20443` (per [port-mapping.md](port-mapping.md)). Even when `remote` mode is selected, the configured local URL **MUST** be validated so latent invalid config fails fast.

| Field | Accepted | Rejected |
|---|---|---|
| Scheme | `http` only | `https`, `ws`, `file`, empty |
| Host | Exact literals `127.0.0.1`, `::1`, or `localhost` (normalized/pinned to `127.0.0.1`; never DNS-resolved) | `0.0.0.0`, LAN IPs, `localhost.evil.com`, `127.0.0.1.evil.com`, `127.1`, `2130706433`, `0x7f.0.0.1`, `[::ffff:127.0.0.1]` |
| Port | `1024..65535` (default `20443` when omitted) | `< 1024`, `> 65535`, non-numeric |
| Path | Empty or `/` | Any non-root path (`/mcp`, `/api`) |
| Userinfo / Query / Fragment | Empty | Any `user:pw@`, `?query`, `#fragment` |

Canonical output format: `http://127.0.0.1:<port>` (or `http://[::1]:<port>` for IPv6 loopback).

### 2.2 `ValidateRemote(raw)`
The pinned constant is `RemoteURL = "https://mcp.agentchatrooms.dev/mcp"`.

| Field | Accepted | Rejected |
|---|---|---|
| Scheme | `https` only | `http`, `ws`, empty |
| Host | `mcp.agentchatrooms.dev` (case-insensitive, no trailing dot) | `mcp.agentchatrooms.dev.`, `mcp.agentchatrooms.dev.evil.com`, `mcp.agentchatrooms.dev@evil.com` |
| Port | Empty or `443` | `:8443`, `:3000`, any non-443 port |
| Path | Exact escaped path `/mcp` | `/mcp/`, `/%6dcp`, `/`, `/api/mcp` |
| Userinfo / Query / Fragment | Empty | Any `user:pw@`, `?next=//evil.com`, `#frag`, `//host/mcp` |

---

## 3. Mode Resolution Algorithm

Inputs:
- `override`: `""` (auto), `"local"`, or `"remote"` (from `--mode` or `ACR_MCP_MODE`)
- `entitlement`: `"none"` | `"free"` | `"pro"` | `"enterprise"` (observed via authenticated host OAuth + gateway status; never decoded client-side from opaque/private token internals)
- `localURL`: Candidate local daemon URL (default `http://127.0.0.1:20443`)

```text
resolve(override, entitlement, localURL):
  local := ValidateLocal(localURL)          # always validate first
  if override == "local":
    return { mode: "local", url: local, reason: "explicit override" }
  if override == "remote":
    return { mode: "remote", url: REMOTE_URL, reason: "explicit override" }
  if override != "":
    return error("override must be local or remote")
  if entitlement in {"pro", "enterprise"}:
    return { mode: "remote", url: REMOTE_URL, reason: "active cloud entitlement" }
  return { mode: "local", url: local, reason: "no paid cloud entitlement; default" }
```

Note on Clerk OAuth discovery: Hosted OAuth 2.1 metadata at `https://mcp.agentchatrooms.dev/.well-known/oauth-protected-resource/mcp` advertises `scopes_supported: ["profile", "email"]` against issuer `https://clerk.agentchatrooms.dev`. Clients **MUST NOT** request `acr:rooms` or `acr:cloud:pro`. Entitlement is resolved server-side from Clerk `sub`.

---

## 4. HTTP Transport & Redirect Hardening

1. **Redirects Never Followed (`noRedirect`)**: Both `NewHTTPClient()` (10 s `RESTTimeout`) and `NewStreamClient()` (unbounded stream with 10 s `ResponseHeaderTimeout`) **MUST** configure `CheckRedirect` to return a non-nil error (`errRedirect`) on any `3xx` status. Never use `http.ErrUseLastResponse`, which hands a `3xx` back as a non-error response to callers checking `status >= 400`.
2. **Strict TLS**: Invalid, expired, or self-signed certificates on `remote` fail closed with zero insecure override flags.
3. **Failure & Retry Semantics**:
   - `401 invalid_token`: Attempt at most one OAuth refresh via the host/auth server; if refresh fails, stay on `remote` and prompt re-authentication (never silently reroute to `local`).
   - `403 subscription_required`: Stop, do not resend the token, negative-cache for ~60 seconds, and display an explicit Cloud Pro / Enterprise plan message.
   - **Reads** (`acr_list_workflows`, `acr_get_workflow`, `acr_get_workflow_status`, `acr_list_rooms`, `acr_room_status`, `acr_room_ledger_tail`, `acr_container_status`, `initialize`, `tools/list`): Exponential backoff with jitter, at most 3 attempts on `5xx` or network timeouts.
   - **Mutations** (`acr_create_room`, `acr_configure_workflow`, `acr_room_send`, `acr_room_consensus`, and local `chat.*` writes): **Zero automatic retries** after the request has been dispatched on timeout or `5xx`. Surface `OUTCOME_UNKNOWN` naming the active endpoint so the caller can reconcile via a read (e.g., `acr_room_ledger_tail` or `acr_room_status`). Pre-dispatch failures (connection refused, DNS/TLS handshake failure) may fail cleanly before commit.

---

## 5. Local Daemon Hardening Contract (`acr-core`)

`acr-core` (`127.0.0.1:20443`) enforces the middleware chain `HostGuard -> OriginGuard -> RequireToken -> handlers`:

1. **Loopback Bind Default**: `-bind` / `ACR_BIND` defaults to `127.0.0.1`. Non-loopback binds refuse to start unless `-allow-nonloopback` (`ACR_ALLOW_NONLOOPBACK=true`), explicit `-allowed-host` (`ACR_ALLOWED_HOSTS`), and a local API token (`-api-token` / `ACR_API_TOKEN` / `~/.acr/api-token`) are all set.
2. **`HostGuard`**: Permits `localhost`, `127.0.0.1`, `::1`, plus explicit `ACR_ALLOWED_HOSTS` entries only (never wildcards). Other hosts receive `403 Forbidden`.
3. **`OriginGuard`**: CORS and PNA default to `false` (disabled unless allowlisted). Exact-match allowlist (`https://agentchatrooms.dev`, `https://www.agentchatrooms.dev`, loopback origins, and `ACR_ALLOWED_ORIGINS`). Never emits wildcard `Access-Control-Allow-Origin` (`*`). Non-allowlisted or `"null"` origins receive `403 Forbidden`. `OPTIONS` preflights from allowlisted origins receive `204 No Content` with `Access-Control-Allow-Origin: <origin>` (when CORS is enabled), `Vary: Origin`, and `Access-Control-Allow-Private-Network: true` (when PNA is enabled) before token enforcement; unauthenticated `OPTIONS` without `Origin` is rejected (`403 Forbidden` / `401 Unauthorized`).
4. **`RequireToken`**: Constant-time `Authorization: Bearer <token>` check (`subtle.ConstantTimeCompare`) on every route—including reads, SSE streams, webhooks (`/webhooks/gitea`), and `/api/v1/config/security`—except public routes (`/health`, `/healthz`, `/api/v1/health`, `/api/v1/auth/challenge`, `/api/v1/auth/verify`). Mutations to `/api/v1/config/security` also reject any non-empty `Origin` header (`403 Forbidden`) and non-loopback peer (`403 Forbidden`).
