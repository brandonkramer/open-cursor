import assert from "node:assert/strict";
import test from "node:test";

import type { AgentServerMessage } from "../src/__generated__/agent/v1/agent_pb.js";
import { wrapAbortSafeStream } from "../src/agent.js";

function createNeverEndingStream(returnSpy?: {
  called: boolean;
}): AsyncIterable<AgentServerMessage> {
  return {
    [Symbol.asyncIterator]() {
      return {
        next() {
          return new Promise<IteratorResult<AgentServerMessage>>(() => {});
        },
        async return() {
          if (returnSpy) {
            returnSpy.called = true;
          }
          return { done: true, value: undefined as never };
        },
      };
    },
  };
}

test("wrapAbortSafeStream aborts by closing the underlying iterator", async () => {
  const controller = new AbortController();
  const returnSpy = { called: false };
  const stream = wrapAbortSafeStream(createNeverEndingStream(returnSpy), controller.signal);

  const iterator = stream[Symbol.asyncIterator]();
  const nextPromise = iterator.next();
  controller.abort();

  await assert.rejects(nextPromise, (error: unknown) => {
    assert.ok(error instanceof Error);
    assert.equal(error.name, "AbortError");
    return true;
  });
  assert.equal(returnSpy.called, true);
});

test("wrapAbortSafeStream returns next item when not aborted", async () => {
  const controller = new AbortController();

  const stream = wrapAbortSafeStream(
    {
      [Symbol.asyncIterator]() {
        return {
          next() {
            return Promise.resolve({
              done: false,
              value: { message: { case: "interactionUpdate", value: {} } },
            } as IteratorResult<AgentServerMessage>);
          },
          async return() {
            return { done: true, value: undefined as never };
          },
        };
      },
    },
    controller.signal,
  );

  const iterator = stream[Symbol.asyncIterator]();
  const result = await iterator.next();

  assert.equal(result.done, false);
  assert.ok(result.value);
});

test("wrapAbortSafeStream propagates stream done", async () => {
  const controller = new AbortController();

  const stream = wrapAbortSafeStream(
    {
      [Symbol.asyncIterator]() {
        return {
          next() {
            return Promise.resolve({ done: true, value: undefined as never });
          },
          async return() {
            return { done: true, value: undefined as never };
          },
        };
      },
    },
    controller.signal,
  );

  const iterator = stream[Symbol.asyncIterator]();
  const result = await iterator.next();

  assert.equal(result.done, true);
});

test("wrapAbortSafeStream handles pre-aborted signal", async () => {
  const controller = new AbortController();
  const reason = new Error("pre-aborted");
  reason.name = "AbortError";
  controller.abort(reason);

  const returnSpy = { called: false };
  const stream = wrapAbortSafeStream(createNeverEndingStream(returnSpy), controller.signal);

  const iterator = stream[Symbol.asyncIterator]();
  await assert.rejects(iterator.next(), (error: unknown) => {
    assert.ok(error instanceof Error);
    assert.equal(error.name, "AbortError");
    return true;
  });
  assert.equal(returnSpy.called, true);
});
