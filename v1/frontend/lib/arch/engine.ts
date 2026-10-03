/**
 * Simulation of the CensorNet pipeline. It is a small, deterministic copy of what the real backend does,
 * stepped one "tick" at a time:
 *
 *   upload -> FastAPI -> PostgreSQL rows + Redis "prepare" task -> worker splits the video into chunks
 *   -> chunks become Redis queue members (score = priority) and PostgreSQL rows (status = pending)
 *   -> workers pop the lowest score, claim the row, analyse + render, save the result
 *   -> segments land on disk, the player pulls them; a seek re-scores the whole queue.
 *
 * The rules (tiers, scores, claim, lease) are the ones in backend/app/services/queue_service.py.
 * No randomness: the same inputs always give the same story.
 */
import { PATH, type Pt } from "./layout";

/* ------------------------------------------------------------------ constants */
export const N = 12; // chunks in the demo video
export const WORKERS = 3;
export const CHUNK_SECONDS = 4;
export const PREFETCH = 3; // PREFETCH_CHUNKS in the backend
export const VIDEO_ID = 1;
export const TICK_MS = 650;
export const VIDEO_SECONDS = N * CHUNK_SECONDS;

const UPLOAD_TICKS = 2;
const PREPARE_TICKS = 2;
const ANALYZE_TICKS = 3; // frames + speech run in parallel
const RENDER_TICKS = 2; // +1 when something has to be blurred (full-resolution pipe)
const DWELL_TICKS = 3; // how long the viewer "watches" one chunk
const DONE_HOLD_TICKS = 8;
const TOUR_TARGET = 9;
const BASE_TIME = Date.UTC(2026, 9, 3, 10, 0, 0);

/** Priority scores - lower is popped first. Same numbers as queue_service.py. */
export const SCORE = { prepare: -10_000_000, stall: -2_000_000, urgent: -1_000_000, behind: 100_000 } as const;

/* ------------------------------------------------------------------ types */
export type RowStatus = "absent" | "pending" | "processing" | "completed";
export type Tier = "prepare" | "stall" | "urgent" | "ahead" | "behind";
export type FlightKind = "upload" | "doc" | "task" | "pop" | "claim" | "result" | "segment" | "serve" | "seek";
export type LogTone = "info" | "queue" | "db" | "worker" | "play" | "seek";

export interface Detection {
  label: string;
  category: string;
  score: number;
  t_start: number;
  t_end: number;
  box: [number, number, number, number] | null;
  action: "blur";
}
export interface AudioEvent { start: number; end: number; words: string[]; label: "profanity" }

export interface ChunkRow {
  index: number;
  status: RowStatus;
  attempts: number;
  worker: number | null;
  startedTick: number | null;
  finishedTick: number | null;
  processMs: number;
  detections: Detection[];
  audioEvents: AudioEvent[];
  version: number; // bumps whenever the row changes (drives the "row updated" flash)
}

export interface QueueEntry {
  member: string;
  kind: "prepare" | "chunk";
  index: number;
  score: number;
  tier: Tier;
  bornTick: number;
  changedTick: number;
}

export interface WorkerSim {
  id: number;
  task: { kind: "prepare" | "chunk"; index: number } | null;
  step: number;
  total: number;
  freed: boolean;
}

export interface Lease { member: string; worker: number; bornTick: number; total: number }
export interface Flight { id: number; tick: number; kind: FlightKind; label: string; pts: Pt[]; dur: number }
export interface LogLine { tick: number; tone: LogTone; text: string }
export interface Caption { step: number; title: string; text: string; until: number }

export interface Sim {
  tick: number;
  phase: "upload" | "run" | "done";
  phaseTick: number;
  videoExists: boolean;
  job: { exists: boolean; status: "preparing" | "processing" | "completed"; completed: number; total: number };
  rows: ChunkRow[];
  queue: QueueEntry[];
  leases: Lease[];
  workers: WorkerSim[];
  segments: boolean[];
  segmentTick: (number | null)[];
  playerOn: boolean;
  playhead: number;
  dwell: number;
  stalledOn: number | null;
  ended: boolean;
  seeks: number;
  userSeeked: boolean;
  tourDone: boolean;
  lastTouched: number | null; // the row the inspector follows when nothing is selected
  flights: Flight[];
  nextFlightId: number;
  log: LogLine[];
  caption: Caption;
  focus: number[]; // stepper stages active this tick
  lastFocus: Record<number, number>;
  doneTicks: number;
}

