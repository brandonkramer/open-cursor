import assert from "node:assert/strict";
import test from "node:test";

import type { ToolResultMessage } from "@earendil-works/pi-ai";

import { LiveEventChannel } from "../../src/bridge/live-session.js";
import {
  rejectPendingForSession,
  requestToolExecution,
  resolveToolResult,
} from "../../src/bridge/tools/relay.js";

test("LiveEventChannel queues and delivers events", async () => {
  const ch = new LiveEventChannel("test-1");

  ch.push({ kind: "content", data: { kind: "text-delta", text: "Hello" } });
  ch.push({ kind: "content", data: { kind: "text-delta", text: " World" } });

  const e1 = await ch.next();
  assert.equal(e1?.kind, "content");
  if (e1?.kind === "content") {
    assert.equal(e1.data.text, "Hello");
  }

  const e2 = await ch.next();
  assert.equal(e2?.kind, "content");
  if (e2?.kind === "content") {
    assert.equal(e2.data.text, " World");
  }
});

test("LiveEventChannel returns null after markDone", async () => {
  const ch = new LiveEventChannel("test-done");
  ch.markDone();
  const event = await ch.next();
  assert.equal(event, null);
});

test("LiveEventChannel returns null for empty done channel", async () => {
  const ch = new LiveEventChannel("test-empty");
  ch.markDone();
  assert.equal(await ch.next(), null);
});

test("LiveEventChannel delivers queued events then null after done", async () => {
  const ch = new LiveEventChannel("test-queued-done");
  ch.push({ kind: "cursor-done" });
  ch.markDone();

  const event = await ch.next();
  assert.equal(event?.kind, "cursor-done");
  assert.equal(await ch.next(), null);
});

test("LiveEventChannel async event delivery", async () => {
  const ch = new LiveEventChannel("test-async");

  // Start consuming before pushing
  const promise = ch.next();

  // Give the promise time to register the waiter
  await new Promise((r) => setTimeout(r, 10));

  ch.push({ kind: "token-delta", tokens: 42 });

  const event = await promise;
  assert.equal(event?.kind, "token-delta");
  if (event?.kind === "token-delta") {
    assert.equal(event.tokens, 42);
  }
});

test("tool-bridge resolves pending requests", async () => {
  const ch = new LiveEventChannel("tb-test");

  const promise = requestToolExecution(ch, {
    toolCallId: "call-tb-1",
    cursorExecType: "shell",
    piToolName: "bash",
    piToolArgs: { command: "echo hi" },
  });

  // Wait for the channel to receive the exec request
  const chEvent = await ch.next();
  assert.equal(chEvent?.kind, "tool-exec-request");
  if (chEvent?.kind === "tool-exec-request") {
    assert.equal(chEvent.request.toolCallId, "call-tb-1");
  }

  // Resolve via tool-bridge
  const result: ToolResultMessage = {
    role: "toolResult",
    toolCallId: "call-tb-1",
    toolName: "bash",
    content: [{ type: "text", text: "hi" }],
    isError: false,
    timestamp: Date.now(),
  };

  const resolved = resolveToolResult(result);
  assert.equal(resolved, true);

  const output = await promise;
  assert.equal(output.toolName, "bash");
  assert.equal(output.content.length, 1);
});

test("rejectPendingForSession cleans up pending tools by session", async () => {
  const ch1 = new LiveEventChannel("reject-1");
  const ch2 = new LiveEventChannel("reject-2");

  const p1 = requestToolExecution(ch1, {
    toolCallId: "r1",
    cursorExecType: "read",
    piToolName: "read",
    piToolArgs: { path: "a.ts" },
  });

  const p2 = requestToolExecution(ch2, {
    toolCallId: "r2",
    cursorExecType: "shell",
    piToolName: "bash",
    piToolArgs: { command: "ls" },
  });

  // Consume channel events so the request doesn't block
  void ch1.next();
  void ch2.next();

  // Only reject session reject-1
  rejectPendingForSession("reject-1", "Test cleanup");

  // p1 should reject
  await assert.rejects(p1, /Test cleanup/);

  // p2 should still resolve normally
  const result2: ToolResultMessage = {
    role: "toolResult",
    toolCallId: "r2",
    toolName: "bash",
    content: [{ type: "text", text: "ok" }],
    isError: false,
    timestamp: Date.now(),
  };
  assert.equal(resolveToolResult(result2), true);
  const output2 = await p2;
  assert.equal(output2.toolName, "bash");
});

test("resolveToolResult returns false for unknown toolCallId", () => {
  const result: ToolResultMessage = {
    role: "toolResult",
    toolCallId: "unknown-id",
    toolName: "bash",
    content: [{ type: "text", text: "" }],
    isError: false,
    timestamp: Date.now(),
  };
  assert.equal(resolveToolResult(result), false);
});
