/** Log transport metadata only: never credentials, questions, URLs or response bodies. */
export function instrumentEngineFetch(
  original: typeof fetch,
  engineOrigin: string,
  report: (event: Record<string, string | number | boolean>) => void,
): typeof fetch {
  return async (input, init) => {
    const response = await original(input, init);
    const url = new URL(input instanceof Request ? input.url : String(input));
    if (url.origin !== engineOrigin) return response;
    const type = response.headers.get("content-type") || "";
    report({
      event: "engine_transport",
      operation: url.pathname.endsWith("/intake") ? "intake"
        : url.pathname.endsWith("/jobs") ? "submit" : "poll",
      status: response.status,
      format: type.includes("application/json") ? "json" : type.includes("text/html") ? "html" : "other",
      challenge: response.headers.get("cf-mitigated") === "challenge",
      renderOrigin: response.headers.has("x-render-origin-server"),
    });
    return response;
  };
}
