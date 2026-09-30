"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ingestYouTube, uploadVideo } from "@/lib/api";

type Tab = "file" | "youtube";

function UploadInner() {
  const router = useRouter();
  const params = useSearchParams();
  const initial: Tab = params.get("tab") === "youtube" ? "youtube" : "file";

  const [tab, setTab] = useState<Tab>(initial);
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { setErr(null); }, [tab]);

  async function submitFile() {
    if (!file) return;
    setBusy(true); setErr(null);
    try {
      const { id } = await uploadVideo(file);
      router.push(`/video/${id}`);
    } catch (e: any) {
      setErr(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function submitUrl() {
    if (!url.trim()) return;
    setBusy(true); setErr(null);
    try {
      const { id } = await ingestYouTube(url.trim());
      router.push(`/video/${id}`);
    } catch (e: any) {
      setErr(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-6">New video</h1>

      <div className="inline-flex rounded-xl border border-white/10 overflow-hidden mb-6">
        {(["file", "youtube"] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm ${
              tab === t
                ? "bg-emerald-500 text-black font-medium"
                : "text-white/70 hover:text-white"
            }`}
          >
            {t === "file" ? "Upload file" : "YouTube URL"}
          </button>
        ))}
      </div>

      {tab === "file" && (
        <div>
          <div
            onDragOver={e => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={e => {
              e.preventDefault(); setDrag(false);
              const f = e.dataTransfer.files?.[0];
              if (f) setFile(f);
            }}
            onClick={() => inputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition ${
              drag
                ? "border-emerald-400 bg-emerald-500/5"
                : "border-white/15 hover:border-white/30"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept="video/*"
              className="hidden"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
            />
            {file ? (
              <div>
                <div className="text-emerald-400 text-lg">✓</div>
                <div className="mt-2 font-medium">{file.name}</div>
                <div className="text-sm text-white/50">
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </div>
              </div>
            ) : (
              <div>
                <div className="text-3xl">📁</div>
                <div className="mt-2 text-white/80">Drop a video here or click to pick</div>
                <div className="text-sm text-white/40 mt-1">MP4, MOV, WEBM</div>
              </div>
            )}
          </div>

          <button
            disabled={!file || busy}
            onClick={submitFile}
            className="mt-6 w-full rounded-xl bg-emerald-500 text-black font-medium py-3 disabled:opacity-40 hover:bg-emerald-400 transition"
          >
            {busy ? "Uploading…" : "Start processing"}
          </button>
        </div>
      )}

      {tab === "youtube" && (
        <div>
          <label className="text-sm text-white/60">YouTube URL</label>
          <input
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=…"
            className="mt-2 w-full rounded-xl bg-white/[0.04] border border-white/10 px-4 py-3 outline-none focus:border-emerald-400/60"
          />
          <p className="text-xs text-white/40 mt-2">
            Single video only. Downloads with yt-dlp at best quality.
          </p>
          <button
            disabled={!url.trim() || busy}
            onClick={submitUrl}
            className="mt-6 w-full rounded-xl bg-emerald-500 text-black font-medium py-3 disabled:opacity-40 hover:bg-emerald-400 transition"
          >
            {busy ? "Starting download…" : "Download & process"}
          </button>
        </div>
      )}

      {err && (
        <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-200 text-sm px-4 py-3">
          {err}
        </div>
      )}
    </div>
  );
}

export default function UploadPage() {
  return (
    <Suspense fallback={<div className="text-white/60">Loading…</div>}>
      <UploadInner />
    </Suspense>
  );
}
