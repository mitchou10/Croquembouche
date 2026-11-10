from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.comment_out import CommentOut
    from ..models.template_fields import TemplateFields


T = TypeVar("T", bound="SuggestionOut")


@_attrs_define
class SuggestionOut:
    author_id: str
    author_name: str
    comments: list[CommentOut]
    date: datetime.date
    fields: TemplateFields
    id: str
    message: str
    stars: list[str]
    status: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        author_id = self.author_id

        author_name = self.author_name

        comments = []
        for comments_item_data in self.comments:
            comments_item = comments_item_data.to_dict()
            comments.append(comments_item)

        date = self.date.isoformat()

        fields = self.fields.to_dict()

        id = self.id

        message = self.message

        stars = self.stars

        status = self.status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "authorId": author_id,
                "authorName": author_name,
                "comments": comments,
                "date": date,
                "fields": fields,
                "id": id,
                "message": message,
                "stars": stars,
                "status": status,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.comment_out import CommentOut  # noqa: PLC0415
        from ..models.template_fields import TemplateFields  # noqa: PLC0415

        d = dict(src_dict)
        author_id = d.pop("authorId")

        author_name = d.pop("authorName")

        comments = []
        _comments = d.pop("comments")
        for comments_item_data in _comments:
            comments_item = CommentOut.from_dict(comments_item_data)

            comments.append(comments_item)

        date = datetime.date.fromisoformat(d.pop("date"))

        fields = TemplateFields.from_dict(d.pop("fields"))

        id = d.pop("id")

        message = d.pop("message")

        stars = cast(list[str], d.pop("stars"))

        status = d.pop("status")

        suggestion_out = cls(
            author_id=author_id,
            author_name=author_name,
            comments=comments,
            date=date,
            fields=fields,
            id=id,
            message=message,
            stars=stars,
            status=status,
        )

        suggestion_out.additional_properties = d
        return suggestion_out

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
