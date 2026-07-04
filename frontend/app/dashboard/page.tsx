import { redirect } from "next/navigation";

export default function DashboardPage() {
  // Dashboard redirects to the main landing with module cards.
  redirect("/");
}
