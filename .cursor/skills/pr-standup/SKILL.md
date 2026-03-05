---
name: pr-watch
description: PR health monitor — surfaces PRs waiting for review, blocked tickets, CI failures, and anything stale for 2+ days across GitHub repositories. Configurable per team via config.yaml. Use when a user asks about PR status, what's blocked, what needs review, CI failures, stale PRs, or mentions team labels like area/gen-ai or area/eval-hub.
---

# PR Watch — PR Health Monitor

Gives a full health snapshot of open PRs for a team: what's waiting for review, what's blocked, what's failing CI, and what's been sitting too long.

## Configuration

Read team config from [config.yaml](config.yaml) before starting. It defines:
- `repo` — GitHub owner/repo
- `teams` — list of team configs, each with a `name` and `labels` array
- `stale_days` — threshold for "stale" (default: 2)

If the user specifies labels or a repo in their message, use those instead of config.yaml.

## Two modes

**Quick mode** (default) — uses label signals only, no CI calls, finishes in seconds.
**CI mode** — fetches CI status for stuck PRs only, triggered when user asks about CI failures.

Detect which mode from the user's message:
- CI mode keywords: "ci", "failing", "checks", "overnight", "broken build"
- Everything else → Quick mode

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

### Step 2 — Parse PR metadata

For each PR extract: `number`, `title`, `html_url`, `user.login` (author), `assignee.login`, `created_at`, `updated_at`, `labels[].name`, `draft`, `comments`, `body`.

Compute `days_open = today - created_at`.

Flag labels — these are the primary signals, sufficient for Quick mode:
- `do-not-merge/hold` → BLOCKED
- `do-not-merge/work-in-progress` → WIP
- `needs-rebase` → NEEDS REBASE
- `needs-ok-to-test` → BOT/CI GATED
- `lgtm` → has lgtm (one approval signal present)
- `approved` → fully approved
- `Stale` → marked stale by bot

Skip bot authors: `dependabot[bot]`, `red-hat-konflux[bot]`, `renovate[bot]`.

Extract Jira ticket IDs from PR body: pattern `RHOAIENG-\d+`. Link as `https://issues.redhat.com/browse/<ticket>`.

### Step 3 — CI status (CI mode only)

**Skip this step entirely in Quick mode.**

In CI mode, only call `get_pull_request_status` for PRs that are:
- Not a bot, not WIP/draft, not HOLD
- `days_open >= 2` (stuck)
- Missing both `lgtm` and `approved`

Call one at a time. From the response:
- `context: "tide"` → `description` reveals merge blockers
- Any non-CodeRabbit status with `state: "failure"` → CI failure
- Overnight = `updated_at` between yesterday 18:00–today 08:00 and `state: "failure"`

**Never call `get_pull_request_reviews`** — it hangs. Use `lgtm`/`approved` labels instead.

### Step 4 — Build the report

Use the output template below. Add a note at the top if in Quick mode: `> ⚡ Quick mode — CI status not fetched. Ask "show CI failures" for full check.`

## Output Template

```markdown
## PR Health Report — <date>
**Repo**: <owner/repo> | **Team**: <team> | **Stale**: 2+ days

---

### 🔴 Blocked
PRs with `do-not-merge/hold` or merge conflicts.
| # | Title | Author | Assignee | Age | Reason |

### 🔥 CI Failing
PRs where CI checks are failing (overnight failures flagged).
| # | Title | Author | Age | Failed Check | Jira |

### 👀 Waiting for Review
Open 2+ days, CI green, missing `approved` and/or `lgtm`.
| # | Title | Author | Assignee | Age | Jira | Needs |

### 🟢 Recently Opened
Open < 2 days — in the review window, no action needed yet.
| # | Title | Author | Age | Jira |

### ⚫ WIP / Draft
Not ready for review yet.
| # | Title | Author | Age | Note |

### 🤖 Bot PRs — Needs `/ok-to-test`
| # | Title | Age |

---

### Action Items
Prioritised — most urgent first.
| Priority | Action |
```

## Section definitions

| Section | Criteria |
|---------|----------|
| Blocked | `do-not-merge/hold` label OR tide says "Merge conflict" |
| CI Failing | Any non-CodeRabbit check has `state: failure` |
| Waiting for Review | `days_open >= stale_days`, no hold/WIP, CI green, missing `approved`/`lgtm` |
| Recently Opened | `days_open < stale_days`, no hold/WIP |
| WIP / Draft | `draft=true` OR `do-not-merge/work-in-progress` label |
| Bot PRs | Bot author + `needs-ok-to-test` label |

## Critical Rules

1. **Never call MCP tools in parallel** — always sequential, one at a time
2. **Never use `get_pull_request_reviews`** — hangs; use `lgtm`/`approved` labels instead
3. **Skip CodeRabbit** from all CI and review output
4. **Action Items** — list reviewer/assignee by name so ownership is clear

## Additional Resources

- Team configuration: [config.yaml](config.yaml)
- PR data formatter: [scripts/process_prs.py](scripts/process_prs.py)
