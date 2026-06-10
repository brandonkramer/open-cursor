#!/usr/bin/env python3
"""
Compare the extracted protobuf definitions from the live cursor-agent against
the local .proto files in proto/agent/v1/ and proto/aiserver/v1/.

This script:
1. Extracts types from the cursor-agent bundle (or reads a pre-extracted JSON)
2. Parses the local .proto files
3. Reports differences: missing types, added fields, removed fields, type changes

Usage:
    python3 scripts/diff-protos.py [--extracted extracted.json]

If --extracted is not provided, the script will extract from the cursor-agent bundle.
"""

import re
import json
import os
import sys
import glob

# Import extractor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_protos import find_agent_bundle, extract_message_fields, extract_enum_values


LOCAL_PROTO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "shared",
    "protocol",
    "proto"
)

SCALAR_TYPES = {
    "double": "scalar",
    "float": "scalar",
    "int32": "scalar",
    "int64": "scalar",
    "uint32": "scalar",
    "uint64": "scalar",
    "sint32": "scalar",
    "sint64": "scalar",
    "fixed32": "scalar",
    "fixed64": "scalar",
    "sfixed32": "scalar",
    "sfixed64": "scalar",
    "bool": "scalar",
    "string": "scalar",
    "bytes": "scalar",
}


def extract_brace_block(text, start_pos):
    """Extract content inside braces starting from the opening brace at start_pos.
    Returns (content, end_pos) tuple. Handles nested braces correctly.
    """
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


def parse_proto_content(content):
    """Parse .proto content, returns (package, messages, enums)."""
    pkg_match = re.search(r'package\s+([\w.]+)\s*;', content)
    pkg = pkg_match.group(1) if pkg_match else ""

    # Remove comments first
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    messages = {}  # full_name -> fields
    enums = {}     # full_name -> values

    # Find top-level blocks: message, enum, oneof, etc.
    top_pattern = re.compile(
        r'(?:public\s+)?(message|enum)\s+(\w+)\s*(\{|extends)'
    )

    def parse_fields(body):
        """Parse field definitions from a message body, handling nested oneofs."""
        fields = []

        # Extract oneof blocks first
        oneof_idx = 0
        while True:
            om = re.search(r'oneof\s+(\w+)\s*\{', body[oneof_idx:])
            if not om:
                break
            ostart = oneof_idx + om.start()
            oneof_name = om.group(1)
            oneof_body, oend = extract_brace_block(body, ostart + len(om.group(0)) - 1)
            # Parse fields inside oneof
            of_pattern = r'(?:optional\s+|repeated\s+)?(\w+(?:\.\w+)*)\s+(\w+)\s*=\s*(\d+)'
            for ofm in re.finditer(of_pattern, oneof_body):
                fields.append({
                    "no": int(ofm.group(3)),
                    "name": ofm.group(2),
                    "type": ofm.group(1),
                    "kind": "optional",
                    "oneof": oneof_name,
                })
            oneof_idx = oend

        # Parse regular fields (outside oneof)
        # Remove consumed oneof blocks
        remaining = re.sub(r'oneof\s+\w+\s*\{[^}]*\}', '', body)
        # Now parse remaining fields
        for fm in re.finditer(
            r'(?:repeated\s+|optional\s+|map<[^>]+>\s+)?(\w+(?:\.\w+)*)\s+(\w+)\s*=\s*(\d+)',
            remaining
        ):
            prefix = (content[fm.start():fm.start(1)].strip()
                      if fm.start() > 0 else "")
            field_no = int(fm.group(3))
            # Skip if already found via oneof
            if any(f["no"] == field_no for f in fields):
                continue
            fields.append({
                "no": field_no,
                "name": fm.group(2),
                "type": fm.group(1),
                "kind": "optional",  # default in proto3
            })

        fields.sort(key=lambda x: x["no"])
        return fields

    pos = 0
    while pos < len(content):
        tm = top_pattern.search(content, pos)
        if not tm:
            break

        kind = tm.group(1)
        name = tm.group(2)
        brace_start = content.index('{', tm.start())
        body, end = extract_brace_block(content, brace_start)
        full_name = f"{pkg}.{name}" if pkg else name

        if kind == "message":
            messages[full_name] = {
                "type": "message",
                "fields": parse_fields(body),
            }
        elif kind == "enum":
            values = []
            for vm in re.finditer(r'(\w+)\s*=\s*(-?\d+)', body):
                values.append({
                    "no": int(vm.group(2)),
                    "name": vm.group(1),
                })
            enums[full_name] = {
                "type": "enum",
                "values": values,
            }

        pos = end

    return pkg, messages, enums


