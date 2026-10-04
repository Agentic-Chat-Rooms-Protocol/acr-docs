# Factorial Deliberation Attribution & Pareto Plan Pruning (DoE / ANOVA)

## 1. Overview
The Retort Attribution Engine decomposes multi-agent deliberation variance across models, prompt strategies, and harness architectures using multi-way Analysis of Variance (ANOVA). Crucially, the engine isolates tooling harness false-fails via honest diagnosis scoring, ensuring that harness bugs do not penalize model deliberation quality. Suboptimal execution paths are pruned via an accuracy-vs-cost Pareto frontier.

## 2. Factorial Grid Definition
A Design of Experiments (DoE) grid is defined over the Cartesian space:
$$\mathcal{G} = \mathcal{M} \times \mathcal{P} \times \mathcal{H} \times \mathcal{T}$$
where:
- $\mathcal{M}$: Set of evaluated models (e.g., Claude-3.7, DeepSeek-R1, GPT-4o).
- $\mathcal{P}$: Set of prompt strategies (e.g., ReAct, Plan-and-Solve, ReflAct).
- $\mathcal{H}$: Harness execution architectures.
- $\mathcal{T}$: Benchmark tasks and operational scenarios.

Each cell $c \in \mathcal{G}$ produces a record containing:
- Coverage: Requirement coverage percentage ($[0, 100]$).
- Code Quality: Static lint/test verification score ($[0, 100]$).
- Cost: Dollar compute spend ($USD$).
- Latency: Wall-clock duration ($ms$).
- Diagnosis: Outcome classification enum $\in \{\text{Pass}, \text{Genuine}, \text{Tooling}\}$.

## 3. Honest Scoring & Tooling False-Fail Exclusion
Harness false-failures (e.g., test runner timeouts, unhandled socket closes) frequently corrupt benchmark evaluations. The Retort engine enforces honest scoring:
1. When a cell evaluates with `Diagnosis::Tooling`, its outcome is excluded from the model's accuracy computation:
   $$\mathcal{G}_{\text{valid}} = \{ c \in \mathcal{G} \mid \text{diagnosis}(c) \neq \text{Tooling} \}$$
2. Excluded cells are recorded in `cells_excluded_tooling` and audited in the telemetry stream.

## 4. Multi-Way ANOVA Mathematical Formulation
Total variation across valid cells is decomposed into main effects and residual error:
$$SS_{\text{Total}} = SS_{\text{Model}} + SS_{\text{Prompt}} + SS_{\text{Harness}} + SS_{\text{Error}}$$

### Sum of Squares
$$SS_{\text{Total}} = \sum_{i=1}^{N} (y_i - \bar{y})^2$$
$$SS_{\text{Factor}} = \sum_{j=1}^{k} n_j (\bar{y}_j - \bar{y})^2$$
$$SS_{\text{Error}} = SS_{\text{Total}} - \sum_{\text{factors}} SS_{\text{Factor}}$$

### Degrees of Freedom
- $df_{\text{Model}} = |\mathcal{M}| - 1$
- $df_{\text{Prompt}} = |\mathcal{P}| - 1$
- $df_{\text{Harness}} = |\mathcal{H}| - 1$
- $df_{\text{Total}} = N - 1$
- $df_{\text{Error}} = df_{\text{Total}} - \sum df_{\text{Factors}}$

### Mean Square and F-Statistic
For each factor $f$:
$$MS_f = \frac{SS_f}{df_f}, \quad MS_{\text{Error}} = \frac{SS_{\text{Error}}}{df_{\text{Error}}}$$
$$F_f = \frac{MS_f}{MS_{\text{Error}}}$$

### Variance Explained ($\eta^2$)
$$\eta^2_f = \frac{SS_f}{SS_{\text{Total}}}$$

## 5. Accuracy-vs-Cost Pareto Frontier (NSGA-II)
Candidate stacks are mapped to a two-dimensional objective space:
$$f(x) = (\text{accuracy}(x), -\text{cost}(x))$$
Configuration $A$ dominates configuration $B$ ($A \succ B$) if:
$$\text{accuracy}(A) \ge \text{accuracy}(B) \quad \land \quad \text{cost}(A) \le \text{cost}(B)$$
with at least one strict inequality.

Dominated configurations ($\text{rank} > 1$) are automatically pruned from deliberation dispatch, reserving compute budget for non-dominated Pareto-optimal stacks.
