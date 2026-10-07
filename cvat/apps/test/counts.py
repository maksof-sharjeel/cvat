# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from collections import Counter

from django.db.models import Count

from cvat.apps.engine.models import JobType, LabeledImage, LabeledShape, LabeledTrack, Task


def count_annotations_by_label(task: Task) -> dict:
    # Ground truth and consensus replica jobs hold extra copies of frames that
    # annotation jobs already cover, so only annotation jobs are counted.
    # Skeleton points are child rows (parent is set) of one skeleton and are
    # not separate annotations.
    in_task = {
        "job__segment__task_id": task.id,
        "job__type": str(JobType.ANNOTATION),
    }
    counts = Counter()
    for queryset in (
        LabeledShape.objects.filter(**in_task, parent__isnull=True),
        LabeledTrack.objects.filter(**in_task, parent__isnull=True),
        LabeledImage.objects.filter(**in_task),
    ):
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
        "total": sum(label["count"] for label in labels),
        "labels": labels,
    }
