from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.document_out import DocumentOut


T = TypeVar("T", bound="TemplateVersionOut")


@_attrs_define
class TemplateVersionOut:
    """A version of a model, X.Y.Z, as it was saved."""

    author_id: str
    author_name: str
    date: datetime.date
    version: str
    document: DocumentOut | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.document_out import DocumentOut  # noqa: PLC0415

        author_id = self.author_id

        author_name = self.author_name

        date = self.date.isoformat()

        version = self.version

        document: dict[str, Any] | None | Unset
        if isinstance(self.document, Unset):
            document = UNSET
        elif isinstance(self.document, DocumentOut):
            document = self.document.to_dict()
        else:
            document = self.document

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "authorId": author_id,
                "authorName": author_name,
                "date": date,
                "version": version,
            }
        )
        if document is not UNSET:
            field_dict["document"] = document

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.document_out import DocumentOut  # noqa: PLC0415

        d = dict(src_dict)
        author_id = d.pop("authorId")

        author_name = d.pop("authorName")

        date = datetime.date.fromisoformat(d.pop("date"))

        version = d.pop("version")

        def _parse_document(data: object) -> DocumentOut | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                document_type_0 = DocumentOut.from_dict(data)

                return document_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(DocumentOut | None | Unset, data)

        document = _parse_document(d.pop("document", UNSET))

        template_version_out = cls(
            author_id=author_id,
            author_name=author_name,
            date=date,
            version=version,
            document=document,
        )

        template_version_out.additional_properties = d
        return template_version_out

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
