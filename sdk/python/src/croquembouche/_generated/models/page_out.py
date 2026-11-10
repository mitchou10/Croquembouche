from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.classification_out import ClassificationOut
    from ..models.review_out import ReviewOut


T = TypeVar("T", bound="PageOut")


@_attrs_define
class PageOut:
    """What one page of the document tried could be, and what was decided of it."""

    classifications: list[ClassificationOut]
    page: int
    review: ReviewOut
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        classifications = []
        for classifications_item_data in self.classifications:
            classifications_item = classifications_item_data.to_dict()
            classifications.append(classifications_item)

        page = self.page

        review = self.review.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "classifications": classifications,
                "page": page,
                "review": review,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.classification_out import ClassificationOut  # noqa: PLC0415
        from ..models.review_out import ReviewOut  # noqa: PLC0415

        d = dict(src_dict)
        classifications = []
        _classifications = d.pop("classifications")
        for classifications_item_data in _classifications:
            classifications_item = ClassificationOut.from_dict(classifications_item_data)

            classifications.append(classifications_item)

        page = d.pop("page")

        review = ReviewOut.from_dict(d.pop("review"))

        page_out = cls(
            classifications=classifications,
            page=page,
            review=review,
        )

        page_out.additional_properties = d
        return page_out

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
