# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cvat.apps.engine.models import Task
from cvat.apps.engine.permissions import TaskPermission
from cvat.apps.engine.types import ExtendedRequest

from .counts import CountMode, count_annotations_by_label
from .serializers import LabelCountsSerializer


class TaskLabelCountsView(APIView):
    # Authentication uses CVAT's default classes (session, token, basic);
    # access to the task is decided by the same OPA rule as viewing the task.
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Count the annotations of a task per label",
        parameters=[
            OpenApiParameter(
                "count",
                location=OpenApiParameter.QUERY,
                type=OpenApiTypes.STR,
                enum=[mode.value for mode in CountMode],
                default=CountMode.SHAPES.value,
                description="Count every shape, or count shapes grouped on one frame once",
            ),
        ],
        responses={"200": LabelCountsSerializer},
    )
    def get(self, request: ExtendedRequest, pk: int):
        try:
            mode = CountMode(request.query_params.get("count", CountMode.SHAPES.value))
        except ValueError:
            raise ValidationError({"count": [f"Must be one of: {[m.value for m in CountMode]}"]})

        task = get_object_or_404(Task, pk=pk)
        if not TaskPermission.create_scope_view(request, task).check_access().allow:
            raise PermissionDenied()

        return Response(LabelCountsSerializer(count_annotations_by_label(task, mode)).data)
