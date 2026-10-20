// Base building blocks shared by every page.

import { useId } from "react";

import { AlertIcon, CheckIcon, CrossIcon, InfoIcon, QuestionIcon } from "./icons";
import { STOCK_LABELS } from "@/lib/messages";

type Variant = "primary" | "secondary" | "ghost" | "stock" | "out" | "danger";
type Size = "lg" | "md" | "sm";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-dark border-brand",
  secondary: "bg-surface text-brand border-brand hover:bg-brand-soft",
  ghost: "bg-transparent text-brand border-transparent hover:bg-brand-soft underline-offset-4",
  stock: "bg-surface text-stock border-stock hover:bg-stock-soft",
  out: "bg-surface text-out border-out hover:bg-out-soft",
  danger: "bg-out text-white border-out hover:bg-[#861a1a]",
};

const SIZES: Record<Size, string> = {
  lg: "min-h-13 px-6 text-lg gap-2.5",
  md: "min-h-11 px-4 text-base gap-2",
  sm: "min-h-10 px-3 text-base gap-1.5",
};

/** Classes for a button, usable on <button> and on links. */
export function buttonClass(variant: Variant = "primary", size: Size = "md", extra = "") {
  return [
    "inline-flex items-center justify-center rounded-lg border-2 font-semibold transition-colors",
    "disabled:cursor-not-allowed disabled:opacity-60",
    VARIANTS[variant],
    SIZES[size],
    extra,
  ].join(" ");
}

export const inputClass =
  "block w-full min-h-12 rounded-lg border-2 border-line bg-surface px-3.5 text-base text-ink " +
  "placeholder:text-muted/80 focus:border-brand aria-[invalid=true]:border-out";

interface FieldProps {
  label: string;
  hint?: string;
  error?: string | null;
  children: (props: { id: string; "aria-describedby"?: string; "aria-invalid": boolean }) => React.ReactNode;
}

/** A label, the input (rendered by `children`), an optional hint and the error. */
export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block font-semibold">
        {label}
      </label>
      {hint && (
        <p id={hintId} className="text-muted text-[0.95rem]">
          {hint}
        </p>
      )}
      {children({ id, "aria-describedby": describedBy, "aria-invalid": Boolean(error) })}
      {error && (
        <p id={errorId} className="flex items-start gap-1.5 font-semibold text-out">
          <AlertIcon className="mt-0.5 h-5 w-5" />
          {error}
        </p>
      )}
    </div>
  );
}

type Tone = "info" | "caution" | "danger" | "success";

const TONES: Record<Tone, { box: string; icon: React.ReactNode }> = {
  info: { box: "bg-brand-soft border-brand/40 text-ink", icon: <InfoIcon className="h-6 w-6 text-brand" /> },
  caution: {
    box: "bg-caution-soft border-caution-line text-ink",
    icon: <AlertIcon className="h-6 w-6 text-caution" />,
  },
  danger: { box: "bg-out-soft border-out-line text-ink", icon: <AlertIcon className="h-6 w-6 text-out" /> },
  success: { box: "bg-stock-soft border-stock-line text-ink", icon: <CheckIcon className="h-6 w-6 text-stock" /> },
};

export function Notice({
  tone = "info",
  title,
  children,
  role,
}: {
  tone?: Tone;
  title?: string;
  children?: React.ReactNode;
  role?: "alert" | "status";
}) {
  const t = TONES[tone];
  return (
    <div role={role} className={`flex gap-3 rounded-xl border-2 p-4 ${t.box}`}>
      <div className="pt-0.5">{t.icon}</div>
      <div className="min-w-0 space-y-1">
        {title && <p className="font-bold">{title}</p>}
        {children && <div className="space-y-2">{children}</div>}
      </div>
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-6 text-muted">
      <span className="h-5 w-5 animate-spin rounded-full border-[3px] border-brand/30 border-t-brand" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Notice tone="danger" title="Something went wrong" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className={buttonClass("secondary", "sm")}>
          Try again
        </button>
      )}
    </Notice>
  );
}

export type StockKind = "en_stock" | "rupture" | "unknown";

const BADGES: Record<StockKind, { className: string; icon: React.ReactNode }> = {
  en_stock: { className: "bg-stock-soft text-stock border-stock-line", icon: <CheckIcon className="h-4 w-4" /> },
  rupture: { className: "bg-out-soft text-out border-out-line", icon: <CrossIcon className="h-4 w-4" /> },
  unknown: {
    className: "bg-unknown-soft text-unknown border-unknown-line",
    icon: <QuestionIcon className="h-4 w-4" />,
  },
};

/** Stock status: always an icon AND a word, never colour alone. */
export function StatusBadge({ status }: { status: StockKind }) {
  const b = BADGES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[0.95rem] font-bold ${b.className}`}
    >
      {b.icon}
      {STOCK_LABELS[status]}
    </span>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-line bg-surface p-4 sm:p-5 ${className}`}>{children}</div>;
}

export function PageTitle({ children, lead }: { children: React.ReactNode; lead?: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h1 className="text-[1.9rem] leading-tight font-bold sm:text-4xl">{children}</h1>
      {lead && <p className="text-lg text-muted">{lead}</p>}
    </div>
  );
}
