"""Uvicorn asosiy event loop — boshqa threaddan async Socket.IO emit uchun."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, Optional

log = logging.getLogger(__name__)
_loop: Optional[asyncio.AbstractEventLoop] = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def schedule_coro(coro: Coroutine[Any, Any, Any]) -> None:
    if _loop is None:
        log.debug("ASGI loop hali yo'q — emit o'tkazib yuborildi")
        coro.close()
        return
    try:
        fut = asyncio.run_coroutine_threadsafe(coro, _loop)
        fut.add_done_callback(_log_future_error)
    except Exception:
        log.exception("schedule_coro xato")
        coro.close()


def _log_future_error(fut: asyncio.Future) -> None:
    exc = fut.exception()
    if exc:
        log.error("Background coroutine: %s", exc)
