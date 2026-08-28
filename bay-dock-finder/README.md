# Dock Finder — Bay Wheels

A phone-sized web map that answers the one question the Lyft app won't:
**where do I park this e-bike when I get there?**

Pick a destination, and it shows the closest Bay Wheels rack that actually has a
free dock right now, the route to it, and a walking link for the last block.

## Why it exists

The Bay Wheels app routes you to bikes, not to racks. When you're already riding
and heading somewhere specific, you want the rack nearest your destination, with
confirmation that it has room, plus a backup in case someone fills it while
you're en route.

## What it does

- **Search a destination** (Photon, falling back to Nominatim), or long-press
  the map to drop a pin.
- **Park here** — the nearest rack to your destination with `docks > 0` and
  `is_returning = 1`, with live open-dock count, walk time from rack to
  destination, and a warning when only 1–2 docks are free.
- **Backups** — the next three racks. Tap one in the list *or* tap its numbered
  pin on the map to switch to it. Your pick sticks through auto-refreshes until
  you tap "Auto-pick" (or it fills up, which it tells you about).
- **Route start is always noted** — the rack closest to wherever the ride
  begins, so you know your bearings at both ends:
  - *Already riding* — routes from your live position; the start card shows the
    nearest rack to you (handy if you need to swap a bike out).
  - *Need a bike* — the nearest rack holding an e-bike, and the route runs
    rack → rack.
- **Live location tracking** via `watchPosition`: the blue dot and its accuracy
  ring follow you, distances update as you ride, and the map re-centres until
  you pan away (tap ◎ to re-follow).
- Refreshes station status every 60 s and on app resume; flags any station whose
  status is more than 30 minutes stale.
- Installs to your home screen and opens offline (app shell is cached; live data
  never is).

## Ranking

Candidates are sorted by straight-line distance to the destination, then a
tiebreak: among racks within 150 m of the closest, the one with the most free
docks wins. Two racks a few metres apart are the same walk — the one with 22
open docks is the better bet than the one with 12.

## Performance notes

A GPS tick every second must not mean a re-route every second:

- The plan is recomputed only when you've moved more than **70 m**, or 25 s have
  passed. In between, distances update from the existing plan — no network.
- Route requests carry a token; out-of-order replies are dropped, so overlapping
  requests can't stack polylines on the map.
- The route is keyed on origin (rounded to ~11 m) + destination rack, so GPS
  jitter doesn't refetch an identical route.
- The map only re-frames on a deliberate change (new destination, new rack
  pick) — never on a location update.

## Data

| Thing | Source |
|---|---|
| Stations + live dock/bike counts | `gbfs.lyft.com/gbfs/1.1/bay/en/` (`station_information`, `station_status`) — public, CORS-open, 633 stations Bay-wide |
| Address search | `photon.komoot.io`, fallback `nominatim.openstreetmap.org` |
| Cycling route | `routing.openstreetmap.de/routed-bike` (OSRM) |
| Tiles | CartoDB Voyager / OpenStreetMap |

All free, no API keys, no backend.

Stations the feed marks `station_type: "lightweight"` (25 of the 633) are
labelled *corral* — lock-to racks rather than classic dock points.

## Running it

```bash
python serve.py 8731
```

Run it from inside this folder. Use this rather than plain
`python -m http.server`: on Windows the stock server reads MIME types from the
registry and hands out `.js` as `text/plain`, which makes the browser reject the
service worker. `serve.py` pins the right types and is threaded (a
single-threaded server deadlocks on the browser's keep-alive connection).

### Getting it on your phone

**Live location needs a secure context** — HTTPS, or `localhost`. It does *not*
work over a plain LAN address, so `http://10.0.0.59:8731` from your phone will
show the map and search but the blue dot will never appear.

For the real thing, put it on any HTTPS static host (GitHub Pages works), open
it in Safari/Chrome, and use Share → Add to Home Screen. It then launches
full-screen with no browser chrome.

## Known limits

- Dock counts are as fresh as Lyft's feed (60 s TTL). A rack showing 1 free dock
  can be full by the time you arrive — that's what the backups are for.
- Distances to candidate racks are straight-line; only the chosen route is
  road-network accurate.
- Nominatim's usage policy caps you near one search per second. The box debounces
  at 350 ms and Photon is tried first, so normal use stays well under it.
- iOS pauses `watchPosition` when the screen locks. Position resumes on wake, and
  the app re-checks station data whenever it becomes visible again.
