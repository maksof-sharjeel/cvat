# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from cvat.apps.engine.models import (
    Job,
    JobType,
    Label,
    LabeledImage,
    LabeledShape,
    LabeledTrack,
    Segment,
    Task,
)
from cvat.apps.engine.tests.utils import ForceLogin
from cvat.apps.iam.models import User


class LabelCountsAPITestCase(APITestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name="user")
        self.owner = User.objects.create_user(username="owner", password="owner")
        self.owner.groups.add(group)

        self.task = Task.objects.create(name="task", owner=self.owner)
        self.cat = Label.objects.create(task=self.task, name="cat")
        self.dog = Label.objects.create(task=self.task, name="dog")
        self.unused = Label.objects.create(task=self.task, name="zebra")
        self.person = Label.objects.create(task=self.task, name="person", type="skeleton")
        self.nose = Label.objects.create(task=self.task, name="nose", parent=self.person)

        self.job = self._add_job(JobType.ANNOTATION, 0, 9)
        self.gt_job = self._add_job(JobType.GROUND_TRUTH, 0, 9)

    def _add_job(self, job_type: JobType, start: int, stop: int) -> Job:
        segment = Segment.objects.create(task=self.task, start_frame=start, stop_frame=stop)
        return Job.objects.create(segment=segment, type=str(job_type))

    def _add_shape(self, label: Label, shape_type="rectangle", job=None, parent=None):
        return LabeledShape.objects.create(
            job=job or self.job,
            label=label,
            frame=0,
            type=shape_type,
            points=[0, 0, 1, 1],
            parent=parent,
        )

    def _get(self, user, task_id=None, query=""):
        url = f"/api/test/tasks/{task_id or self.task.id}/label-counts{query}"
        if user is None:
            return self.client.get(url)
        with ForceLogin(user, self.client):
            return self.client.get(url)

    def test_counts_shapes_tracks_and_tags_per_label(self):
        self._add_shape(self.cat)
        self._add_shape(self.cat, "polygon")
        self._add_shape(self.dog)
        LabeledTrack.objects.create(job=self.job, label=self.dog, frame=0)
        LabeledImage.objects.create(job=self.job, label=self.cat, frame=1)

        response = self._get(self.owner)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        counts = {label["name"]: label["count"] for label in response.data["labels"]}
        self.assertEqual(counts, {"cat": 3, "dog": 2, "person": 0, "zebra": 0})
        self.assertEqual(response.data["total"], 5)

    def test_skeleton_counts_once_and_ground_truth_is_ignored(self):
        skeleton = self._add_shape(self.person, "skeleton")
        self._add_shape(self.nose, "points", parent=skeleton)
        self._add_shape(self.cat, job=self.gt_job)

        response = self._get(self.owner)

        counts = {label["name"]: label["count"] for label in response.data["labels"]}
        self.assertEqual(counts["person"], 1)
        self.assertEqual(counts["cat"], 0)
        self.assertNotIn("nose", counts)

    def test_objects_mode_counts_a_group_of_parts_once(self):
        for _ in range(2):
            part = self._add_shape(self.cat, "polygon")
            part.group = 1
            part.save()
        self._add_shape(self.cat)

        shapes = self._get(self.owner, query="?count=shapes")
        objects = self._get(self.owner, query="?count=objects")

        self.assertEqual(shapes.data["total"], 3)
        self.assertEqual(objects.data["total"], 2)
        self.assertEqual(objects.data["count_mode"], "objects")

    def test_unknown_count_mode_is_400(self):
        response = self._get(self.owner, query="?count=pixels")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_task_is_404(self):
        response = self._get(self.owner, task_id=self.task.id + 1000)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_without_access_to_task_is_403(self):
        outsider = User.objects.create_user(username="outsider", password="outsider")
        outsider.groups.add(Group.objects.get(name="user"))

        response = self._get(outsider)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_request_is_401(self):
        response = self._get(None)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
