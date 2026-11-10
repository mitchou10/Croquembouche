from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.analysis_out_status import AnalysisOutStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.analysis_out_template_versions import AnalysisOutTemplateVersions
    from ..models.consumption_out import ConsumptionOut
    from ..models.run_out import RunOut
    from ..models.share import Share


T = TypeVar("T", bound="AnalysisOut")


@_attrs_define
class AnalysisOut:
    """An analysis. One the person cannot open is only named, with its date and how it is going: the rest (who made it,
    what it is for, its uses, its recipients) is empty.

    """

    can_open: bool
    date: datetime.date
    description: str
    id: str
    is_public: bool
    matches: int
    name: str
    owner_id: str
    owner_name: str
    runs: list[RunOut]
    shares: list[Share]
    status: AnalysisOutStatus
    template_ids: list[str]
    views: int
    consumption: ConsumptionOut | Unset = UNSET
    """ What computing something consumed: the electricity (Wh), the CO2 it made (g), the water it cost (mL,
    estimated
    from the electricity) and the time it took (s). """
    template_versions: AnalysisOutTemplateVersions | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        can_open = self.can_open

        date = self.date.isoformat()

        description = self.description

        id = self.id

        is_public = self.is_public

        matches = self.matches

        name = self.name

        owner_id = self.owner_id

        owner_name = self.owner_name

        runs = []
        for runs_item_data in self.runs:
            runs_item = runs_item_data.to_dict()
            runs.append(runs_item)

        shares = []
        for shares_item_data in self.shares:
            shares_item = shares_item_data.to_dict()
            shares.append(shares_item)

        status = self.status.value

        template_ids = self.template_ids

        views = self.views

        consumption: dict[str, Any] | Unset = UNSET
        if not isinstance(self.consumption, Unset):
            consumption = self.consumption.to_dict()

        template_versions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.template_versions, Unset):
            template_versions = self.template_versions.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "canOpen": can_open,
                "date": date,
                "description": description,
                "id": id,
                "isPublic": is_public,
                "matches": matches,
                "name": name,
                "ownerId": owner_id,
                "ownerName": owner_name,
                "runs": runs,
                "shares": shares,
                "status": status,
                "templateIds": template_ids,
                "views": views,
            }
        )
        if consumption is not UNSET:
            field_dict["consumption"] = consumption
        if template_versions is not UNSET:
            field_dict["templateVersions"] = template_versions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.analysis_out_template_versions import AnalysisOutTemplateVersions  # noqa: PLC0415
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415
        from ..models.run_out import RunOut  # noqa: PLC0415
        from ..models.share import Share  # noqa: PLC0415

        d = dict(src_dict)
        can_open = d.pop("canOpen")

        date = datetime.date.fromisoformat(d.pop("date"))

        description = d.pop("description")

        id = d.pop("id")

        is_public = d.pop("isPublic")

        matches = d.pop("matches")

        name = d.pop("name")

        owner_id = d.pop("ownerId")

        owner_name = d.pop("ownerName")

        runs = []
        _runs = d.pop("runs")
        for runs_item_data in _runs:
            runs_item = RunOut.from_dict(runs_item_data)

            runs.append(runs_item)

        shares = []
        _shares = d.pop("shares")
        for shares_item_data in _shares:
            shares_item = Share.from_dict(shares_item_data)

            shares.append(shares_item)

        status = AnalysisOutStatus(d.pop("status"))

        template_ids = cast(list[str], d.pop("templateIds"))

        views = d.pop("views")

        _consumption = d.pop("consumption", UNSET)
        consumption: ConsumptionOut | Unset
        if isinstance(_consumption, Unset):
            consumption = UNSET
        else:
            consumption = ConsumptionOut.from_dict(_consumption)

        _template_versions = d.pop("templateVersions", UNSET)
        template_versions: AnalysisOutTemplateVersions | Unset
        if isinstance(_template_versions, Unset):
            template_versions = UNSET
        else:
            template_versions = AnalysisOutTemplateVersions.from_dict(_template_versions)

        analysis_out = cls(
            can_open=can_open,
            date=date,
            description=description,
            id=id,
            is_public=is_public,
            matches=matches,
            name=name,
            owner_id=owner_id,
            owner_name=owner_name,
            runs=runs,
            shares=shares,
            status=status,
            template_ids=template_ids,
            views=views,
            consumption=consumption,
            template_versions=template_versions,
        )

        analysis_out.additional_properties = d
        return analysis_out

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
