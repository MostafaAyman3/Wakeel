import { redirect } from "next/navigation";

export default function LoginPage() {
  // Demo mode — no login required, auto-JWT handles authentication.
  // Redirect to landing page.
  redirect("/");
}
