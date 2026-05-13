# mcp-onboarder

> Cross-platform CLI: parse any MCP server URL → emit ready-to-paste client config + pre-install risk audit + tool inventory. Built for Claude Code, Claude Desktop, Cursor.

**Status:** alpha (v0.1) · **License:** MIT · **Author:** [Luis Gerardo Rodriguez](https://github.com/GerardoRdz96) ([PenguinAlley](https://github.com/PenguinAlleyApps))

## What this solves

El ecosistema MCP en 2026 tiene **13k+ servers fragmentados en 6+ registries** (Glama, mcp.so, mcpservers.org, Smithery, awesome-mcp-servers, repos sueltos). Cada server llega con install ceremony distinto (`npx`, `pip`, `docker`, custom), JSON paste manual por cliente (Claude Code / Claude Desktop / Cursor), y **Anthropic explícitamente disclaims responsibility** por security audit de MCPs. Resultado: developers gastan tiempo copiando configs y, peor, instalan servers maliciosos sin notarlo.

`mcp-onboarder` cierra el gap: 1 comando → install command + ready-to-paste config + risk audit + recommendations.

## Demo

```bash
$ mcp-onboarder https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem

# mcp-onboarder · npm:@modelcontextprotocol/server-filesystem

**Description:** MCP server for filesystem access

## Install command
```bash
npx -y @modelcontextprotocol/server-filesystem
```

## Client config (claude-code)
```json
{
  "mcpServers": {
    "server-filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
  }
}
```

## Risk audit · score 20/100 · band LOW
- fs_write keyword detected (+20)

**Recommendations:**
- Scope --allowed-dirs to specific paths; never project root or $HOME.
```

## Install

```bash
pipx install mcp-onboarder   # recommended (isolated env)
# or
pip install --user mcp-onboarder
```

Requirements:
- Python ≥3.10
- stdlib only (no external deps)

## Usage

```bash
mcp-onboarder <url> [--client claude-code|claude-desktop|cursor] [--no-audit] [--json]
```

Supported URL formats:
- `https://github.com/<owner>/<repo>`
- `https://www.npmjs.com/package/<name>` or `<scope/name>`
- `https://pypi.org/project/<name>`
- `https://smithery.ai/server/<slug>`

Exit codes:
- `0` — success, LOW or MED risk
- `1` — fetch / HTTP error
- `2` — unsupported URL format
- `3` — success but HIGH risk band detected (CI-friendly fail-fast)

## How it works

- **Fetcher** uses stdlib `urllib` (no extra deps) to pull manifest from source-specific API.
- **Parser** extracts install command via curated regex set (npx, pip, pipx, docker) + scans README for env vars matching sensitive patterns.
- **Risk auditor** is heuristic v0.1: keywords for fs write, subprocess exec, network egress, shell invocation, plus star-count signal. Returns score 0-100 + band LOW/MED/HIGH + recommendations.
- **Emitter** renders Markdown or JSON, configures `mcpServers` block per target client.

## Scope (out of scope explicit)

What this **does not** do:
- Auto-install (no `pip install` invocation — you stay in control).
- Sandboxed execution.
- Cloud gateway proxy.
- LLM-judge audit (heuristic v0.1; LLM tier on roadmap).
- Team whitelist registry (Premium SaaS feature).
- CI/CD GitHub Action (Premium SaaS feature).
- Compliance report SOC2 (Enterprise tier).

## Tiered offering

| Tier | Price | Audience | Features |
|---|---|---|---|
| **OSS (this repo)** | $0 MIT | Solo builders, hobbyist | CLI + 3 client formats + heuristic audit + tool inventory |
| **Premium SaaS** | $9-19/mo | Teams 2-10 | Team whitelist registry + CI/CD GitHub Action + audit history 90d + ToS-change alerts |
| **Enterprise** | $99-299/mo | Companies 10+ + compliance | SSO + role-based whitelist enforcement + compliance reports + on-prem self-hosted gateway |

Premium / Enterprise: waitlist via penguinalley.com (coming soon).

## Roadmap (v0.2+)

- LLM-judge audit fallback when heuristic underdetermines.
- Smithery API proper (current v0.1 scrapes HTML).
- npm tarball deep inspection (download + grep deps).
- pip-audit cross-link (CVE check for python servers).
- Multi-server batch mode (`mcp-onboarder --batch <file.txt>`).
- Output diff vs existing `mcp.json` (additive merge mode).
- Cross-platform installer test (Windows ARM, Linux musl).

## Contributing

Issues and PRs welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Security

Report vulnerabilities via private GitHub security advisory. Do NOT open public issues for security bugs.

## License

MIT — see [`LICENSE`](./LICENSE).

## Related

- [PenguinAlley](https://github.com/PenguinAlleyApps) — more open AI builder tooling.
- [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers) — official MCP server reference.
- [`HarmonicSecurity/claudit-sec`](https://github.com/HarmonicSecurity/claudit-sec) — POST-install audit (macOS). Complementary tool.
