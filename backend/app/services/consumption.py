"""What computing something consumed, in the units people read."""

from app.config import MatchingSettings
from app.schemas.analysis import ConsumptionOut


def consumed(energy_kwh: float, co2_kg: float, duration_s: float) -> ConsumptionOut:
    """What a use (or all of them) consumed, in the units people read: Wh, g of CO2, mL of water, seconds. The water is
    estimated from the electricity."""
    water_liters = energy_kwh * MatchingSettings().WATER_LITERS_PER_KWH
    return ConsumptionOut(
        duration_s=duration_s, energy_wh=energy_kwh * 1000, co2_g=co2_kg * 1000, water_ml=water_liters * 1000
    )
