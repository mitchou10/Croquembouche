from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.template_out_visibility import TemplateOutVisibility
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.document_out import DocumentOut
    from ..models.entity_out import EntityOut
    from ..models.share import Share
    from ..models.sub_model_out import SubModelOut
    from ..models.suggestion_out import SuggestionOut
    from ..models.template_page_out import TemplatePageOut


T = TypeVar("T", bound="TemplateOut")


@_attrs_define
class TemplateOut:
    categories: list[str]
    description: str
    entities: list[EntityOut]
    id: str
    name: str
    owner_id: str
    owner_name: str
    pages: list[TemplatePageOut]
    stars: list[str]
    suggestions: list[SuggestionOut]
    version: str
    children: list[SubModelOut] | Unset = UNSET
    document: DocumentOut | None | Unset = UNSET
    parent_id: None | str | Unset = UNSET
    parent_name: None | str | Unset = UNSET
    shares: list[Share] | Unset = UNSET
    visibility: TemplateOutVisibility | Unset = TemplateOutVisibility.PUBLIC
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.document_out import DocumentOut  # noqa: PLC0415

        categories = self.categories

        description = self.description

        entities = []
        for entities_item_data in self.entities:
            entities_item = entities_item_data.to_dict()
            entities.append(entities_item)

        id = self.id

        name = self.name

        owner_id = self.owner_id

        owner_name = self.owner_name

        pages = []
        for pages_item_data in self.pages:
            pages_item = pages_item_data.to_dict()
            pages.append(pages_item)

        stars = self.stars

        suggestions = []
        for suggestions_item_data in self.suggestions:
            suggestions_item = suggestions_item_data.to_dict()
            suggestions.append(suggestions_item)

        version = self.version

        children: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.children, Unset):
            children = []
            for children_item_data in self.children:
                children_item = children_item_data.to_dict()
                children.append(children_item)

        document: dict[str, Any] | None | Unset
        if isinstance(self.document, Unset):
            document = UNSET
        elif isinstance(self.document, DocumentOut):
            document = self.document.to_dict()
        else:
            document = self.document

        parent_id: None | str | Unset
        if isinstance(self.parent_id, Unset):
            parent_id = UNSET
        else:
            parent_id = self.parent_id

        parent_name: None | str | Unset
        if isinstance(self.parent_name, Unset):
            parent_name = UNSET
        else:
            parent_name = self.parent_name

        shares: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.shares, Unset):
            shares = []
            for shares_item_data in self.shares:
                shares_item = shares_item_data.to_dict()
                shares.append(shares_item)

        visibility: str | Unset = UNSET
        if not isinstance(self.visibility, Unset):
            visibility = self.visibility.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "categories": categories,
                "description": description,
                "entities": entities,
                "id": id,
                "name": name,
                "ownerId": owner_id,
                "ownerName": owner_name,
                "pages": pages,
                "stars": stars,
                "suggestions": suggestions,
                "version": version,
            }
        )
        if children is not UNSET:
            field_dict["children"] = children
        if document is not UNSET:
            field_dict["document"] = document
        if parent_id is not UNSET:
            field_dict["parentId"] = parent_id
        if parent_name is not UNSET:
            field_dict["parentName"] = parent_name
        if shares is not UNSET:
            field_dict["shares"] = shares
        if visibility is not UNSET:
            field_dict["visibility"] = visibility

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.document_out import DocumentOut  # noqa: PLC0415
        from ..models.entity_out import EntityOut  # noqa: PLC0415
        from ..models.share import Share  # noqa: PLC0415
        from ..models.sub_model_out import SubModelOut  # noqa: PLC0415
        from ..models.suggestion_out import SuggestionOut  # noqa: PLC0415
        from ..models.template_page_out import TemplatePageOut  # noqa: PLC0415

        d = dict(src_dict)
        categories = cast(list[str], d.pop("categories"))

        description = d.pop("description")

        entities = []
        _entities = d.pop("entities")
        for entities_item_data in _entities:
            entities_item = EntityOut.from_dict(entities_item_data)

            entities.append(entities_item)

        id = d.pop("id")

        name = d.pop("name")

        owner_id = d.pop("ownerId")

        owner_name = d.pop("ownerName")

        pages = []
        _pages = d.pop("pages")
        for pages_item_data in _pages:
            pages_item = TemplatePageOut.from_dict(pages_item_data)

            pages.append(pages_item)

        stars = cast(list[str], d.pop("stars"))

        suggestions = []
        _suggestions = d.pop("suggestions")
        for suggestions_item_data in _suggestions:
            suggestions_item = SuggestionOut.from_dict(suggestions_item_data)

            suggestions.append(suggestions_item)

        version = d.pop("version")

        _children = d.pop("children", UNSET)
        children: list[SubModelOut] | Unset = UNSET
        if _children is not UNSET:
            children = []
            for children_item_data in _children:
                children_item = SubModelOut.from_dict(children_item_data)

                children.append(children_item)

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

        def _parse_parent_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        parent_id = _parse_parent_id(d.pop("parentId", UNSET))

        def _parse_parent_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        parent_name = _parse_parent_name(d.pop("parentName", UNSET))

        _shares = d.pop("shares", UNSET)
        shares: list[Share] | Unset = UNSET
        if _shares is not UNSET:
            shares = []
            for shares_item_data in _shares:
                shares_item = Share.from_dict(shares_item_data)

                shares.append(shares_item)

        _visibility = d.pop("visibility", UNSET)
        visibility: TemplateOutVisibility | Unset
        if isinstance(_visibility, Unset):
            visibility = UNSET
        else:
            visibility = TemplateOutVisibility(_visibility)

        template_out = cls(
            categories=categories,
            description=description,
            entities=entities,
            id=id,
            name=name,
            owner_id=owner_id,
            owner_name=owner_name,
            pages=pages,
            stars=stars,
            suggestions=suggestions,
            version=version,
            children=children,
            document=document,
            parent_id=parent_id,
            parent_name=parent_name,
            shares=shares,
            visibility=visibility,
        )

        template_out.additional_properties = d
        return template_out

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
