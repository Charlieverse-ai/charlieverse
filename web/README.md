# Charlieverse Web Dashboard

Local web UI for browsing and managing your Charlieverse data.

## Stack

- React 19 + TypeScript
- Vite 7
- TanStack Query
- Tailwind CSS v4

## Development

```bash
cd web
npm install
npm run dev
```

The dashboard connects to the Charlieverse REST API (default `http://localhost:8765`). Make sure `charlie server start` is running.

## Build

```bash
npm run build
```

The built output is served by the Charlieverse server at `/` when running.

## Pages

- **Dashboard** — Story timeline grouped by month with chapter headers
- **Memories** — Entity list with type filtering and pin support
- **Knowledge** — Knowledge articles with search and CRUD
- **Sessions** — Session history with grouping
- **Stories** — Story browser with tier filtering
- **Settings** — Server status, data info, rebuild actions
