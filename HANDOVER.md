# Gladiators App — Handover Document

## Project overview

A single-page web app for tracking a gym-attendance competition between John and Eve, running from spring/summer 2026 until **20 August 2026**. UK Gladiators (TV show) themed: when either user logs a workout, their muscle-bound, lycra-clad gladiator avatar swings a pugil stick and bashes the opposing avatar on the head with a “BOSH!” impact burst. Built as a single static HTML file talking to a Supabase backend with real-time sync between devices. Deployed on Netlify.

## Live deployment

- **Hosted on:** Netlify (free tier)
- **Backend:** Supabase (free tier, EU region)
- **Source:** Single `index.html` file — no build step, no framework, no package.json
- **Users:** John and Eve, both with the app added to their iOS/Android home screens via “Add to Home Screen”

## File structure

There is one file: `index.html`. That’s it. Everything is inline:

- Inline `<style>` block with all CSS
- Inline `<script>` blocks for config, then app logic
- Inline SVG for both gladiator characters
- Two CDN dependencies loaded via `<script>` tag: `@supabase/supabase-js@2` and `chart.js@4.4.1`

To deploy changes: edit `index.html` locally, drag onto Netlify (or use Netlify CLI / git-connected deploy if set up).

## Configuration

At the top of `index.html`, inside the first `<script>` block:

```javascript
const SUPABASE_URL  = "https://krpnvhcyjldyrhshvpdc.supabase.co";
const SUPABASE_KEY  = "sb_publishable_...";
```

The key is the new-format Supabase **publishable key** (starts with `sb_publishable_`), not the legacy `anon` JWT format (`eyJ...`). The `supabase-js` v2 client accepts both formats transparently.

## Database schema

One table in Supabase, `public.workouts`:

```sql
create table workouts (
  id uuid primary key default gen_random_uuid(),
  player text not null check (player in ('john', 'eve')),
  type text not null check (type in ('weights', 'swimming', 'running', 'class', 'no_booze_x3')),
  ts timestamptz not null default now(),
  created_at timestamptz not null default now()
);
```

### Row Level Security

RLS is **enabled** with three policies:

- `anyone can read` — `select using (true)`
- `anyone can insert` — `insert with check (true)`
- `anyone can delete` — `delete using (true)`

### Critical GRANTs (don’t forget these if recreating)

The new Supabase publishable-key system requires explicit table grants in addition to RLS policies, which is **not** mentioned in most older Supabase docs. Without these, you get `permission denied for table workouts` even with permissive RLS policies:

```sql
grant select, insert, delete on table workouts to anon;
grant select, insert, delete on table workouts to authenticated;
```

### Realtime

The table is added to the realtime publication so both clients see live updates:

```sql
alter publication supabase_realtime add table workouts;
```

## App architecture

### State

Single in-memory array `workouts` holds all records. No local persistence — the Supabase database is the single source of truth. On load:

1. `loadWorkouts()` fetches all rows ordered by `ts ascending`
1. `subscribeRealtime()` opens a websocket to listen for `INSERT` and `DELETE` events on the `workouts` table
1. When a remote insert arrives, the bash animation plays automatically for the logging player

### Logging flow

1. User taps a player toggle (`activePlayer` state, default `'john'`)
1. User taps a workout-type toggle (`activeType` state, default `'weights'`)
1. User taps ENGAGE button
1. `logWorkout()` calls `supa.from('workouts').insert(entry).select().single()`
1. On success, the new row is appended to local state, animation triggers, toast shows
1. Realtime subscription on the *other* user’s device receives the INSERT and triggers the same animation there within ~1 second

There’s deliberate duplicate-prevention logic (`if (!workouts.find(w => w.id === payload.new.id))`) so the local optimistic update and the realtime echo don’t double-count.

### Workout types

Five types, all worth 1 point — the breakdown panel shows per-type counts but the leaderboard treats them equally:

- `weights` 🏋
- `swimming` 🏊
- `running` 🏃
- `class` 💪
- `no_booze_x3` 🚫🍺 — log once per completed three-day alcohol-free stretch (added June 2026; see `migrations/2026-06-12-add-no-booze-x3.sql` for the constraint change it required)

### UI panels (in order down the page)

1. **Header** — title, countdown to 20 August, sync indicator (green dot when connected)
1. **Scoreboard** — big scores, “LEADING” badge for whoever’s ahead, “leads by N” text
1. **Arena** — both gladiator SVGs, neon stadium aesthetic, animation target
1. **Log workout panel** — player toggle, type toggle, ENGAGE button
1. **Event breakdown panel** — per-type counts side by side (hidden until any workouts exist)
1. **Leaderboard chart** — cumulative line chart per player using Chart.js (hidden until multiple days of data)
1. **Event history panel** — collapsed by default, shows every log with delete (✕) button per row

### Visual design system

- **Fonts:** `Bebas Neue` (display, headings, scores), `Oswald` (body, labels)
- **Palette:**
  - John: `#00d4ff` (cyan)
  - Eve: `#ff1f6d` (hot pink/magenta)
  - Accent yellow: `#ffeb00`
  - Backgrounds: dark navy/purple gradient `#0a0a1e → #2a0a4e`
