# Domain Agent Pods & Meta-LLM Darwin Loops

## 1. Overview
Multi-agent swarms frequently incur excessive token spend by defaulting every task to expensive frontier models, or fail tasks by remaining locked on lightweight models.

ACR implements Domain Agent Pods (`PodTemplate`) with behavioral assertion gates (`bench_assertions`), programmatic spend caps (`per_agent_cap_usd`), and an autonomous tier escalation state machine termed the **Darwin Loop**.

---

## 2. PodTemplate Specification Format

Pods are configured per domain (`research`, `coding`, `security`, `trading`):

```yaml
schema: agentbbs.pod.v1
id: pod-coding-worker-01
domain: coding
initial_tier: low
max_tier: high
per_agent_cap_usd: 5.00
bench_assertions:
  - id: ast_valid
    type: lint_check
    must_pass: true
  - id: unit_test_pass
    type: test_runner
    min_coverage_pct: 90
```

---

## 3. Darwin Loop State Machine

The Darwin Loop starts at the cheapest model tier by default and escalates only when behavioral assertions fail:

```text
[Spawned] (Initial Tier: Low, e.g. $0.002/run)
    |
    v
[Executing]
    |
    v
[Evaluating] ----> (All bench_assertions pass) ----> [Completed]
    |
    +------------> (bench_assertions fail && current_tier < max_tier)
                        |
                        v
                   [Escalating] (Bump Tier: Low -> Mid $0.015 -> High $0.080)
                        |
                        +---> Re-enters [Executing]
```

### Spend Governance
1. **Reserve-and-Commit**: Before executing tool steps or model inference, the pod requests token allocation from the budget controller.
2. **Hard Ceiling**: If cumulative spend reaches `per_agent_cap_usd`, the pod halts immediately with `SpendCapExceeded`.
3. **Pareto Dominance Ranking**: Configurations across `{domain x model x tier}` are evaluated via `podrank` to identify non-dominated configurations maximizing assertion coverage per dollar spend.
