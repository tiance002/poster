from __future__ import annotations

from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler


class PollingScheduler:
    def __init__(self, callback: Callable[[], object]) -> None:
        self.scheduler = BackgroundScheduler()
        self.callback = callback
        self.scheduler.start()

    def update(self, interval_seconds: int) -> None:
        if interval_seconds <= 0:
            self.scheduler.remove_job("mail-poll") if self.scheduler.get_job("mail-poll") else None
            return
        self.scheduler.add_job(
            self.callback,
            "interval",
            seconds=interval_seconds,
            id="mail-poll",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
