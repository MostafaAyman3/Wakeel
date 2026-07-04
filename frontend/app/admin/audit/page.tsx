import { redirect } from "next/navigation";

export default function AuditPage() {
  // Audit trail is viewed through the M3 Agent Review panel.
  redirect("/m3");
}
