# Cross-Repository VCS Deliberation via GitHub & Jujutsu

## 1. Overview
Multi-agent engineering squads coordinate changes across repositories using mockable CLI adapters driving GitHub (`gh`) and Jujutsu (`jj`). In strict compliance with zero-token-leakage principles, adapters never store credentials in memory or prompt contexts, relying entirely on host environment credentials (`GH_TOKEN`).

## 2. GitHubAdapter (`gh` CLI)
The `GitHubAdapter` drives GitHub operations using standard JSON output schemas:
- `issue_list(repo)`: Queries issues via `gh issue list --repo <repo> --json ...`.
- `issue_create(repo, title, body)`: Authors new issues with structured markdown.
- `issue_comment(repo, number, body)`: Records agent deliberation notes and consensus summaries.
- `pr_list(repo)`: Inspects active pull requests across participating repositories.
- `pr_create(repo, title, body, head, base)`: Authors branch pull requests.
- `pr_comment(repo, number, body)`: Submits AST review notes.
- `pr_merge(repo, number, method)`: Executes atomic merges using `squash`, `merge`, or `rebase`.

## 3. JujutsuAdapter (`jj` CLI)
The `JujutsuAdapter` drives local agentic version control:
- `status()`: Evaluates working copy state.
- `diff()`: Generates unified diffs for AST analysis.
- `log(limit)`: Traverses revision logs.
- `new_change(message)`: Creates isolated working changes (`jj new -m <msg>`).
- `describe(message)`: Updates change descriptions.
- `git_push()`: Pushes bookmarks to Git remotes.

## 4. Offline Verification & CommandRunner Abstraction
All adapters execute through an injectable `CommandRunner` function:
```typescript
export type CommandRunner = (
  command: string,
  args: string[],
  options?: CommandOptions
) => Promise<CommandResult>;
```
This enables 100% offline unit testing via `FakeCommandRunner`, asserting exact argument vector construction without spawning child processes.
