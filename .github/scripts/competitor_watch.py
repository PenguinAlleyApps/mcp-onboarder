#!/usr/bin/env python3
"""
competitor_watch.py — Weekly competitor coverage scan (CI/CD).

Reads .github/competitors.yml + previous state, polls competitor changelog feeds,
detects gap-closure events (competitor shipped feature matching our gap keywords),
emits markdown report + updates state.json + flags GAP_CLOSED env for workflow.

Stdlib only (urllib + json) + feedparser + pyyaml.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "last_scan_utc": None, "competitors": {}, "alerts_history": []}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def scan_competitor(c: dict, gap_keywords: list[str], state_entry: dict) -> dict:
    """Returns {entries_new: [...], alerts: [...]}."""
    feed_url = c.get("changelog_rss")
    if not feed_url:
        return {"entries_new": [], "alerts": []}
    parsed = feedparser.parse(feed_url, etag=state_entry.get("etag"), modified=state_entry.get("modified"))
    if getattr(parsed, "status", None) == 304:
        return {"entries_new": [], "alerts": []}
    seen = set(state_entry.get("last_seen_guids", []))
    entries_new = []
    alerts = []
    rx = re.compile("|".join(re.escape(k) for k in gap_keywords), re.I)
    for e in parsed.entries:
        guid = e.get("id") or e.get("link") or ""
        if guid in seen:
            continue
        text = (e.get("title", "") + " " + e.get("summary", ""))
        entries_new.append({"guid": guid, "title": e.get("title", ""), "url": e.get("link"), "published": e.get("published", "")})
        if rx.search(text):
            alerts.append({
                "competitor": c["name"],
                "title": e.get("title", ""),
                "url": e.get("link"),
                "matched_keywords": rx.findall(text)[:5],
                "risk": c.get("risk_if_close_gap", "MED"),
            })
    state_entry["last_seen_guids"] = (state_entry.get("last_seen_guids", []) + [n["guid"] for n in entries_new])[-200:]
    if getattr(parsed, "etag", None):
        state_entry["etag"] = parsed.etag
    if getattr(parsed, "modified", None):
        state_entry["modified"] = parsed.modified
    return {"entries_new": entries_new, "alerts": alerts}


def render_report(product: str, north_star: str, all_alerts: list[dict], all_entries: dict, scanned_ts: str) -> str:
    lines = [
        f"# competitor-watch report · {product}",
        "",
        f"**Scanned:** {scanned_ts}",
        f"**North star:** {north_star}",
        "",
        "## Gap-closure alerts" if all_alerts else "## No gap-closure alerts this scan",
    ]
    for a in all_alerts:
        lines.append(f"- **[{a['risk']}] {a['competitor']}** shipped: [{a['title']}]({a['url']})  ")
        lines.append(f"  Matched keywords: `{', '.join(a['matched_keywords'])}`")
    lines += ["", "## Per-competitor new entries (audit trail)"]
    for comp, entries in all_entries.items():
        if not entries:
            continue
        lines.append(f"\n### {comp} ({len(entries)} new)")
        for e in entries[:5]:
            lines.append(f"- [{e['title']}]({e['url']}) · {e.get('published', 'n/a')}")
        if len(entries) > 5:
            lines.append(f"- ... +{len(entries) - 5} more")
    lines += ["", "## Action items", "- Review alerts → decide adapt vs defer", "- Update ROADMAP.md competitive landscape table", "- Open feature issues per gap-closure if leap-frog viable"]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    config = load_yaml(Path(args.config))
    state = load_state(Path(args.state))
    state["competitors"] = state.get("competitors", {})
    gap_keywords = config.get("detection", {}).get("gap_keywords", [])
    all_alerts = []
    all_entries = {}
    for c in config.get("competitors", []):
        entry = state["competitors"].setdefault(c["name"], {})
        res = scan_competitor(c, gap_keywords, entry)
        all_entries[c["name"]] = res["entries_new"]
        all_alerts.extend(res["alerts"])
    scanned_ts = datetime.now(timezone.utc).isoformat()
    state["last_scan_utc"] = scanned_ts
    if all_alerts:
        state["alerts_history"].append({"ts": scanned_ts, "count": len(all_alerts), "alerts": all_alerts})
    save_state(Path(args.state), state)
    report = render_report(config.get("product", "unknown"), config.get("north_star", ""), all_alerts, all_entries, scanned_ts)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report, encoding="utf-8")
    if all_alerts:
        gh_env = os.environ.get("GITHUB_ENV")
        if gh_env:
            with open(gh_env, "a", encoding="utf-8") as f:
                f.write("GAP_CLOSED=true\n")
                f.write(f"GAP_REPORT_PATH={args.output}\n")
    print(f"Scanned {len(config.get('competitors', []))} competitors. Alerts: {len(all_alerts)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
