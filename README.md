# Projects

Data & analytics portfolio — Jaime Benitez.

| Project | Description | Stack |
|---|---|---|
| [Corporate Scorecard](corporate-scorecard/) | End-to-end governed financial KPI pipeline modeled on a hardware + subscription wearables business: dimensional model with SCD2, penny-exact reconciliation controls, DuckDB → Databricks migration, executive dashboard with full lineage. | dbt · SQL · Databricks · DuckDB · Python |
| [Stream Radar](stream-radar/) | Self-refreshing pipeline that predicts which game Twitch is about to crown next: snapshots Twitch viewership + Steam player charts every 2 hours via GitHub Actions, scores momentum and streamer-ignition events, and recommits a **[live breakout leaderboard](stream-radar/reports/breakout_watch.md)**
| [Dock Finder](bay-dock-finder/) | Phone web map that finds the Bay Wheels rack with a free dock nearest your destination — the question the Lyft app won't answer. Live GBFS dock counts, live GPS tracking, OSRM cycling routes, installable PWA that opens offline. No backend, no API keys. | JavaScript · Leaflet · GBFS · OSRM · PWA |
