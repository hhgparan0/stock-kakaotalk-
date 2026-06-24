export interface Env {
  GH_PAT: string;
  GH_REPO: string;
  GH_WORKFLOW: string;
  GH_REF: string;
}

async function dispatch(env: Env, market: "us" | "kr"): Promise<{ ok: boolean; status: number; body: string }> {
  const url = `https://api.github.com/repos/${env.GH_REPO}/actions/workflows/${env.GH_WORKFLOW}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_PAT}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "cf-worker-stock-cron",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      ref: env.GH_REF,
      inputs: { market },
    }),
  });

  const body = await res.text();
  return { ok: res.ok, status: res.status, body };
}

export default {
  async scheduled(controller: ScheduledController, env: Env, _ctx: ExecutionContext): Promise<void> {
    const market: "us" | "kr" = controller.cron === "53 4 * * MON-FRI" ? "kr" : "us";
    const result = await dispatch(env, market);
    if (!result.ok) {
      console.error(`dispatch failed cron=${controller.cron} market=${market} status=${result.status} body=${result.body}`);
      throw new Error(`GitHub dispatch failed: ${result.status}`);
    }
    console.log(`dispatch ok cron=${controller.cron} market=${market}`);
  },

  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const market = (url.searchParams.get("market") === "kr" ? "kr" : "us") as "us" | "kr";
    const result = await dispatch(env, market);
    return new Response(
      JSON.stringify({ market, status: result.status, ok: result.ok, body: result.body }, null, 2),
      { status: result.ok ? 200 : 500, headers: { "Content-Type": "application/json" } }
    );
  },
};
