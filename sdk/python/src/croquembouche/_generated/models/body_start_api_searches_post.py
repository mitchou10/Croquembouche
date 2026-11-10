from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from .. import types
from ..types import UNSET, File, Unset

T = TypeVar("T", bound="BodyStartApiSearchesPost")


@_attrs_define
class BodyStartApiSearchesPost:
    file: File
    k: int | Unset = 6
    template_ids: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        file = self.file.to_tuple()

        k = self.k

        template_ids: list[str] | None | Unset
        if isinstance(self.template_ids, Unset):
            template_ids = UNSET
        elif isinstance(self.template_ids, list):
            template_ids = self.template_ids

        else:
            template_ids = self.template_ids

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "file": file,
            }
        )
        if k is not UNSET:
            field_dict["k"] = k
        if template_ids is not UNSET:
            field_dict["templateIds"] = template_ids

        return field_dict

    def to_multipart(self) -> types.RequestFiles:
        files: types.RequestFiles = []

        files.append(("file", self.file.to_tuple()))

        if not isinstance(self.k, Unset):
            files.append(("k", (None, str(self.k).encode(), "text/plain")))

        if not isinstance(self.template_ids, Unset):
            if isinstance(self.template_ids, list):
                for template_ids_type_0_item_element in self.template_ids:
                    files.append(("templateIds", (None, str(template_ids_type_0_item_element).encode(), "text/plain")))
            else:
                files.append(("templateIds", (None, str(self.template_ids).encode(), "text/plain")))

        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))

        return files

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        file = File(payload=BytesIO(d.pop("file")))

        k = d.pop("k", UNSET)

        def _parse_template_ids(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                template_ids_type_0 = cast(list[str], data)

                return template_ids_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        template_ids = _parse_template_ids(d.pop("templateIds", UNSET))

        body_start_api_searches_post = cls(
            file=file,
            k=k,
            template_ids=template_ids,
        )

        body_start_api_searches_post.additional_properties = d
        return body_start_api_searches_post

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
