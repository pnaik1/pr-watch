---
name: pr-standup
description: Generates a daily standup PR summary for GitHub repositories — PRs waiting for review, blocked tickets, CI failures, and stale items (5+ days). Configurable per team via config.yaml. Use when a user asks for a standup summary, PR status report, daily PR digest, or mentions labels like area/gen-ai or area/eval-hub.
---

# PR Standup Summary Skill

Generates a daily standup report for open PRs filtered by team labels. Covers: waiting for review, blocked, CI status, and stale PRs (5+ days old).

## Configuration

Read team config from [config.yaml](config.yaml) before starting. It defines:
- `repo` — GitHub owner/repo
- `teams` — list of team configs, each with a `name` and `labels` array
- `stale_days` — threshold for "stale" (default: 5)

If the user specifies labels or a repo in their message, use those instead of config.yaml.

## Workflow

Follow these steps **sequentially** — never run MCP calls in parallel (causes Cursor to hang).

### Step 1 — Fetch PRs per label

For each label in the team config, call `search_issues` (user-github MCP):
```
q: "repo:<owner>/<repo> is:pr is:open label:<label>"
sort: "updated"
order: "desc"
perPage: 50
```

Collect all results. Deduplicate by PR number (a PR may have multiple matching labels).

### Step 2 — Parse PR metadata from search results

For each PR extract: `number`, `title`, `html_url`, `user.login` (author), `assignee.login`, `created_at`, `updated_at`, `labels[].name`, `draft`, `comments`.

Compute `days_open = today - created_at`.

Flag labels:
- `do-not-merge/hold` → BLOCKED
- `do-not-merge/work-in-progress` → WIP
- `needs-rebase` → NEEDS REBASE
- `needs-ok-to-test` → BOT/CI GATED
- `lgtm` → has lgtm
- `approved` → has approved

Skip bot authors: `dependabot[bot]`, `red-hat-konflux[bot]`, `renovate[bot]`.

### Step 3 — Fetch CI status for non-bot, non-WIP PRs

For each qualifying PR (not bot, not WIP/draft), call `get_pull_request_status` **one at a time**:
```
owner, repo, pullNumber
```

From the response, find the `tide` status context. Its `description` contains the merge blocker, e.g.:
- `"Not mergeable. Needs approved, lgtm labels."` → extract missing labels
- `"Not mergeable. Merge conflict."` → conflict
- absent / success → mergeable

Check if any non-CodeRabbit status has `state: "failure"` → CI failure.

### Step 4 — Build the report

Run `python3 scripts/process_prs.py <path-to-collected-json>` to format output, OR format inline using the template below.

## Output Template

```markdown
## PR Standup — <date>
**Repo**: <owner/repo> | **Labels**: <label list>

---

### 🔴 Blocked / On Hold
| # | Title | Author | Assignee | Age | Reason |

### 🟡 Waiting for Review (5+ days, CI green)
| # | Title | Author | Assignee | Age | Missing |

### 🟢 Active — In Review Window (< 5 days)
| # | Title | Author | Age | Jira | Notes |

### ⚫ WIP / Draft
| # | Title | Author | Age | Notes |

### 🤖 Bot PRs — Needs `/ok-to-test`
| # | Title | Age |

---

### Action Items
| Priority | Action |
```

Fill each section:
- **Blocked** — has `do-not-merge/hold`
- **Waiting for Review** — `days_open >= stale_days`, no hold/WIP, CI green, missing `approved`/`lgtm`
- **Active** — `days_open < stale_days`, no hold/WIP
- **WIP/Draft** — `draft=true` or `do-not-merge/work-in-progress`
- **Bot PRs** — bot authors with `needs-ok-to-test`

For Action Items, list the most urgent items first with the reviewer/assignee tagged.

## Critical Rules

1. **Never call MCP tools in parallel** — always sequential, one at a time
2. **Never use `get_pull_request_reviews`** — it hangs; use label signals (`lgtm`, `approved`) instead
3. **Skip CodeRabbit** from CI status checks and review summaries
4. **Jira links** — extract `RHOAIENG-XXXXX` from PR body and include as link: `https://issues.redhat.com/browse/<ticket>`

## Additional Resources

- Team configuration: [config.yaml](config.yaml)
- PR processing script: [scripts/process_prs.py](scripts/process_prs.py)
