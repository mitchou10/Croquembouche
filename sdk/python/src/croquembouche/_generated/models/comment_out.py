from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="CommentOut")


@_attrs_define
class CommentOut:
    author_id: str
    author_name: str
    date: datetime.date
    id: str
    text: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        author_id = self.author_id

        author_name = self.author_name

        date = self.date.isoformat()

        id = self.id

        text = self.text

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "authorId": author_id,
                "authorName": author_name,
                "date": date,
                "id": id,
                "text": text,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        author_id = d.pop("authorId")

        author_name = d.pop("authorName")

        date = datetime.date.fromisoformat(d.pop("date"))

        id = d.pop("id")

        text = d.pop("text")

        comment_out = cls(
            author_id=author_id,
            author_name=author_name,
            date=date,
            id=id,
            text=text,
        )

        comment_out.additional_properties = d
        return comment_out

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
