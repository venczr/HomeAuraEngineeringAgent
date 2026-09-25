export async function POST(request: Request) {
  const apiBase = process.env.HOMEAURA_API_BASE ?? "http://127.0.0.1:8000";
  try {
    const target = new URL(apiBase);
    if (target.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(target.hostname)) throw new Error("HOMEAURA_API_BASE must remain loopback-only");
    const response = await fetch(`${apiBase}/building-preview`, { method: "POST", headers: { "content-type": "application/json" }, body: await request.text(), cache: "no-store", signal: AbortSignal.timeout(20000) });
    return new Response(await response.text(), { status: response.status, headers: { "content-type": response.headers.get("content-type") ?? "application/json" } });
  } catch {
    return Response.json({ detail: { code: "homeaura_api_unavailable", message: "Локальное инженерное ядро HomeAura недоступно." } }, { status: 503 });
  }
}
