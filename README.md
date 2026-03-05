# ODH Team Cursor Skills

Shared [Cursor AI](https://cursor.com) skills for the OpenDataHub dashboard teams.

Clone this repo and open it in Cursor — skills are automatically available in every chat.

---

## Skills

### `pr-standup`

Generates a daily standup PR summary from GitHub, scoped by team label.

**Triggers automatically when you say things like:**
- _"run standup for gen-ai"_
- _"give me the PR status report for eval-hub"_
- _"what PRs are stale for model-registry?"_
- _"daily PR digest for all areas"_

**What it surfaces:**
| Section | What it shows |
|---------|--------------|
| 🔴 Blocked / On Hold | PRs with `do-not-merge/hold` |
| 🟡 Waiting for Review | Open 5+ days, CI green, missing `approved`/`lgtm` |
| 🟢 Active | Open < 5 days, in review window |
| ⚫ WIP / Draft | Draft PRs or `do-not-merge/work-in-progress` |
| 🤖 Bot PRs | Dependabot/Konflux PRs gated on `/ok-to-test` |
| ✅ Action Items | Prioritised list of who needs to do what |

---

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/<your-org>/odh-cursor-skills
```

### 2. Open in Cursor

Open the cloned folder in Cursor. The skills in `.cursor/skills/` are automatically picked up.

### 3. Make sure GitHub MCP is connected

The skill uses the `user-github` MCP tool (`search_issues`, `get_pull_request_status`).  
Set it up in **Cursor Settings → MCP** if not already configured.

---

## Configuration

Edit [`.cursor/skills/pr-standup/config.yaml`](.cursor/skills/pr-standup/config.yaml) to:

- **Add your team** — copy any `teams` entry, change `name` and `labels`
- **Change the repo** — update the `repo` field
- **Adjust stale threshold** — change `stale_days` (default: 5)

```yaml
repo: opendatahub-io/odh-dashboard
stale_days: 5

teams:
  - name: my-team
    labels:
      - area/my-label
    description: My team standup
```

### Available teams (pre-configured)

| Team key | Labels watched |
|----------|---------------|
| `gen-ai` | `area/gen-ai` |
| `eval-hub` | `area/eval-hub` |
| `gen-ai-and-eval-hub` | Both of the above |
| `model-registry` | `area/model-registry` |
| `pipelines` | `area/pipelines`, `area/ds-pipelines` |
| `model-serving` | `area/model-serving`, `area/nim` |
| `platform` | `area/platform`, `area/backend`, `area/frontend`, `area/components` |
| `all-areas` | All area labels |

---

## Adding a new skill

1. Create a new directory under `.cursor/skills/your-skill-name/`
2. Add a `SKILL.md` with YAML frontmatter (`name` + `description`) and instructions
3. Commit and push — everyone who pulls gets the skill automatically

---

## Repo structure

```
.cursor/
└── skills/
    └── pr-standup/
        ├── SKILL.md              ← Agent instructions & workflow
        ├── config.yaml           ← Team label configuration
        └── scripts/
            └── process_prs.py    ← PR data formatter
README.md
```
