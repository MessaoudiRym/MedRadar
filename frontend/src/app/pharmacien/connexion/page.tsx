import type { Metadata } from "next";

import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = {
  title: "Pharmacist login",
  description: "Log in to update the stock of your pharmacy on MedRadar.",
};

export default function LoginPage() {
  return <LoginForm />;
}
