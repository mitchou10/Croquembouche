from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.suggested_entity_source import SuggestedEntitySource

if TYPE_CHECKING:
    from ..models.zone import Zone


T = TypeVar("T", bound="SuggestedEntity")


@_attrs_define
class SuggestedEntity:
    """An entity a document suggests by itself, with where it is: to be taken as it is or changed."""

    name: str
    source: SuggestedEntitySource
    type_: str
    zone: Zone
    """ Fractions (0 to 1) of the page, so that a zone does not depend on the size it is shown at. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        source = self.source.value

        type_ = self.type_

        zone = self.zone.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "source": source,
                "type": type_,
                "zone": zone,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.zone import Zone  # noqa: PLC0415

        d = dict(src_dict)
        name = d.pop("name")

        source = SuggestedEntitySource(d.pop("source"))

        type_ = d.pop("type")

        zone = Zone.from_dict(d.pop("zone"))

        suggested_entity = cls(
            name=name,
            source=source,
            type_=type_,
            zone=zone,
        )

        suggested_entity.additional_properties = d
        return suggested_entity

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
