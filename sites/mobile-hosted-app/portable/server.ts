import { resolve } from "node:path";
import type { RequestListener } from "node:http";
import { SqliteDatabase } from "./sqlite.ts";
import { normalizedAddress, sanitizeRequest } from "./request-boundary.ts";
import { createStaticHandler } from "./static-assets.ts";
import { instrumentEngineFetch } from "./upstream-diagnostics.ts";

const port = Number(process.env.PORT || "3000");
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid PORT");
const configuredOrigin = process.env.GUANXIANG_PUBLIC_ORIGIN || process.env.RENDER_EXTERNAL_URL;
if (process.env.NODE_ENV === "production" && !configuredOrigin) {
  throw new Error("Production requires GUANXIANG_PUBLIC_ORIGIN (or RENDER_EXTERNAL_URL)");
}
const origin = new URL(configuredOrigin || `http://localhost:${port}`);
if (origin.username || origin.password || origin.pathname !== "/" || origin.search || origin.hash ||
    !["http:", "https:"].includes(origin.protocol)) throw new Error("Invalid GUANXIANG_PUBLIC_ORIGIN");
if (process.env.NODE_ENV === "production" && origin.protocol !== "https:" &&
    !["localhost", "127.0.0.1"].includes(origin.hostname)) throw new Error("Public deployment requires HTTPS");
process.env.GUANXIANG_PUBLIC_ORIGIN = origin.origin;
process.env.VINEXT_TRUST_PROXY = "1";
process.env.GUANXIANG_ENGINE_PREFLIGHT = "true";
delete process.env.ABALO_LOCAL_PREVIEW_BYPASS_AUTH;

const trustedPeers = new Set((process.env.GUANXIANG_TRUST_PROXY_PEERS || "").split(",").filter(Boolean).map(value => {
  const address = normalizedAddress(value);
  if (!address) throw new Error("Proxy peers must be literal IP addresses");
  return address;
}));
const filename = process.env.GUANXIANG_SQLITE_PATH || resolve("data/guanxiang.sqlite");
if (process.env.RENDER === "true" && !resolve(filename).startsWith("/var/data/") &&
    process.env.GUANXIANG_ALLOW_EPHEMERAL_BETA !== "true") {
  throw new Error("Render needs persistent /var/data storage; ephemeral acceptance testing must be explicitly enabled");
}
const db = new SqliteDatabase(filename);
Object.assign(globalThis, { __guanxiangPortableDb: db });
if (process.env.PYTHON_ENGINE_URL) {
  globalThis.fetch = instrumentEngineFetch(globalThis.fetch, new URL(process.env.PYTHON_ENGINE_URL).origin,
    event => console.info(JSON.stringify(event)));
}
const { startProdServer } = await import("vinext/server/prod-server");
const serveStatic = await createStaticHandler(resolve("dist-portable/client"));
// Import and initialize on loopback before installing the public boundary.
const { server } = await startProdServer({ port: 0, host: "127.0.0.1", outDir: resolve("dist-portable") });
await new Promise<void>((done, reject) => server.close(error => error ? reject(error) : done()));
const handlers = server.listeners("request") as RequestListener[];
server.removeAllListeners("request");
server.on("request", (request, response) => {
  sanitizeRequest(request, trustedPeers, origin);
  if (serveStatic(request, response)) return;
  if (request.url?.split("?", 1)[0] === "/healthz") {
    try {
      db.connection.prepare("SELECT 1").get();
      response.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      response.end(JSON.stringify({ status: "ok", service: "guanxiang-portable" }));
    } catch { response.writeHead(503); response.end("unavailable"); }
    return;
  }
  for (const handler of handlers) handler.call(server, request, response);
});
await new Promise<void>((done, reject) => {
  server.once("error", reject);
  server.listen(port, process.env.HOST || "0.0.0.0", () => done());
});
console.log(`Guanxiang portable ready on port ${port}`);
for (const signal of ["SIGINT", "SIGTERM"] as const) process.once(signal, () => {
  server.close(() => { db.close(); process.exit(0); });
  setTimeout(() => process.exit(1), 10_000).unref();
});
