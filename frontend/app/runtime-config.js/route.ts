import { connection } from "next/server";

/**
 * The API address for the browser, read from the container's environment on every request.
 * NEXT_PUBLIC_* values are frozen at build time; this lets one image serve any deployment
 * (Darkube cannot pass build arguments). Falls back to the build-time value.
 */
export async function GET(): Promise<Response> {
  await connection();
  const configured = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "";
  const base = /^https?:\/\/[^\s"'<>]+$/.test(configured) ? configured : "";
  return new Response(`window.__ME_AGENT_API_BASE__ = ${JSON.stringify(base)};\n`, {
    headers: {
      "content-type": "text/javascript; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
