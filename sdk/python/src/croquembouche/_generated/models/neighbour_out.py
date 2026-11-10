from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="NeighbourOut")


@_attrs_define
class NeighbourOut:
    """A page of a model of the catalogue that looks like a page of the document. `document_id` is the example document
    of the model that was looked at (a model has had several: each version X has its own), to show the right image.

    """

    document_id: str
    id: str
    similarity: float
    template_id: str
    template_page: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        document_id = self.document_id

        id = self.id

        similarity = self.similarity

        template_id = self.template_id

        template_page = self.template_page

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "documentId": document_id,
                "id": id,
                "similarity": similarity,
                "templateId": template_id,
                "templatePage": template_page,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        document_id = d.pop("documentId")

        id = d.pop("id")

        similarity = d.pop("similarity")

        template_id = d.pop("templateId")

        template_page = d.pop("templatePage")

        neighbour_out = cls(
            document_id=document_id,
            id=id,
            similarity=similarity,
            template_id=template_id,
            template_page=template_page,
        )

        neighbour_out.additional_properties = d
        return neighbour_out

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
