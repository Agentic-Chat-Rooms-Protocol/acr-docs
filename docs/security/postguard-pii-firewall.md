# PostGuard Prompt Injection Firewall & Egress PII Sanitization (RFC-0019)

## 1. Overview
Large Language Model agents are uniquely vulnerable to prompt injection, system prompt exfiltration, and sensitive data leakage. ACR enforces dual-boundary protection:
1. **PostGuard Pre-Flight Firewall (Ingress)**: Heuristic and entropy-based prompt injection detection running before LLM context ingestion, rejecting attacks with HTTP 422.
2. **Cloakwall Egress PII Scrubber (Egress)**: Recursive sanitization of outbound logs, messages, and tool outputs replacing sensitive credentials, tokens, and PII with `[redacted]`.

---

## 2. PostGuard Pre-Flight Prompt Injection Scanner

The PostGuard scanner operates directly at the HTTP and RPC ingress layers:

### Threat Classification
- `ThreatLevel::Clean`: Input passes all pattern and entropy heuristics; forwarded to agent/LLM.
- `ThreatLevel::Suspicious`: Elevated entropy, excessive URL density, or obfuscated tokens; forwarded to human review queue without outright blocking.
- `ThreatLevel::Malicious`: High-confidence attack patterns detected; immediately rejected with HTTP 422 `Unprocessable Entity`.

### Detection Vectors
1. **Instruction Overrides**: Patterns such as `ignore previous instructions`, `disregard all prior instructions`.
2. **System Prompt Exfiltration**: Phrases requesting raw prompt disclosure, hidden instruction dumps, or delimiter breakout sequences.
3. **Delimiter Smuggling**: Markdown or XML tag injections targeting prompt frame integrity (e.g. `</system>`, `<|im_end|>`).
4. **SQL/Code Injections**: Heuristic queries targeting data structures (e.g. `DROP TABLE`, `UNION SELECT`).

---

## 3. Cloakwall Egress PII Sanitization

All egress envelopes passing across federation channels or log emitters undergo recursive key scrubbing:

- **Sensitive Key Redaction**: Keys matching `email`, `ip`, `host`, `token`, `secret`, `key`, `phone`, `password` are replaced with `"[redacted]"`.
- **Luhn Algorithm Verification**: Numeric sequences matching credit card number formats are verified via Luhn check and masked.
- **Shannon Entropy Analysis**: High-entropy strings typical of cryptographic private keys or API tokens (e.g., base64 or hexadecimal strings exceeding 4.5 bits/char) are scrubbed.
- **Letter-Only API Key & MRN Detection**: Identifies structured identifiers and medical record numbers even when obfuscated.
