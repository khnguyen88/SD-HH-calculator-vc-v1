/**
 * noaa-proxy — Cloudflare Worker
 *
 * Proxies NOAA Atlas 14 PFDS requests to bypass the server's
 * Cross-Origin-Resource-Policy: same-origin header, which blocks all
 * cross-origin browser loads (both fetch() and <script> tag injection).
 *
 * DEPLOY (one-time, free Cloudflare account):
 *   1. Go to https://dash.cloudflare.com → Workers & Pages → Create
 *   2. Create a new Worker, paste this entire file, click Deploy
 *   3. Copy the Worker URL (e.g. https://noaa-proxy.yourname.workers.dev)
 *   4. Paste that URL into the "NOAA proxy URL" field on the Rainfall tab
 *
 * The Worker URL persists in your Excel export so you only configure it once.
 *
 * REQUEST FORMAT (sent by the app):
 *   GET https://your-worker.workers.dev?lat=39.05&lon=-77.05
 *
 * RESPONSE:
 *   Plain text — the raw NOAA quantiles JavaScript blob,
 *   with Access-Control-Allow-Origin: * added.
 */

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(),
      });
    }

    const lat = url.searchParams.get("lat");
    const lon = url.searchParams.get("lon");

    if (!lat || !lon || !isFinite(+lat) || !isFinite(+lon)) {
      return new Response("Missing or invalid lat/lon parameters.", {
        status: 400,
        headers: corsHeaders(),
      });
    }

    const noaaUrl =
      "https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py" +
      "?type=pf&series=pds&units=us&statname=&lat=" + lat + "&lon=" + lon;

    try {
      const upstream = await fetch(noaaUrl);
      const text = await upstream.text();

      if (!text || text.indexOf("quantiles") === -1) {
        return new Response("Upstream NOAA response missing quantiles data.", {
          status: 502,
          headers: corsHeaders(),
        });
      }

      return new Response(text, {
        status: 200,
        headers: {
          ...corsHeaders(),
          "Content-Type": "text/plain; charset=utf-8",
          "Cache-Control": "public, max-age=86400", // cache 24h — data rarely changes
        },
      });
    } catch (err) {
      return new Response("Upstream fetch failed: " + err.message, {
        status: 502,
        headers: corsHeaders(),
      });
    }
  },
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}
