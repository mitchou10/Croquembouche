from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.zone import Zone


T = TypeVar("T", bound="EntityFields")


@_attrs_define
class EntityFields:
    name: str
    type_: str
    definition: str | Unset = ""
    examples: list[str] | Unset = UNSET
    id: None | str | Unset = UNSET
    tags: list[str] | Unset = UNSET
    zone: None | Unset | Zone = UNSET
    zones: list[Zone] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.zone import Zone  # noqa: PLC0415

        name = self.name

        type_ = self.type_

        definition = self.definition

        examples: list[str] | Unset = UNSET
        if not isinstance(self.examples, Unset):
            examples = self.examples

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        tags: list[str] | Unset = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags

        zone: dict[str, Any] | None | Unset
        if isinstance(self.zone, Unset):
            zone = UNSET
        elif isinstance(self.zone, Zone):
            zone = self.zone.to_dict()
        else:
            zone = self.zone

        zones: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.zones, Unset):
            zones = []
            for zones_item_data in self.zones:
                zones_item = zones_item_data.to_dict()
                zones.append(zones_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "type": type_,
            }
        )
        if definition is not UNSET:
            field_dict["definition"] = definition
        if examples is not UNSET:
            field_dict["examples"] = examples
        if id is not UNSET:
            field_dict["id"] = id
        if tags is not UNSET:
            field_dict["tags"] = tags
        if zone is not UNSET:
            field_dict["zone"] = zone
        if zones is not UNSET:
            field_dict["zones"] = zones

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.zone import Zone  # noqa: PLC0415

        d = dict(src_dict)
        name = d.pop("name")

        type_ = d.pop("type")

        definition = d.pop("definition", UNSET)

        examples = cast(list[str], d.pop("examples", UNSET))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        tags = cast(list[str], d.pop("tags", UNSET))

        def _parse_zone(data: object) -> None | Unset | Zone:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                zone_type_0 = Zone.from_dict(data)

                return zone_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | Zone, data)

        zone = _parse_zone(d.pop("zone", UNSET))

        _zones = d.pop("zones", UNSET)
        zones: list[Zone] | Unset = UNSET
        if _zones is not UNSET:
            zones = []
            for zones_item_data in _zones:
                zones_item = Zone.from_dict(zones_item_data)

                zones.append(zones_item)

        entity_fields = cls(
            name=name,
            type_=type_,
            definition=definition,
            examples=examples,
            id=id,
            tags=tags,
            zone=zone,
            zones=zones,
        )

        entity_fields.additional_properties = d
        return entity_fields

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
