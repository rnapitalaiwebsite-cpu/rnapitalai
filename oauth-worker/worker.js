// Sign-in helper for the RNL editing screen (Decap CMS + GitHub).
//
// Runs free on Cloudflare Workers. It lets staff sign in to /admin with their
// GitHub account. It stores nothing; it only swaps GitHub's one-time code for
// a sign-in token and hands it back to the editing screen.
//
// Set two secrets on the worker (Cloudflare dashboard > Worker > Settings > Variables):
//   GITHUB_CLIENT_ID      from the GitHub OAuth App RNL creates
//   GITHUB_CLIENT_SECRET  from the same OAuth App (keep secret)
// And one plain variable:
//   ALLOWED_ORIGIN        https://napitalaiengineers.com

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = env.ALLOWED_ORIGIN || "https://napitalaiengineers.com";

    if (url.pathname === "/auth") {
      const state = crypto.randomUUID();
      const authorize = new URL("https://github.com/login/oauth/authorize");
      authorize.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
      authorize.searchParams.set("scope", "repo,user");
      authorize.searchParams.set("state", state);
      authorize.searchParams.set("redirect_uri", `${url.origin}/callback`);
      return new Response(null, {
        status: 302,
        headers: {
          Location: authorize.toString(),
          "Set-Cookie": `rnl_oauth_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`,
        },
      });
    }

    if (url.pathname === "/callback") {
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state");
      const cookie = (request.headers.get("Cookie") || "").match(/rnl_oauth_state=([^;]+)/);
      if (!code || !state || !cookie || cookie[1] !== state) {
        return page("error", { message: "Sign-in check failed. Please close this window and try again." }, origin);
      }
      const res = await fetch("https://github.com/login/oauth/access_token", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
          redirect_uri: `${url.origin}/callback`,
        }),
      });
      const data = await res.json();
      if (!data.access_token) {
        return page("error", { message: data.error_description || "GitHub did not return a sign-in token." }, origin);
      }
      return page("success", { token: data.access_token, provider: "github" }, origin);
    }

    return new Response("RNL editing screen sign-in helper.", { status: 200 });
  },
};

// The handshake Decap CMS expects: announce, wait for the editing screen to
// reply, then send the result only to the RNL website's own address.
function page(status, content, origin) {
  const msg = `authorization:github:${status}:${JSON.stringify(content)}`;
  const html = `<!doctype html><html><body><p>Signing in…</p><script>
(function () {
  var allowed = ${JSON.stringify(origin)};
  function receive(e) {
    if (e.origin !== allowed) return;
    window.opener.postMessage(${JSON.stringify(msg)}, e.origin);
    window.removeEventListener("message", receive);
    setTimeout(function () { window.close(); }, 300);
  }
  window.addEventListener("message", receive, false);
  window.opener.postMessage("authorizing:github", allowed);
})();
</script></body></html>`;
  return new Response(html, {
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}
