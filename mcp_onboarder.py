#!/usr/bin/env python3
"""
mcp-onboarder — Cross-platform MCP server install + pre-install risk audit CLI.

Parse a GitHub repo / npm pkg / pypi pkg URL → emit ready-to-paste client config +
risk audit + tool inventory. Built for Claude Code, Claude Desktop, Cursor.

Usage:
    mcp-onboarder <url> [--client claude-code|claude-desktop|cursor] [--no-audit] [--json]

License: MIT — PenguinAlley, 2026.
"""
from __future__ import annotations
import argparse, json, re, shlex, sys, urllib.error, urllib.parse, urllib.request
from dataclasses import dataclass, field, asdict

UA = "mcp-onboarder/0.1 (+github.com/PenguinAlleyApps/mcp-onboarder)"
SENSITIVE_ENV_RX = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|PRIVATE)", re.I)
_PKG = r"(?:@[\w.-]+/[\w.-]+|[\w.-]{3,})(?:@[\w.+-]+)?"
INSTALL_NPX_RX = re.compile(rf"\bnpx\s+(?:-y\s+)?({_PKG})", re.I)
INSTALL_PIP_RX = re.compile(rf"\bpip\s+install\s+(?:--user\s+)?({_PKG})", re.I)
INSTALL_PIPX_RX = re.compile(rf"\bpipx\s+install\s+({_PKG})", re.I)
INSTALL_DOCKER_RX = re.compile(r"\bdocker\s+run\s+[^\n]*?([\w./-]+:[\w.-]+)", re.I)
RISK_KEYWORDS = {
    "fs_write": (re.compile(r"\b(write[_-]?file|writeFile|fs\.write|file_put|os\.write)\b", re.I), 20),
    "exec": (re.compile(r"\b(child_process|subprocess|spawn|execSync|os\.exec)\b", re.I), 20),
    "network": (re.compile(r"\b(axios|requests\.(get|post)|node-fetch|http\.request|fetch\()", re.I), 10),
    "shell": (re.compile(r"\b(shell|bash\s+-c|cmd\.exe|powershell)\b", re.I), 15),
}


@dataclass
class Source:
    kind: str
    owner: str
    name: str
    raw_url: str


@dataclass
class Manifest:
    install_cmd: str | None = None
    package_name: str | None = None
    env_vars: list[str] = field(default_factory=list)
    description: str = ""
    readme_excerpt: str = ""
    stars: int | None = None
    last_pushed: str | None = None


@dataclass
class RiskAudit:
    score: int
    band: str  # LOW MED HIGH
    flags: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class FetchError(RuntimeError):
    """Wraps any network/parse failure during fetch with a stable message."""


def fetch(url: str, accept: str = "application/json") -> dict | str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise FetchError(f"{type(exc).__name__}: {exc}") from exc
    if accept.startswith("application/json"):
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise FetchError(f"invalid JSON from {url}: {exc}") from exc
    return body


def detect_source(url: str) -> Source:
    m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", url)
    if m:
        return Source("github", m.group(1), m.group(2).rstrip(".git"), url)
    m = re.match(r"https?://(?:www\.)?npmjs\.com/package/(@?[^/?#]+(?:/[^/?#]+)?)", url)
    if m:
        return Source("npm", "", m.group(1), url)
    m = re.match(r"https?://pypi\.org/project/([^/?#]+)", url)
    if m:
        return Source("pypi", "", m.group(1), url)
    m = re.match(r"https?://(?:www\.)?smithery\.ai/server/([^/?#]+)", url)
    if m:
        return Source("smithery", "", m.group(1), url)
    raise ValueError(f"unsupported url, expected github/npm/pypi/smithery: {url}")


def fetch_github(s: Source) -> Manifest:
    meta = fetch(f"https://api.github.com/repos/{s.owner}/{s.name}")
    try:
        readme = fetch(
            f"https://raw.githubusercontent.com/{s.owner}/{s.name}/HEAD/README.md",
            accept="text/plain",
        )
    except urllib.error.HTTPError:
        readme = ""
    return Manifest(
        install_cmd=extract_install(readme),
        package_name=meta.get("name"),
        env_vars=extract_env_vars(readme),
        description=(meta.get("description") or "").strip(),
        readme_excerpt=readme[:4000],
        stars=meta.get("stargazers_count"),
        last_pushed=meta.get("pushed_at"),
    )


