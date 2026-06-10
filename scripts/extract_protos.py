#!/usr/bin/env python3
"""
Extract protobuf message and enum type definitions from the cursor-agent CLI bundle.

The cursor-agent CLI bundles @bufbuild/protobuf-compiled TypeScript which contains
field descriptor arrays embedded in the minified JavaScript. This script extracts
those definitions and outputs them in a structured format.

Usage:
    python3 scripts/extract-protos.py [--agent-path PATH]

The agent path defaults to ~/.local/share/cursor-agent/versions/*/index.js
(or the latest version if multiple exist).
"""

import re
import json
import os
import sys
import glob

# Scalar type mapping for @bufbuild/protobuf
SCALAR_TYPES = {
    0: "double",
    1: "float",
    2: "int64",
    3: "uint64",
    4: "int32",
    5: "fixed64",
    6: "fixed32",
    7: "bool",
    8: "string",
    9: "group",
    10: "message",
    11: "bytes",
    12: "uint32",
    13: "enum",
    14: "sfixed32",
    15: "sfixed64",
    16: "sint32",
    17: "sint64",
}

# Reverse: our mapping from the fields JSON
FIELD_KIND_MAP = {
    5: "int32",
    8: "bool",
    9: "string",
    12: "bytes",
    13: "uint32",
    4: "uint64",
    3: "int64",
    2: "double",
    1: "float",
    7: "sfixed32",
}


def find_agent_bundle():
    """Find the cursor-agent index.js bundle."""
    home = os.path.expanduser("~")
    paths = sorted(glob.glob(
        f"{home}/.local/share/cursor-agent/versions/*/index.js"
    ))
    if not paths:
        print("ERROR: No cursor-agent bundle found at ~/.local/share/cursor-agent/versions/*/index.js",
              file=sys.stderr)
        print("Make sure cursor-agent is installed: curl -fsS https://cursor.com/install | bash",
              file=sys.stderr)
        sys.exit(1)
    return paths[-1]  # Latest version


def extract_type_names(content, package="agent.v1"):
    """Extract all type names registered for the given package."""
    pattern = rf'typeName="{re.escape(package)}\.([^"]+)"'
    names = set()
    for m in re.finditer(pattern, content):
        names.add(m.group(1))
    return sorted(names)


def extract_message_fields(content, type_name):
    """Extract fields for a message type by finding its newFieldList definition."""
    full_name = type_name if "." in type_name else f"agent.v1.{type_name}"
    idx = content.find(full_name)
    if idx == -1:
        return None

    search_area = content[idx:idx+20000]
    field_match = re.search(
        r'newFieldList\(\(\(\)=>\[(.*?)\]\)\)', search_area, re.DOTALL
    )
    if not field_match:
        return None

    fields_str = field_match.group(1)

    # Match each complete field entry: {no:N,name:"...",kind:"...",...}
    # The entry ends at the first unquoted '}'
    fields = []
    for raw in re.finditer(r'\{[^}]*\}', fields_str):
        entry_text = raw.group()

        # Extract basic field info
        base = re.search(r'no:(\d+),name:"([^"]+)",kind:"([^"]+)"', entry_text)
        if not base:
            continue

        f_no = int(base.group(1))
        f_name = base.group(2)
        f_kind = base.group(3)

        entry = {
            "no": f_no,
            "name": f_name,
            "kind": f_kind,
        }

        # Extract T value (can be int, undefined, or dotted ref like o.InteractionUpdate)
        t_match = re.search(r',T:([^,}]+)', entry_text)
        if t_match:
            t_val = t_match.group(1).strip()
            if t_val != "undefined":
                # For message/enum/map types, T is a type reference
                # For scalar types, T is a numeric field kind (string=9, int32=13, etc.)
                entry["T"] = t_val
                if f_kind == "scalar":
                    try:
                        scalar_val = int(t_val)
                        entry["type"] = FIELD_KIND_MAP.get(scalar_val, t_val)
                    except ValueError:
                        entry["type"] = t_val

        # Extract oneof
        oneof_match = re.search(r',oneof:"([^"]+)"', entry_text)
        if oneof_match:
            entry["oneof"] = oneof_match.group(1)

        # Extract repeated
        if ",repeated:!0" in entry_text:
            entry["repeated"] = True

        # Extract optional
        if ",opt:!0" in entry_text:
            entry["opt"] = True

        fields.append(entry)

    return fields if fields else None


def extract_enum_values(content, type_name):
    """Extract values for an enum type."""
    full_name = type_name if "." in type_name else f"agent.v1.{type_name}"
    idx = content.find(full_name)
    if idx == -1:
        return None

    search_area = content[idx:idx+5000]
    enum_match = re.search(
        r'setEnumType\([^,]+,"[^"]+",\[(.*?)\]\)', search_area, re.DOTALL
    )
    if not enum_match:
        return None

    values_str = enum_match.group(1)
    val_pattern = r'\{no:(\d+),name:"([^"]+)"\}'
    values = []
    for m in re.finditer(val_pattern, values_str):
        values.append({
            "no": int(m.group(1)),
            "name": m.group(2),
        })
    return values if values else None


def main():
    bundle_path = find_agent_bundle()
    print(f"Reading bundle: {bundle_path}", file=sys.stderr)
    
    with open(bundle_path, 'r', errors='ignore') as f:
        content = f.read()
    
    print(f"Bundle size: {len(content):,} bytes", file=sys.stderr)
    
    # Extract all type names for agent.v1
    type_names = extract_type_names(content, "agent.v1")
    print(f"Found {len(type_names)} agent.v1 types", file=sys.stderr)
    
    aiserver_types = extract_type_names(content, "aiserver.v1")
    print(f"Found {len(aiserver_types)} aiserver.v1 types", file=sys.stderr)
    
    # Extract message fields and enum values for each type
    result = {
        "agent": {},
        "aiserver": {},
    }
    
    for name in type_names:
        fields = extract_message_fields(content, f"agent.v1.{name}")
        if fields:
            result["agent"][name] = {"type": "message", "fields": fields}
            continue
        values = extract_enum_values(content, f"agent.v1.{name}")
        if values:
            result["agent"][name] = {"type": "enum", "values": values}
    
    for name in aiserver_types:
        fields = extract_message_fields(content, f"aiserver.v1.{name}")
        if fields:
            result["aiserver"][name] = {"type": "message", "fields": fields}
            continue
        values = extract_enum_values(content, f"aiserver.v1.{name}")
        if values:
            result["aiserver"][name] = {"type": "enum", "values": values}
    
    # Output as JSON
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
