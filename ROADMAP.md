# Roadmap — mcp-onboarder

> Living document. Auto-updated weekly por `.github/workflows/competitor-watch.yml`. Manual review monthly.
> Last sync: 2026-05-12

## North Star

**Cross-platform pre-install CLI: 1 comando MCP server URL → ready-to-paste client config + risk audit + tool inventory.** Closes the gap left by 6+ fragmented registries, 3 client config formats, and zero Anthropic audit.

## Versioning policy

- `v0.x` — alpha, breaking changes OK.
- `v1.x` — stable API, SemVer.
- Releases via `release-please` GitHub Actions.

## v0.1 (current, 2026-05-12) — Foundation

### Shipped
- Python CLI 274 LOC stdlib-only (urllib + json + re + argparse + dataclasses).
- 4 source fetchers: GitHub, npm, pypi, Smithery.
- Heuristic risk auditor: 7 axes + score 0-100 + band LOW/MED/HIGH.
- 3-client config emitter: Claude Code, Claude Desktop, Cursor.
- Exit codes CI-friendly: 0=ok, 1=fetch err, 2=bad URL, 3=HIGH risk.
- README + LICENSE MIT + CONTRIBUTING + .gitignore (PenguinAlley scaffold).

### Known gaps (v0.1 limitations)
- Smithery scrapes HTML (no public manifest API v0.1).
- Heuristic audit (no LLM judge v0.1).
- No team/multi-server batch mode.
- No diff merge against existing `mcp.json`.

## v0.2 — Next sprint (target 2 weeks: 2026-05-26)

Driven by 3 inputs:
1. User feedback (issues + PRs).
2. **Competitor gaps** (auto-tracked weekly).
3. North Star drift check.

### Planned
- [ ] LLM-judge audit fallback (Codex 2nd-opinion cuando heurística underdetermines).
- [ ] Smithery API proper (cuando expongan).
- [ ] npm tarball deep inspection (download + grep deps tree).
- [ ] Multi-server batch mode (`mcp-onboarder --batch <file.txt>`).
- [ ] Diff merge mode (`--merge` con existing `mcp.json`).

## v1.0 — Stable target (4-8 weeks)

### Definition
- API frozen post-batch + merge mode shipped.
- >=3 production users con PyPI download metrics >=100/wk.
- Test coverage >=80% (pytest + integration tests against 5 known MCPs).
- Docs complete: README + reference + tutorial bilingue es-en.

## Beyond v1.0 — Vision (3-6 months)

Premium SaaS tier launch:
- Team shared whitelist registry (curated trusted MCPs).
- CI/CD GitHub Action pre-merge audit.
- ToS-change alerting (cross-link Alyx legal-watch).
- Compliance reports SOC2-style (Enterprise tier).
- On-prem self-hosted gateway option.

## Competitive landscape (auto-updated weekly por competitor-watch)

| Competitor | Their strength | Gap they leave | Our coverage |
|---|---|---|---|
| HarmonicSecurity/claudit-sec | Post-install audit, single-cmd visibility | macOS-only, no pre-install path, no install gen | v0.1 cross-platform pre-install |
| Apigene gateway | One-click install via gateway | Vendor lock, proxy through their infra, no audit transparency | v0.1 transparent local audit, open source |
| Smithery CLI | Install from Smithery hub | Hub-only sources, no risk audit, no cross-client config | v0.1 4 source types + audit + 3 clients |
| awesome-mcp-servers | Curated list 86k stars | Static list, no install/audit tooling | Complementary; we onboard from their list |
| mcp.so / mcpservers.org | Search/discover catalogs | No install ceremony, no audit | User can paste URL from these catalogs into our CLI |

## Adaptation triggers

- **G1 Competitor closes pre-install audit gap (e.g. claudit-sec ships cross-platform pre-install):** evaluate within 7d. Options: (a) leap-frog con LLM-judge audit + multi-server batch (v0.2), (b) niche-down LATAM bilingual UI + Spanish-first docs, (c) merge complementary (cross-promote).
- **G2 MCP marketplace consolidates a 1 registry:** reframe scope to deep-audit + compliance reports (v1.0 enterprise tier emerges as primary).
- **G3 Anthropic ships native MCP install + audit in Claude Code CLI:** product redundant. Pivot to Cursor + GenericMCPClient tooling con cross-platform consolidacion.
- **G4 ToS / API deprecation (Anthropic/OpenAI/MCP spec change):** legal-watch alerts then patch within 48h.
- **G5 30d zero issues + 0 downloads:** archive con post-mortem.

## Monetization milestones

- [ ] **OSS Tier:** 500 GitHub stars en 30 dias.
- [ ] **OSS Tier:** >=100 PyPI downloads/sem.
- [ ] **Premium SaaS:** 50 cuentas en 90 dias = $450-950/mo MRR.
- [ ] **Premium SaaS:** primer paying customer.
- [ ] **Enterprise:** 3 logos en 180 dias = $300-900/mo MRR.
- [ ] **Enterprise:** primer enterprise inquiry.

## Release cadence

- Patches `v0.x.Y`: rolling.
- Minor `v0.X.0`: biweekly target.
- Major `vX.0.0`: quarterly max.

## Process commitments

- 30-day maintenance commitment.
- PR first response <=7 days.
- Security advisories <=48h.

## Cross-references

- `README.md` — que hace.
- `MVP-PLAN.md` — scope original (immutable).
- `.github/competitors.yml` — competitor watchlist config.
- `.github/workflows/competitor-watch.yml` — weekly auto-scan.
- `runs/competitor-watch/state.json` — scan state.
