# Dock Finder — Bay Wheels

A phone map that answers the one question the Lyft app won't:
**where do I park this e-bike when I get there?**

Type a destination and it walks you through the trip one leg at a time:

1. **Get bike** — walk to the nearest e-bike, docked *or* free-floating
2. **Ride** — to the nearest rack to your destination that has a real free dock
3. **Arrive** — walk the last block

One card, one button, one decision per screen. The button never moves.

## Why it exists

The Bay Wheels app routes you to bikes, not to racks. When you're riding
somewhere specific you want the rack nearest your destination, confirmation it
has room, and a backup for when someone fills it while you're en route.

## The three legs

Each step shows exactly one card, one collapsed drawer of alternates, and one
full-width action button pinned to the same spot on screen.

| Step | Shows | Map | Button |
|---|---|---|---|
| Get bike | nearest e-bike, its battery range, walk time | dashed walk line | "I've got the bike" |
| Ride | rack with room, open docks, walk-to-door time | solid ride line | "I'm parked" |
| Arrive | your destination, distance from the rack | dashed walk line | "Done" |

The rail at the top of the sheet shows where you are; completed steps stay
tappable so you can go back. Arriving at the bike *arms* the button (buzz +
highlight) but never taps it for you — standing at a rack is not the same event
as having a bike in your hands. Parking auto-advances with a 10-second "Not
parked yet" undo. Nothing in the flow is irreversible.

"I'm already on a bike" is a link on step 1 that jumps straight to the ride.

## What it gets right that the naive version doesn't

**Virtual stations are excluded from parking.** 25 of the 633 stations are
`station_type: "lightweight"` — a Lyft extension meaning a painted zone at
ordinary public bike racks, with no docking hardware. Their status is frozen:
median **1,016 days stale**, worst 1,119. They still advertise
`is_returning: 1` and a healthy dock count, so a distance-only search sends you
to Golden Gate Park chasing "19 open docks" last confirmed in 2023. They now
appear only in the backups drawer, labelled, with no dock number attached.

**Free-floating e-bikes are included for pickup.** ~580 e-bikes carry no
`station_id` and are invisible to the station feed, roughly a fifth of the
fleet. They're listed by the plate number printed on the bike, with battery
range from the v2.3 feed (median ~14 mi). They're never offered as somewhere to
*park* — a loose bike marks where someone left one, not a sanctioned spot.

**Targets lock as you commit to them.** The pickup freezes once you're riding.
The dropoff only re-picks if it loses its last dock or something beats it by a
clear margin, so a rack two doors down gaining one dock can't flip your
destination mid-ride. A rack you picked by hand is never overridden silently.

**Ranking.** Sorted by straight-line distance, then a tiebreak: among racks
within 150 m of the closest, the one with the most free docks wins. Racks
reporting nothing for 30+ minutes are never auto-picked; 5+ minutes gets a
stale flag.

## Live location

`watchPosition`, with the failure modes that actually bite on iOS handled:

- The ◎ button distinguishes **live and following** (solid), **live but you
  panned away** (ring), **asking** (pulse), and **blocked** (red). It used to go
  dark the moment you searched, which reads exactly like tracking died.
- A watch that was denied or timed out is torn down and genuinely retried on
  tap, so fixing the permission in Settings actually takes effect.
- `geoState: 'live'` only means a fix arrived *once*; a freshness check catches
  a watch iOS suspended on screen lock and re-arms it when you come back.
- A 12-second watchdog reports it when iOS never answers at all.
- High-accuracy timeouts retry once at coarse accuracy — indoors that's usually
  the difference between a fix and nothing.
- Errors can't be silently erased by an unrelated toast finishing.

**Tap the footer for a diagnostic panel** — secure context, permission state,
watch id, seconds since last fix, accuracy, last error code, and whether you're
running as a home-screen app. That's what to read from if it misbehaves.

## Data

| Thing | Source |
|---|---|
| Stations + live dock counts | `gbfs.lyft.com/gbfs/1.1/bay/en/` — 633 stations, CORS-open |
| Free-floating e-bikes + range | same host, `2.3/.../free_bike_status.json` |
| E-bike plate numbers | `1.1/.../free_bike_status.json` (v2.3 drops the plate) |
| Address search | `photon.komoot.io`, fallback `nominatim.openstreetmap.org` |
| Cycling + walking routes | `routing.openstreetmap.de` (`routed-bike`, `routed-foot`) |
| Tiles | `tile.openstreetmap.org` — CARTO's free basemaps now watermark every tile |

No API keys, no backend, one static page.

**Data use:** station status is ~240 KB per refresh, every 60 s. The free-bike
feed (~180 KB) is only fetched while you're looking for a bike, not while
riding. Budget roughly 15 MB an hour with the app open on cellular.

## Known limits

- Dock counts run 1–3 minutes behind reality: feed generation, CDN edge cache,
  and per-station reporting all add lag. A rack showing 1 free dock can be full
  when you arrive — that's what the backups drawer is for.
- Distances to candidate racks are straight-line; only the drawn route is
  road-network accurate.
- Bay Wheels runs two e-bike fleets, cable-lock and dock-only, and the feed has
  no field distinguishing them. Virtual stations only work for cable-lock bikes,
  which is why they're never the automatic pick.
- iOS suspends `watchPosition` when the screen locks. It resumes on wake, and
  the app re-checks both the watch and the station data when it becomes visible.
- No background location — no web API provides it on any platform. This app is
  meant to be looked at.

## Running it

```bash
python serve.py 8731
```

Run from inside this folder. Use this rather than `python -m http.server`: on
Windows the stock server reads MIME types from the registry and serves `.js` as
`text/plain`, which makes the browser reject the service worker. `serve.py` pins
the right types and is threaded (single-threaded deadlocks on the browser's
keep-alive connection).

### On your phone

Live at **https://jaimelub17.github.io/projects/bay-dock-finder/**

Open in Safari, allow location, then Share → Add to Home Screen. It launches
full-screen and opens offline (the shell is cached; live data never is).

Location needs a secure context — HTTPS or `localhost`. A plain LAN address like
`http://10.0.0.59:8731` shows the map but never the blue dot.
