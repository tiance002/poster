from app.scheduler import PollingScheduler


def test_scheduler_replaces_single_polling_job() -> None:
    called = []
    scheduler = PollingScheduler(lambda: called.append(True))

    scheduler.update(60)
    scheduler.update(120)

    job = scheduler.scheduler.get_job("mail-poll")
    assert job is not None
    assert job.trigger.interval.total_seconds() == 120
    scheduler.shutdown()
