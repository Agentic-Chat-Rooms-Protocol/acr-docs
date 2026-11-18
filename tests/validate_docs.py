#!/usr/bin/env python3
"""Validation suite for acr-docs specifications, endpoint vectors, and markdown links."""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VECTORS_FILE = ROOT / "docs" / "specs" / "fixtures" / "endpoint-vectors.json"

CANONICAL_11_TOOLS = [
    "acr_create_room",
    "acr_list_workflows",
    "acr_get_workflow",
    "acr_configure_workflow",
    "acr_get_workflow_status",
    "acr_list_rooms",
    "acr_room_status",
    "acr_room_ledger_tail",
    "acr_room_send",
    "acr_room_consensus",
    "acr_container_status",
]

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
ALLOWLISTED_ORIGINS = {"https://agentchatrooms.dev", "https://www.agentchatrooms.dev"}
PUBLIC_ROUTES = {"/health", "/healthz", "/api/v1/health", "/api/v1/auth/challenge", "/api/v1/auth/verify"}


def validate_local(raw: str) -> tuple[bool, str | None]:
    if not raw or raw.strip() != raw or "://" not in raw or "#" in raw or "?" in raw:
        return False, None
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme != "http" or parsed.username is not None or parsed.password is not None:
        return False, None
    if parsed.query or parsed.fragment:
        return False, None
    if parsed.path not in ("", "/"):
        return False, None
    netloc = parsed.netloc
    if not netloc or "@" in netloc or netloc.endswith(":"):
        return False, None
    host = parsed.hostname
    if not host:
        return False, None
    if host == "localhost":
        pinned = "127.0.0.1"
    elif host in ("127.0.0.1", "::1"):
        pinned = host
    else:
        return False, None
    # Verify exact ASCII digit port when present
    try:
        parsed_port = parsed.port
    except ValueError:
        return False, None
    if parsed_port is not None:
        port_part = netloc.rsplit(":", 1)[1]
        if not (port_part.isascii() and port_part.isdigit()):
            return False, None
        port = int(port_part)
    else:
        port = 20443
    if port < 1024 or port > 65535:
        return False, None
    if ":" in pinned:
        return True, f"http://[{pinned}]:{port}"
    return True, f"http://{pinned}:{port}"


def validate_remote(raw: str) -> bool:
    if not raw or raw.strip() != raw or raw.startswith("//") or "#" in raw or "?" in raw:
        return False
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None:
        return False
    if not parsed.netloc or "@" in parsed.netloc or parsed.netloc.endswith(":") or parsed.query or parsed.fragment:
        return False
    if not parsed.hostname or parsed.hostname.lower() != "mcp.agentchatrooms.dev":
        return False
    host_only = parsed.netloc.split(":")[0]
    if host_only.lower() != "mcp.agentchatrooms.dev":
        return False
    try:
        if parsed.port not in (None, 443):
            return False
    except ValueError:
        return False
    if parsed.path != "/mcp":
        return False
    return True


def resolve_mode(override: str, entitlement: str, local_url: str) -> tuple[bool, str | None, str | None]:
    ok, normalized_local = validate_local(local_url)
    if not ok or normalized_local is None:
        return False, None, None
    if override == "local":
        return True, "local", normalized_local
    if override == "remote":
        return True, "remote", "https://mcp.agentchatrooms.dev/mcp"
    if override != "":
        return False, None, None
    if entitlement in ("pro", "enterprise"):
        return True, "remote", "https://mcp.agentchatrooms.dev/mcp"
    return True, "local", normalized_local


def simulate_daemon_guard(case: dict) -> tuple[int, bool, bool]:
    host_raw = case["host"].strip()
    if host_raw.startswith("[") and "]" in host_raw:
        host = host_raw[1 : host_raw.index("]")].lower()
    else:
        host = host_raw.split(":", 1)[0].lower()
    if host not in LOOPBACK_HOSTS:
        return 403, False, False

    require_auth = case.get("requireAuth", True)
    origin = case.get("origin", "")
    method = case["method"]
    path = case["path"]
    if origin:
        if origin not in ALLOWLISTED_ORIGINS:
            return 403, False, False
        if method == "OPTIONS":
            return 204, bool(case.get("enablePna", False)), False
    elif method == "OPTIONS" and not require_auth:
        return 403, False, False

    if require_auth and path not in PUBLIC_ROUTES and case.get("auth") != "valid":
        return 401, False, False

    if path == "/api/v1/config/security" and method in ("POST", "PUT") and origin:
        return 403, False, False

    return 200, False, True