/* ------------------------------------------------------------------ what the demo video contains */
interface Fixture { det?: Omit<Detection, "action">[]; beeps?: Omit<AudioEvent, "label">[] }
const FIXTURE: Record<number, Fixture> = {
  1: { beeps: [{ start: 5.2, end: 5.78, words: ["f***"] }] },
  3: { det: [{ label: "weapon", category: "weapon", score: 0.91, t_start: 12.4, t_end: 14.6, box: [0.52, 0.32, 0.22, 0.34] }] },
  5: { det: [{ label: "FEMALE_BREAST_EXPOSED", category: "nudity", score: 0.62, t_start: 21.2, t_end: 22.9, box: [0.3, 0.4, 0.2, 0.25] }] },
  6: { det: [{ label: "blood", category: "blood", score: 0.71, t_start: 24.6, t_end: 27.1, box: [0.4, 0.5, 0.3, 0.3] }] },
  8: {
    det: [{ label: "weapon", category: "weapon", score: 0.84, t_start: 33.0, t_end: 35.2, box: [0.2, 0.3, 0.25, 0.3] }],
    beeps: [{ start: 34.1, end: 34.6, words: ["shit"] }],
  },
  10: { beeps: [{ start: 41.3, end: 41.9, words: ["bastard"] }] },
};
const hasVisual = (i: number) => (FIXTURE[i]?.det?.length ?? 0) > 0;

/* ------------------------------------------------------------------ small helpers */
const pad = (n: number) => String(n).padStart(2, "0");
export const memberOf = (kind: "prepare" | "chunk", i: number) => (kind === "prepare" ? `p:${VIDEO_ID}` : `c:${VIDEO_ID}:${i}`);
export const segName = (i: number) => `seg_${String(i).padStart(5, "0")}.ts`;
export const tickToSeconds = (t: number) => (t * TICK_MS) / 1000;
export const iso = (tick: number) => new Date(BASE_TIME + tick * TICK_MS).toISOString();
export const clock = (sec: number) => `${Math.floor(sec / 60)}:${pad(Math.floor(sec % 60))}`;
export const fmtScore = (n: number) => (n < 0 ? "\u2212" : "") + Math.abs(n).toLocaleString("en-US");

const clone = <T,>(x: T): T => structuredClone(x);

/** Same rules as priority_for() in queue_service.py. d = chunk - playhead. */
export function priorityFor(idx: number, playhead: number, stalled: number | null): { score: number; tier: Tier } {
  const d = idx - playhead;
  if (stalled !== null && idx === stalled) return { score: SCORE.stall + Math.max(d, 0), tier: "stall" };
  if (d >= 0 && d < PREFETCH) return { score: SCORE.urgent + d, tier: "urgent" };
  if (d >= 0) return { score: d, tier: "ahead" };
  return { score: SCORE.behind + -d, tier: "behind" };
}

export function sortedQueue(s: Sim): QueueEntry[] {
  return [...s.queue].sort((a, b) => a.score - b.score || a.index - b.index);
}

function blankRow(i: number): ChunkRow {
  return { index: i, status: "absent", attempts: 0, worker: null, startedTick: null, finishedTick: null, processMs: 0, detections: [], audioEvents: [], version: 0 };
}

function say(s: Sim, step: number, title: string, text: string, force = false, hold = 3) {
  if (!force && s.tick < s.caption.until) return;
  s.caption = { step, title, text, until: s.tick + hold };
}
function log(s: Sim, tone: LogTone, text: string) {
  s.log.push({ tick: s.tick, tone, text });
  if (s.log.length > 60) s.log.shift();
}
function mark(s: Sim, ...steps: number[]) {
  for (const k of steps) {
    if (!s.focus.includes(k)) s.focus.push(k);
    s.lastFocus[k] = s.tick;
  }
}
function fly(s: Sim, kind: FlightKind, label: string, pts: Pt[], dur = 0.9) {
  s.flights.push({ id: ++s.nextFlightId, tick: s.tick, kind, label, pts, dur });
}

