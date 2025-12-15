import React from "react";

export function Card(props: React.PropsWithChildren<{ className?: string }>) {
  return (
    <div className={`rounded-2xl border border-neutral-800 bg-neutral-900/40 shadow-sm ${props.className ?? ""}`}>
      {props.children}
    </div>
  );
}

export function CardHeader(props: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <div className="px-5 pt-5">
      <div className="text-lg font-semibold text-neutral-100">{props.title}</div>
      {props.subtitle ? <div className="text-sm text-neutral-400 mt-1">{props.subtitle}</div> : null}
      {props.children}
      <div className="mt-4 h-px bg-neutral-800" />
    </div>
  );
}

export function CardBody(props: React.PropsWithChildren) {
  return <div className="px-5 py-5">{props.children}</div>;
}

export function Label(props: React.PropsWithChildren) {
  return <div className="text-xs text-neutral-400 mb-1">{props.children}</div>;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-xl border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600 ${
        props.className ?? ""
      }`}
    />
  );
}

export function Button(
  props: React.PropsWithChildren<{ variant?: "primary" | "ghost"; disabled?: boolean; onClick?: () => void }>
) {
  const variant = props.variant ?? "primary";
  const base =
    "rounded-xl px-4 py-2 text-sm font-medium transition border inline-flex items-center justify-center gap-2";
  const cls =
    variant === "ghost"
      ? "border-neutral-800 bg-transparent text-neutral-200 hover:bg-neutral-800/40"
      : "border-neutral-800 bg-neutral-100 text-neutral-950 hover:bg-white";
  return (
    <button disabled={props.disabled} onClick={props.onClick} className={`${base} ${cls} disabled:opacity-50`}>
      {props.children}
    </button>
  );
}

export function Badge(props: React.PropsWithChildren<{ tone?: "ok" | "warn" | "bad" | "neutral" }>) {
  const tone = props.tone ?? "neutral";
  const cls =
    tone === "ok"
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
      : tone === "warn"
      ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
      : tone === "bad"
      ? "border-rose-500/40 bg-rose-500/10 text-rose-200"
      : "border-neutral-700 bg-neutral-800/40 text-neutral-200";
  return <span className={`px-2 py-1 rounded-lg border text-xs ${cls}`}>{props.children}</span>;
}
