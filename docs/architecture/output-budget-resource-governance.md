# High-Density Pod Governance & Output Budget Guards

## 1. Overview
In multi-tenant agent execution environments, runaway streaming outputs and idle session loops can exhaust node memory and CPU cycles.

ACR implements a suite of resource guards designed to guarantee high session density, sub-second response times, and memory bounds:
1. **OutputBudget Memory Guards**: Hard 32 MB per-session buffer ceiling with stall disconnects.
2. **Adaptive Dirty Gate Rendering**: Differential rendering engine relaxing wake frequency during idle states.
3. **Graceful Session Draining**: Long-lived sessions drain gracefully up to 6 hours (`termination_grace_period_seconds: 21600`) during rolling deployments.
4. **Fuel-Metered WASM Executor**: WebAssembly sandbox execution bounded by instruction fuel meters.

---

## 2. OutputBudget Memory Backpressure Guard

Streaming terminal and message sessions enforce strict memory bounds:
- **Ceiling**: A maximum unconsumed output buffer of 32 MB per active session.
- **Backpressure Pause**: If buffer consumption stalls and unconsumed bytes exceed the ceiling, the emitter pauses event dispatch immediately.
- **Stall Disconnect**: If the client fails to drain the buffer within 30 seconds of stall detection, the socket connection is terminated to protect node memory.

---

## 3. Adaptive Dirty Gate TUI Rendering

To minimize CPU utilization during idle periods, the rendering loop evaluates a dirty state flag:
- **Active State**: 66ms wake cycle (approximately 15 FPS) while terminal output or deliberations change.
- **Dirty Check**: If no screen cells or buffer items were mutated, the render pass is skipped entirely (~20% clean skip ratio).
- **Idle Relaxation**: When successive frames remain clean, the wake interval gradually relaxes from 66ms down to a 500ms sleep floor.
