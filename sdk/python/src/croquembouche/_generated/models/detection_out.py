from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.detection_out_source import DetectionOutSource
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.classification_out import ClassificationOut
    from ..models.review_out import ReviewOut
    from ..models.zone import Zone


T = TypeVar("T", bound="DetectionOut")


@_attrs_define
class DetectionOut:
    classifications: list[ClassificationOut]
    id: str
    review: ReviewOut
    source: DetectionOutSource
    zone: Zone
    """ Fractions (0 to 1) of the page, so that a zone does not depend on the size it is shown at. """
    entity_id: None | str | Unset = UNSET
    found_in_text: bool | Unset = False
    text: None | str | Unset = UNSET
    zone_index: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        classifications = []
        for classifications_item_data in self.classifications:
            classifications_item = classifications_item_data.to_dict()
            classifications.append(classifications_item)

        id = self.id

        review = self.review.to_dict()

        source = self.source.value

        zone = self.zone.to_dict()

        entity_id: None | str | Unset
        if isinstance(self.entity_id, Unset):
            entity_id = UNSET
        else:
            entity_id = self.entity_id

        found_in_text = self.found_in_text

        text: None | str | Unset
        if isinstance(self.text, Unset):
            text = UNSET
        else:
            text = self.text

        zone_index: int | None | Unset
        if isinstance(self.zone_index, Unset):
            zone_index = UNSET
        else:
            zone_index = self.zone_index

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "classifications": classifications,
                "id": id,
                "review": review,
                "source": source,
                "zone": zone,
            }
        )
        if entity_id is not UNSET:
            field_dict["entityId"] = entity_id
        if found_in_text is not UNSET:
            field_dict["foundInText"] = found_in_text
        if text is not UNSET:
            field_dict["text"] = text
        if zone_index is not UNSET:
            field_dict["zoneIndex"] = zone_index

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.classification_out import ClassificationOut  # noqa: PLC0415
        from ..models.review_out import ReviewOut  # noqa: PLC0415
        from ..models.zone import Zone  # noqa: PLC0415

        d = dict(src_dict)
        classifications = []
        _classifications = d.pop("classifications")
        for classifications_item_data in _classifications:
            classifications_item = ClassificationOut.from_dict(classifications_item_data)

            classifications.append(classifications_item)

        id = d.pop("id")

        review = ReviewOut.from_dict(d.pop("review"))

        source = DetectionOutSource(d.pop("source"))

        zone = Zone.from_dict(d.pop("zone"))

        def _parse_entity_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        entity_id = _parse_entity_id(d.pop("entityId", UNSET))

        found_in_text = d.pop("foundInText", UNSET)

        def _parse_text(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        text = _parse_text(d.pop("text", UNSET))

        def _parse_zone_index(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        zone_index = _parse_zone_index(d.pop("zoneIndex", UNSET))

        detection_out = cls(
            classifications=classifications,
            id=id,
            review=review,
            source=source,
            zone=zone,
            entity_id=entity_id,
            found_in_text=found_in_text,
            text=text,
            zone_index=zone_index,
        )

        detection_out.additional_properties = d
        return detection_out

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
