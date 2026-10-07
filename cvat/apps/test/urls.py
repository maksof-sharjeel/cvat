# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.urls import path

from .views import TaskLabelCountsView

urlpatterns = [
    path("tasks/<int:pk>/label-counts", TaskLabelCountsView.as_view()),
]
