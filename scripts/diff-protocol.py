#!/usr/bin/env python3
"""
diff-protocol.py — Compare protocol message oneof cases (live bundle vs .proto files).

This script finds protocol-level gaps that would cause runtime errors:
  - Unhandled InteractionQuery types (would crash)
  - Unhandled InteractionUpdate types (silently dropped)
  - New ExecServerMessage oneof cases (silently dropped)
  - New ExecClientMessage oneof cases
  - Changed AgentClientMessage oneof cases
  - New/removed AgentServerMessage cases

Usage:
  python3 scripts/diff-protocol.py
  python3 scripts/diff-protocol.py --proto-dir shared/protocol/proto

Exit code: 0 if match, 1 if gaps found
"""

import argparse
import json
import os
import re
import sys

# Add scripts dir to path for importing extract_protos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from extract_protos import find_agent_bundle, extract_message_fields


# Protocol message types to check — these are the top-level routing types
# that affect the vendor protocol layer (split-stream, interaction, exec)
PROTOCOL_TYPES = [
    # Agent-level message routing
    ("agent.v1.AgentServerMessage", "agent/v1/agent.proto", "message"),
    ("agent.v1.AgentClientMessage", "agent/v1/agent.proto", "message"),

    # Interaction types (affect interaction-conversion.ts)
    ("agent.v1.InteractionUpdate", "agent/v1/agent.proto", "message"),
    ("agent.v1.InteractionQuery", "agent/v1/agent.proto", "query"),
    ("agent.v1.InteractionResponse", "agent/v1/agent.proto", "result"),

    # Exec types (affect exec-controller.ts, resources.ts)
    ("agent.v1.ExecServerMessage", "agent/v1/exec.proto", "message"),
    ("agent.v1.ExecClientMessage", "agent/v1/exec.proto", "message"),
    ("agent.v1.ExecServerControlMessage", "agent/v1/exec.proto", "message"),
    ("agent.v1.ExecClientControlMessage", "agent/v1/exec.proto", "message"),

    # KV types (affect agent-kv/)
    ("agent.v1.KvServerMessage", "agent/v1/kv.proto", "message"),
    ("agent.v1.KvClientMessage", "agent/v1/kv.proto", "message"),
]


def snake_to_camel(snake: str) -> str:
    """Convert snake_case to camelCase."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def extract_brace_block(text, start_pos):
    """Extract content inside braces handling nesting."""
    if start_pos >= len(text) or text[start_pos] != '{':
        return "", start_pos + 1
    depth = 1
    pos = start_pos + 1
    while depth > 0 and pos < len(text):
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
        pos += 1
    return text[start_pos + 1:pos - 1], pos


def extract_oneofs_from_proto(content: str, type_name: str) -> dict:
    """Extract oneof field names from a .proto file for the given message type."""
    short_name = type_name.split(".")[-1]

    # Remove comments
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    # Find the message definition
    msg_pattern = rf'message\s+{re.escape(short_name)}\s*' + r'\{'
    m = re.search(msg_pattern, content)
    if not m:
        return {}

    brace_start = content.index('{', m.start())
    msg_body, _ = extract_brace_block(content, brace_start)

    oneofs = {}
    pos = 0
    while True:
        om = re.search(r'oneof\s+(\w+)\s*\{', msg_body[pos:])
        if not om:
            break
        ostart = pos + om.start()
        oneof_name = om.group(1)
        oneof_body, oend = extract_brace_block(
            msg_body, ostart + len(om.group(0)) - 1
        )

        fields = []
        for fm in re.finditer(
            r'(?:optional\s+|repeated\s+)?(\w+(?:\.\w+)*)\s+(\w+)\s*=\s*(\d+)',
            oneof_body,
        ):
            fields.append({
                "no": int(fm.group(3)),
                "name": fm.group(2),
            })

        oneofs[oneof_name] = fields
        pos = oend

    return oneofs


def get_live_oneof_map(content: str, type_name: str) -> dict:
    """Get fields grouped by oneof from live bundle."""
    fields = extract_message_fields(content, type_name)
    if not fields:
        return {}
    oneof_map = {}
    for f in fields:
        if "oneof" in f:
            oname = f["oneof"]
            if oname not in oneof_map:
                oneof_map[oname] = []
            oneof_map[oname].append(f)
    return oneof_map


def main():
    parser = argparse.ArgumentParser(description="Compare protocol oneof cases between live bundle and .proto files")
    parser.add_argument("--proto-dir", default="shared/protocol/proto",
                        help="Path to .proto files directory")
    args = parser.parse_args()

    # Resolve paths
    project_root = os.path.dirname(SCRIPT_DIR)
    proto_dir = os.path.join(project_root, args.proto_dir) if not os.path.isabs(args.proto_dir) else args.proto_dir

    # Load live bundle
    bundle_path = find_agent_bundle()
    if not bundle_path:
        print("ERROR: Could not find cursor-agent bundle.")
        sys.exit(1)

    with open(bundle_path, "r", errors="ignore") as f:
        bundle_content = f.read()

    has_gaps = False

    print("=" * 72)
    print("Protocol Layer Gap Analysis")
    print(f"Bundle: {bundle_path}")
    print(f"Protos: {proto_dir}")
    print("=" * 72)
    print()

    for type_name, proto_relpath, target_oneof in PROTOCOL_TYPES:
        short_name = type_name.split(".")[-1]

        # Get live oneof fields from bundle
        live_oneofs = get_live_oneof_map(bundle_content, type_name)
        live_fields = live_oneofs.get(target_oneof, [])
        live_snake = set(f["name"] for f in live_fields)

        # Get oneof fields from .proto file
        proto_path = os.path.join(proto_dir, proto_relpath)
        if not os.path.exists(proto_path):
            print(f"  SKIP {short_name}: {proto_path} not found")
            continue

        with open(proto_path, "r") as f:
            proto_content = f.read()

        proto_oneofs = extract_oneofs_from_proto(proto_content, type_name)
        proto_fields = proto_oneofs.get(target_oneof, [])
        proto_snake = set(f["name"] for f in proto_fields)

        missing = live_snake - proto_snake
        extra = proto_snake - live_snake

        if missing or extra:
            has_gaps = True
            severity = "🔴 CRASH RISK" if "Query" in short_name else "🟡 Protocol gap"
            print(f"\n  {severity}: {short_name} (oneof: '{target_oneof}')")
            print(f"  {'─' * 60}")
            if missing:
                print(f"  🔴 NEW (not in .proto):")
                for name in sorted(missing):
                    no = next((f["no"] for f in live_fields if f["name"] == name), "?")
                    print(f"     no:{no} {name}")
            if extra:
                print(f"  🟡 REMOVED (in .proto but not live):")
                for name in sorted(extra):
                    print(f"     no:{name}")
            print()
        else:
            print(f"  ✅ {short_name}: match ({len(live_fields)} cases)")

    print()
    print("─" * 72)
    if has_gaps:
        print("  🔴 GAPS FOUND — review and update vendor code / proto files")
        sys.exit(1)
    else:
        print("  ✅ All protocol message types match — no gaps")
        sys.exit(0)


if __name__ == "__main__":
    main()