/* ------------------------------------------------------------------ initial state */
export function initSim(): Sim {
  const s: Sim = {
    tick: 0, phase: "upload", phaseTick: 0, videoExists: false,
    job: { exists: false, status: "preparing", completed: 0, total: 0 },
    rows: Array.from({ length: N }, (_, i) => blankRow(i)),
    queue: [], leases: [],
    workers: Array.from({ length: WORKERS }, (_, id) => ({ id, task: null, step: 0, total: 0, freed: false })),
    segments: Array(N).fill(false), segmentTick: Array(N).fill(null),
    playerOn: false, playhead: 0, dwell: 0, stalledOn: null, ended: false, seeks: 0,
    userSeeked: false, tourDone: false, lastTouched: null,
    flights: [], nextFlightId: 0, log: [],
    caption: { step: 1, title: "", text: "", until: 0 },
    focus: [], lastFocus: {}, doneTicks: 0,
  };
  fly(s, "upload", "demo.mp4", PATH.upload, 1.4);
  mark(s, 1);
  say(s, 1, "Upload", "The browser streams demo.mp4 to FastAPI, which saves it to disk.", true, 3);
  log(s, "info", `POST /videos/upload  demo.mp4 (${VIDEO_SECONDS} s)`);
  return s;
}

/* ------------------------------------------------------------------ the tick */
export function step(prev: Sim): Sim {
  const s = clone(prev);
  s.tick += 1;
  s.phaseTick += 1;
  s.flights = s.flights.filter((f) => s.tick - f.tick < 2);
  s.focus = [];

  if (s.phase === "upload") {
    mark(s, 1);
    if (s.phaseTick >= UPLOAD_TICKS) register(s);
    return s;
  }

  advanceWorkers(s);
  playback(s);

  if (s.phase === "run" && s.job.status === "completed" && s.ended) {
    s.phase = "done";
    say(s, 6, "All done", "Every chunk is censored and recorded in PostgreSQL. Redis could be wiped now and nothing would be lost.", true, 6);
    log(s, "info", "job completed: " + N + "/" + N + " chunks");
  }
  if (s.phase === "done") s.doneTicks += 1;
  return s;
}

/** Wraps step() with the scripted "tour": one automatic seek so a first-time visitor sees re-prioritisation. */
export function director(s: Sim): Sim {
  if (s.phase === "done" && s.doneTicks >= DONE_HOLD_TICKS) return initSim();
  if (!s.tourDone && !s.userSeeked && s.phase === "run" && s.playerOn && s.job.completed >= 3 && s.playhead < 6) {
    const t = seek(s, TOUR_TARGET);
    t.tourDone = true;
    return t;
  }
  return s;
}

/* ------------------------------------------------------------------ 1. upload -> register */
function register(s: Sim) {
  s.phase = "run";
  s.phaseTick = 0;
  s.videoExists = true;
  s.job = { exists: true, status: "preparing", completed: 0, total: 0 };
  const entry: QueueEntry = { member: memberOf("prepare", 0), kind: "prepare", index: -1, score: SCORE.prepare, tier: "prepare", bornTick: s.tick, changedTick: 0 };
  s.queue.push(entry);
  fly(s, "doc", "INSERT video + job", PATH.corridor, 1.5);
  fly(s, "task", "p:1", PATH.enqueue(0), 1.1);
  mark(s, 2, 3);
  say(s, 2, "Register", "FastAPI writes a video row and a job row to PostgreSQL, the permanent record, and pushes one \u201Cprepare\u201D task into Redis.", true, 4);
  log(s, "db", "INSERT INTO videos, jobs  (job 1: preparing)");
  log(s, "queue", `ZADD vc:queue ${fmtScore(SCORE.prepare)} p:1`);
}

/* ------------------------------------------------------------------ 2. workers */
function advanceWorkers(s: Sim) {
  for (const w of s.workers) {
    w.freed = false;
    if (!w.task) continue;
    w.step += 1;
    mark(s, 4);
    if (w.step >= w.total) (w.task.kind === "prepare" ? finishPrepare : finishChunk)(s, w);
  }
  for (const w of s.workers) {
    if (!w.task && !w.freed) popFor(s, w);
  }
}

