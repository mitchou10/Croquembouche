from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ClassificationOut")


@_attrs_define
class ClassificationOut:
    """What something could be, and how sure the analysis is (0 to 1); no model is « other ». For a page of the
    document, the page of the model it looks like (« form X, page 3 »).

    """

    confidence: float
    template_id: None | str
    template_page: int | None | Unset = UNSET
    template_version: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        confidence = self.confidence

        template_id: None | str
        template_id = self.template_id

        template_page: int | None | Unset
        if isinstance(self.template_page, Unset):
            template_page = UNSET
        else:
            template_page = self.template_page

        template_version: None | str | Unset
        if isinstance(self.template_version, Unset):
            template_version = UNSET
        else:
            template_version = self.template_version

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "confidence": confidence,
                "templateId": template_id,
            }
        )
        if template_page is not UNSET:
            field_dict["templatePage"] = template_page
        if template_version is not UNSET:
            field_dict["templateVersion"] = template_version

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        confidence = d.pop("confidence")

        def _parse_template_id(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        template_id = _parse_template_id(d.pop("templateId"))

        def _parse_template_page(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        template_page = _parse_template_page(d.pop("templatePage", UNSET))

        def _parse_template_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        template_version = _parse_template_version(d.pop("templateVersion", UNSET))

        classification_out = cls(
            confidence=confidence,
            template_id=template_id,
            template_page=template_page,
            template_version=template_version,
        )

        classification_out.additional_properties = d
        return classification_out

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
