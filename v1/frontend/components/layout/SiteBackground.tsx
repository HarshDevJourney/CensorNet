/** Fixed, theme-aware backdrop shared by every page. */
export default function SiteBackground() {
  return (
    <div aria-hidden className="site-bg">
      <div className="site-bg-glow" />
      <div className="site-bg-grid" />
      <div className="site-bg-orb -right-24 top-24 h-72 w-72 bg-accent/15" />
      <div className="site-bg-orb -left-24 bottom-10 h-80 w-80 bg-accent2/15" style={{ animationDelay: "-9s" }} />
    </div>
  );
}
