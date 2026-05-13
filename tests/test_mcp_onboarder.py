"""Unit tests for mcp_onboarder. Pytest; offline (no network).

Covers: detect_source, extract_install, extract_env_vars, audit_risk,
emit_client_config (shlex), render_text (no-audit variant), main exit codes.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

# Make sibling module importable when running `pytest` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mcp_onboarder as mo  # noqa: E402


# ---------- detect_source ----------

@pytest.mark.parametrize("url, expected_kind, owner, name", [
    ("https://github.com/foo/bar", "github", "foo", "bar"),
    ("https://github.com/foo/bar.git", "github", "foo", "bar"),
    ("https://www.npmjs.com/package/@scope/pkg", "npm", "", "@scope/pkg"),
    ("https://www.npmjs.com/package/simple-pkg", "npm", "", "simple-pkg"),
    ("https://pypi.org/project/anthropic", "pypi", "", "anthropic"),
    ("https://smithery.ai/server/example", "smithery", "", "example"),
])
def test_detect_source_valid(url, expected_kind, owner, name):
    src = mo.detect_source(url)
    assert src.kind == expected_kind
    assert src.owner == owner
    assert src.name == name


def test_detect_source_invalid():
    with pytest.raises(ValueError):
        mo.detect_source("https://example.com/not-supported")


# ---------- extract_install ----------

def test_extract_install_npx_scoped():
    text = "Install with `npx -y @anthropic/server-foo`"
    assert mo.extract_install(text) == "npx -y @anthropic/server-foo"


def test_extract_install_pip():
    text = "Use pip install --user my-package and then run."
    assert mo.extract_install(text) == "pip install --user my-package"


def test_extract_install_pipx():
    text = "Recommended: pipx install awesome-tool"
    assert mo.extract_install(text) == "pipx install awesome-tool"


def test_extract_install_none():
    assert mo.extract_install("nothing actionable here") is None


def test_extract_install_short_token_filtered():
    # 'in' alone should NOT match as a package — _PKG requires 3+ chars or scoped
    assert mo.extract_install("Type NPX in this terminal") is None


# ---------- extract_env_vars ----------

def test_extract_env_vars_sensitive():
    text = "Set API_KEY=xxx and ANTHROPIC_TOKEN=yyy before running."
    assert "API_KEY" in mo.extract_env_vars(text)
    assert "ANTHROPIC_TOKEN" in mo.extract_env_vars(text)


def test_extract_env_vars_no_match():
    assert mo.extract_env_vars("plain prose without env vars.") == []


# ---------- audit_risk ----------

def test_audit_risk_low_when_clean():
    m = mo.Manifest(readme_excerpt="Hello world, harmless documentation.", stars=200)
    a = mo.audit_risk(m)
    assert a.band == "LOW"
    assert a.score < 30


def test_audit_risk_flags_fs_write():
    m = mo.Manifest(readme_excerpt="Use writeFile to persist data to disk.", stars=200)
    a = mo.audit_risk(m)
    assert any("fs_write" in f for f in a.flags)


def test_audit_risk_stars_cap_when_serious():
    """Popularity cannot drop score >5 if a serious (+20) flag is present."""
    m = mo.Manifest(
        readme_excerpt="Calls child_process.spawn and writeFile to disk.",
        stars=50_000,
    )
    a = mo.audit_risk(m)
    # Should NOT see -10 popularity reduction; should see -5 cap
    assert any("(-5)" in f for f in a.flags), a.flags
    assert not any("(-10)" in f for f in a.flags)


# ---------- emit_client_config (shlex) ----------

def test_emit_client_config_quotes_preserved():
    """Cmd with quoted arg must keep the whole quoted string as one arg, not 3."""
    m = mo.Manifest(install_cmd='npx -y pkg --token "my secret"', package_name="pkg")
    out = mo.emit_client_config(m, "claude-code")
    block = json.loads(out)["mcpServers"]["pkg"]
    assert block["command"] == "npx"
    assert "my secret" in block["args"]  # quoted preserved as single arg


def test_emit_client_config_basic():
    m = mo.Manifest(install_cmd="npx -y pkg", package_name="pkg")
    out = mo.emit_client_config(m, "claude-desktop")
    data = json.loads(out)
    assert "mcpServers" in data
    assert data["mcpServers"]["pkg"]["command"] == "npx"
    assert data["mcpServers"]["pkg"]["args"] == ["-y", "pkg"]


def test_emit_client_config_env_block():
    m = mo.Manifest(
        install_cmd="npx -y pkg",
        package_name="pkg",
        env_vars=["API_TOKEN", "SECRET_KEY"],
    )
    out = mo.emit_client_config(m, "cursor")
    block = json.loads(out)["mcpServers"]["pkg"]
    assert "env" in block
    assert "API_TOKEN" in block["env"]


def test_emit_client_config_no_cmd():
    m = mo.Manifest(install_cmd=None, package_name=None)
    out = mo.emit_client_config(m, "claude-code")
    # Falls back to placeholder; ensure it does not crash and produces valid output
    assert "mcpServers" in out


def test_emit_client_config_refuses_malformed_quotes():
    """Codex re-review #1: unbalanced quotes must NOT silently emit a misleading config."""
    m = mo.Manifest(install_cmd='npx -y pkg --flag "unterminated', package_name="pkg")
    out = mo.emit_client_config(m, "claude-code")
    data = json.loads(out)
    assert "_error" in data
    assert "malformed" in data["_error"].lower()
    # MUST NOT contain a usable mcpServers block — that would be the bug
    assert "mcpServers" not in data


def test_npm_url_encoding_scoped():
    """Codex re-review #3: confirm urllib.parse.quote with safe='@' percent-encodes '/'."""
    import urllib.parse
    encoded = urllib.parse.quote("@scope/pkg", safe="@")
    assert encoded == "@scope%2Fpkg", f"got {encoded!r}"


# ---------- render_text ----------

def test_render_text_no_audit_omits_score():
    src = mo.Source(kind="npm", owner="", name="pkg", raw_url="https://example.com")
    m = mo.Manifest(install_cmd="npx -y pkg", package_name="pkg")
    out = mo.render_text(src, m, audit=None, client="claude-code")
    assert "Audit skipped" in out
    assert "score 0" not in out
    assert "band LOW" not in out


def test_render_text_includes_install_warning():
    src = mo.Source(kind="github", owner="o", name="r", raw_url="https://github.com/o/r")
    m = mo.Manifest(install_cmd="npx -y r", package_name="r")
    out = mo.render_text(src, m, audit=mo.RiskAudit(score=0, band="LOW"), client="claude-code")
    assert "WARNING" in out
    assert "Verify before running" in out


def test_render_text_with_audit():
    src = mo.Source(kind="npm", owner="", name="pkg", raw_url="https://example.com")
    m = mo.Manifest(install_cmd="npx -y pkg", package_name="pkg")
    audit = mo.RiskAudit(score=45, band="MED", flags=["fs_write detected"], recommendations=["Scope dirs"])
    out = mo.render_text(src, m, audit=audit, client="claude-code")
    assert "score 45" in out
    assert "band MED" in out
    assert "fs_write detected" in out
    assert "Scope dirs" in out


# ---------- main exit codes ----------

def test_main_bad_url_returns_2(capsys):
    rc = mo.main(["https://example.com/not-mcp"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unsupported" in err.lower()
