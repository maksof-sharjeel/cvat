# Objectives

Targets are set here before the code exists. Results are filled in below each target after
measuring, with the raw output pasted as it came out.

**Machine:** Intel i7-3770 (4 cores / 8 threads, 3.4 GHz), 11.7 GB RAM, Windows 10 Home 10.0.19045,
Docker Desktop (engine 29.8.2, WSL2 backend).
**CVAT commit cloned:** `d8193c584be9ce6cf9882dad06c0dd920cc0b9c5`.

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

### Result

_Not measured yet._

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
