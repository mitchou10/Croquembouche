from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.consumption_out import ConsumptionOut


T = TypeVar("T", bound="AnalysisConsumptionOut")


@_attrs_define
class AnalysisConsumptionOut:
    """What the uses of a person consumed in one analysis. `measured` are the uses that were (the others add
    nothing).

    """

    consumption: ConsumptionOut
    """ What computing something consumed: the electricity (Wh), the CO2 it made (g), the water it cost (mL,
    estimated
    from the electricity) and the time it took (s). """
    id: str
    measured: int
    name: str
    uses: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        consumption = self.consumption.to_dict()

        id = self.id

        measured = self.measured

        name = self.name

        uses = self.uses

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "consumption": consumption,
                "id": id,
                "measured": measured,
                "name": name,
                "uses": uses,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415

        d = dict(src_dict)
        consumption = ConsumptionOut.from_dict(d.pop("consumption"))

        id = d.pop("id")

        measured = d.pop("measured")

        name = d.pop("name")

        uses = d.pop("uses")

        analysis_consumption_out = cls(
            consumption=consumption,
            id=id,
            measured=measured,
            name=name,
            uses=uses,
        )

        analysis_consumption_out.additional_properties = d
        return analysis_consumption_out

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
