import React from "react";

type LogoProps = {
  /** "auto" scales with the screen. Others are fixed tile sizes. */
  size?: "auto" | "sm" | "md" | "lg" | "xl";
  /** inline = icon left of name. stacked = icon above name (README, hero). */
  layout?: "inline" | "stacked";
  /** Trailing pink "." like the banners. */
  period?: boolean;
  /** Hide the name on very small screens and show only the icon. */
  compactOnXs?: boolean;
  className?: string;
};

// Tile size. Everything else is in `em`, so it all scales from this.
const SIZE: Record<NonNullable<LogoProps["size"]>, string> = {
  auto: "text-[24px] min-[400px]:text-[28px] sm:text-[32px] lg:text-[36px]",
  sm: "text-[28px]",
  md: "text-[44px]",
  lg: "text-[72px]",
  xl: "text-[104px]",
};

export default function Logo({
  size = "auto",
  layout = "inline",
  period = false,
  compactOnXs = false,
  className = "",
}: LogoProps) {
  const stacked = layout === "stacked";

  return (
    <span
      aria-label="CensorNet"
      className={`inline-flex select-none items-center ${SIZE[size]} ${
        stacked ? "flex-col gap-[0.2em]" : "gap-[0.3em]"
      } ${className}`}
    >
      {/* ── Mark ── */}
      {/*  */}

      {/* ── Wordmark ── */}
      <span
        className={`whitespace-nowrap font-display font-bold leading-none tracking-[-0.04em] ${
          stacked ? "text-[1.05em]" : "text-[1em]"
        } ${compactOnXs ? "hidden min-[400px]:inline" : ""}`}
      >
        <span className="bg-gradient-to-b from-ink to-muted dark:from-white dark:to-[#cfcae6] bg-clip-text text-transparent">
          Censor
        </span>
        <span className="bg-gradient-to-r from-[#a855f7] via-[#d946ef] to-[#f0589f] bg-clip-text text-transparent">
          Net
        </span>
        {period && <span className="text-[#f0589f]">.</span>}
      </span>
    </span>
  );
}