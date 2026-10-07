# Definition of Done

Written before starting. Each line gets ticked only with a number, a command output or a
file link beside it.

## Floor (brief items 1–4)

- [ ] Endpoint returns per-class counts that match an independent count of the same task
      (COCO json filtered to the uploaded images).
- [ ] Endpoint reads from the database, not from the export/dataset pipeline.
- [ ] Page in the CVAT UI calls the endpoint and draws a bar chart.
- [ ] Page shows a clear empty state for a task with no annotations.
- [ ] Page shows a clear error state, with retry, when the request fails.

## Access (item 5)

- [ ] Request with no login is refused (status code shown).
- [ ] Logged-in user without access to the task is refused (status code shown).
- [ ] Owner of the task gets 200.

## Speed (item 6)

- [ ] MO-1 measured, 5 runs, raw output pasted in `objectives.md`.
- [ ] Target met, or missed with the reason written down.

## Beyond the floor (items 7–10)

- [ ] Grouping by shape type works in the API and the chart, and the reason is written down.
- [ ] Chart updates without reload when annotations are saved in a job.
- [ ] Page reconnects after the server restarts, and says so while disconnected.
- [ ] Decision record at the end of `plan.md`.

## Hygiene

- [ ] Backend tests for the endpoint pass.
- [ ] No dead code, no commented-out blocks, no stray files in the diff.
- [ ] Commits show the work in steps.
- [ ] Everything not finished is listed below with the reason.

## Not finished

_Filled in at the end._
