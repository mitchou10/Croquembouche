from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.model_quality import ModelQuality
    from ..models.page_quality import PageQuality
    from ..models.quality import Quality


T = TypeVar("T", bound="QualityOverview")


@_attrs_define
class QualityOverview:
    """The quality of the analysis over every model together, and model by model: of the decisions of one person (what
    they said of their own tests), or of everyone's (for an administrator).

    """

    elements: Quality
    """ How right the analysis has been, as far as people have said so: it grows with every prediction looked at.

    `correct` and `wrong` are the predictions someone decided on (validated or annotated with this very model,
    against
    invalidated or annotated with another); `pending` are the ones nobody has looked at yet; `missed` are what
    people
    found that the analysis did not (added by hand, or annotated as this model on a prediction of another). """
    models: list[ModelQuality]
    pages: PageQuality
    reviewers: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        elements = self.elements.to_dict()

        models = []
        for models_item_data in self.models:
            models_item = models_item_data.to_dict()
            models.append(models_item)

        pages = self.pages.to_dict()

        reviewers: int | None | Unset
        if isinstance(self.reviewers, Unset):
            reviewers = UNSET
        else:
            reviewers = self.reviewers

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "elements": elements,
                "models": models,
                "pages": pages,
            }
        )
        if reviewers is not UNSET:
            field_dict["reviewers"] = reviewers

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.model_quality import ModelQuality  # noqa: PLC0415
        from ..models.page_quality import PageQuality  # noqa: PLC0415
        from ..models.quality import Quality  # noqa: PLC0415

        d = dict(src_dict)
        elements = Quality.from_dict(d.pop("elements"))

        models = []
        _models = d.pop("models")
        for models_item_data in _models:
            models_item = ModelQuality.from_dict(models_item_data)

            models.append(models_item)

        pages = PageQuality.from_dict(d.pop("pages"))

        def _parse_reviewers(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        reviewers = _parse_reviewers(d.pop("reviewers", UNSET))

        quality_overview = cls(
            elements=elements,
            models=models,
            pages=pages,
            reviewers=reviewers,
        )

        quality_overview.additional_properties = d
        return quality_overview

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