- **Vibe:** 90s UK TV game-show neon, scanlines, glow shadows, skewed badges, exaggerated text-shadows
- The styling deliberately leans into kitsch — feel free to keep that energy when adding features

### Gladiator SVGs

Two inline SVGs in the `.arena` div, both within `viewBox="0 0 220 320"`:

- **John (left)** — dark hair, square jaw, bared teeth, blue lycra trunks with a yellow lightning bolt, cyan boots and wristbands
- **Eve (right)** — long blonde 90s mane, pink headband with yellow star, hot pink leotard with star detail, red lipstick, pink boots and wristbands; the entire SVG group is flipped via `transform="scale(-1, 1) translate(-220, 0)"` so she faces left

Both share the same body structure:

- `.body-group` — toggled with `.hit` class to apply a translate+rotate recoil
- `.club-arm` / `.club-arm-eve` — toggled with `.swing` class to rotate the pugil-stick arm from `25deg` (resting) to `-105deg` (mid-swing)

### Animation sequence (`triggerAnim(swinger)`)

1. Immediately: add `.swing` to the swinger’s club arm (CSS transition handles the rotation)
1. After 220ms: add `.hit` to target’s body (recoil) and `.shake` to target’s slot (screen shake), inject a `<div class="burst">` with the “BOSH!” SVG at the impact point
1. After 600ms: remove the burst element from DOM
1. After 750ms: remove `.swing`, `.hit`, `.shake` classes — system back to resting state

Burst position is `38%` or `62%` left depending on target.

## Known quirks and decisions

- **No authentication.** Anyone with the URL can read, insert, and delete. This is acceptable for two trusted users; URL is unguessable. If sharing more broadly, add a passphrase gate or Supabase auth.
- **Last-write-wins** for concurrent edits. If both users tap ENGAGE within the same millisecond, both inserts succeed (different UUIDs) and both count. No conflict possible.
- **The realtime echo fires `triggerAnim` for the logging player on the *remote* device.** This means John’s phone shows the bash when Eve logs from her phone — intentional and good. Local logs play the animation immediately via the optimistic insert, then the realtime echo arrives and is deduplicated.
- **Chart only shows when there are multiple days of data** (`labels.length > 1`). With a single day’s logs the breakdown panel is more useful.
- **Countdown auto-updates** every 60s via `setInterval`. Will display `0 DAYS` after the end date passes; doesn’t stop logging.
- **Sync indicator** is purely cosmetic — it goes red on initial load failure but doesn’t actively monitor connection health afterwards. Could be improved.

## Suggested future enhancements (not yet implemented)

If the user asks for any of these, here’s some context on each:

- **Streaks** — consecutive days each player has logged. Would go in the breakdown or scoreboard area.
- **Per-week breakdown** — show this week’s workouts separately from total.
- **Weekly winner stars** — award a star to whoever logged more in each completed week, display along bottom of scoreboard.
- **Editable workout types** — currently hardcoded; would need a `types` table or just a config array exposed in settings.
- **Notes per workout** — e.g. “5k run, 28 mins” — would need a `notes text` column on `workouts`.
- **Edit (not just delete) a logged workout** — change the type or attribution after the fact. Backend already supports it (RLS allows UPDATE if a policy is added), UI would need an edit affordance.
- **Sounds** — a satisfying THWACK on each bash. Use the Web Audio API or `<audio>` with a CDN sample.
- **Confetti / fanfare** — when one player reaches a milestone (10, 25, 50).
- **Endgame screen** — when the countdown hits zero, show a winner-takes-all overlay with both gladiators and the final score.
- **Daily reminder push notification** — would require service worker + push subscription setup; non-trivial but doable.

## Coding conventions for changes

- Keep it a single `index.html` file. The whole point is that John can host it on Netlify without a build pipeline.
- Vanilla JS only — no React, no bundlers, no TypeScript. The previous artifact version used React but the deployment version is plain DOM manipulation by design.
- Inline SVG for visuals; CDN for libraries.
- Use the existing CSS class system rather than introducing new utility frameworks.
- Don’t add new dependencies casually — each CDN script is a load-time cost and a point of failure.

## How to test changes locally

1. Edit `index.html` in any text/code editor
1. Double-click to open in browser
1. The app talks to the live Supabase database directly — no local backend needed
1. Use the Supabase Table Editor to inspect / clean up rows during testing
1. To reset to zero: `delete from workouts;` in Supabase SQL Editor

## How to deploy changes

1. Save edited `index.html`
1. Either:
- **Drag-drop:** go to Netlify dashboard, find the site, drag the new `index.html` into the deploy zone
- **Netlify CLI:** `netlify deploy --prod --dir=.` from the file’s directory (requires `npm install -g netlify-cli` and `netlify link`)
1. Hard-refresh on both phones to clear cache (or wait — Netlify cache is short)

## Credentials & access (for John to share with Claude Code if needed)

John will need to share:

- Path to local `index.html`
- Supabase project URL (already in the file, safe to share)
- Supabase publishable key (already in the file; safe-ish — has the permissions described above but no service-role access)
- Netlify site name (so deploys go to the right place)

The Supabase service-role key and database password are **not** in the HTML file and should never be added to it. They live in the Supabase dashboard only.

-----

Good luck. May the better gladiator win. ⚡