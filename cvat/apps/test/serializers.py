# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from rest_framework import serializers


class LabelCountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    color = serializers.CharField()
    count = serializers.IntegerField()


class LabelCountsSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    count_mode = serializers.CharField()
    total = serializers.IntegerField()
    labels = LabelCountSerializer(many=True)
