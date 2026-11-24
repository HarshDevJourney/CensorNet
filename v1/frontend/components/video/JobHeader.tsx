import { JobInfo } from "@/lib/api";

interface Props {
  videoId: number;
  job: JobInfo;
  running: boolean;
}

export default function JobHeader({ videoId, job, running }: Props) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Video #{videoId}</h1>
        <p className="mt-1 text-sm text-muted">
          {job.source_type === "youtube" ? "From YouTube" : "Uploaded file"}
        </p>
      </div>
      <div className="text-sm font-medium">
        {job.status === "completed" && <Badge className="bg-ready text-white dark:text-[#06150f]">Fully censored</Badge>}
        {running && (
          <Badge className="bg-working text-[#101318]">
            {job.status === "downloading" ? "Downloading…" : `${job.completed}/${job.total} chunks`}
          </Badge>
        )}
        {job.status === "failed" && <Badge className="bg-failed text-white dark:text-[#2a0a07]">Failed</Badge>}
      </div>
    </div>
  );
}

function Badge({ className, children }: { className: string; children: React.ReactNode }) {
  return <span className={`inline-block rounded-full px-3.5 py-1.5 ${className}`}>{children}</span>;
}
