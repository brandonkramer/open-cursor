import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import type { ToolResultMessage } from "@earendil-works/pi-ai";

import {
  buildLsCommand,
  buildLsResultFromToolResult,
} from "../../../../src/bridge/tools/executors/ls.js";

function createToolResult(text: string): ToolResultMessage {
  return {
    role: "toolResult",
    toolCallId: "tool-1",
    toolName: "bash",
    content: [{ type: "text", text }],
    isError: false,
    timestamp: 0,
  };
}

test("buildLsCommand uses a simple ls command", () => {
  assert.equal(buildLsCommand("/tmp/pi-ls-snapshot-dir"), "ls -A1p -- '/tmp/pi-ls-snapshot-dir'");
});

test("buildLsResultFromToolResult parses ls stdout snapshot", () => {
  const stdout = fs.readFileSync(
    new URL("../../../fixtures/ls/basic.stdout.txt", import.meta.url),
    "utf8",
  );

  const result = buildLsResultFromToolResult(
    "/workspace/sample",
    "/cwd/ignored",
    createToolResult(stdout),
  );

  assert.equal(result.result.case, "success");
  const success = result.result.value;
  const root = success.directoryTreeRoot;

  assert.ok(root);
  assert.equal(root.absPath, "/workspace/sample");
  assert.equal(root.childrenWereProcessed, true);
  assert.equal(root.numFiles, 3);

  assert.deepEqual(
    root.childrenDirs.map((child) => child.absPath),
    ["/workspace/sample/docs", "/workspace/sample/nested space"],
  );

  assert.deepEqual(
    root.childrenFiles.map((child) => child.name),
    [".env", "alpha.ts", "z-last.md"],
  );
});