def parse_local_protos():
    """Parse all .proto files in the local proto directory."""
    types = {}
    
    proto_files = []
    for root, dirs, files in os.walk(LOCAL_PROTO_DIR):
        for f in files:
            if f.endswith('.proto'):
                proto_files.append(os.path.join(root, f))
    
    for filepath in proto_files:
        relpath = os.path.relpath(filepath, LOCAL_PROTO_DIR)
        with open(filepath, 'r') as f:
            content = f.read()
        
        pkg, messages, enums = parse_proto_content(content)
        
        for name, info in messages.items():
            info["source_file"] = relpath
            types[name] = info
        for name, info in enums.items():
            info["source_file"] = relpath
            types[name] = info
    
    return types


def extract_live_types(bundle_path=None):
    """Extract types from the cursor-agent bundle."""
    if bundle_path is None:
        bundle_path = find_agent_bundle()
    
    print(f"Reading bundle: {bundle_path}", file=sys.stderr)
    with open(bundle_path, 'r', errors='ignore') as f:
        content = f.read()
    
    types = {}
    
    # Find all type names
    pattern = r'typeName="((?:agent|aiserver)\.v1\.[^"]+)"'
    for m in re.finditer(pattern, content):
        full_name = m.group(1)
        types[full_name] = {"found": True}
    
    # Extract fields for each type
    for name in list(types.keys()):
        fields = extract_message_fields(content, name)
        if fields:
            types[name] = {"type": "message", "fields": fields}
            continue
        values = extract_enum_values(content, name)
        if values:
            types[name] = {"type": "enum", "values": values}
    
    return types


