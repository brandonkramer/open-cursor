import assert from "node:assert/strict";
import test from "node:test";

import { backoff } from "../src/backoff.js";

test("backoff resolves on first success", async () => {
  let callCount = 0;
  const result = await backoff(
    () => {
      callCount++;
      return Promise.resolve(42);
    },
    { retries: 3, delay: 10 },
  );

  assert.equal(result, 42);
  assert.equal(callCount, 1);
});

test("backoff retries on failure then succeeds", async () => {
  let callCount = 0;
  const result = await backoff(
    () => {
      callCount++;
      if (callCount < 3) return Promise.reject(new Error("not yet"));
      return Promise.resolve("done");
    },
    { retries: 5, delay: 10 },
  );

  assert.equal(result, "done");
  assert.equal(callCount, 3);
});

test("backoff throws after exhausting retries", async () => {
  let callCount = 0;
  await assert.rejects(
    backoff(
      () => {
        callCount++;
        return Promise.reject(new Error("always fails"));
      },
      { retries: 3, delay: 10 },
    ),
    { message: "always fails" },
  );
  assert.equal(callCount, 3);
});

test("backoff throws immediately when shouldRetry returns false", async () => {
  let callCount = 0;
  await assert.rejects(
    backoff(
      () => {
        callCount++;
        return Promise.reject(new Error("fatal"));
      },
      {
        retries: 5,
        delay: 10,
        shouldRetry: () => false,
      },
    ),
    { message: "fatal" },
  );
  assert.equal(callCount, 1);
});

test("backoff passes error and attempt number to shouldRetry", async () => {
  const seen: Array<{ error: string; attempt: number }> = [];
  await assert.rejects(
    backoff(() => Promise.reject(new Error("boom")), {
      retries: 3,
      delay: 10,
      shouldRetry: (error, attempt) => {
        seen.push({ error: (error as Error).message, attempt });
        return attempt < 2; // retry only first 2 attempts
      },
    }),
  );

  assert.equal(seen.length, 3); // called for each of the 3 retries
});
