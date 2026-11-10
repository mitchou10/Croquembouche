from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.review_out_status import ReviewOutStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="ReviewOut")


@_attrs_define
class ReviewOut:
    status: ReviewOutStatus
    template_id: None | str | Unset = UNSET
    template_page: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status = self.status.value

        template_id: None | str | Unset
        if isinstance(self.template_id, Unset):
            template_id = UNSET
        else:
            template_id = self.template_id

        template_page: int | None | Unset
        if isinstance(self.template_page, Unset):
            template_page = UNSET
        else:
            template_page = self.template_page

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
            }
        )
        if template_id is not UNSET:
            field_dict["templateId"] = template_id
        if template_page is not UNSET:
            field_dict["templatePage"] = template_page

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = ReviewOutStatus(d.pop("status"))

        def _parse_template_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        template_id = _parse_template_id(d.pop("templateId", UNSET))

        def _parse_template_page(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        template_page = _parse_template_page(d.pop("templatePage", UNSET))

        review_out = cls(
            status=status,
            template_id=template_id,
            template_page=template_page,
        )

        review_out.additional_properties = d
        return review_out

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
