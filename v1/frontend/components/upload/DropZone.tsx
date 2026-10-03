import type { DragEvent, RefObject } from "react";

interface Props {
  file: File | null;
  drag: boolean;
  inputRef: RefObject<HTMLInputElement>;
  onDragOver: (e: DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: DragEvent) => void;
  onPick: (file: File | null) => void;
}

export default function DropZone({ file, drag, inputRef, onDragOver, onDragLeave, onDrop, onPick }: Props) {
  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition sm:p-14 ${
        drag ? "border-accent bg-accent/5" : "border-ink/25 bg-surface hover:border-ink"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={e => onPick(e.target.files?.[0] ?? null)}
      />
      {file ? (
        <div>
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-ready text-xl text-white" aria-hidden>✓</div>
          <div className="mt-4 break-all font-display text-lg font-semibold">{file.name}</div>
          <div className="text-sm text-muted">{(file.size / 1024 / 1024).toFixed(1)} MB</div>
        </div>
      ) : (
        <div>
          <svg className="mx-auto h-10 w-10 text-ink" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <path d="M12 16V9m0 0-3 3m3-3 3 3" />
          </svg>
          <div className="mt-4 font-display text-lg font-semibold">Drop a video here or click to pick</div>
          <div className="mt-1 text-sm text-muted">MP4, MOV, WEBM</div>
        </div>
      )}
    </div>
  );
}
