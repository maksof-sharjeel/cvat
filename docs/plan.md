# Plan — Annotation Analytics (per-class counts)

Branch `dev-test01`, cloned at CVAT commit `d8193c584be9ce6cf9882dad06c0dd920cc0b9c5`.
Machine: Intel i7-3770 (4 cores / 8 threads, 3.4 GHz), 11.7 GB RAM, Windows 10 Home 19045,
Docker Desktop (engine 29.8.2).

## What I found before planning

- Annotations live in `cvat/apps/engine/models.py`: `LabeledShape`, `LabeledTrack`,
  `LabeledImage` (tags). All inherit `Annotation`, which has `job` and `label` foreign keys.
  A task reaches its annotations through `Job -> Segment -> Task`, and a label name through
  `Annotation.label -> Label.name`. Skeleton points are child shapes (`parent` not null) and
  must not be counted as separate annotations.
- Access control is OPA based. `TaskPermission.create_scope_view(request, task)` in
  `cvat/apps/engine/permissions.py` is the existing "can this user see this task" check. I will
  reuse it instead of writing a rule of my own.
- The server already runs under uvicorn (ASGI) with `websockets` installed, and the internal
  nginx already forwards `Upgrade` headers. So a WebSocket needs no new dependency.
- Every annotation save goes through `dataset_manager/task.py` and calls `task.touch()`, so
  `Task.updated_date` changes whenever annotations change.
- The UI already ships `chart.js` + `react-chartjs-2`. `/tasks/:tid/analytics` is taken, so my
  page goes on `/tasks/:tid/label-counts`.

## Order of work (8 h budget)

| # | Step | Budget |
|---|------|--------|
| 0 | Stack up, import COCO val2017 subset, record image count (runs in background) | 0:30 |
| 1 | Plan, Objectives targets, Definition of Done — committed before any code | 0:30 |
| 2 | Django app `cvat.apps.test`: `GET /api/test/tasks/<id>/label-counts`, one `GROUP BY` query | 1:00 |
| 3 | Auth: CVAT session/token auth + `TaskPermission` view check; prove 401 and 403 | 0:30 |
| 4 | UI page with bar chart, empty state, error state, link from the task page | 1:30 |
| 5 | MO-1 measurement: 5 runs, raw output in `docs/objectives.md` | 0:30 |
| 6 | Grouping: counts split by shape type (`?group_by=type`) | 0:45 |
| 7 | WebSocket live updates (`/api/test/ws/tasks/<id>/label-counts`) | 1:15 |
| 8 | Reconnect with backoff when the socket drops | 0:30 |
| 9 | Decision record, DoD ticked with evidence, PR into my fork | 0:30 |

Items 1–4 of the brief (steps 2–4 here) are the floor. I do not start step 7 before the page
handles empty and error states.

## Changes to the plan

- **Step 6, grouping: shape type → shapes vs objects.** Checking the endpoint against COCO showed
  8109 shapes for 7204 COCO objects. CVAT stores each polygon of a multi-part COCO segmentation
  as its own shape and ties the parts together with `group`. "Annotations per class" is
  ambiguous between the two, and the gap is up to 2× for some classes (skis: 97 shapes, 44
  objects), so a switch between "every shape" and "grouped shapes count once" answers a real
  question about this data. Shape type would only have split polygons from 87 crowd masks.
- **Code location in the container.** The stock image keeps the code in `/opt/cvat`, not
  `/home/django`, so the bind mount goes over `/opt/cvat/cvat`. My first mount over
  `/home/django/cvat` only worked by accident (the server's working directory shadowed the
  real package) and made `manage.py test` run the image's old code.
- **UI dev server.** `yarn start` hard-codes `API_URL=http://localhost:7000`, a port only the dev
  compose file exposes. I run `webpack serve --env API_URL=http://localhost:8080` instead, and
  added `ws: true` to its proxy so the WebSocket reaches the server in development.

## What happened against the budget

