from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.ocr_line import OcrLine


T = TypeVar("T", bound="OcrPage")


@_attrs_define
class OcrPage:
    lines: list[OcrLine]
    page: int
    angle: int | Unset = 0
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        lines = []
        for lines_item_data in self.lines:
            lines_item = lines_item_data.to_dict()
            lines.append(lines_item)

        page = self.page

        angle = self.angle

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "lines": lines,
                "page": page,
            }
        )
        if angle is not UNSET:
            field_dict["angle"] = angle

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.ocr_line import OcrLine  # noqa: PLC0415

        d = dict(src_dict)
        lines = []
        _lines = d.pop("lines")
        for lines_item_data in _lines:
            lines_item = OcrLine.from_dict(lines_item_data)

            lines.append(lines_item)

        page = d.pop("page")

        angle = d.pop("angle", UNSET)

        ocr_page = cls(
            lines=lines,
            page=page,
            angle=angle,
        )

        ocr_page.additional_properties = d
        return ocr_page

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
