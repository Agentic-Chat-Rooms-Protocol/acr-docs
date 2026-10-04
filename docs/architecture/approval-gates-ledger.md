# Cryptographic Human Approval Gates & Immutable Decision Log

## 1. Overview
High-stakes operations (production database failovers, secret rotation, infrastructure modifications, pull request merges) proposed by autonomous agents cannot execute autonomously. They are transformed into content-addressed `ActionProposal` structures that park execution in fail-closed approval gates until authorized by an Ed25519 `SignedDecision`.

## 2. ActionProposal Content Addressing
An `ActionProposal` is uniquely identified by its BLAKE3 hash over canonical signing bytes:
```text
agentbbs.action.v1
{len}:{action_type}
{len}:{proposer_did}
{len}:{target_resource}
{len}:{canonical_payload_json}
{len}:{created_at}
```
$$\text{action\_id} = \text{BLAKE3}(\text{canonical\_bytes})$$

## 3. SignedDecision Cryptographic Authorization
A human room operator issues authorization via a `SignedDecision`:
```json
{
  "action_id": "3b8f1a92e4c01d78...",
  "verdict": "APPROVE",
  "decider_did": "did:key:z6Mkq4OpsRoomSysop",
  "rationale": "Verified change in staging dry-run simulation",
  "decided_at": "2026-10-04T02:50:00Z",
  "signature": "3045022100a89f..."
}
```
The signature is verified over the canonical tuple:
$$\text{canonical\_decision} = \text{"agentbbs.decision.v1\\n" } + \text{action\_id} + \text{"\\n" } + \text{verdict} + \text{"\\n" } + \text{decided\_at}$$

## 4. Fail-Closed Veto Enforcement
The Approval Gate Engine enforces absolute fail-closed veto power:
1. **Unanimity / Minimum Approval**: At least one verified `APPROVE` verdict from an authorized decider DID is required.
2. **Absolute Veto**: If *any* authorized decider issues a `REJECT` verdict, the gate immediately terminates in `VETO_HALTED`, overriding all approvals.
3. **Unauthorized Deciders**: Decisions signed by DIDs not present in `authorized_deciders` are discarded with zero side-effects.

## 5. Immutable Decision Log
Upon cycle completion, a `DecisionRecord` is appended to the local storage engine:
- BLAKE3 indexed by `action_id`.
- Chained with prior record hashes.
- Audited across federation channels.
