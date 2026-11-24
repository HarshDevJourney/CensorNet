import { formatTime, JobInfo } from "@/lib/api";
import Panel from "@/components/ui/Panel";

export default function JobStats({ job }: { job: JobInfo }) {
  const items: [string, string | number][] = [
    ["Length", formatTime(job.duration)],
    ["Playhead", `chunk #${job.playhead}`],
    ["Workers online", job.workers],
    ["Queue", job.queue_length],
  ];
  return (
    <Panel className="p-5">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
        {items.map(([label, value]) => (
          <div key={label}>
            <dt className="text-sm text-muted">{label}</dt>
            <dd className="mt-0.5 font-display text-2xl font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}