def compare_types(live_types, local_types):
    """Compare live vs local types and report differences."""
    diffs = {
        "only_in_live": [],
        "only_in_local": [],
        "field_diffs": [],
    }
    
    live_names = set(live_types.keys())
    local_names = set(local_types.keys())
    
    # Types only in live
    for name in sorted(live_names - local_names):
        info = live_types[name]
        if info.get("found"):
            diffs["only_in_live"].append(name)
        else:
            diffs["only_in_live"].append(f"{name} (no fields extracted)")
    
    # Types only in local (stale)
    for name in sorted(local_names - live_names):
        info = local_types[name]
        source = info.get("source_file", "?")
        diffs["only_in_local"].append(f"{name} ({source})")
    
    # Field-level comparison for types that exist in both
    for name in sorted(live_names & local_names):
        live_info = live_types[name]
        local_info = local_types[name]
        
        if not isinstance(live_info, dict) or not isinstance(local_info, dict):
            continue
        
        # Skip 'found' entries (matched by pattern but no fields extracted)
        if live_info.get("found"):
            continue
        
        if live_info.get("type") != local_info.get("type"):
            diffs["field_diffs"].append({
                "type": name,
                "diff": f"Type mismatch: live={live_info.get('type')} local={local_info.get('type')}"
            })
            continue
        
        if live_info.get("type") == "enum":
            # Compare enum values
            lv = {v["name"]: v["no"] for v in (live_info.get("values") or [])}
            lc = {v["name"]: v["no"] for v in (local_info.get("values") or [])}
            
            added = set(lv.keys()) - set(lc.keys())
            removed = set(lc.keys()) - set(lv.keys())
            
            if added:
                diffs["field_diffs"].append({
                    "type": name,
                    "diff": f"Added enum values: {', '.join(sorted(added))}"
                })
            if removed:
                diffs["field_diffs"].append({
                    "type": name,
                    "diff": f"Removed enum values: {', '.join(sorted(removed))}"
                })
            continue
        
        if live_info.get("type") != "message":
            continue
        
        live_fields = {f["no"]: f for f in (live_info.get("fields") or [])}
        local_fields = {f["no"]: f for f in (local_info.get("fields") or [])}
        
        live_nos = set(live_fields.keys())
        local_nos = set(local_fields.keys())
        
        added = live_nos - local_nos
        removed = local_nos - live_nos
        common = live_nos & local_nos
        
        changes = []
        for no in sorted(added):
            f = live_fields[no]
            changes.append(f"+ field {no}: {f['name']} ({f['kind']})")
        
        for no in sorted(removed):
            f = local_fields[no]
            changes.append(f"- field {no}: {f['name']}")
        
        # Check for type/name changes
        for no in sorted(common):
            lf = live_fields[no]
            lc = local_fields[no]
            if lf["name"] != lc["name"] or lf["kind"] != lc.get("kind"):
                changes.append(f"~ field {no}: local={lc['name']}({lc.get('kind','?')}) → live={lf['name']}({lf['kind']})")
        
        if changes:
            diffs["field_diffs"].append({
                "type": name,
                "diff": changes,
            })
    
    return diffs


def main():
    # Parse local protos
    print("Parsing local proto files...", file=sys.stderr)
    local_types = parse_local_protos()
    print(f"  Found {len(local_types)} types in local protos", file=sys.stderr)
    
    # Extract from live bundle
    print("Extracting from cursor-agent bundle...", file=sys.stderr)
    live_types = extract_live_types()
    extracted_count = sum(
        1 for v in live_types.values()
        if isinstance(v, dict) and "fields" in v
    )
    enum_count = sum(
        1 for v in live_types.values()
        if isinstance(v, dict) and v.get("type") == "enum"
    )
    print(f"  Found {extracted_count} message types + {enum_count} enums", file=sys.stderr)
    
    # Compare
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)
    
    diffs = compare_types(live_types, local_types)
    
    print(f"\n--- Types only in cursor-agent (live) ---")
    print(f"  Count: {len(diffs['only_in_live'])}")
    for name in diffs['only_in_live'][:30]:
        print(f"  + {name}")
    if len(diffs['only_in_live']) > 30:
        print(f"  ... and {len(diffs['only_in_live']) - 30} more")
    
    print(f"\n--- Types only in local protos (may be stale/renamed) ---")
    print(f"  Count: {len(diffs['only_in_local'])}")
    for name in diffs['only_in_local'][:10]:
        print(f"  - {name}")
    if len(diffs['only_in_local']) > 10:
        print(f"  ... and {len(diffs['only_in_local']) - 10} more")
    
    print(f"\n--- Field-level differences ---")
    print(f"  Count: {len(diffs['field_diffs'])}")
    for entry in diffs['field_diffs'][:30]:
        print(f"\n  {entry['type']}:")
        diff_lines = entry['diff']
        if isinstance(diff_lines, list):
            for line in diff_lines:
                print(f"    {line}")
        else:
            print(f"    {diff_lines}")
    if len(diffs['field_diffs']) > 30:
        print(f"  ... and {len(diffs['field_diffs']) - 30} more")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Live types:         {len(live_types)}")
    print(f"  Local types:        {len(local_types)}")
    print(f"  Only in live:       {len(diffs['only_in_live'])}")
    print(f"  Only in local:      {len(diffs['only_in_local'])}")
    print(f"  Field differences:  {len(diffs['field_diffs'])}")


if __name__ == "__main__":
    main()
