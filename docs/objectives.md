# Objectives

Targets are set here before the code exists. Results are filled in below each target after
measuring, with the raw output pasted as it came out.

**Machine:** Intel i7-3770 (4 cores / 8 threads, 3.4 GHz), 11.7 GB RAM, Windows 10 Home 10.0.19045,
Docker Desktop (engine 29.8.2, WSL2 backend).
**CVAT commit cloned:** `d8193c584be9ce6cf9882dad06c0dd920cc0b9c5`.
**Stack:** stock `cvat/server:dev` and `cvat/ui:dev` images with this branch's `cvat/` bind-mounted
over `/opt/cvat/cvat`; the UI page served by `webpack serve` on port 3000 (idle during timing).

## MO-1 — Endpoint response time

| Field | Entry |
|---|---|
| What is measured | Wall-clock time of `GET /api/test/tasks/<id>/label-counts` from request sent to last byte received, as seen by the client. |
| How | `curl -s -o /dev/null -w "%{time_total}"` from the host against `http://localhost:8080`, authenticated with a CVAT access token. One untimed warm-up request, then 5 timed runs. Report the median and min–max spread. |
| Target | Median of 5 runs at or below **150 ms**. |
| Conditions | Local Docker stack, the COCO val2017 task described in the Plan, no annotation job open, nothing else running in the stack. |
| Not included | The first request after a server restart (cold Python imports and DB connection), and browser rendering time. |

**Why 150 ms.** The work is one `GROUP BY label_id` over the task's annotation rows plus the
OPA permission call that every CVAT endpoint already pays. On this 2012-era CPU I expect the
fixed cost of a CVAT request (session lookup, OPA round trip) to be most of the time. I will
measure CVAT's own `GET /api/tasks/<id>` the same way as a baseline, so the result shows how
much my query adds on top of what CVAT already costs.

### Result — target met

Task 1: COCO val2017, first 1000 images by file name, 8109 shapes (7204 COCO objects) in one
annotation job. Measured against commit `8f9310c1b` (endpoint + permission check).

| Endpoint | Median | Spread (min–max) |
|---|---|---|
| `GET /api/test/tasks/1/label-counts` (mine) | **82.4 ms** | 78.5–110.3 ms |
| `GET /api/tasks/1` (CVAT baseline) | 70.9 ms | 67.6–86.7 ms |

Raw output, as printed:

```
2026-10-07T06:27:23Z
## http://localhost:8080/api/test/tasks/1/label-counts
run 1: 200 time_total=0.110261s
run 2: 200 time_total=0.098606s
run 3: 200 time_total=0.078538s
run 4: 200 time_total=0.082408s
run 5: 200 time_total=0.081293s
## http://localhost:8080/api/tasks/1
run 1: 200 time_total=0.075455s
run 2: 200 time_total=0.086666s
run 3: 200 time_total=0.067561s
run 4: 200 time_total=0.070948s
run 5: 200 time_total=0.067911s
```

Command (token redacted; one untimed warm-up request precedes each block):

```sh
m() { echo "## $1"; curl -s -o /dev/null -H "Authorization: Token $T" "$1"
      for i in 1 2 3 4 5; do curl -s -o /dev/null -H "Authorization: Token $T" \
        -w "run $i: %{http_code} time_total=%{time_total}s\n" "$1"; done; }
m http://localhost:8080/api/test/tasks/1/label-counts; m http://localhost:8080/api/tasks/1
```

**What the number says.** The endpoint costs about 11 ms more than CVAT's own task detail
request; the rest is the fixed cost every CVAT request pays. I cleared the target without
optimising anything, so I checked where the database time goes instead of stopping there.
`EXPLAIN ANALYZE` of the shape query (the largest of the three):

```
GroupAggregate  (actual time=24.139..25.396 rows=79 loops=1)
  ->  Sort  (actual time=23.597..24.283 rows=8109 loops=1)
        Sort Key: engine_labeledshape.label_id
        ->  Nested Loop  (actual time=1.409..7.682 rows=8109 loops=1)
              ->  Hash Join  (actual time=1.255..5.723 rows=8109 loops=1)
                    ->  Seq Scan on engine_labeledshape  (actual time=0.049..2.900 rows=8109 loops=1)
...
Execution Time: 26.583 ms
```

**Limit of this result.** The database holds only this task, so Postgres scans the whole
`engine_labeledshape` table; that is cheap here and would not be on a server with many tasks.
The time grows with the number of shapes in the task, because every row is read and sorted.
I did not measure a larger task (all 5000 images, ~36k objects) in the time I had.

## MO-2 — Live update delay (only if the WebSocket step is reached)

| Field | Entry |
|---|---|
| What is measured | Time from an annotation save being acknowledged by the server to the new counts arriving on an open WebSocket. |
| How | A script saves one shape through `PATCH /api/jobs/<id>/annotations?action=create` and records the time of the response, while a WebSocket client on the same task records the time the next counts message arrives. 5 runs, median and spread. |
| Target | Median at or below **2.5 s**. |
| Conditions | Same as MO-1, one WebSocket client. |
| Not included | Reconnect time after a dropped connection. |

### Result

_Not measured yet._
