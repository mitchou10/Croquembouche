from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from .. import types
from ..types import UNSET, File, Unset

T = TypeVar("T", bound="BodyStartRunApiAnalysesAnalysisIdRunsPost")


@_attrs_define
class BodyStartRunApiAnalysesAnalysisIdRunsPost:
    file: File
    keep_screenshot: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        file = self.file.to_tuple()

        keep_screenshot = self.keep_screenshot

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "file": file,
            }
        )
        if keep_screenshot is not UNSET:
            field_dict["keepScreenshot"] = keep_screenshot

        return field_dict

    def to_multipart(self) -> types.RequestFiles:
        files: types.RequestFiles = []

        files.append(("file", self.file.to_tuple()))

        if not isinstance(self.keep_screenshot, Unset):
            files.append(("keepScreenshot", (None, str(self.keep_screenshot).encode(), "text/plain")))

        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))

        return files

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        file = File(payload=BytesIO(d.pop("file")))

        keep_screenshot = d.pop("keepScreenshot", UNSET)

        body_start_run_api_analyses_analysis_id_runs_post = cls(
            file=file,
            keep_screenshot=keep_screenshot,
        )

        body_start_run_api_analyses_analysis_id_runs_post.additional_properties = d
        return body_start_run_api_analyses_analysis_id_runs_post

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
