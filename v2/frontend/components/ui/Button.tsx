import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary";

const base =
  "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40";
const variants: Record<Variant, string> = {
  primary: "bg-ink text-surface shadow-[0_8px_24px_-8px_rgb(var(--c-accent)/0.6)] hover:-translate-y-0.5 hover:bg-ink/90",
  secondary: "border border-ink/25 text-ink hover:border-ink hover:bg-ink/5",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button {...props} className={`${base} ${variants[variant]} ${className}`} />;
}

export function ButtonLink({
  href,
  variant = "primary",
  children,
}: {
  href: string;
  variant?: Variant;
  children: ReactNode;
}) {
  const cls = `${base} ${variants[variant]}`;
  return href.startsWith("#") ? (
    <a href={href} className={cls}>{children}</a>
  ) : (
    <Link href={href} className={cls}>{children}</Link>
  );
}
