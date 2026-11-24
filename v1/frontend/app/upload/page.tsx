"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ingestYouTube, uploadVideo } from "@/lib/api";
import SourceTabs, { Tab } from "@/components/upload/SourceTabs";
import DropZone from "@/components/upload/DropZone";
import YouTubeForm from "@/components/upload/YouTubeForm";
import { Button } from "@/components/ui/Button";
import Alert from "@/components/ui/Alert";

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
      <h1 className="font-display text-4xl font-semibold tracking-tight sm:text-5xl">New video</h1>
      <p className="mb-8 mt-3 text-muted">Add a video and start watching while it is censored.</p>

      <SourceTabs tab={tab} onChange={setTab} />

      {tab === "file" && (
        <div>
          <DropZone
            file={file}
            drag={drag}
            inputRef={inputRef}
            onDragOver={e => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={e => {
              e.preventDefault(); setDrag(false);
              const f = e.dataTransfer.files?.[0];
              if (f) setFile(f);
            }}
            onPick={setFile}
          />
          <Button disabled={!file || busy} onClick={submitFile} className="mt-6 w-full py-3.5">
            {busy ? "Uploading…" : "Start processing"}
          </Button>
        </div>
      )}

      {tab === "youtube" && (
        <div>
          <YouTubeForm url={url} onChange={setUrl} />
          <Button disabled={!url.trim() || busy} onClick={submitUrl} className="mt-6 w-full py-3.5">
            {busy ? "Starting download…" : "Download & process"}
          </Button>
        </div>
      )}

      {err && <div className="mt-4"><Alert>{err}</Alert></div>}
    </div>
  );
}

export default function UploadPage() {
  return (
    <Suspense fallback={<div className="text-muted">Loading…</div>}>
      <UploadInner />
    </Suspense>
  );
}
