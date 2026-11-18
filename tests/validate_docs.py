#!/usr/bin/env python3
"""Validation suite for acr-docs specifications, endpoint vectors, and markdown links."""

from __future__ import annotations

import ipaddress
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


def validate_local(raw: str) -> tuple[bool, str | None]:
    if not raw or "://" not in raw:
        return False, None
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme != "http" or parsed.username is not None or parsed.password is not None:
        return False, None
    if parsed.query or parsed.fragment or "?" in raw or "#" in raw:
        return False, None
    if parsed.path not in ("", "/"):
        return False, None
    netloc = parsed.netloc
    if "@" in netloc:
        return False, None
    host = parsed.hostname
    if not host:
        return False, None
    # Reject raw netloc tricks like decimal/hex/short IPv4 or IPv4-mapped IPv6
    if host == "localhost":
        pinned = "127.0.0.1"
    elif host in ("127.0.0.1", "::1"):
        pinned = host
    else:
        return False, None
    # Ensure raw host token matches exact literal (not e.g. 0x7f.0.0.1)
    port = 20443
    try:
        if parsed.port is not None:
            port = parsed.port
    except ValueError:
        return False, None
    if port < 1024 or port > 65535:
        return False, None
    if ":" in pinned:
        return True, f"http://[{pinned}]:{port}"
    return True, f"http://{pinned}:{port}"


def validate_remote(raw: str) -> bool:
    if not raw or raw.startswith("//"):
        return False
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None:
        return False
    if "@" in parsed.netloc or parsed.query or parsed.fragment or "?" in raw or "#" in raw:
        return False
    if not parsed.hostname or parsed.hostname.lower() != "mcp.agentchatrooms.dev":
        return False
    # Reject trailing dot in netloc
    host_only = parsed.netloc.split(":")[0]
    if host_only.lower() != "mcp.agentchatrooms.dev":
        return False
    try:
        if parsed.port not in (None, 443):
            return False
    except ValueError:
        return False
    # Exact escaped path /mcp
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


def test_endpoint_vectors() -> None:
    vectors = json.loads(VECTORS_FILE.read_text(encoding="utf-8"))
    assert vectors["remoteUrl"] == "https://mcp.agentchatrooms.dev/mcp"
    assert vectors["defaultLocalUrl"] == "http://127.0.0.1:20443"
    assert vectors["oauth"]["scopesSupported"] == ["profile", "email"]

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

    assert len(vectors["daemonGuards"]) >= 16


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
    for term in ["20443", "20444", "20445", "20447", "acr-opsroom", "127.0.0.1", "OriginGuard", "HostGuard", "ACR_API_TOKEN", "false"]:
        assert term in port_mapping, f"port-mapping.md missing term: {term}"
    assert "Access-Control-Allow-Origin: *" not in port_mapping

    resolution_doc = (ROOT / "docs" / "specs" / "mcp-endpoint-resolution.md").read_text(encoding="utf-8")
    for term in ["ValidateLocal", "ValidateRemote", "noRedirect", "NewHTTPClient", "NewStreamClient", "OUTCOME_UNKNOWN"]:
        assert term in resolution_doc, f"mcp-endpoint-resolution.md missing term: {term}"

    # Verify zero forbidden legacy domains or wildcard CORS recommendations across docs/ and SECURITY.md
    for md in list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md")):
        txt = md.read_text(encoding="utf-8")
        assert "vrillabs.com" not in txt.lower(), f"Forbidden legacy domain in {md.relative_to(ROOT)}"
        assert "acr.network" not in txt.lower(), f"Forbidden legacy domain in {md.relative_to(ROOT)}"
        assert "Access-Control-Allow-Origin: *" not in txt, f"Wildcard CORS in {md.relative_to(ROOT)}"

    # Verify relative markdown links resolve across README.md, changelog, and specs
    link_re = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")
    check_files = [ROOT / "README.md", ROOT / "docs" / "changelog.md"] + list((ROOT / "docs" / "specs").glob("*.md"))
    for md in check_files:
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
