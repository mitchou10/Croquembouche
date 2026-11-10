from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.entity_quality import EntityQuality
    from ..models.page_quality import PageQuality
    from ..models.quality import Quality


T = TypeVar("T", bound="TemplateMetrics")


@_attrs_define
class TemplateMetrics:
    """The quality of the analysis on one model: its pages, its elements, and each of its entities."""

    elements: Quality
    """ How right the analysis has been, as far as people have said so: it grows with every prediction looked at.

    `correct` and `wrong` are the predictions someone decided on (validated or annotated with this very model,
    against
    invalidated or annotated with another); `pending` are the ones nobody has looked at yet; `missed` are what
    people
    found that the analysis did not (added by hand, or annotated as this model on a prediction of another). """
    entities: list[EntityQuality]
    pages: PageQuality
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        elements = self.elements.to_dict()

        entities = []
        for entities_item_data in self.entities:
            entities_item = entities_item_data.to_dict()
            entities.append(entities_item)

        pages = self.pages.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "elements": elements,
                "entities": entities,
                "pages": pages,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.entity_quality import EntityQuality  # noqa: PLC0415
        from ..models.page_quality import PageQuality  # noqa: PLC0415
        from ..models.quality import Quality  # noqa: PLC0415

        d = dict(src_dict)
        elements = Quality.from_dict(d.pop("elements"))

        entities = []
        _entities = d.pop("entities")
        for entities_item_data in _entities:
            entities_item = EntityQuality.from_dict(entities_item_data)

            entities.append(entities_item)

        pages = PageQuality.from_dict(d.pop("pages"))

        template_metrics = cls(
            elements=elements,
            entities=entities,
            pages=pages,
        )

        template_metrics.additional_properties = d
        return template_metrics

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