The `cvat/server` image took most of the first two hours to download on my connection, and a
GitHub Desktop sync mixed up the order of my first two commits, which I rebuilt in the right
order before any code was committed. I wrote the endpoint, tests and page while the image was
downloading, but committed each step only after it ran against the real stack. That is why the
commits are close together in time:

| Commit | Time | Step |
|---|---|---|
| `187859400`, `7e9a160ed` | 10:37 | Plan, objectives, definition of done |
| `0dad3bc78` | 11:06 | Endpoint, checked against COCO (step 2) |
| `8f9310c1b` | 11:08 | Permission check, 401/403 shown (step 3) |
| `499fb0217` | 11:27 | UI page: chart, empty, error (step 4) |
| `19c529e52` | 11:28 | MO-1 measured (step 5) |
| `86c5786ea` | 11:34 | Shapes/objects switch (step 6, changed) |
| `4e2d97c34` | 11:45 | WebSocket live updates (step 7) |
| `e7713e06e` | 11:50 | Reconnect (step 8) |

## How I will run my code

The stock `cvat/server:dev` image does not contain my app. Rather than rebuilding the server
image (slow on this machine), I bind-mount `./cvat` into every backend container with a local
`docker-compose.override.yml` (already in `.gitignore`, so it is not committed). The UI runs
from webpack's dev server on port 3000, which proxies `/api` to the stack on 8080.

```yaml
# docker-compose.override.yml (gitignored); the same block for every cvat_worker_* service
services:
  cvat_server:
    volumes:
      - ./cvat:/opt/cvat/cvat
      - C:/www/val2017:/home/django/share/val2017:ro
      - C:/www/annotations:/home/django/share/annotations:ro
```

```sh
docker compose up -d
cd cvat-ui && ../node_modules/.bin/webpack serve --env API_URL=http://localhost:8080 \
  --config ./webpack.config.js --mode=development     # then open http://localhost:3000
```

The task was created from the share (`server_files`) with the first 1000 images of val2017 by
file name, and the annotations were imported as COCO 1.0 from `instances_val2017.json`
filtered to those images.

## Decided to skip

- Project-level and job-level pages. The endpoint is per task, as asked.
- Counting by attribute values.
- Caching the counts. One indexed `GROUP BY` should be fast enough; MO-1 tells me if not.
- Automated frontend tests. Backend gets a small API test; the UI is checked by hand with
  screenshots.
- Production hardening of the WebSocket (rate limits, many viewers per task).

## Decision record — how the page learns that counts changed

**Took:** a raw ASGI router in `cvat/asgi.py` sends `/api/test/ws/...` to a small handler in
`cvat/apps/test/websocket.py`. Once a second it reads `Task.updated_date` (one primary-key
query), and when the timestamp moved it replays the REST endpoint through Django's own
middleware stack with the handshake's headers and pushes the response body.

**Rejected:** Django Channels with a Redis channel layer, and a push from the annotation save
path (a signal or `group_send` after `dataset_manager` writes) to every socket watching that
task.

**Why:** the save path (`cvat/apps/dataset_manager/task.py`, e.g. line 442) writes annotations
through `cvat/utils/django_database`'s wrapper around Django's `bulk_create`, which sends no
`post_save` signals, so a push would have meant editing CVAT's annotation code in `dataset_manager`, plus
adding Channels and a channel layer so pushes reach sockets held by the other uvicorn
processes. Polling `updated_date` uses a timestamp CVAT already maintains, touches no engine
code, and works across processes because every process reads the same database. Replaying the
REST endpoint means login, the OPA check and the count mode are the same code over HTTP and
over the socket, and access revoked mid-session closes the socket on the next change.

**What rejecting it cost:**
- Up to about 1 s of delay per change (MO-2 median 962 ms) where a push would be near instant.
- One query per open page per second even when nothing changes. 100 open pages is 100
  queries a second; a push design costs nothing while idle.
- Any task edit (renaming it, for example) also moves `updated_date` and causes a needless
  recount (about 80 ms, MO-1).
- Changes made outside `dataset_manager` that do not touch the task (raw SQL, the Django admin)
  are not noticed until something else touches it.
