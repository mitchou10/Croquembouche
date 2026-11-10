from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.analysis_create_template_versions import AnalysisCreateTemplateVersions
    from ..models.share import Share


T = TypeVar("T", bound="AnalysisCreate")


@_attrs_define
class AnalysisCreate:
    name: str
    template_ids: list[str]
    description: str | Unset = ""
    is_public: bool | Unset = False
    shares: list[Share] | Unset = UNSET
    template_versions: AnalysisCreateTemplateVersions | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        template_ids = self.template_ids

        description = self.description

        is_public = self.is_public

        shares: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.shares, Unset):
            shares = []
            for shares_item_data in self.shares:
                shares_item = shares_item_data.to_dict()
                shares.append(shares_item)

        template_versions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.template_versions, Unset):
            template_versions = self.template_versions.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "templateIds": template_ids,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if is_public is not UNSET:
            field_dict["isPublic"] = is_public
        if shares is not UNSET:
            field_dict["shares"] = shares
        if template_versions is not UNSET:
            field_dict["templateVersions"] = template_versions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.analysis_create_template_versions import AnalysisCreateTemplateVersions  # noqa: PLC0415
        from ..models.share import Share  # noqa: PLC0415

        d = dict(src_dict)
        name = d.pop("name")

        template_ids = cast(list[str], d.pop("templateIds"))

        description = d.pop("description", UNSET)

        is_public = d.pop("isPublic", UNSET)

        _shares = d.pop("shares", UNSET)
        shares: list[Share] | Unset = UNSET
        if _shares is not UNSET:
            shares = []
            for shares_item_data in _shares:
                shares_item = Share.from_dict(shares_item_data)

                shares.append(shares_item)

        _template_versions = d.pop("templateVersions", UNSET)
        template_versions: AnalysisCreateTemplateVersions | Unset
        if isinstance(_template_versions, Unset):
            template_versions = UNSET
        else:
            template_versions = AnalysisCreateTemplateVersions.from_dict(_template_versions)

        analysis_create = cls(
            name=name,
            template_ids=template_ids,
            description=description,
            is_public=is_public,
            shares=shares,
            template_versions=template_versions,
        )

        analysis_create.additional_properties = d
        return analysis_create

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
