import type { ReactNode } from "react";

export default function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-surface/85 backdrop-blur ${className}`}>{children}</div>;
}
