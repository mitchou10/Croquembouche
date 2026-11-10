from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.search_summary_out_status import SearchSummaryOutStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.consumption_out import ConsumptionOut


T = TypeVar("T", bound="SearchSummaryOut")


@_attrs_define
class SearchSummaryOut:
    created_at: datetime.datetime
    file_name: str
    id: str
    k: int
    neighbour_count: int
    pages: int
    status: SearchSummaryOutStatus
    template_ids: list[str] | None
    consumption: ConsumptionOut | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415

        created_at = self.created_at.isoformat()

        file_name = self.file_name

        id = self.id

        k = self.k

        neighbour_count = self.neighbour_count

        pages = self.pages

        status = self.status.value

        template_ids: list[str] | None
        if isinstance(self.template_ids, list):
            template_ids = self.template_ids

        else:
            template_ids = self.template_ids

        consumption: dict[str, Any] | None | Unset
        if isinstance(self.consumption, Unset):
            consumption = UNSET
        elif isinstance(self.consumption, ConsumptionOut):
            consumption = self.consumption.to_dict()
        else:
            consumption = self.consumption

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "createdAt": created_at,
                "fileName": file_name,
                "id": id,
                "k": k,
                "neighbourCount": neighbour_count,
                "pages": pages,
                "status": status,
                "templateIds": template_ids,
            }
        )
        if consumption is not UNSET:
            field_dict["consumption"] = consumption

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415

        d = dict(src_dict)
        created_at = datetime.datetime.fromisoformat(d.pop("createdAt"))

        file_name = d.pop("fileName")

        id = d.pop("id")

        k = d.pop("k")

        neighbour_count = d.pop("neighbourCount")

        pages = d.pop("pages")

        status = SearchSummaryOutStatus(d.pop("status"))

        def _parse_template_ids(data: object) -> list[str] | None:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                template_ids_type_0 = cast(list[str], data)

                return template_ids_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None, data)

        template_ids = _parse_template_ids(d.pop("templateIds"))

        def _parse_consumption(data: object) -> ConsumptionOut | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                consumption_type_0 = ConsumptionOut.from_dict(data)

                return consumption_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ConsumptionOut | None | Unset, data)

        consumption = _parse_consumption(d.pop("consumption", UNSET))

        search_summary_out = cls(
            created_at=created_at,
            file_name=file_name,
            id=id,
            k=k,
            neighbour_count=neighbour_count,
            pages=pages,
            status=status,
            template_ids=template_ids,
            consumption=consumption,
        )

        search_summary_out.additional_properties = d
        return search_summary_out

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
