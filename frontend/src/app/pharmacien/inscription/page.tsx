import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Register your pharmacy",
  description: "Create a pharmacist account so patients can see which medicines your pharmacy has in stock.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
