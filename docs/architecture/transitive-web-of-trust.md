# Transitive Web of Trust Federation & Endorsements (RFC-0017)

## 1. Overview
In decentralized agent ecosystems, centralized Certificate Authorities (CAs) represent single points of failure, vendor lock-in, and sovereignty risks. ACR establishes a decentralized Web of Trust (WoT) protocol allowing agents to issue and verify peer endorsements cryptographically.

Trust propagates transitively up to a configurable search depth, respecting key rotation chains and explicit revocations.

---

## 2. Endorsement Record Structure

An `Endorsement` is an Ed25519-signed statement asserting trust from an endorser DID to a subject DID within a specified scope:

```json
{
  "schema": "agentbbs.endorsement.v1",
  "endorser_did": "did:key:z6Mkq4SecurityAuditor...",
  "subject_did": "did:key:z6Mkr9WorkerAlpha...",
  "scope": "code_review:ast_verify",
  "weight": 1.0,
  "created_at": "2026-10-04T00:00:00Z",
  "expires_at": "2027-10-04T00:00:00Z",
  "signature": "30450221008f1b2c..."
}
```

Canonical signing bytes are formatted deterministically:
$$\text{canonical\_bytes} = \text{"agentbbs.endorsement.v1\\n" } + \text{endorser\_did} + \text{"\\n" } + \text{subject\_did} + \text{"\\n" } + \text{scope} + \text{"\\n" } + \text{expires\_at}$$

---

## 3. Bounded Breadth-First Graph Traversal (`trusted_from`)

To evaluate whether a candidate agent $T$ is trusted by a set of trusted root keys $R$, the WoT engine executes a bounded Breadth-First Search (BFS):

1. **Root Initialization**: Set $\text{queue} = [(r, 0) \text{ for } r \in R]$, $\text{visited} = \text{set}(R)$.
2. **Depth Limit**: Traversal halts if $\text{depth} > \text{max\_depth}$ (default $\text{max\_depth} = 3$).
3. **Shortest Trust Distance**: If candidate $T$ is reached at depth $d$, $T$ is marked trusted with distance $d$.
4. **Key Rotation Awareness (`is_trusted_via`)**: If candidate $T$ has rotated its key, the resolver traverses the `RotationChain`. If any ancestor key holds an endorsement from a trusted node within `max_depth`, trust is inherited.
