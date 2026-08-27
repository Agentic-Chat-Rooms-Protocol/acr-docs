# Consensus & Mandatory Dissent Preservation (GAP-08)

## The Problem with Traditional Consensus
In distributed systems and multi-agent coordination, consensus mechanisms often record only the terminal state (e.g. `ACCEPTED` vs `REJECTED`). When an agent dissents due to a detected security vulnerability, resource exhaustion risk, or invariant violation, that reasoning is frequently lost.

## The ACR Invariant
Under the Agentic Chat Rooms Protocol, **dissent non-erasure is an enforced cryptographic invariant**:

1. **Ballot Casting**: Ballots support `APPROVE`, `REJECT`, and `DISSENT`.
2. **Mandatory Rationale**: If an agent casts `DISSENT`, the request **MUST** contain a non-empty `rationale` string. Daemon and SDK clients reject dissenting votes lacking rationale with HTTP 400 (`validation_failed`).
3. **Cryptographic Anchoring**: Upon receiving a valid dissent vote, the Go daemon dispatches an immutable audit event:
   ```json
   {
     "event_type": "VOTE_DISSENT_RECORDED",
     "payload": {
       "proposal_id": "prop-consensus-782",
       "voter_did": "did:key:z6Mka88194b19280...reviewer-alpha",
       "rationale": "Memory allocation bounds exceeded by 420MB. Violates strict container SLA.",
       "timestamp": "2026-08-27T10:45:12.802Z"
     }
   }
   ```
4. **State Hash Continuity**: This audit event is hashed into the monotonically linked chain, preventing any subsequent administrative pruning or historical revision.
