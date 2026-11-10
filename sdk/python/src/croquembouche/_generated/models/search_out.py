from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.search_out_status import SearchOutStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.consumption_out import ConsumptionOut
    from ..models.link_out import LinkOut
    from ..models.neighbour_out import NeighbourOut


T = TypeVar("T", bound="SearchOut")


@_attrs_define
class SearchOut:
    created_at: datetime.datetime
    file_name: str
    id: str
    k: int
    links: list[LinkOut]
    neighbour_count: int
    neighbours: list[NeighbourOut]
    pages: int
    status: SearchOutStatus
    template_ids: list[str] | None
    consumption: ConsumptionOut | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415

        created_at = self.created_at.isoformat()

        file_name = self.file_name

        id = self.id

        k = self.k

        links = []
        for links_item_data in self.links:
            links_item = links_item_data.to_dict()
            links.append(links_item)

        neighbour_count = self.neighbour_count

        neighbours = []
        for neighbours_item_data in self.neighbours:
            neighbours_item = neighbours_item_data.to_dict()
            neighbours.append(neighbours_item)

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
                "links": links,
                "neighbourCount": neighbour_count,
                "neighbours": neighbours,
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
        from ..models.link_out import LinkOut  # noqa: PLC0415
        from ..models.neighbour_out import NeighbourOut  # noqa: PLC0415

        d = dict(src_dict)
        created_at = datetime.datetime.fromisoformat(d.pop("createdAt"))

        file_name = d.pop("fileName")

        id = d.pop("id")

        k = d.pop("k")

        links = []
        _links = d.pop("links")
        for links_item_data in _links:
            links_item = LinkOut.from_dict(links_item_data)

            links.append(links_item)

        neighbour_count = d.pop("neighbourCount")

        neighbours = []
        _neighbours = d.pop("neighbours")
        for neighbours_item_data in _neighbours:
            neighbours_item = NeighbourOut.from_dict(neighbours_item_data)

            neighbours.append(neighbours_item)

        pages = d.pop("pages")

        status = SearchOutStatus(d.pop("status"))

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

        search_out = cls(
            created_at=created_at,
            file_name=file_name,
            id=id,
            k=k,
            links=links,
            neighbour_count=neighbour_count,
            neighbours=neighbours,
            pages=pages,
            status=status,
            template_ids=template_ids,
            consumption=consumption,
        )

        search_out.additional_properties = d
        return search_out

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
