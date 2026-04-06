"""Uvicorn asosiy event loop — boshqa threaddan async Socket.IO emit uchun."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, Optional

from monitoring.io_bus import sio

log = logging.getLogger(__name__)
_loop: Optional[asyncio.AbstractEventLoop] = None
_PENDING_MAX = 200
_pending_vitals: list[dict[str, Any]] = []


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop
    if not _pending_vitals:
        return
    batch = _pending_vitals[:]
    _pending_vitals.clear()
    if len(batch) > 50:
        log.info("Socket.IO: navbatdan %s ta vitals_update bir vaqtda yuborilmoqda", len(batch))

    async def _flush() -> None:
        await sio.emit("vitals_update", batch, namespace="/")

    try:
        fut = asyncio.run_coroutine_threadsafe(_flush(), loop)
        fut.add_done_callback(_log_future_error)
    except Exception:
        log.exception("set_event_loop: navbatni yuborish xato")


def schedule_vitals_emit(payloads: list[dict[str, Any]]) -> None:
    """HL7/REST threaddan vitals_update yuboradi; loop bo‘lmasa navbatda saqlanadi."""
    if not payloads:
        return
    if _loop is None:
        for p in payloads:
            if len(_pending_vitals) >= _PENDING_MAX:
                dropped = _pending_vitals.pop(0)
                log.warning(
                    "vitals_update navbati to‘ldi — eng eski yozuv tashlandi (patient=%s)",
                    dropped.get("id"),
                )
            _pending_vitals.append(p)
        log.warning(
            "Socket.IO loop hali yo‘q — %s ta vitals_update navbatga (ulanish / on_startup kutilmoqda)",
            len(payloads),
        )
        return

    async def _go() -> None:
        await sio.emit("vitals_update", payloads, namespace="/")

    try:
        fut = asyncio.run_coroutine_threadsafe(_go(), _loop)
        fut.add_done_callback(_log_future_error)
    except Exception:
        log.exception("schedule_vitals_emit xato")


def schedule_coro(coro: Coroutine[Any, Any, Any]) -> None:
    if _loop is None:
        log.warning("ASGI loop yo‘q — coroutine bajarilmadi (vitals uchun schedule_vitals_emit ishlating)")
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
