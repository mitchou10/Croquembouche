from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.entity_fields import EntityFields
    from ..models.page_fields import PageFields


T = TypeVar("T", bound="TemplateFields")


@_attrs_define
class TemplateFields:
    name: str
    categories: list[str] | Unset = UNSET
    description: str | Unset = ""
    entities: list[EntityFields] | Unset = UNSET
    pages: list[PageFields] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        categories: list[str] | Unset = UNSET
        if not isinstance(self.categories, Unset):
            categories = self.categories

        description = self.description

        entities: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.entities, Unset):
            entities = []
            for entities_item_data in self.entities:
                entities_item = entities_item_data.to_dict()
                entities.append(entities_item)

        pages: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.pages, Unset):
            pages = []
            for pages_item_data in self.pages:
                pages_item = pages_item_data.to_dict()
                pages.append(pages_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if categories is not UNSET:
            field_dict["categories"] = categories
        if description is not UNSET:
            field_dict["description"] = description
        if entities is not UNSET:
            field_dict["entities"] = entities
        if pages is not UNSET:
            field_dict["pages"] = pages

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.entity_fields import EntityFields  # noqa: PLC0415
        from ..models.page_fields import PageFields  # noqa: PLC0415

        d = dict(src_dict)
        name = d.pop("name")

        categories = cast(list[str], d.pop("categories", UNSET))

        description = d.pop("description", UNSET)

        _entities = d.pop("entities", UNSET)
        entities: list[EntityFields] | Unset = UNSET
        if _entities is not UNSET:
            entities = []
            for entities_item_data in _entities:
                entities_item = EntityFields.from_dict(entities_item_data)

                entities.append(entities_item)

        _pages = d.pop("pages", UNSET)
        pages: list[PageFields] | Unset = UNSET
        if _pages is not UNSET:
            pages = []
            for pages_item_data in _pages:
                pages_item = PageFields.from_dict(pages_item_data)

                pages.append(pages_item)

        template_fields = cls(
            name=name,
            categories=categories,
            description=description,
            entities=entities,
            pages=pages,
        )

        template_fields.additional_properties = d
        return template_fields

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
