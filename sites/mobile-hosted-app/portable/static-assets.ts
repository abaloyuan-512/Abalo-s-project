import { createReadStream } from "node:fs";
import { readdir, stat } from "node:fs/promises";
import { extname, join } from "node:path";
import { pipeline } from "node:stream";
import type { IncomingMessage, ServerResponse } from "node:http";

const types: Record<string, string> = {
  ".js": "application/javascript", ".mjs": "application/javascript", ".css": "text/css",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
  ".avif": "image/avif", ".gif": "image/gif", ".svg": "image/svg+xml", ".ico": "image/x-icon",
  ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
  ".mp4": "video/mp4", ".mp3": "audio/mpeg", ".webmanifest": "application/manifest+json",
};

/** Exact startup allowlist; URL keys always use '/', including on Windows.
 * vinext 0.0.50's native cache uses platform separators for nested file keys.
 * Never serve source maps, dotfiles, runtime databases or arbitrary disk paths.
 */
export async function createStaticHandler(clientDirectory: string) {
  const files = new Map<string, { path: string; size: number; type: string }>();
  async function walk(directory: string, prefix: string): Promise<void> {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (entry.name.startsWith(".")) continue;
      const path = join(directory, entry.name);
      const key = `${prefix}/${entry.name}`;
      if (entry.isDirectory()) await walk(path, key);
      else if (entry.isFile() && types[extname(entry.name)]) {
        files.set(key, { path, size: (await stat(path)).size, type: types[extname(entry.name)] });
      }
    }
  }
  await walk(clientDirectory, "");
  return (request: IncomingMessage, response: ServerResponse): boolean => {
    if (request.method !== "GET" && request.method !== "HEAD") return false;
    let pathname: string;
    try { pathname = decodeURIComponent((request.url || "/").split("?", 1)[0]); }
    catch { return false; }
    if (pathname.split(/[\\/]/).some(part => part.startsWith(".")) || pathname.endsWith(".map")) {
      response.writeHead(404, { "Cache-Control": "no-store" });
      response.end("Not found"); return true;
    }
    const file = files.get(pathname);
    if (!file) return false;
    let start = 0;
    let end = file.size - 1;
    let status = 200;
    const headers: Record<string, string> = {
      "Content-Type": file.type, "X-Content-Type-Options": "nosniff", "Accept-Ranges": "bytes",
      "Cache-Control": pathname.startsWith("/assets/") ? "public, max-age=31536000, immutable" : "no-cache",
    };
    if (request.headers.range && request.method === "GET") {
      const match = /^bytes=(\d*)-(\d*)$/.exec(request.headers.range);
      const first = match?.[1] ? Number(match[1]) : undefined;
      const last = match?.[2] ? Number(match[2]) : undefined;
      if (first === undefined && last !== undefined) start = Math.max(0, file.size - last);
      else if (first !== undefined) { start = first; end = last === undefined ? end : Math.min(end, last); }
      if (!match || (first === undefined && last === undefined) || !Number.isSafeInteger(start) ||
          !Number.isSafeInteger(end) || start < 0 || start > end || start >= file.size) {
        response.writeHead(416, { ...headers, "Content-Range": `bytes */${file.size}` });
        response.end(); return true;
      }
      status = 206;
      headers["Content-Range"] = `bytes ${start}-${end}/${file.size}`;
    }
    headers["Content-Length"] = String(Math.max(0, end - start + 1));
    response.writeHead(status, headers);
    if (request.method === "HEAD" || file.size === 0) response.end();
    else pipeline(createReadStream(file.path, { start, end }), response, error => {
      if (error) response.destroy();
    });
    return true;
  };
}
