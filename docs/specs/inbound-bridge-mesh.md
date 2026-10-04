# Enterprise Inbound Re-Signing Bridge Mesh Specification

## 1. Overview
The ACR Inbound Bridge Mesh (`acr-bridge`) establishes bi-directional bridges between enterprise communication platforms (Slack, Microsoft Teams, WhatsApp) and ACR agent deliberation rooms.

To preserve zero-trust integrity, external webhooks are verified natively, re-signed into Ed25519 envelopes, deduplicated against a replay cache, and delivered to ACR rooms with cryptographic non-repudiation.

---

## 2. Inbound Platform Adapters

### 2.1 Slack Adapter (`/api/bridge/slack/events`)
- **Signature Verification**: Verifies `X-Slack-Signature` using HMAC-SHA256 and the shared signing secret.
- **Timestamp Freshness**: Rejects requests where `X-Slack-Request-Timestamp` deviates by more than 300 seconds from the local clock.
- **Replay Protection**: Stores message hashes in an in-memory `SeenSet` sliding window cache.

### 2.2 Microsoft Teams Bot Framework Adapter (`/api/bridge/teams/messages`)
- **Dynamic OpenID JWKS**: Fetches Microsoft's OpenID configuration and public JWKS (`https://login.botframework.com/v1/.well-known/keys`).
- **In-Memory Cache & TTL**: Caches public keys with dynamic TTL to prevent network overhead while supporting automated key rotation.
- **Key ID (`kid`) Resolution**: Matches the incoming JWT `kid` header to the active JWKS keys, verifying RS256 signatures.
- **Claims Verification**: Validates `iss` (`https://api.botframework.com`), `aud` (configured App ID), and expiration timestamps.

### 2.3 WhatsApp Business Cloud API (`/api/bridge/whatsapp/webhook`)
- **Hub Signature**: Validates `X-Hub-Signature-256` using HMAC-SHA256.
- **Payload Normalization**: Maps incoming WhatsApp cloud message payloads to canonical ACR event envelopes.

---

## 3. Re-Signing & Loop Guard

When an inbound message is verified:
1. **Ed25519 Envelope Re-Signing**: The bridge re-signs the normalized message using a deterministic 32-byte Ed25519 seed configured for that platform bridge.
2. **Author Identity**: Authors are mapped to deterministic synthetic identities:
   $$\text{DID} = \text{did:key:z6Mk...[derived from bridge key]}$$
   with metadata `bridge:<platform>:<external_id>`.
3. **Loop Guard**: All bridge-forwarded messages carry a `X-ACR-Bridge-Origin` header. Outbound forwarders ignore messages originating from the bridge to prevent infinite echo loops.
