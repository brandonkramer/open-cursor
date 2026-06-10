import assert from "node:assert/strict";
import test from "node:test";

import { toCanonicalId, toCursorId } from "../../src/models/mapping.js";

test("toCursorId returns id as-is for unknown model", () => {
  assert.equal(toCursorId("unknown-model"), "unknown-model");
  assert.equal(toCursorId("unknown-model", "high"), "unknown-model");
});

test("toCursorId returns default variant without thinking level", () => {
  assert.equal(toCursorId("claude-sonnet-4-5"), "claude-4.5-sonnet");
  assert.equal(toCursorId("grok-4.3"), "grok-4.3");
  assert.equal(toCursorId("gpt-5.4"), "gpt-5.4-medium");
});

test("toCursorId maps thinking levels correctly", () => {
  // Sonnet 4.5 — binary thinking
  assert.equal(toCursorId("claude-sonnet-4-5", "low"), "claude-4.5-sonnet-thinking");
  assert.equal(toCursorId("claude-sonnet-4-5", "high"), "claude-4.5-sonnet-thinking");

  // Opus 4.8 — graduated thinking
  assert.equal(toCursorId("claude-opus-4-8", "low"), "claude-opus-4-8-thinking-medium");
  assert.equal(toCursorId("claude-opus-4-8", "high"), "claude-opus-4-8-thinking-high");
  assert.equal(toCursorId("claude-opus-4-8", "xhigh"), "claude-opus-4-8-thinking-max");

  // Opus 4.7 — different variant names
  assert.equal(toCursorId("claude-opus-4-7", "high"), "claude-opus-4-7-thinking-high");
  assert.equal(toCursorId("claude-opus-4-7", "xhigh"), "claude-opus-4-7-thinking-max");

  // Fable 5 — multi-level variants
  assert.equal(toCursorId("claude-fable-5", "low"), "claude-fable-5-thinking-medium");
  assert.equal(toCursorId("claude-fable-5", "xhigh"), "claude-fable-5-thinking-max");

  // GPT-5.4 — graduated
  assert.equal(toCursorId("gpt-5.4", "low"), "gpt-5.4-low");
  assert.equal(toCursorId("gpt-5.4", "medium"), "gpt-5.4-medium");
  assert.equal(toCursorId("gpt-5.4", "xhigh"), "gpt-5.4-xhigh");
});

test("toCursorId falls back to default for unhandled thinking level", () => {
  // Models with no specific level map fall back to default
  assert.equal(toCursorId("composer-2.5", "high"), "composer-2.5");
  assert.equal(toCursorId("gpt-5-mini", "high"), "gpt-5-mini");
});

test("toCanonicalId returns canonical for known default IDs", () => {
  assert.equal(toCanonicalId("claude-4.5-sonnet"), "claude-sonnet-4-5");
  assert.equal(toCanonicalId("gpt-5.4-medium"), "gpt-5.4");
  assert.equal(toCanonicalId("kimi-k2.5"), "kimi-k2.5");
});

test("toCanonicalId returns null for variant models (hidden from list)", () => {
  assert.equal(toCanonicalId("claude-4.5-sonnet-thinking"), null);
  assert.equal(toCanonicalId("gpt-5.4-low"), null);
  assert.equal(toCanonicalId("claude-opus-4-8-thinking-max"), null);
});

test("toCanonicalId returns id as-is for unknown models", () => {
  assert.equal(toCanonicalId("completely-unknown-model"), "completely-unknown-model");
});

test("round-trip: canonical → cursor default → canonical", () => {
  const families = [
    "claude-sonnet-4-5",
    "claude-opus-4-8",
    "claude-fable-5",
    "gpt-5.4",
    "gpt-5.5",
    "gpt-5.4-mini",
    "gemini-3.5-pro-preview",
    "grok-4.3",
    "kimi-k2.5",
  ];

  for (const fam of families) {
    const cursorId = toCursorId(fam);
    const canonical = toCanonicalId(cursorId);
    assert.equal(
      canonical,
      fam,
      `round-trip failed for ${fam}: cursorId=${cursorId} canonical=${canonical}`,
    );
  }
});

test("new model families have correct defaults", () => {
  // claude-opus-4-7-max
  assert.equal(toCursorId("claude-opus-4-7-max"), "claude-opus-4-7-thinking-high");
  assert.equal(toCursorId("claude-opus-4-7-max", "xhigh"), "claude-opus-4-7-thinking-max");

  // claude-opus-4-8-max
  assert.equal(toCursorId("claude-opus-4-8-max"), "claude-opus-4-8-max-thinking-high");
  assert.equal(toCursorId("claude-opus-4-8-max", "xhigh"), "claude-opus-4-8-max-thinking-max");

  // gpt-5.5-pro
  assert.equal(toCursorId("gpt-5.5-pro"), "gpt-5.5-pro-medium");
  assert.equal(toCursorId("gpt-5.5-pro", "high"), "gpt-5.5-pro-high");

  // gpt-5.4-pro
  assert.equal(toCursorId("gpt-5.4-pro"), "gpt-5.4-pro-medium");
  assert.equal(toCursorId("gpt-5.4-pro", "low"), "gpt-5.4-pro-low");

  // gemini 3.5
  assert.equal(toCursorId("gemini-3.5-pro-preview"), "gemini-3.5-pro");
  assert.equal(toCursorId("gemini-3.5-flash-preview"), "gemini-3.5-flash");
});
