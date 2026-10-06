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
  auto: "text-[34px] min-[400px]:text-[40px] sm:text-[48px] lg:text-[56px]",
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
      <span aria-hidden className="relative block size-[1em] shrink-0">
        {/* soft glow under tile */}
        <span className="absolute inset-0 translate-y-[8%] rounded-[27%] bg-[#a855f7]/30 blur-[0.28em]" />
        {/* tile */}
        <span className="absolute inset-0 rounded-[27%] bg-gradient-to-b from-[#faf8ff] to-[#d9d2f6] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7),0_0.1em_0.3em_rgba(0,0,0,0.45)]" />
        {/* dark bar */}
        <span className="absolute left-[27%] top-[30%] h-[11.5%] w-[46%] rounded-full bg-[#1c1833]" />
        {/* dot glow */}
        <span className="absolute left-[51%] top-[55%] size-[30%] rounded-full bg-[#d946ef]/60 blur-[0.06em]" />
        {/* dot + ring */}
        <span className="absolute left-[55.5%] top-[59.5%] size-[21%] rounded-full bg-[radial-gradient(circle_at_42%_40%,#f5a3ff,#c15cf0_55%,#8b5cf6)] shadow-[0_0_0_0.03em_#c5b7ff,0_0_0_0.06em_rgba(197,183,255,0.35)]" />
      </span>

      {/* ── Wordmark ── */}
      <span
        className={`whitespace-nowrap font-display font-bold leading-none tracking-[-0.04em] ${
          stacked ? "text-[1.05em]" : "text-[0.7em]"
        } ${compactOnXs ? "hidden min-[400px]:inline" : ""}`}
      >
        <span className="bg-gradient-to-b from-white to-[#cfcae6] bg-clip-text text-transparent">
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