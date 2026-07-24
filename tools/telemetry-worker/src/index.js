// 몽중농원 텔레메트리 수신기 — POST /v1/events 배치를 D1에 그대로 쌓는다.
// 분석은 서버가 아니라 로컬(tools/behavior_report.py)에서 한다 — 여기는 수집만.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method !== "POST" || url.pathname !== "/v1/events") {
      return new Response("not found", { status: 404 });
    }
    let body;
    try {
      const buf = await request.arrayBuffer();
      let text;
      if (request.headers.get("content-encoding") === "gzip") {
        const ds = new DecompressionStream("gzip");
        text = await new Response(new Response(buf).body.pipeThrough(ds)).text();
      } else {
        text = new TextDecoder().decode(buf);
      }
      body = JSON.parse(text);
    } catch (e) {
      return new Response("bad request", { status: 400 });
    }
    if (!body || typeof body.client_id !== "string" || !Array.isArray(body.events) ||
        body.events.length === 0 || body.events.length > 5000) {
      return new Response("bad request", { status: 400 });
    }
    const payload = JSON.stringify(body.events);
    if (payload.length > 1000000) {
      return new Response("too large", { status: 413 });
    }
    await env.DB.prepare(
      "INSERT INTO batches (client_id, game_version, received_at, payload) VALUES (?, ?, ?, ?)"
    ).bind(
      body.client_id.slice(0, 64),
      String(body.game_version || "").slice(0, 32),
      Date.now(),
      payload
    ).run();
    return new Response("ok");
  },
};
