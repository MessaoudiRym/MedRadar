"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { buttonClass, Field, inputClass, Notice, PageTitle } from "../ui";
import { errorMessage } from "@/lib/api";
import { login, useLoginNotice, useSession } from "@/lib/auth";

const HOME_BY_ROLE = { pharmacien: "/pharmacien", admin: "/admin" } as const;

export function LoginForm() {
  const router = useRouter();
  const { session } = useSession();
  const notice = useLoginNotice();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Already logged in: go straight to the right space
  useEffect(() => {
    if (session) router.replace(HOME_BY_ROLE[session.role]);
  }, [session, router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password) {
      setError("Enter your email and your password.");
      return;
    }
    setSending(true);
    setError(null);
    try {
      const s = await login(email, password);
      router.replace(HOME_BY_ROLE[s.role]);
    } catch (e) {
      setError(errorMessage(e));
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <PageTitle lead="Update your pharmacy's stock in a few taps.">Pharmacist login</PageTitle>

      {notice && (
        <Notice tone="info" role="status">
          <p>{notice}</p>
        </Notice>
      )}

      <form onSubmit={submit} noValidate className="space-y-5 rounded-xl border border-line bg-surface p-5">
        <Field label="Email">
          {(props) => (
            <input
              {...props}
              type="email"
              inputMode="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          )}
        </Field>
        <Field label="Password">
          {(props) => (
            <div className="flex gap-2">
              <input
                {...props}
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-pressed={showPassword}
                className={buttonClass("secondary", "md", "shrink-0")}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          )}
        </Field>

        {error && (
          <Notice tone="danger" role="alert">
            <p>{error}</p>
          </Notice>
        )}

        <button type="submit" disabled={sending} className={buttonClass("primary", "lg", "w-full")}>
          {sending ? "Logging in…" : "Log in"}
        </button>
      </form>

      <p className="text-center">
        No account yet?{" "}
        <Link href="/pharmacien/inscription" className="font-semibold text-brand underline">
          Register your pharmacy
        </Link>
      </p>
    </div>
  );
}
