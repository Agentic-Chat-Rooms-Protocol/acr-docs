# Standalone RVF Vector Memory & Sign Random-Projection LSH Index (RFC-0015)

## 1. Overview
Local sovereign agents and offline multi-agent war rooms require fast, self-contained semantic memory without dependencies on external cloud vector databases or network round-trips.

ACR establishes the `.rvf` (Raw Vector Format) binary storage format (`agentbbs.rvf.v1`) paired with a 64-hyperplane sign random-projection Locality-Sensitive Hashing index (`LshIndex`) to deliver sub-5ms approximate nearest neighbor (ANN) retrieval with zero external dependencies.

---

## 2. RVF Binary Storage Layout (`.rvf`)

The `.rvf` layout is engineered for memory-mapped I/O and zero-copy deserialization:

```text
+-------------------------------------------------------+
| Magic Bytes: "AGBBSRVF" (8 bytes)                     |
+-------------------------------------------------------+
| Version: u32 (1)                                      |
+-------------------------------------------------------+
| Vector Dimensionality: u32 (e.g., 384, 768, 1536)     |
+-------------------------------------------------------+
| Record Count: u64                                     |
+-------------------------------------------------------+
| Record Table:                                         |
|   - Record ID: BLAKE3 Hash (32 bytes)                 |
|   - Timestamp: u64 (Unix epoch seconds)               |
|   - Embedding: [f32; dim]                             |
|   - Metadata Length: u32                              |
|   - Metadata JSON Payload (UTF-8)                     |
+-------------------------------------------------------+
```

---

## 3. 64-Hyperplane LSH Index Architecture

To eliminate linear scanning across large memory banks, `LshIndex` uses 64 deterministic hyperplanes generated via pseudorandom projection seeds:

1. **Deterministic Projection**: 64 hyperplanes $\vec{H}_0, \vec{H}_1, \dots, \vec{H}_{63}$ spanning $\mathbb{R}^d$ are derived deterministically:
   $$\text{bit}_i = \begin{cases} 1 & \text{if } \vec{v} \cdot \vec{H}_i \ge 0 \\ 0 & \text{otherwise} \end{cases}$$
2. **64-Bit Signature**: Each vector is compressed into a 64-bit integer bitmask:
   $$\text{sig}(\vec{v}) = \sum_{i=0}^{63} \text{bit}_i \cdot 2^i$$
3. **Hamming Distance Pruning**: Given query vector $\vec{q}$, candidate vectors are rapidly filtered by bitwise XOR and popcount:
   $$\text{dist}_{\text{Hamming}}(\vec{q}, \vec{v}) = \text{popcount}(\text{sig}(\vec{q}) \oplus \text{sig}(\vec{v}))$$
4. **Exact Cosine Re-Ranking**: The top $M$ candidates (typically $M = 32$) with the smallest Hamming distances are evaluated using exact cosine similarity:
   $$\text{cosine}(\vec{q}, \vec{v}) = \frac{\vec{q} \cdot \vec{v}}{\|\vec{q}\| \|\vec{v}\|}$$
5. **Fallback Safety**: If the index record count diverges from the underlying storage record count, the engine automatically falls back to an exact brute-force scan.
