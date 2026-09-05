import { isIP } from "node:net";
import type { IncomingMessage } from "node:http";

export function normalizedAddress(value: string): string | null {
  const address = value.trim().replace(/^::ffff:/, "");
  return isIP(address) ? address : null;
}

/** Only an explicitly trusted socket peer may supply one proxy hop. */
export function sanitizeRequest(
  request: Pick<IncomingMessage, "headers"> & { socket: { remoteAddress?: string } },
  trustedPeers: ReadonlySet<string>,
  publicOrigin: URL,
): void {
  const peer = normalizedAddress(request.socket.remoteAddress ?? "");
  const forwarded = request.headers["x-forwarded-for"];
  let client = peer;
  if (peer && trustedPeers.has(peer)) {
    const chain = typeof forwarded === "string" ? forwarded.split(",") : [];
    client = normalizedAddress(chain.at(-1) ?? "") ?? peer;
  }
  for (const name of Object.keys(request.headers)) {
    if (name.startsWith("oai-") || name.startsWith("cf-") ||
        name.startsWith("x-forwarded-") || name === "x-real-ip" || name === "forwarded") {
      delete request.headers[name];
    }
  }
  // This internal header is synthesized, never accepted from a public client.
  if (client) request.headers["cf-connecting-ip"] = client;
  request.headers.host = publicOrigin.host;
  request.headers["x-forwarded-proto"] = publicOrigin.protocol.slice(0, -1);
}
