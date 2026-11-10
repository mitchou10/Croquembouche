from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.analysis_consumption_out import AnalysisConsumptionOut
    from ..models.consumption_out import ConsumptionOut
    from ..models.searches_consumption_out import SearchesConsumptionOut


T = TypeVar("T", bound="MyConsumptionOut")


@_attrs_define
class MyConsumptionOut:
    """What all the uses of a person consumed, and the detail by analysis, the most consuming first; and, apart, what
    their searches for similar documents consumed.

    """

    analyses: list[AnalysisConsumptionOut]
    consumption: ConsumptionOut
    """ What computing something consumed: the electricity (Wh), the CO2 it made (g), the water it cost (mL,
    estimated
    from the electricity) and the time it took (s). """
    measured: int
    searches: SearchesConsumptionOut
    """ What the searches for similar documents of a person consumed: how many, how many were measured (the others
    add
    nothing), and what. """
    uses: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        analyses = []
        for analyses_item_data in self.analyses:
            analyses_item = analyses_item_data.to_dict()
            analyses.append(analyses_item)

        consumption = self.consumption.to_dict()

        measured = self.measured

        searches = self.searches.to_dict()

        uses = self.uses

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "analyses": analyses,
                "consumption": consumption,
                "measured": measured,
                "searches": searches,
                "uses": uses,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.analysis_consumption_out import AnalysisConsumptionOut  # noqa: PLC0415
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415
        from ..models.searches_consumption_out import SearchesConsumptionOut  # noqa: PLC0415

        d = dict(src_dict)
        analyses = []
        _analyses = d.pop("analyses")
        for analyses_item_data in _analyses:
            analyses_item = AnalysisConsumptionOut.from_dict(analyses_item_data)

            analyses.append(analyses_item)

        consumption = ConsumptionOut.from_dict(d.pop("consumption"))

        measured = d.pop("measured")

        searches = SearchesConsumptionOut.from_dict(d.pop("searches"))

        uses = d.pop("uses")

        my_consumption_out = cls(
            analyses=analyses,
            consumption=consumption,
            measured=measured,
            searches=searches,
            uses=uses,
        )

        my_consumption_out.additional_properties = d
        return my_consumption_out

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