def fetch_npm(s: Source) -> Manifest:
    # URL-encode scoped names like @scope/name → @scope%2Fname for the npm registry
    encoded = urllib.parse.quote(s.name, safe="@")
    meta = fetch(f"https://registry.npmjs.org/{encoded}")
    latest = meta.get("dist-tags", {}).get("latest", "")
    v = meta.get("versions", {}).get(latest, {})
    readme = meta.get("readme") or v.get("readme") or ""
    return Manifest(
        install_cmd=extract_install(readme) or f"npx -y {s.name}",
        package_name=s.name,
        env_vars=extract_env_vars(readme),
        description=(v.get("description") or meta.get("description") or "").strip(),
        readme_excerpt=readme[:4000],
    )


def fetch_pypi(s: Source) -> Manifest:
    meta = fetch(f"https://pypi.org/pypi/{urllib.parse.quote(s.name)}/json")
    info = meta.get("info", {})
    readme = info.get("description") or ""
    return Manifest(
        install_cmd=extract_install(readme) or f"pipx install {s.name}",
        package_name=s.name,
        env_vars=extract_env_vars(readme),
        description=(info.get("summary") or "").strip(),
        readme_excerpt=readme[:4000],
    )


def fetch_smithery(s: Source) -> Manifest:
    # Smithery has no public REST manifest in v0.1 spec; scrape page for hints
    page = fetch(f"https://smithery.ai/server/{s.name}", accept="text/html")
    return Manifest(
        install_cmd=extract_install(page),
        package_name=s.name,
        env_vars=extract_env_vars(page),
        description="Smithery hosted server (manifest scraped from page)",
        readme_excerpt=page[:4000] if isinstance(page, str) else "",
    )


def extract_install(text: str) -> str | None:
    for rx in (INSTALL_NPX_RX, INSTALL_PIP_RX, INSTALL_PIPX_RX, INSTALL_DOCKER_RX):
        m = rx.search(text)
        if m:
            return m.group(0).strip()
    return None


def extract_env_vars(text: str) -> list[str]:
    found = set()
    for line in text.splitlines():
        for m in re.finditer(r"\b([A-Z][A-Z0-9_]{3,})\s*[=:]", line):
            v = m.group(1)
            if SENSITIVE_ENV_RX.search(v) or v.endswith("_URL") or v.endswith("_HOST"):
                found.add(v)
    return sorted(found)


def audit_risk(m: Manifest) -> RiskAudit:
    score = 0
    flags: list[str] = []
    text = m.readme_excerpt
    for label, (rx, weight) in RISK_KEYWORDS.items():
        if rx.search(text):
            score += weight
            flags.append(f"{label} keyword detected (+{weight})")
    for v in m.env_vars:
        if SENSITIVE_ENV_RX.search(v):
            score += 5
            flags.append(f"sensitive env var: {v} (+5)")
    # Popularity adjusts score, but cannot mask serious risk: cap reduction at -5 when any
    # +20 weighted flag (fs_write/exec) was raised.
    has_serious = any("fs_write" in f or "exec" in f for f in flags)
    if m.stars is not None:
        if m.stars > 1000:
            reduction = 5 if has_serious else 10
            score -= reduction
            flags.append(f"popularity bonus, {m.stars} stars (-{reduction})")
        elif m.stars < 50:
            score += 10
            flags.append(f"low-stars caveat, {m.stars} stars (+10)")
    score = max(0, min(100, score))
    band = "LOW" if score < 30 else ("MED" if score < 60 else "HIGH")
    recs = []
    if any("fs_write" in f for f in flags):
        recs.append("Scope --allowed-dirs to specific paths; never project root or $HOME.")
    if any("exec" in f for f in flags):
        recs.append("Review subprocess invocations; consider sandbox or container runtime.")
    if m.env_vars:
        recs.append(f"Configure secrets via env, never commit. Required: {', '.join(m.env_vars)}.")
    if band == "HIGH":
        recs.append("HIGH risk — pin a known commit/version, audit deps tree, prefer alternatives if available.")
    return RiskAudit(score=score, band=band, flags=flags, recommendations=recs)


