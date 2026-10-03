/**
 * Geometry of the architecture diagram. One SVG coordinate system (viewBox 1120 x 660) so the picture scales
 * as a whole, and so the simulation can say "fly a packet from here to there" with plain numbers.
 */
export type Pt = [number, number];

export const VB_W = 1120;
export const VB_H = 660;

/** SVG <rect> wants width/height; the layout table uses w/h. */
export const rectProps = (b: { x: number; y: number; w: number; h: number }) => ({ x: b.x, y: b.y, width: b.w, height: b.h });

/* ----- the big boxes ----- */
export const BOX = {
  upload: { x: 0, y: 44, w: 170, h: 64 },
  api: { x: 0, y: 190, w: 170, h: 150 },
  redis: { x: 240, y: 44, w: 210, h: 438 },
  pool: { x: 500, y: 44, w: 220, h: 438 },
  pg: { x: 790, y: 44, w: 330, h: 438 },
  player: { x: 0, y: 512, w: 700, h: 136 },
  doc: { x: 790, y: 512, w: 330, h: 136 },
} as const;

/* ----- redis queue: one slot per queued member, lowest score at the top ----- */
export const QUEUE_X = 252;
export const QUEUE_W = 186;
export const SLOT_H = 23;
export const slotY = (rank: number) => 108 + rank * 26;
export const LEASE_Y = 444;

/* ----- workers ----- */
export const WORKER_X = 512;
export const WORKER_W = 152;
export const WORKER_H = 88;
export const workerY = (w: number) => 92 + w * 98;

/* ----- disk (segment files) ----- */
export const RAIL_X = 684;
export const RAIL_END_Y = 392;
export const tilePos = (i: number) => ({ x: 524 + (i % 6) * 31, y: 406 + Math.floor(i / 6) * 28 });
export const TILE_W = 26;
export const TILE_H = 20;

/* ----- postgres table ----- */
export const PG_X = 798;
export const PG_W = 314;
export const ROW_H = 22;
export const rowY = (i: number) => 152 + i * 24;
export const BUS_X = 755;

/* ----- player timeline ----- */
export const CELL_X0 = 160;
export const CELL_PITCH = 45;
export const CELL_W = 41;
export const CELL_Y = 566;
export const CELL_H = 28;
export const cellX = (i: number) => CELL_X0 + i * CELL_PITCH;

/* ----- packet paths (all orthogonal, so they follow the drawn connectors) ----- */
export const PATH = {
  upload: [[85, 108], [85, 190]] as Pt[],
  /** API -> PostgreSQL, along the corridor under the main row */
  corridor: [[40, 340], [40, 494], [955, 494], [955, 482]] as Pt[],
  /** API -> a slot in the Redis queue */
  enqueue: (rank: number): Pt[] => [[170, 262], [245, 262], [QUEUE_X + 10, slotY(rank) + 12]],
  /** queue slot -> worker */
  pop: (rank: number, w: number): Pt[] => [
    [QUEUE_X + QUEUE_W, slotY(rank) + 12], [474, slotY(rank) + 12], [474, workerY(w) + 44], [WORKER_X, workerY(w) + 44],
  ],
  /** worker -> a row of the chunks table */
  toRow: (w: number, row: number, dy = 28): Pt[] => [
    [WORKER_X + WORKER_W, workerY(w) + dy], [BUS_X, workerY(w) + dy], [BUS_X, rowY(row) + 11], [PG_X, rowY(row) + 11],
  ],
  /** worker -> middle of the chunks table (bulk INSERT) */
  toTable: (w: number): Pt[] => [
    [WORKER_X + WORKER_W, workerY(w) + 28], [BUS_X, workerY(w) + 28], [BUS_X, 296], [PG_X, 296],
  ],
  /** worker -> top of the Redis queue (bulk ZADD) */
  toQueue: (w: number): Pt[] => [
    [WORKER_X, workerY(w) + 20], [474, workerY(w) + 20], [474, slotY(0) + 12], [QUEUE_X + QUEUE_W, slotY(0) + 12],
  ],
  /** worker -> segment tile on disk */
  toDisk: (w: number, i: number): Pt[] => {
    const t = tilePos(i);
    return [[WORKER_X + WORKER_W, workerY(w) + 66], [RAIL_X, workerY(w) + 66], [RAIL_X, RAIL_END_Y], [t.x + TILE_W / 2, RAIL_END_Y], [t.x + TILE_W / 2, t.y + 6]];
  },
  /** segment tile -> player cell */
  serve: (i: number): Pt[] => {
    const t = tilePos(i);
    return [[t.x + TILE_W / 2, t.y + TILE_H], [t.x + TILE_W / 2, 500], [cellX(i) + CELL_W / 2, 500], [cellX(i) + CELL_W / 2, CELL_Y]];
  },
  /** player -> API -> Redis (seek / stall request) */
  seek: (i: number): Pt[] => [
    [cellX(i) + CELL_W / 2, CELL_Y], [cellX(i) + CELL_W / 2, 526], [130, 526], [130, 300], [244, 300],
  ],
};

export function polyLength(pts: Pt[]): number {
  let total = 0;
  for (let i = 1; i < pts.length; i++) total += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  return total;
}

/** Point at distance d along a polyline (clamped to its ends). */
export function pointAt(pts: Pt[], d: number): Pt {
  if (d <= 0) return pts[0];
  let left = d;
  for (let i = 1; i < pts.length; i++) {
    const seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (left <= seg && seg > 0) {
      const t = left / seg;
      return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t];
    }
    left -= seg;
  }
  return pts[pts.length - 1];
}
