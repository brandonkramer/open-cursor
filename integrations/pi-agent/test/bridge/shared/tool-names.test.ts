import assert from "node:assert/strict";
import test from "node:test";

import {
  getDefaultPiToolName,
  inferCursorExecType,
} from "../../../src/bridge/shared/tool-names.js";

test("getDefaultPiToolName forward mapping", () => {
  assert.equal(getDefaultPiToolName("read"), "read");
  assert.equal(getDefaultPiToolName("write"), "write");
  assert.equal(getDefaultPiToolName("write-binary"), "bash");
  assert.equal(getDefaultPiToolName("shell"), "bash");
  assert.equal(getDefaultPiToolName("shell-stream"), "bash");
  assert.equal(getDefaultPiToolName("grep"), "bash");
  assert.equal(getDefaultPiToolName("ls"), "bash");
  assert.equal(getDefaultPiToolName("delete"), "bash");
});

test("inferCursorExecType direct tool mappings", () => {
  assert.equal(inferCursorExecType("read", { path: "a.ts" }), "read");
  assert.equal(inferCursorExecType("write", { path: "a.ts", content: "" }), "write");
  assert.equal(inferCursorExecType("edit", {}), undefined);
  assert.equal(inferCursorExecType("subagent", {}), undefined);
});

test("inferCursorExecType bash command heuristics", () => {
  assert.equal(inferCursorExecType("bash", { command: "echo hello" }), "shell");
  assert.equal(inferCursorExecType("bash", { command: "rg -n pattern src/" }), "grep");
  assert.equal(inferCursorExecType("bash", { command: "grep -r todo ." }), "grep");
  assert.equal(inferCursorExecType("bash", { command: "ls -A1p -- '/tmp'" }), "ls");
  assert.equal(inferCursorExecType("bash", { command: "find . -name '*.ts'" }), "ls");
  assert.equal(inferCursorExecType("bash", { command: "rm '/tmp/x.txt'" }), "delete");
  assert.equal(
    inferCursorExecType("bash", { command: "base64 -d > /tmp/img.png" }),
    "write-binary",
  );
});