def test_endpoint_vectors() -> None:
    vectors = json.loads(VECTORS_FILE.read_text(encoding="utf-8"))
    assert vectors["remoteUrl"] == "https://mcp.agentchatrooms.dev/mcp"
    assert vectors["defaultLocalUrl"] == "http://127.0.0.1:20443"
    assert vectors["oauth"]["scopesSupported"] == ["profile", "email"]
    assert vectors["oauth"]["forbiddenClientScopes"] == ["acr:rooms", "acr:cloud:pro"]

    for case in vectors["validateLocal"]:
        ok, norm = validate_local(case["input"])
        assert ok == case["valid"], f"validateLocal({case['name']}): expected {case['valid']}, got {ok}"
        if ok and "normalized" in case:
            assert norm == case["normalized"], f"validateLocal({case['name']}): expected {case['normalized']}, got {norm}"

    for case in vectors["validateRemote"]:
        ok = validate_remote(case["input"])
        assert ok == case["valid"], f"validateRemote({case['name']}): expected {case['valid']}, got {ok}"

    for case in vectors["resolveMode"]:
        ok, mode, url = resolve_mode(case["override"], case["entitlement"], case["localUrl"])
        if case["expectError"]:
            assert not ok, f"resolveMode({case['name']}): expected error"
        else:
            assert ok, f"resolveMode({case['name']}): unexpected error"
            assert mode == case["expectMode"], f"resolveMode({case['name']}): expected {case['expectMode']}, got {mode}"
            assert url == case["expectUrl"], f"resolveMode({case['name']}): expected {case['expectUrl']}, got {url}"

    assert len(vectors["daemonGuards"]) >= 18
    for case in vectors["daemonGuards"]:
        status, pna, reached = simulate_daemon_guard(case)
        assert status == case["expectStatus"], f"daemonGuards({case['name']}): expected {case['expectStatus']}, got {status}"
        assert reached == case["handlerReached"], f"daemonGuards({case['name']}): expected reached={case['handlerReached']}, got {reached}"
        if "expectPna" in case:
            assert pna == case["expectPna"], f"daemonGuards({case['name']}): expected pna={case['expectPna']}, got {pna}"


def test_specs_and_links() -> None:
    remote_mcp = (ROOT / "docs" / "specs" / "remote-mcp.md").read_text(encoding="utf-8")
    for tool in CANONICAL_11_TOOLS:
        assert tool in remote_mcp, f"remote-mcp.md missing tool {tool}"
    for term in [
        'view?: "summary"',
        '"full"',
        "execution_supported: false",
        "room_limit_reached",
        "workflow_conflict",
        "privacy@agentchatrooms.dev",
        "security@agentchatrooms.dev",
        "support@agentchatrooms.dev",
        '"profile", "email"',
        "subscription_required",
        "workflow-catalog.json",
    ]:
        assert term in remote_mcp, f"remote-mcp.md missing term: {term}"

    port_mapping = (ROOT / "docs" / "specs" / "port-mapping.md").read_text(encoding="utf-8")
    for term in ["20443", "20444", "20445", "20447", "acr-opsroom", "127.0.0.1", "OriginGuard", "HostGuard", "ACR_API_TOKEN", "/api/v1/auth/verify", "false"]:
        assert term in port_mapping, f"port-mapping.md missing term: {term}"
    assert "Access-Control-Allow-Origin: *" not in port_mapping

    resolution_doc = (ROOT / "docs" / "specs" / "mcp-endpoint-resolution.md").read_text(encoding="utf-8")
    for term in ["ValidateLocal", "ValidateRemote", "noRedirect", "NewHTTPClient", "NewStreamClient", "OUTCOME_UNKNOWN", "/api/v1/auth/verify"]:
        assert term in resolution_doc, f"mcp-endpoint-resolution.md missing term: {term}"

    # Verify zero forbidden legacy domains or wildcard CORS across markdown, HTML, and SVG assets
    check_text_files = list(ROOT.rglob("*.md")) + [ROOT / "video" / "index.html"] + list((ROOT / "assets").glob("*.svg"))
    for path in check_text_files:
        if ".git" in path.parts or ".claude" in path.parts:
            continue
        txt = path.read_text(encoding="utf-8")
        assert "vrillabs.com" not in txt.lower(), f"Forbidden legacy domain in {path.relative_to(ROOT)}"
        assert "acr.network" not in txt.lower(), f"Forbidden legacy domain in {path.relative_to(ROOT)}"
        if path.suffix == ".md":
            assert "Access-Control-Allow-Origin: *" not in txt, f"Wildcard CORS in {path.relative_to(ROOT)}"

    # Verify relative markdown links resolve across all markdown files
    link_re = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")
    for md in ROOT.rglob("*.md"):
        if ".git" in md.parts or ".claude" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        for target in link_re.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (md.parent / target).resolve()
            assert resolved.exists(), f"Broken link in {md.relative_to(ROOT)}: {target}"


def main() -> int:
    test_endpoint_vectors()
    test_specs_and_links()
    print("OK: validated endpoint-vectors.json, remote-mcp.md, port-mapping.md, mcp-endpoint-resolution.md, and doc links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
