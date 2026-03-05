#!/usr/bin/env python3
"""
process_prs.py — Formats raw GitHub PR + CI JSON into a standup markdown report.

Usage:
    python3 process_prs.py --prs prs.json [--ci ci.json] [--stale-days 5] [--team "gen-ai"]

Input JSON format (prs.json):
    List of PR objects from GitHub search_issues API response items[].
    Optionally augmented with a "ci_state" key per PR from get_pull_request_status.

Output:
    Markdown standup report printed to stdout.
"""

import json
import sys
import re
import argparse
from datetime import datetime, timezone


BOT_AUTHORS = {"dependabot[bot]", "red-hat-konflux[bot]", "renovate[bot]", "github-actions[bot]"}
SKIP_CI_CONTEXTS = {"CodeRabbit", "coderabbit"}

TODAY = datetime.now(timezone.utc)


def days_since(iso_str):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return (TODAY - dt).days


def label_names(pr):
    return {l["name"] for l in pr.get("labels", [])}


def extract_jira(body):
    if not body:
        return []
    return re.findall(r'RHOAIENG-\d+', body)


def tide_missing_labels(ci_statuses):
    """Extract what tide says is missing from merge."""
    for s in ci_statuses:
        if s.get("context") == "tide":
            desc = s.get("description", "")
            if "Needs" in desc:
                return desc
    return None


def has_ci_failure(ci_statuses):
    """Returns True if any non-bot, non-CodeRabbit check failed."""
    for s in ci_statuses:
        ctx = s.get("context", "")
        if any(skip in ctx for skip in SKIP_CI_CONTEXTS):
            continue
        if s.get("state") == "failure":
            return True
    return False


def classify_prs(prs, stale_days=5):
    blocked, stale_review, active, wip, bots, ci_failing = [], [], [], [], [], []

    for pr in prs:
        author = pr["user"]["login"]
        labels = label_names(pr)
        age = days_since(pr["created_at"])
        is_draft = pr.get("draft", False)
        ci = pr.get("ci_statuses", [])
        ci_fail = has_ci_failure(ci)

        # Bot PRs
        if author in BOT_AUTHORS:
            if "needs-ok-to-test" in labels:
                bots.append(pr)
            continue

        # WIP / Draft
        if is_draft or "do-not-merge/work-in-progress" in labels:
            wip.append(pr)
            continue

        # Blocked / On Hold
        if "do-not-merge/hold" in labels:
            blocked.append(pr)
            continue

        # CI Failing (non-bot, non-WIP, non-blocked)
        if ci_fail:
            ci_failing.append(pr)
            continue

        # Stale waiting for review
        if age >= stale_days:
            stale_review.append(pr)
        else:
            active.append(pr)

    return blocked, stale_review, active, wip, bots, ci_failing


def pr_row(pr, show_jira=True):
    num = pr["number"]
    url = pr["html_url"]
    title = pr["title"]
    author = pr["user"]["login"]
    assignee = (pr.get("assignee") or {}).get("login", "—")
    age = days_since(pr["created_at"])
    labels = label_names(pr)
    ci = pr.get("ci_statuses", [])
    tide = tide_missing_labels(ci) or ""
    missing = ""
    if "approved" in tide.lower() and "lgtm" in tide.lower():
        missing = "`approved` + `lgtm`"
    elif "approved" in tide.lower():
        missing = "`approved`"
    elif "lgtm" in tide.lower():
        missing = "`lgtm`"
    elif "conflict" in tide.lower():
        missing = "⚠️ merge conflict"

    jira_tickets = extract_jira(pr.get("body", "") or "")
    jira_str = " ".join(f"[{t}](https://issues.redhat.com/browse/{t})" for t in jira_tickets[:2])

    age_str = f"**{age}d**" if age >= 5 else f"{age}d"

    if show_jira and jira_str:
        return f"| [#{num}]({url}) | {title[:60]} | `{author}` | `{assignee}` | {age_str} | {jira_str} | {missing} |"
    return f"| [#{num}]({url}) | {title[:60]} | `{author}` | `{assignee}` | {age_str} | {missing} |"


