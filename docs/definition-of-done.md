# Definition of Done

Written before starting (commit `7e9a160ed`). Each line gets ticked only with a number, a command
output or a file link beside it. Data: task 1 = COCO val2017, first **1000** images by file name,
annotations from `instances_val2017.json` filtered to those images, imported as COCO 1.0.

## Floor (brief items 1–4)

- [x] Endpoint returns per-class counts that match an independent count of the same task
      (COCO json filtered to the uploaded images).
      All 80 labels match, 8109 = COCO polygon parts + crowd masks:
      ```
      GET /api/test/tasks/1/label-counts -> 200
      api total: 8109 | expected (COCO polygon parts + crowd masks): 8109
      labels compared: 80 | mismatches: {}
      ```
      Why parts and not objects: see the shapes/objects note in `plan.md`. Unit tests also cover
      shapes + tracks + tags, skeletons counted once, ground truth jobs ignored
      (`cvat/apps/test/tests/test_label_counts.py`).
- [x] Endpoint reads from the database, not from the export/dataset pipeline.
      `cvat/apps/test/counts.py`: `GROUP BY label_id` on `LabeledShape`, `LabeledTrack`,
      `LabeledImage`; the `EXPLAIN ANALYZE` in `objectives.md` shows the SQL plan.
- [x] Page in the CVAT UI calls the endpoint and draws a bar chart.
      [evidence/ui-chart.png](evidence/ui-chart.png); route `/tasks/:tid/label-counts`, menu item
      "Label counts" in the task actions.
- [x] Page shows a clear empty state for a task with no annotations.
      Task 2 (two labels, no annotations): [evidence/ui-empty.png](evidence/ui-empty.png).
- [x] Page shows a clear error state, with retry, when the request fails.
      User without access opening task 1: [evidence/ui-error.png](evidence/ui-error.png).

## Access (item 5)

Raw output against the running stack:

```
$ curl -s -w "\nHTTP %{http_code}\n" http://localhost:8080/api/test/tasks/1/label-counts
{"detail":"Authentication credentials were not provided."}
HTTP 401

$ curl -s -u outsider:*** -w "\nHTTP %{http_code}\n" http://localhost:8080/api/test/tasks/1/label-counts
{"detail":"You do not have permission to perform this action."}
HTTP 403

$ curl -s -u admin:*** -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/api/test/tasks/1/label-counts
HTTP 200
```

- [x] Request with no login is refused (status code shown). 401 above; also over the
      WebSocket, close code 4401 (`objectives.md`, MO-2 output).
- [x] Logged-in user without access to the task is refused (status code shown). 403 above,
      `outsider` is a plain user who does not own the task; WebSocket close code 4403.
- [x] Owner of the task gets 200. Above.

## Speed (item 6)

- [x] MO-1 measured, 5 runs, raw output pasted in `objectives.md`.
- [x] Target met, or missed with the reason written down. Met: median 82.4 ms against a
      150 ms target (78.5–110.3 ms), with the limits of that result written down.

## Beyond the floor (items 7–10)

- [x] Grouping works in the API and the chart, and the reason is written down. Changed from
      shape type to shapes/objects (`plan.md`, "Changes to the plan"). `?count=objects`:
      ```
      GET ...?count=objects -> 200 | api total: 7204 | COCO objects: 7204
      labels compared: 80 | mismatches: {}
      GET ...?count=pixels -> 400 {"count":["Must be one of: ['shapes', 'objects']"]}
      ```
      [evidence/ui-objects.png](evidence/ui-objects.png).
- [x] Chart updates without reload when annotations are saved in a job. Headless Chrome on the
      page, one rectangle saved through the API:
      ```
      before save: 8109 annotations
      after save:  8110 annotations (page changed 765 ms after the save returned, no reload)
      after delete: 8109 annotations
      ```
      [evidence/ui-live.png](evidence/ui-live.png); MO-2 median 962 ms.
- [x] Page reconnects after the server restarts, and says so while disconnected.
      ```
      [+14.6s] page open, status tag: "Live"
      [+20.8s] cvat_server stopped
      [+20.8s] status tag: "Connection lost, reconnecting…"
      [+22.3s] cvat_server started
      [+79.5s] status tag: "Live" (reconnected without reload)
      [+81.2s] after save on the new connection: 8109 annotations -> 8110 annotations
      ```
      [evidence/ui-reconnecting.png](evidence/ui-reconnecting.png).
- [x] Decision record at the end of `plan.md`.

## Hygiene

- [x] Backend tests for the endpoint pass. 7 tests, run inside `cvat_server`:
      ```
      $ python3 manage.py test cvat.apps.test.tests --noinput
      Ran 7 tests in 6.603s
      OK
      ```
      `manage.py test cvat.apps.test` (the app label) does not work: unittest discovery resolves
      the package name `test` to Python's standard-library `test` package. The full module path
      above avoids it; the app name was fixed by the brief.
- [x] No dead code, no commented-out blocks, no stray files in the diff. Python passes
      `black` and `isort` with the repo settings, the UI files pass the repo's ESLint config.
      The setup and measurement scripts and the compose override stayed out of the repo.
- [x] Commits show the work in steps. One commit per step, listed with times in `plan.md`.
- [x] Everything not finished is listed below with the reason.

## Not finished

- **No frontend tests.** The UI was checked with headless-Chrome scripts and screenshots, not
  with Cypress tests in `tests/cypress`. Skipped for time, as the plan said.
- **`cvat/schema.yml` and the generated SDK are not regenerated** for the new endpoint. CVAT's CI
  checks the schema is current, so that check would fail on this branch. The endpoint has an
  `extend_schema` description, so regenerating is one command; I left it out to keep the diff
  to my own code.
- **WebSocket checks only that the user may view the task, at connect and on every change.**
  It does not check the `Origin` header; it relies on CVAT's `sessionid` cookie being
  `SameSite=Lax` (checked in the login response), which browsers do not send on cross-site
  WebSocket handshakes. No rate limit and no cap on
  sockets per user.
- **Only one task size measured** (1000 images, one job). A larger task and a database with
  many tasks are the cases where MO-1 could fail (see `objectives.md`).
- **Label edits are untested live.** Every push carries the full label list, so a label added
  or renamed should appear on the next push, but I only tested saving and deleting shapes.