function popFor(s: Sim, w: WorkerSim) {
  const head = sortedQueue(s)[0];
  if (!head) return;
  const rank = 0;
  s.queue = s.queue.filter((e) => e.member !== head.member);
  s.leases.push({ member: head.member, worker: w.id, bornTick: s.tick, total: 0 });
  fly(s, "pop", head.member, PATH.pop(rank, w.id), 0.9);
  mark(s, 4);

  if (head.kind === "prepare") {
    w.task = { kind: "prepare", index: -1 };
    w.step = 0;
    w.total = PREPARE_TICKS;
    s.leases[s.leases.length - 1].total = w.total;
    say(s, 4, "A worker takes the task", `Worker ${w.id + 1} pops p:1 (lowest score = first out), probes the file with ffprobe and prepares to split it into ${N} chunks of ${CHUNK_SECONDS} s.`);
    log(s, "worker", `worker-${w.id + 1} ZPOPMIN \u2192 p:1  (lease 90 s in vc:inflight)`);
    return;
  }

  const i = head.index;
  const row = s.rows[i];
  row.status = "processing";
  row.attempts += 1;
  row.worker = w.id;
  row.startedTick = s.tick;
  row.version += 1;
  s.lastTouched = i;
  w.task = { kind: "chunk", index: i };
  w.step = 0;
  w.total = ANALYZE_TICKS + RENDER_TICKS + (hasVisual(i) ? 1 : 0);
  s.leases[s.leases.length - 1].total = w.total;
  fly(s, "claim", "claim", PATH.toRow(w.id, i, 18), 1.0);
  say(s, 4, "Pop and claim", `Worker ${w.id + 1} pops c:1:${i} (score ${fmtScore(head.score)}) and claims its row with an atomic UPDATE \u2026 WHERE status = 'pending', so no other worker can take it.`);
  log(s, "worker", `worker-${w.id + 1} ZPOPMIN \u2192 c:1:${i}  (${fmtScore(head.score)})`);
  log(s, "db", `UPDATE chunks SET status='processing' WHERE index=${i} AND status='pending'  \u2192 1 row`);
}

function finishPrepare(s: Sim, w: WorkerSim) {
  s.leases = s.leases.filter((l) => l.worker !== w.id || l.member !== memberOf("prepare", 0));
  w.task = null;
  w.freed = true;

  for (const row of s.rows) {
    row.status = "pending";
    row.version += 1;
  }
  s.job = { exists: true, status: "processing", completed: 0, total: N };
  for (let i = 0; i < N; i++) {
    const { score, tier } = priorityFor(i, 0, null);
    s.queue.push({ member: memberOf("chunk", i), kind: "chunk", index: i, score, tier, bornTick: s.tick, changedTick: 0 });
  }
  s.playerOn = true;
  fly(s, "doc", `INSERT \u00D7${N} chunks`, PATH.toTable(w.id), 1.0);
  fly(s, "task", `ZADD \u00D7${N}`, PATH.toQueue(w.id), 1.0);
  mark(s, 2, 3);
  say(s, 3, "Split into chunks", `The video becomes ${N} chunks: ${N} pending rows in PostgreSQL and ${N} members in the Redis queue. Their score is how far they are from the playhead.`, true, 4);
  log(s, "db", `INSERT INTO chunks \u00D7${N}  (status = pending)`);
  log(s, "queue", `ZADD vc:queue \u00D7${N}  (chunk 0 \u2192 ${fmtScore(SCORE.urgent)}, chunk 5 \u2192 5)`);
}