def format_report(prs, stale_days=5, team="", repo=""):
    blocked, stale_review, active, wip, bots, ci_failing = classify_prs(prs, stale_days)
    date_str = TODAY.strftime("%a %b %-d, %Y")

    lines = [
        f"## PR Standup — {date_str}",
        f"**Repo**: `{repo}` | **Team**: {team or 'all'} | **Stale threshold**: {stale_days}+ days",
        "",
    ]

    def section(title, items, cols, row_fn):
        lines.append(f"### {title}")
        if not items:
            lines.append("_None_ ✅")
            lines.append("")
            return
        lines.append(f"| {' | '.join(cols)} |")
        lines.append(f"| {' | '.join(['---'] * len(cols))} |")
        for pr in items:
            lines.append(row_fn(pr))
        lines.append("")

    # Blocked
    section(
        "🔴 Blocked / On Hold",
        blocked,
        ["#", "Title", "Author", "Assignee", "Age", "Reason"],
        lambda pr: f"| [#{pr['number']}]({pr['html_url']}) | {pr['title'][:55]} | `{pr['user']['login']}` | `{(pr.get('assignee') or {}).get('login','—')}` | {days_since(pr['created_at'])}d | `do-not-merge/hold` |"
    )

    # CI Failing
    section(
        "🔥 CI Failing",
        ci_failing,
        ["#", "Title", "Author", "Age", "Jira"],
        lambda pr: f"| [#{pr['number']}]({pr['html_url']}) | {pr['title'][:55]} | `{pr['user']['login']}` | **{days_since(pr['created_at'])}d** | {' '.join(f'[{t}](https://issues.redhat.com/browse/{t})' for t in extract_jira(pr.get('body','') or '')[:1])} |"
    )

    # Stale waiting
    section(
        f"🟡 Waiting for Review ({stale_days}+ days, CI green)",
        sorted(stale_review, key=lambda p: -days_since(p['created_at'])),
        ["#", "Title", "Author", "Assignee", "Age", "Jira", "Missing"],
        pr_row
    )

    # Active
    section(
        "🟢 Active — In Review Window",
        active,
        ["#", "Title", "Author", "Assignee", "Age", "Jira", "Missing"],
        pr_row
    )

    # WIP
    section(
        "⚫ WIP / Draft",
        wip,
        ["#", "Title", "Author", "Age", "Note"],
        lambda pr: f"| [#{pr['number']}]({pr['html_url']}) | {pr['title'][:55]} | `{pr['user']['login']}` | **{days_since(pr['created_at'])}d** | {'draft' if pr.get('draft') else 'WIP label'} |"
    )

    # Bots
    section(
        "🤖 Bot PRs — Needs `/ok-to-test`",
        bots,
        ["#", "Title", "Age"],
        lambda pr: f"| [#{pr['number']}]({pr['html_url']}) | {pr['title'][:70]} | {days_since(pr['created_at'])}d |"
    )

    # Action items
    lines.append("### Action Items")
    lines.append("| Priority | Action |")
    lines.append("| --- | --- |")
    for pr in sorted(stale_review, key=lambda p: -days_since(p['created_at'])):
        assignee = (pr.get("assignee") or {}).get("login", "**unassigned**")
        age = days_since(pr["created_at"])
        emoji = "🔥" if age >= 14 else "⚠️"
        lines.append(f"| {emoji} | [#{pr['number']}]({pr['html_url']}) — `{assignee}` to review ({age}d waiting) |")
    for pr in blocked:
        lines.append(f"| 🔴 | [#{pr['number']}]({pr['html_url']}) — confirm if hold is still valid |")
    for pr in ci_failing:
        lines.append(f"| 🔥 | [#{pr['number']}]({pr['html_url']}) — CI failing, needs fix |")
    for pr in wip:
        age = days_since(pr["created_at"])
        if age >= 7:
            lines.append(f"| 💬 | [#{pr['number']}]({pr['html_url']}) — `{pr['user']['login']}` WIP for {age}d, still active? |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Format GitHub PRs into standup markdown")
    parser.add_argument("--prs", required=True, help="Path to JSON file with PR list")
    parser.add_argument("--stale-days", type=int, default=5)
    parser.add_argument("--team", default="")
    parser.add_argument("--repo", default="")
    args = parser.parse_args()

    with open(args.prs) as f:
        data = json.load(f)

    # Accept either a raw search_issues response or a plain list
    prs = data.get("items", data) if isinstance(data, dict) else data

    print(format_report(prs, stale_days=args.stale_days, team=args.team, repo=args.repo))


if __name__ == "__main__":
    main()
