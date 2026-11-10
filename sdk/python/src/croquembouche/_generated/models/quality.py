from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Quality")


@_attrs_define
class Quality:
    """How right the analysis has been, as far as people have said so: it grows with every prediction looked at.

    `correct` and `wrong` are the predictions someone decided on (validated or annotated with this very model, against
    invalidated or annotated with another); `pending` are the ones nobody has looked at yet; `missed` are what people
    found that the analysis did not (added by hand, or annotated as this model on a prediction of another).

    """

    correct: int
    f1: float | None
    mean_confidence_correct: float | None
    mean_confidence_wrong: float | None
    missed: int
    pending: int
    precision: float | None
    recall: float | None
    reviewed: int
    wrong: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        correct = self.correct

        f1: float | None
        f1 = self.f1

        mean_confidence_correct: float | None
        mean_confidence_correct = self.mean_confidence_correct

        mean_confidence_wrong: float | None
        mean_confidence_wrong = self.mean_confidence_wrong

        missed = self.missed

        pending = self.pending

        precision: float | None
        precision = self.precision

        recall: float | None
        recall = self.recall

        reviewed = self.reviewed

        wrong = self.wrong

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "correct": correct,
                "f1": f1,
                "meanConfidenceCorrect": mean_confidence_correct,
                "meanConfidenceWrong": mean_confidence_wrong,
                "missed": missed,
                "pending": pending,
                "precision": precision,
                "recall": recall,
                "reviewed": reviewed,
                "wrong": wrong,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        correct = d.pop("correct")

        def _parse_f1(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        f1 = _parse_f1(d.pop("f1"))

        def _parse_mean_confidence_correct(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        mean_confidence_correct = _parse_mean_confidence_correct(d.pop("meanConfidenceCorrect"))

        def _parse_mean_confidence_wrong(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        mean_confidence_wrong = _parse_mean_confidence_wrong(d.pop("meanConfidenceWrong"))

        missed = d.pop("missed")

        pending = d.pop("pending")

        def _parse_precision(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        precision = _parse_precision(d.pop("precision"))

        def _parse_recall(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        recall = _parse_recall(d.pop("recall"))

        reviewed = d.pop("reviewed")

        wrong = d.pop("wrong")

        quality = cls(
            correct=correct,
            f1=f1,
            mean_confidence_correct=mean_confidence_correct,
            mean_confidence_wrong=mean_confidence_wrong,
            missed=missed,
            pending=pending,
            precision=precision,
            recall=recall,
            reviewed=reviewed,
            wrong=wrong,
        )

        quality.additional_properties = d
        return quality

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
