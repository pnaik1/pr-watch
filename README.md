# pr-watch

A shared [Cursor AI](https://cursor.com) skill that gives your team a **live health snapshot of open PRs** — what's waiting for review, what's blocked, what's failing CI, and what's been sitting too long.

Clone this repo, open it in Cursor, and the skill is immediately available in every chat.

---

## What it shows

| Section | What it covers |
|---------|---------------|
| 🔴 Blocked | PRs with `do-not-merge/hold` or merge conflicts |
| 🔥 CI Failing | PRs where checks are failing (overnight failures flagged) |
| 👀 Waiting for Review | Open 2+ days, CI green, missing `approved` / `lgtm` |
| 🟢 Recently Opened | Open < 2 days — in the review window |
| ⚫ WIP / Draft | Not ready for review yet |
| 🤖 Bot PRs | Dependabot / Konflux PRs gated on `/ok-to-test` |
| ✅ Action Items | Prioritised list of who needs to do what |

---

## How to use

### 1. Clone this repo

```bash
git clone https://github.com/<your-org>/pr-watch
cd pr-watch
```

### 2. Open in Cursor

Open the folder in Cursor. Skills in `.cursor/skills/` are automatically picked up — no setup needed.

### 3. Make sure GitHub MCP is connected

The skill uses the `user-github` MCP tool (`search_issues`, `get_pull_request_status`).
Set it up in **Cursor Settings → MCP** if not already connected.

### 4. Ask Cursor

```
"what's the PR health for gen-ai?"
"show me blocked and CI failing PRs for eval-hub"
"what PRs have been waiting for review for 2+ days in model-registry?"
"full PR health check for all areas"
```

---

## Configuration

Edit [`.cursor/skills/pr-standup/config.yaml`](.cursor/skills/pr-standup/config.yaml):

```yaml
repo: opendatahub-io/odh-dashboard   # ← change to your repo
stale_days: 2                         # ← stale threshold in days

teams:
  - name: my-team
    labels:
      - area/my-label
    description: My team
```

### Pre-configured teams

| Team | Labels |
|------|--------|
| `gen-ai` | `area/gen-ai` |
| `eval-hub` | `area/eval-hub` |
| `gen-ai-and-eval-hub` | Both of the above |
| `model-registry` | `area/model-registry` |
| `pipelines` | `area/pipelines`, `area/ds-pipelines` |
| `model-serving` | `area/model-serving`, `area/nim` |
| `platform` | `area/platform`, `area/backend`, `area/frontend`, `area/components` |
| `all-areas` | All area labels |

---

## Repo structure

```
.cursor/
└── skills/
    └── pr-standup/
        ├── SKILL.md              ← Skill instructions & workflow
        ├── config.yaml           ← Team + repo configuration
        └── scripts/
            └── process_prs.py    ← PR data formatter
README.md
```

---

## Adding more skills

1. Create `.cursor/skills/<skill-name>/SKILL.md`
2. Add YAML frontmatter (`name` + `description`) and instructions
3. Commit and push — everyone who pulls gets the skill
