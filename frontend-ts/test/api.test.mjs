import assert from "node:assert/strict";
import test from "node:test";

const api = await import(new URL("../.tmp-tests/api.js", import.meta.url));

test("parses JSON responses through the shared API helper", async () => {
  const payload = await api.parseJsonResponse(new Response('{"status":"ok"}'));

  assert.deepEqual(payload, { status: "ok" });
});

test("converts HTML responses into a readable backend availability message", async () => {
  await assert.rejects(
    () => api.parseJsonResponse(new Response("<!doctype html><html></html>", { statusText: "OK" })),
    /backend do LojaSync retornou HTML em vez de JSON/,
  );

  assert.match(
    api.buildUnexpectedJsonResponseMessage("<html><body>fallback</body></html>"),
    /runtime principal e o runtime de autenticação/,
  );
});

test("resolves API base URL from runtime override and origin", () => {
  assert.equal(
    api.resolveApiBaseUrl({
      windowBackendUrl: "http://127.0.0.1:8891/",
      origin: "http://127.0.0.1:5197",
    }),
    "http://127.0.0.1:8891",
  );
  assert.equal(api.resolveApiBaseUrl({ origin: "http://127.0.0.1:5197/" }), "http://127.0.0.1:5197");
});

test("keeps polling the same import job after a transient status failure", async () => {
  let requestCount = 0;
  const fetchStatus = async () => {
    requestCount += 1;
    if (requestCount === 1) throw new TypeError("temporary connection failure");
    return { job_id: "job-1", stage: "completed" };
  };

  const status = await api.waitForImportJob("job-1", { intervalMs: 100, fetchStatus });
  assert.equal(status.stage, "completed");
  assert.equal(requestCount, 2);
});
