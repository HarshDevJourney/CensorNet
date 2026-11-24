export default function YouTubeForm({ url, onChange }: { url: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label htmlFor="yt-url" className="text-sm font-medium">YouTube URL</label>
      <input
        id="yt-url"
        value={url}
        onChange={e => onChange(e.target.value)}
        placeholder="https://www.youtube.com/watch?v=…"
        className="mt-2 w-full rounded-xl border border-ink/25 bg-surface px-4 py-3 outline-none transition placeholder:text-muted/70 focus:border-accent focus:ring-2 focus:ring-accent/30"
      />
      <p className="mt-2 text-sm text-muted">Single video only. Downloads with yt-dlp at best quality.</p>
    </div>
  );
}
