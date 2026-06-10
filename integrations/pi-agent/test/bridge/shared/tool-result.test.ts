import assert from "node:assert/strict";
import test from "node:test";

import type { ToolResultMessage } from "@earendil-works/pi-ai";

import {
  toolResultDetailBoolean,
  toolResultToText,
  toolResultWasTruncated,
} from "../../../src/bridge/shared/tool-result.js";

function makeResult(overrides: Partial<ToolResultMessage> = {}): ToolResultMessage {
  return {
    role: "toolResult",
    toolCallId: "call-1",
    toolName: "bash",
    content: [{ type: "text", text: "output" }],
    isError: false,
    timestamp: Date.now(),
    ...overrides,
  };
}

test("toolResultToText extracts text content", () => {
  const result = makeResult({
    content: [
      { type: "text", text: "line1" },
      { type: "text", text: "line2" },
    ],
  });
  assert.equal(toolResultToText(result), "line1\nline2");
});

test("toolResultToText shows image placeholder", () => {
  const result = makeResult({
    content: [
      { type: "text", text: "description" },
      { type: "image", data: "base64...", mimeType: "image/png" },
    ],
  });
  assert.equal(toolResultToText(result), "description\n[image/png image]");
});

test("toolResultToText returns empty string for no content", () => {
  const result = makeResult({ content: [] });
  assert.equal(toolResultToText(result), "");
});

test("toolResultWasTruncated returns false when no details", () => {
  assert.equal(toolResultWasTruncated(makeResult({ details: undefined })), false);
});

test("toolResultWasTruncated returns true when truncated", () => {
  const result = makeResult({
    details: { truncation: { truncated: true, originalLines: 5000, outputLines: 2000 } },
  });
  assert.equal(toolResultWasTruncated(result), true);
});

test("toolResultWasTruncated returns false when not truncated", () => {
  const result = makeResult({
    details: { truncation: { truncated: false } },
  });
  assert.equal(toolResultWasTruncated(result), false);
});

test("toolResultWasTruncated returns false for malformed details", () => {
  const result = makeResult({
    details: "string",
  });
  assert.equal(toolResultWasTruncated(result), false);

  const nullDetails = makeResult({ details: null });
  assert.equal(toolResultWasTruncated(nullDetails), false);
});

test("toolResultDetailBoolean returns false when key missing", () => {
  assert.equal(toolResultDetailBoolean(makeResult({ details: {} }), "isReadonly"), false);
});

test("toolResultDetailBoolean returns actual boolean value", () => {
  const result = makeResult({ details: { isReadonly: true } });
  assert.equal(toolResultDetailBoolean(result, "isReadonly"), true);
});

test("toolResultDetailBoolean returns false for non-boolean values", () => {
  const result = makeResult({ details: { isReadonly: "yes" } });
  assert.equal(toolResultDetailBoolean(result, "isReadonly"), false);
});
