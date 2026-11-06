"""What a use consumed: the electricity and the CO2 of computing it, measured with CodeCarbon.

One tracker per worker process (made on first use: finding the hardware takes a moment), each use being a task of it. A
measure is only a bonus: whatever goes wrong with it, the use is matched all the same and is simply not measured."""

import logging
from contextlib import contextmanager

from app import config

logger = logging.getLogger(__name__)

_tracker = None


def _get_tracker():
    global _tracker
    if _tracker is None:
        from codecarbon import OfflineEmissionsTracker

        _tracker = OfflineEmissionsTracker(
            country_iso_code=config.COUNTRY_ISO_CODE,
            tracking_mode=config.CONSUMPTION_TRACKING_MODE,
            save_to_file=False,
            log_level="error",
            measure_power_secs=1,
        )
    return _tracker


class Measure:
    """What was consumed once the block is over (`{energy_kwh, co2_kg, duration_s}`), or None when not measured."""

    value: dict[str, float] | None = None


@contextmanager
def measured(name: str):
    measure = Measure()
    tracker = None
    if config.MEASURE_CONSUMPTION:
        try:
            tracker = _get_tracker()
            tracker.start_task(name)
        except Exception:
            logger.warning("Could not start measuring what %s consumes", name, exc_info=True)
            tracker = None
    try:
        yield measure
    finally:
        if tracker is not None:
            try:
                data = tracker.stop_task()
                measure.value = {
                    "energy_kwh": max(float(data.energy_consumed), 0.0),
                    "co2_kg": max(float(data.emissions), 0.0),
                    "duration_s": max(float(data.duration), 0.0),
                }
            except Exception:
                logger.warning("Could not measure what %s consumed", name, exc_info=True)
