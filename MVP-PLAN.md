# mcp-onboarder — MVP Plan

> *PenguinAlley flagship · 2026-05-12 · Phase 02 ship candidate from Phase 03 devtools scout*

## Painpoint (one-liner)

**13k+ MCP servers fragmentados en 6+ registries, manual JSON paste por cliente, ZERO pre-install security audit cross-platform — Anthropic explícitamente disclaims responsibility.**

## Scope

### In scope (v0.1)

- CLI Python ≤200 LOC, cross-platform (Windows + Linux + macOS).
- `mcp-onboarder <url>` — accepts GitHub repo URL, npm package URL, pypi URL, or Smithery URL.
- Parse fuente (README + package.json/pyproject.toml + manifest) → extract:
  - install command (`npx`, `pip install`, `docker run`).
  - auth requirements (env vars detected via README scan).
  - tool inventory (list of MCP tools exposed if introspectable).
  - permissions estimate (filesystem read/write, network egress, subprocess spawn).
- Emit:
  - `mcp.json` snippet ready-to-paste para Claude Code / Claude Desktop / Cursor.
  - risk audit markdown (score 0-100 + flags).
- Exit codes: 0 ok, 1 fetch error, 2 parse error, 3 high-risk-warning.

### Out of scope (v0.1 — defer)

- Auto-install (Luis decides install path manually).
- Sandbox execution.
- Cloud gateway proxy.
- Team whitelist registry (Premium tier feature).
- CI/CD GitHub Action (Premium tier).
- Compliance report SOC2 (Enterprise tier).

## Architecture

```
┌─ CLI entrypoint (argparse)
│   └─ url validate + source-type detect (github | npm | pypi | smithery | http)
│
├─ Fetcher (urllib stdlib + retry)
│   ├─ GitHub: api.github.com/repos/<owner>/<repo>/contents/{README.md, package.json, pyproject.toml}
│   ├─ npm: registry.npmjs.org/<package>
│   ├─ pypi: pypi.org/pypi/<package>/json
│   └─ smithery: smithery.ai/<slug>/manifest
│
├─ Parser
│   ├─ README extraction: install commands via regex (`npx <pkg>`, `pip install <pkg>`, `docker run`)
│   ├─ Env vars: scan README + .env.example for `<VAR>=<placeholder>` patterns
│   ├─ Tool inventory: try `mcp_server_*` introspection (defer if not exposed)
│   └─ Permission keywords: filesystem|network|subprocess|exec|fs|fetch|child_process
│
├─ Risk auditor (heuristic v0.1)
│   ├─ +20 if `child_process|exec|spawn` keyword match
│   ├─ +20 if `filesystem write` keyword match
│   ├─ +10 if `fetch|http|axios|requests` outbound network
│   ├─ +10 if auth required (sensitive scopes implied)
│   ├─ +10 if maintainer single + commits last <30d (sole-maintainer risk)
│   ├─ +5 per env var with sensitive name (TOKEN|KEY|SECRET|PASSWORD)
│   └─ +0-20 score-cap for popularity (>1000 stars = -10)
│   Total 0-100. Low <30, Med 30-60, High 60-100.
│
└─ Emitter
    ├─ JSON config snippet (3 client formats supported)
    ├─ Risk audit markdown
    └─ Tool inventory (table)
```

## Build steps

1. Repo scaffold: copia de `templates/penguin-repo/` con vars expanded.
2. `mcp_onboarder.py` ≤200 LOC con argparse + 4 fetcher functions + parser + risk audit + emitter.
3. Tests inline (smoke con 3 known MCPs: `@modelcontextprotocol/server-filesystem` npm, `mcp-server-fetch` pypi, `modelcontextprotocol/servers` GitHub).
4. README poblado con problem + demo + install + sponsor note.
5. `LICENSE` MIT.
6. `CONTRIBUTING.md` boilerplate.
7. `.gitignore`.
8. Demo command screenshot/GIF (defer to Luis post-build).

## Demo plan

```bash
# Install
pip install --user mcp-onboarder
# o vía pipx (recommended)
pipx install mcp-onboarder

# Use
mcp-onboarder https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem

# Expected output:
# ▶ Fetching source...
# ▶ Parsing manifest...
# ▶ Auditing risk...
#
# === Install command ===
# npx -y @modelcontextprotocol/server-filesystem /path/to/allowed-dir
#
# === Client configs ===
# # claude_desktop_config.json
# { "mcpServers": { "filesystem": { ... } } }
#
# === Risk audit (score: 45/100, MED) ===
# - filesystem write detected (+20)
# - subprocess spawn detected (+20)
# - high popularity, official Anthropic source (-10)
# - no auth required (0)
# RECOMMENDATIONS: scope --allowed-dirs to specific paths, never $HOME root.
#
# === Tools inventory ===
# - read_file, write_file, list_directory, create_directory, ...
```

## Monetization tiers

| Tier | Price | Audience | Features |
|---|---|---|---|
| **OSS Free** | $0 (MIT) | Builders solo / hobbyist | CLI + 3 client formats + heuristic audit + tool inventory. GitHub stars surface. |
| **Premium SaaS** | $9-19/mo | Teams 2-10 builders | Team whitelist registry (shared trusted MCPs) + CI/CD GitHub Action pre-merge audit + audit history retained 90d + ToS-change email alerts (cross-link Phase 06 legal-watch). |
| **Enterprise** | $99-299/mo | Companies 10+ + compliance | SSO + role-based whitelist enforcement + compliance reports (SOC2-style export) + on-prem self-hosted gateway option + custom risk policy DSL + dedicated support. |

## Distribution playbook

1. **Day 0 ship:** GitHub public `PenguinAlleyApps/mcp-onboarder`, PyPI publish, README con problema + 1 GIF demo.
2. **Day 1:** post a r/ClaudeAI + LinkedIn Luis personal + X PenguinAlley (cuando active).
3. **Day 3:** HN submission "Show HN: mcp-onboarder — cross-platform MCP install + audit CLI".
4. **Day 7:** Reach out a HarmonicSecurity (claudit-sec) sugiriendo complementariedad pre+post install.
5. **Day 14:** Premium SaaS landing page con waitlist (defer Stripe wire hasta 50 emails).

## Success criteria (30 días)

1. ≥50 GitHub stars.
2. ≥5 PRs/issues externas (community signal).
3. ≥100 PyPI downloads/week.
4. ≥1 inbound enterprise inquiry (validates Premium/Enterprise tier).

## Risk gates

- **G1:** Smithery / Apigene release competing free CLI → defer to v0.2 con differentiated feature (LATAM bilingual UI, on-prem option, etc).
- **G2:** Heuristic risk audit produces false positives → add `--no-audit` flag + curated allowlist mid-term.
- **G3:** MCP protocol spec changes pre-publish → re-spike parser against `modelcontextprotocol/servers` upstream.
- **G4:** Legal Phase 06 surface ToS-change Anthropic re: MCPs → audit policy alignment + update marketing.

## Cross-references

- `llm-wiki/wiki/analyses/vertical-devtools-2026-05-12.md` — Phase 03 source brief.
- `templates/penguin-repo/` — scaffold.
- `references/tools-feeds.md` — MCP monitoring upstream (Phase 07).
- `references/legal-watchlist.md` — Anthropic policies feed (Phase 06).
- `roadmap/phases/02-opensource.md` — ship policy.
- `runs/opensource-ship/2026-05-12-mcp-onboarder/` — workspace.