function finishChunk(s: Sim, w: WorkerSim) {
  const i = w.task!.index;
  const row = s.rows[i];
  const fx = FIXTURE[i];
  row.status = "completed";
  row.finishedTick = s.tick;
  row.detections = (fx?.det ?? []).map((d) => ({ ...d, action: "blur" as const }));
  row.audioEvents = (fx?.beeps ?? []).map((b) => ({ ...b, label: "profanity" as const }));
  row.processMs = 3100 + ((i * 37) % 9) * 80 + (hasVisual(i) ? 900 : 0);
  row.version += 1;
  s.segments[i] = true;
  s.segmentTick[i] = s.tick;
  s.job.completed += 1;
  if (s.job.completed >= N) s.job.status = "completed";
  s.lastTouched = i;
  s.leases = s.leases.filter((l) => l.member !== memberOf("chunk", i));
  w.task = null;
  w.freed = true;

  fly(s, "result", "result", PATH.toRow(w.id, i, 34), 1.0);
  fly(s, "segment", segName(i), PATH.toDisk(w.id, i), 1.1);
  mark(s, 5);
  const found = [...row.detections.map((d) => d.category), ...(row.audioEvents.length ? ["beep"] : [])];
  say(s, 5, "Save the result", found.length
    ? `Chunk ${i} had ${found.join(" + ")}. The blur and the beep are baked into ${segName(i)}, and what was found is written into the chunk's row.`
    : `Chunk ${i} is clean. ${segName(i)} is written to disk and the row is marked completed.`);
  log(s, "db", `UPDATE chunks SET status='completed', detections=${row.detections.length}, audio_events=${row.audioEvents.length}  (chunk ${i}, ${row.processMs} ms)`);
}

/* ------------------------------------------------------------------ 3. the viewer */
function playback(s: Sim) {
  if (!s.playerOn || s.ended) return;
  const want = s.playhead;

  if (s.segments[want]) {
    if (s.stalledOn === want) {
      s.stalledOn = null;
      log(s, "play", `GET ${segName(want)} \u2192 200 (it was waiting)`);
    }
    if (s.dwell === 0) {
      fly(s, "serve", segName(want), PATH.serve(want), 0.9);
      mark(s, 6);
      say(s, 6, "Stream", `The player asks for ${segName(want)}. If it is on disk the API serves it straight away; the censoring is already in the video.`);
      log(s, "play", `GET /videos/1/segments/${want}.ts \u2192 200`);
    }
    s.dwell += 1;
    mark(s, 6);
    if (s.dwell >= DWELL_TICKS) {
      s.dwell = 0;
      if (want + 1 >= N) {
        s.ended = true;
        return;
      }
      s.playhead = want + 1;
      rescore(s, s.playhead, null); // the /playhead ping: what comes next stays in order
    }
    return;
  }

  // The player needs a segment that is not on disk yet.
  if (s.stalledOn !== want) {
    s.stalledOn = want;
    const row = s.rows[want];
    const n = rescore(s, want, want);
    fly(s, "seek", `GET ${want}.ts`, PATH.seek(want), 1.1);
    mark(s, 6, 7);
    if (row.status === "processing" && row.worker !== null) {
      // A worker already has it: nothing to re-order, the viewer just waits for that worker.
      say(s, 6, "Waiting for the segment", `The player asks for ${segName(want)}, but Worker ${row.worker + 1} is still working on it, so the player waits.`);
      log(s, "play", `GET ${segName(want)} \u2192 held until worker-${row.worker + 1} finishes`);
    } else {
      say(s, 7, "Not ready, so it jumps the queue", `${segName(want)} is not ready, so the API gives it the STALL score (${fmtScore(SCORE.stall)}). The next free worker takes it before anything else.`, true, 4);
      log(s, "seek", `GET ${segName(want)} \u2192 not ready \u2192 STALL (${fmtScore(SCORE.stall)}), ${n} queued chunks re-scored`);
    }
  }
}

/** Re-score every chunk that is still queued. Mirrors queue_service.reprioritize() (ZADD XX). */
function rescore(s: Sim, playhead: number, stalled: number | null): number {
  let n = 0;
  for (const e of s.queue) {
    if (e.kind !== "chunk") continue;
    const { score, tier } = priorityFor(e.index, playhead, stalled);
    if (score !== e.score) e.changedTick = s.tick;
    e.score = score;
    e.tier = tier;
    n += 1;
  }
  return n;
}

