# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import asyncio
import io
import re

from asgiref.sync import sync_to_async
from django.core.handlers.asgi import ASGIHandler, ASGIRequest
from django.db import close_old_connections

from cvat.apps.engine.models import Task

LABEL_COUNTS_PATH = re.compile(r"^/api/test/ws/tasks/(?P<task_id>\d+)/label-counts$")
POLL_INTERVAL_SECONDS = 1.0

# Close codes 4000 + HTTP status, so the client can tell "you may not see this"
# (no point reconnecting) from a dropped connection (reconnect).
CLOSE_CODE_HTTP_BASE = 4000

_django = ASGIHandler()


def route_websockets(http_application):
    async def application(scope, receive, send):
        if scope["type"] != "websocket":
            return await http_application(scope, receive, send)

        match = LABEL_COUNTS_PATH.match(scope["path"])
        if not match:
            await receive()
            await send({"type": "websocket.close", "code": CLOSE_CODE_HTTP_BASE + 404})
            return

        await _serve_label_counts(scope, receive, send, int(match["task_id"]))

    return application


async def _fetch_label_counts(scope, task_id: int):
    # Replays the HTTP endpoint through the full Django stack with the
    # handshake's cookies and headers, so login, permission checks and the
    # query are exactly the ones the REST endpoint uses.
    # Accept-Encoding is dropped so GZipMiddleware leaves the body as text.
    http_scope = {
        **scope,
        "type": "http",
        "method": "GET",
        "path": f"/api/test/tasks/{task_id}/label-counts",
        "headers": [(k, v) for k, v in scope["headers"] if k != b"accept-encoding"],
    }
    return await _django.get_response_async(ASGIRequest(http_scope, io.BytesIO()))


@sync_to_async
def _task_updated_date(task_id: int):
    close_old_connections()
    return Task.objects.filter(pk=task_id).values_list("updated_date", flat=True).first()


async def _serve_label_counts(scope, receive, send, task_id: int):
    if (await receive())["type"] != "websocket.connect":
        return
    await send({"type": "websocket.accept"})

    last_change = None
    receiver = asyncio.ensure_future(receive())
    try:
        while True:
            change = await _task_updated_date(task_id)
            if change is None or change != last_change:
                response = await _fetch_label_counts(scope, task_id)
                if response.status_code != 200:
                    await send(
                        {
                            "type": "websocket.close",
                            "code": CLOSE_CODE_HTTP_BASE + response.status_code,
                        }
                    )
                    return
                await send({"type": "websocket.send", "text": response.content.decode()})
                last_change = change

            done, _ = await asyncio.wait({receiver}, timeout=POLL_INTERVAL_SECONDS)
            if receiver in done:
                if receiver.result()["type"] == "websocket.disconnect":
                    return
                receiver = asyncio.ensure_future(receive())
    finally:
        receiver.cancel()