def emit_client_config(m: Manifest, client: str) -> str:
    cmd = m.install_cmd or "npx -y <package>"
    try:
        parts = shlex.split(cmd, posix=True)
    except ValueError as exc:
        # Mismatched quotes: refuse to emit a misleading config (per Codex review).
        return json.dumps(
            {
                "_error": "malformed install command (unbalanced quotes)",
                "_raw": cmd,
                "_detail": str(exc),
                "_action": "edit manually; mcp-onboarder refuses to emit unsafe config",
            },
            indent=2,
        )
    if not parts:
        return "// no install command detected"
    binary, args = parts[0], parts[1:]
    env_block = {v: f"<set-{v.lower()}>" for v in m.env_vars}
    server_name = (m.package_name or "server").rsplit("/", 1)[-1].replace("@", "")
    block = {server_name: {"command": binary, "args": args}}
    if env_block:
        block[server_name]["env"] = env_block
    if client in ("claude-code", "claude-desktop", "cursor"):
        return json.dumps({"mcpServers": block}, indent=2)
    return json.dumps(block, indent=2)


def render_text(s: Source, m: Manifest, audit: RiskAudit | None, client: str) -> str:
    out = [
        f"# mcp-onboarder | {s.kind}:{s.owner + '/' if s.owner else ''}{s.name}",
        "",
        f"**Description:** {m.description or '(none)'}",
        f"**Source URL:** {s.raw_url}",
    ]
    if m.stars is not None:
        out.append(f"**Stars:** {m.stars}  |  **Last pushed:** {m.last_pushed or 'n/a'}")
    out += [
        "",
        "## Install command",
        "",
        "> WARNING: extracted from upstream README. Verify before running. mcp-onboarder",
        "> does not execute this command.",
        "",
        "```bash",
        f"{m.install_cmd or '(not detected - read README manually)'}",
        "```",
        "",
        f"## Client config ({client})",
        "```json",
        emit_client_config(m, client),
        "```",
        "",
    ]
    if audit is None:
        out += [
            "## Risk audit",
            "",
            "Audit skipped (--no-audit). Re-run without the flag for risk scoring.",
        ]
    else:
        out.append(f"## Risk audit | score {audit.score}/100 | band {audit.band}")
        for f in audit.flags or ["(no risk keywords detected)"]:
            out.append(f"- {f}")
        if audit.recommendations:
            out.append("\n**Recommendations:**")
            for r in audit.recommendations:
                out.append(f"- {r}")
    if m.env_vars:
        out += ["", "## Required env vars"]
        for v in m.env_vars:
            out.append(f"- `{v}`")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MCP server install + risk audit CLI (mcp-onboarder)")
    p.add_argument("url", help="MCP server source URL (github / npm / pypi / smithery)")
    p.add_argument("--client", choices=["claude-code", "claude-desktop", "cursor"], default="claude-code")
    p.add_argument("--no-audit", action="store_true", help="Skip risk audit section")
    p.add_argument("--json", action="store_true", help="Emit full result as JSON")
    args = p.parse_args(argv)
    try:
        src = detect_source(args.url)
        m = {"github": fetch_github, "npm": fetch_npm, "pypi": fetch_pypi, "smithery": fetch_smithery}[src.kind](src)
        audit: RiskAudit | None = None if args.no_audit else audit_risk(m)
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} - {e.reason}", file=sys.stderr)
        return 1
    except FetchError as e:
        print(f"ERROR: fetch failed - {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.json:
        payload = {"source": asdict(src), "manifest": asdict(m), "audit": asdict(audit) if audit else None}
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(src, m, audit, args.client))
    return 3 if (audit and audit.band == "HIGH") else 0


if __name__ == "__main__":
    sys.exit(main())
