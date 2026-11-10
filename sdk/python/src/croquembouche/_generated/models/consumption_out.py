from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ConsumptionOut")


@_attrs_define
class ConsumptionOut:
    """What computing something consumed: the electricity (Wh), the CO2 it made (g), the water it cost (mL, estimated
    from the electricity) and the time it took (s).

    """

    co_2g: float | Unset = 0.0
    duration_s: float | Unset = 0.0
    energy_wh: float | Unset = 0.0
    water_ml: float | Unset = 0.0
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        co_2g = self.co_2g

        duration_s = self.duration_s

        energy_wh = self.energy_wh

        water_ml = self.water_ml

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if co_2g is not UNSET:
            field_dict["co2G"] = co_2g
        if duration_s is not UNSET:
            field_dict["durationS"] = duration_s
        if energy_wh is not UNSET:
            field_dict["energyWh"] = energy_wh
        if water_ml is not UNSET:
            field_dict["waterMl"] = water_ml

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        co_2g = d.pop("co2G", UNSET)

        duration_s = d.pop("durationS", UNSET)

        energy_wh = d.pop("energyWh", UNSET)

        water_ml = d.pop("waterMl", UNSET)

        consumption_out = cls(
            co_2g=co_2g,
            duration_s=duration_s,
            energy_wh=energy_wh,
            water_ml=water_ml,
        )

        consumption_out.additional_properties = d
        return consumption_out

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
