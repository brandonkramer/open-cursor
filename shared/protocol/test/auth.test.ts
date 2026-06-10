import assert from "node:assert/strict";
import test from "node:test";

import Auth from "../src/auth.js";

test("Auth.poll sends correct request and parses response", async () => {
  const baseUrl = "https://example.com";

  const auth = new Auth(baseUrl);

  // Use a mock approach: intercept global fetch
  const originalFetch = globalThis.fetch;
  const fetchCalls: Array<[string, RequestInit | undefined]> = [];

  globalThis.fetch = ((url: string, init?: RequestInit) => {
    fetchCalls.push([url, init]);
    return Promise.resolve(
      new Response(JSON.stringify({ accessToken: "at_123", refreshToken: "rt_456" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
  }) as typeof globalThis.fetch;

  try {
    const result = await auth.poll({ uuid: "test-uuid", verifier: "test-verifier" });

    assert.ok(fetchCalls.length > 0);
    const [url, init] = fetchCalls[0]!;
    assert.match(url, /\/auth\/poll/);
    assert.match(url, /uuid=test-uuid/);
    assert.match(url, /verifier=test-verifier/);
    assert.equal(init?.method ?? "GET", "GET"); // default GET

    assert.equal(result.accessToken, "at_123");
    assert.equal(result.refreshToken, "rt_456");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Auth.exchangeUserApiKey sends POST with Bearer token", async () => {
  const baseUrl = "https://example.com";
  const auth = new Auth(baseUrl);

  const originalFetch = globalThis.fetch;
  const fetchCalls: Array<[string, RequestInit | undefined]> = [];

  globalThis.fetch = ((url: string, init?: RequestInit) => {
    fetchCalls.push([url, init]);
    return Promise.resolve(
      new Response(JSON.stringify({ accessToken: "at_ex", refreshToken: "rt_ex" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
  }) as typeof globalThis.fetch;

  try {
    const result = await auth.exchangeUserApiKey({ token: "api_key_abc" });

    const [url, init] = fetchCalls[0]!;
    assert.match(url, /\/auth\/exchange_user_api_key/);
    assert.equal(init?.method, "POST");
    const headers = init?.headers as Record<string, string> | undefined;
    assert.equal(headers?.["authorization"], "Bearer api_key_abc");

    assert.equal(result.accessToken, "at_ex");
    assert.equal(result.refreshToken, "rt_ex");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Auth.poll rejects on non-200 response", async () => {
  const baseUrl = "https://example.com";
  const auth = new Auth(baseUrl);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = (() =>
    Promise.resolve(
      new Response("Unauthorized", { status: 401, statusText: "Unauthorized" }),
    )) as typeof globalThis.fetch;

  try {
    await assert.rejects(auth.poll({ uuid: "bad", verifier: "bad" }), /Fetch failed/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Auth.poll rejects on invalid response shape", async () => {
  const baseUrl = "https://example.com";
  const auth = new Auth(baseUrl);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = (() =>
    Promise.resolve(
      new Response(JSON.stringify({ unexpected: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )) as typeof globalThis.fetch;

  try {
    await assert.rejects(auth.poll({ uuid: "bad", verifier: "bad" }), /invalid response/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
