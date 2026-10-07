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

## How I will run my code

The stock `cvat/server:dev` image does not contain my app. Rather than rebuilding the server
image (slow on this machine), I bind-mount `./cvat` into every backend container with a local
`docker-compose.override.yml` (already in `.gitignore`, so it is not committed). The UI runs
from `yarn start` on port 3000, which proxies `/api` to the stack on 8080.

## Decided to skip

- Project-level and job-level pages. The endpoint is per task, as asked.
- Counting by attribute values; only label and shape type.
- Caching the counts. One indexed `GROUP BY` should be fast enough; MO-1 tells me if not.
- Automated frontend tests. Backend gets a small API test; the UI is checked by hand with
  screenshots.
- Production hardening of the WebSocket (rate limits, many viewers per task).
