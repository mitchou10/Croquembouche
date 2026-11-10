from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.point import Point


T = TypeVar("T", bound="Zone")


@_attrs_define
class Zone:
    """Fractions (0 to 1) of the page, so that a zone does not depend on the size it is shown at."""

    page: int
    points: list[Point]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        page = self.page

        points = []
        for points_item_data in self.points:
            points_item = points_item_data.to_dict()
            points.append(points_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "page": page,
                "points": points,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.point import Point  # noqa: PLC0415

        d = dict(src_dict)
        page = d.pop("page")

        points = []
        _points = d.pop("points")
        for points_item_data in _points:
            points_item = Point.from_dict(points_item_data)

            points.append(points_item)

        zone = cls(
            page=page,
            points=points,
        )

        zone.additional_properties = d
        return zone

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