/** The viewer jumped to chunk `idx` (clicked the timeline, or the scripted tour did). */
export function seek(prev: Sim, idx: number, byUser = false): Sim {
  if (!prev.playerOn) return prev;
  const s = clone(prev);
  s.tick = prev.tick; // same moment; flights below are stamped with it
  idx = Math.max(0, Math.min(N - 1, idx));
  s.playhead = idx;
  s.dwell = 0;
  s.ended = false;
  s.seeks += 1;
  if (byUser) s.userSeeked = true;
  if (s.phase === "done") { s.phase = "run"; s.doneTicks = 0; } // watching again: do not auto-restart under the viewer

  const ready = s.segments[idx];
  const busy = s.rows[idx].status === "processing";
  s.stalledOn = ready ? null : idx;
  const n = rescore(s, idx, ready ? null : idx);
  fly(s, "seek", `SEEK ${idx}`, PATH.seek(idx), 1.2);
  mark(s, 7);

  const t = clock(idx * CHUNK_SECONDS);
  const lead = ready
    ? `Chunk ${idx} is already censored, so it plays at once.`
    : busy
      ? `Chunk ${idx} is being processed right now; the viewer waits for it.`
      : `Chunk ${idx} is not ready, so it gets the STALL score (${fmtScore(SCORE.stall)}) and is next out of the queue.`;
  const lo = ready ? idx : idx + 1;
  const hi = Math.min(N - 1, idx + PREFETCH - 1);
  const urgent = lo > hi ? "" : lo === hi ? `chunk ${lo} becomes urgent` : `chunks ${lo}\u2013${hi} become urgent`;
  say(s, 7, `You jumped to ${t}`, `${lead} One command re-scores the ${n} queued chunks: ${urgent ? urgent + ", " : ""}the rest follow in order, and chunks you skipped go last.`, true, 6);
  log(s, "seek", `POST /seek {t:${idx * CHUNK_SECONDS}} \u2192 ZADD XX  re-scored ${n} queued chunks (playhead = ${idx})`);
  return s;
}

/* ------------------------------------------------------------------ derived data for the views */
export interface DocField { key: string; value: unknown }

/** The row exactly as PostgreSQL stores it (same columns as backend/app/models/chunk.py). */
export function rowRecord(s: Sim, i: number): DocField[] | null {
  const r = s.rows[i];
  if (!r || r.status === "absent") return null;
  return [
    { key: "id", value: i + 1 },
    { key: "video_id", value: VIDEO_ID },
    { key: "index", value: i },
    { key: "status", value: r.status },
    { key: "attempts", value: r.attempts },
    { key: "worker", value: r.worker === null ? null : `worker-${r.worker + 1}` },
    { key: "started_at", value: r.startedTick === null ? null : iso(r.startedTick) },
    { key: "finished_at", value: r.finishedTick === null ? null : iso(r.finishedTick) },
    { key: "process_ms", value: r.status === "completed" ? r.processMs : 0 },
    { key: "censored", value: r.status === "completed" ? r.detections.length + r.audioEvents.length > 0 : false },
    { key: "detections", value: r.detections },
    { key: "audio_events", value: r.audioEvents },
    { key: "error", value: null },
  ];
}

export function tierCounts(s: Sim): Record<Tier, number> {
  const c: Record<Tier, number> = { prepare: 0, stall: 0, urgent: 0, ahead: 0, behind: 0 };
  for (const e of s.queue) c[e.tier] += 1;
  return c;
}

export function workerProgress(w: WorkerSim): { a: number; b: number; c: number } {
  if (!w.task) return { a: 0, b: 0, c: 0 };
  if (w.task.kind === "prepare") {
    const p = Math.min(1, w.step / w.total);
    return { a: Math.min(1, p * 2), b: Math.max(0, Math.min(1, p * 2 - 1)), c: 0 };
  }
  const a = Math.min(1, w.step / ANALYZE_TICKS);
  const c = Math.max(0, Math.min(1, (w.step - ANALYZE_TICKS) / Math.max(1, w.total - ANALYZE_TICKS)));
  return { a, b: a, c };
}

/** Next chunk worth jumping to for the "jump ahead" button. */
export function jumpTarget(s: Sim, dir: 1 | -1): number {
  if (dir < 0) return Math.max(0, s.playhead - 4);
  for (let i = Math.min(N - 1, s.playhead + 3); i < N; i++) if (!s.segments[i]) return i;
  return Math.min(N - 1, s.playhead + 4);
}

export const STAGES = ["Upload", "Register", "Queue", "Process", "Store", "Stream", "Re-prioritise"] as const;
