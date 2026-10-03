# Architecture animation

An animated, interactive picture of how a video travels through the system:
upload → FastAPI → Redis priority queue → workers → PostgreSQL rows + segment files → player, and back to Redis when the viewer seeks.

Used in two places:
- `/architecture` – the full version (`ArchitectureLab`): controls, seek by clicking the timeline, click a PostgreSQL row to open its document.
- homepage – `components/home/ArchitecturePreview.tsx`: the same diagram, plays by itself, read-only.

## How it is built
| File | Job |
|---|---|
| `lib/arch/engine.ts` | The simulation. Pure functions, no randomness. Mirrors `backend/app/services/queue_service.py` (same tiers and scores) and the `chunks` table columns. |
| `lib/arch/layout.ts` | Every coordinate in the picture and every packet path (one SVG, viewBox 1120×660). |
| `lib/arch/useSimulation.ts` | The clock. Ticks the engine; pauses when off-screen, in a background tab, or when paused. |
| `components/architecture/FlightLayer.tsx` | Packets. Animated with requestAnimationFrame straight on the SVG nodes. |
| `components/architecture/diagram/*` | The parts of the picture: `Frame`, `RedisQueue`, `WorkerPool`, `PostgresTable`, `Player`, `DocCard`. |
| `components/architecture/{Stepper,Caption,Controls,Inspector,PriorityPanel,EventLog}.tsx` | The HTML around it. |

Colours come from the theme tokens (`--c-*` in `app/globals.css`), so the animation follows the light/dark toggle. Redis and PostgreSQL got their own tokens (`--c-redis`, `--c-pg`).

## Things you may want to change (all in `lib/arch/engine.ts`)
- `N` – number of chunks in the demo video; `WORKERS` – number of worker cards (the layout fits 3).
- `TICK_MS` – length of one simulation step. `ANALYZE_TICKS`, `RENDER_TICKS`, `DWELL_TICKS` – how long things take.
- `FIXTURE` – what the demo video contains (which chunks have a weapon, blood, nudity or a beep).
- `TOUR_TARGET` – the chunk the automatic demo seek jumps to.

Respects `prefers-reduced-motion`: starts paused, packets jump instead of gliding.
