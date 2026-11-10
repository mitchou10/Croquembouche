from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.template_update_visibility_type_0 import TemplateUpdateVisibilityType0
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.entity_fields import EntityFields
    from ..models.page_fields import PageFields
    from ..models.share import Share


T = TypeVar("T", bound="TemplateUpdate")


@_attrs_define
class TemplateUpdate:
    """`document_id`: absent keeps the document, null removes it, an id replaces it. `visibility` and `shares`: absent
    keeps who the model is shared with.

    """

    name: str
    categories: list[str] | Unset = UNSET
    description: str | Unset = ""
    document_id: None | str | Unset = UNSET
    entities: list[EntityFields] | Unset = UNSET
    pages: list[PageFields] | Unset = UNSET
    shares: list[Share] | None | Unset = UNSET
    visibility: None | TemplateUpdateVisibilityType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        categories: list[str] | Unset = UNSET
        if not isinstance(self.categories, Unset):
            categories = self.categories

        description = self.description

        document_id: None | str | Unset
        if isinstance(self.document_id, Unset):
            document_id = UNSET
        else:
            document_id = self.document_id

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

        shares: list[dict[str, Any]] | None | Unset
        if isinstance(self.shares, Unset):
            shares = UNSET
        elif isinstance(self.shares, list):
            shares = []
            for shares_type_0_item_data in self.shares:
                shares_type_0_item = shares_type_0_item_data.to_dict()
                shares.append(shares_type_0_item)

        else:
            shares = self.shares

        visibility: None | str | Unset
        if isinstance(self.visibility, Unset):
            visibility = UNSET
        elif isinstance(self.visibility, TemplateUpdateVisibilityType0):
            visibility = self.visibility.value
        else:
            visibility = self.visibility

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
        if document_id is not UNSET:
            field_dict["documentId"] = document_id
        if entities is not UNSET:
            field_dict["entities"] = entities
        if pages is not UNSET:
            field_dict["pages"] = pages
        if shares is not UNSET:
            field_dict["shares"] = shares
        if visibility is not UNSET:
            field_dict["visibility"] = visibility

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.entity_fields import EntityFields  # noqa: PLC0415
        from ..models.page_fields import PageFields  # noqa: PLC0415
        from ..models.share import Share  # noqa: PLC0415

        d = dict(src_dict)
        name = d.pop("name")

        categories = cast(list[str], d.pop("categories", UNSET))

        description = d.pop("description", UNSET)

        def _parse_document_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        document_id = _parse_document_id(d.pop("documentId", UNSET))

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

        def _parse_shares(data: object) -> list[Share] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                shares_type_0 = []
                _shares_type_0 = data
                for shares_type_0_item_data in _shares_type_0:
                    shares_type_0_item = Share.from_dict(shares_type_0_item_data)

                    shares_type_0.append(shares_type_0_item)

                return shares_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[Share] | None | Unset, data)

        shares = _parse_shares(d.pop("shares", UNSET))

        def _parse_visibility(data: object) -> None | TemplateUpdateVisibilityType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                visibility_type_0 = TemplateUpdateVisibilityType0(data)

                return visibility_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | TemplateUpdateVisibilityType0 | Unset, data)

        visibility = _parse_visibility(d.pop("visibility", UNSET))

        template_update = cls(
            name=name,
            categories=categories,
            description=description,
            document_id=document_id,
            entities=entities,
            pages=pages,
            shares=shares,
            visibility=visibility,
        )

        template_update.additional_properties = d
        return template_update

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
