import type { NextConfig } from "next";
const defaultApiUrl = process.env.NODE_ENV === "production"
  ? "https://api.2.25.189.129.nip.io"
  : "http://localhost:8000";
const apiOrigin = new URL(process.env.NEXT_PUBLIC_API_URL ?? defaultApiUrl).origin;
const scriptPolicy = process.env.NODE_ENV === "production"
  ? "script-src 'self' 'unsafe-inline'"
  : "script-src 'self' 'unsafe-inline' 'unsafe-eval'";
const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{source: "/(.*)", headers: [
      {key:"X-Content-Type-Options",value:"nosniff"},
      {key:"X-Frame-Options",value:"DENY"},
      {key:"Referrer-Policy",value:"strict-origin-when-cross-origin"},
      {key:"Permissions-Policy",value:"camera=(), microphone=(), geolocation=(self)"},
      {key:"Content-Security-Policy",value:`default-src 'self'; ${scriptPolicy}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ${apiOrigin}; frame-src https://www.openstreetmap.org; frame-ancestors 'none'; object-src 'none'; base-uri 'self'`}
    ]}];
  }
};
export default nextConfig;
