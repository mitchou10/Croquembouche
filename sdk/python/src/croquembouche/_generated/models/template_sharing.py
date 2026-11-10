from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.template_sharing_visibility import TemplateSharingVisibility
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.share import Share


T = TypeVar("T", bound="TemplateSharing")


@_attrs_define
class TemplateSharing:
    """Who can use a model. The people and groups only count when it is `shared`."""

    visibility: TemplateSharingVisibility
    shares: list[Share] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        visibility = self.visibility.value

        shares: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.shares, Unset):
            shares = []
            for shares_item_data in self.shares:
                shares_item = shares_item_data.to_dict()
                shares.append(shares_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "visibility": visibility,
            }
        )
        if shares is not UNSET:
            field_dict["shares"] = shares

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.share import Share  # noqa: PLC0415

        d = dict(src_dict)
        visibility = TemplateSharingVisibility(d.pop("visibility"))

        _shares = d.pop("shares", UNSET)
        shares: list[Share] | Unset = UNSET
        if _shares is not UNSET:
            shares = []
            for shares_item_data in _shares:
                shares_item = Share.from_dict(shares_item_data)

                shares.append(shares_item)

        template_sharing = cls(
            visibility=visibility,
            shares=shares,
        )

        template_sharing.additional_properties = d
        return template_sharing

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
