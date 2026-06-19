/* ─────────────────────────────────────────────────────────────
 * Demo-mode JWT generator for development/demo.
 *
 * In production, replace with real auth flow (login page → cookie).
 * Uses the `jose` library to sign tokens compatible with the
 * backend's HS256 verification in backend/core/auth.py.
 *
 * NOTE: NEXT_PUBLIC_JWT_SECRET must match JWT_SECRET_KEY in
 * the backend's .env file.
 * ───────────────────────────────────────────────────────────── */

import { SignJWT } from "jose";

const DEMO_USER = {
  sub: "demo-user-001",
  email: "demo@wakeel.ai",
  role: "admin",
};

let cachedToken: string | null = null;
let tokenExpiry: number = 0;

/**
 * Get a valid auth token. Generates a demo JWT for development.
 * Caches the token until near expiry.
 */
export async function getAuthToken(): Promise<string> {
  const now = Date.now();

  // Return cached token if still valid (with 5min buffer)
  if (cachedToken && tokenExpiry > now + 5 * 60 * 1000) {
    return cachedToken;
  }

  const secretStr =
    process.env.NEXT_PUBLIC_JWT_SECRET ||
    "dev-secret-key-change-in-production";

  const secret = new TextEncoder().encode(secretStr);

  // Generate new demo token (8h expiry)
  const token = await new SignJWT({
    sub: DEMO_USER.sub,
    email: DEMO_USER.email,
    role: DEMO_USER.role,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("8h")
    .sign(secret);

  cachedToken = token;
  tokenExpiry = now + 8 * 60 * 60 * 1000;

  return token;
}
