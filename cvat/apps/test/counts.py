# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from collections import Counter
from enum import Enum

from django.db.models import Count

from cvat.apps.engine.models import JobType, LabeledImage, LabeledShape, LabeledTrack, Task


class CountMode(str, Enum):
    SHAPES = "shapes"
    "Every stored shape, track and tag counts once."

    OBJECTS = "objects"
    """
    Shapes grouped together on one frame count once. Importers store one object
    with several parts this way, e.g. a COCO object whose segmentation has
    several polygons.
    """


def count_annotations_by_label(task: Task, mode: CountMode = CountMode.SHAPES) -> dict:
    # Ground truth and consensus replica jobs hold extra copies of frames that
    # annotation jobs already cover, so only annotation jobs are counted.
    # Skeleton points are child rows (parent is set) of one skeleton and are
    # not separate annotations.
    in_task = {
        "job__segment__task_id": task.id,
        "job__type": str(JobType.ANNOTATION),
    }
    shapes = LabeledShape.objects.filter(**in_task, parent__isnull=True)
    counted_per_row = [
        LabeledTrack.objects.filter(**in_task, parent__isnull=True),
        LabeledImage.objects.filter(**in_task),
    ]

    counts = Counter()
    if mode == CountMode.OBJECTS:
        counted_per_row.append(shapes.exclude(group__gt=0))
        grouped = shapes.filter(group__gt=0).values_list("label_id", "job_id", "frame", "group")
        counts.update(label_id for label_id, *_ in grouped.distinct())
    else:
        counted_per_row.append(shapes)

    for queryset in counted_per_row:
        for label_id, count in queryset.values_list("label_id").annotate(count=Count("id")):
            counts[label_id] += count

    labels = [
        {
            "id": label.id,
            "name": label.name,
            "color": label.color,
            "count": counts[label.id],
        }
        for label in task.get_labels().order_by("name")
    ]

    return {
        "task_id": task.id,
        "count_mode": mode.value,
        "total": sum(label["count"] for label in labels),
        "labels": labels,
    }
