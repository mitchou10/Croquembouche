from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TaskInstanceOut")


@_attrs_define
class TaskInstanceOut:
    """An instance of a worker that has the task."""

    instance_id: str
    last_seen_at: datetime.datetime
    online: bool
    service: str
    started_at: datetime.datetime
    hostname: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        instance_id = self.instance_id

        last_seen_at = self.last_seen_at.isoformat()

        online = self.online

        service = self.service

        started_at = self.started_at.isoformat()

        hostname: None | str | Unset
        if isinstance(self.hostname, Unset):
            hostname = UNSET
        else:
            hostname = self.hostname

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "instanceId": instance_id,
                "lastSeenAt": last_seen_at,
                "online": online,
                "service": service,
                "startedAt": started_at,
            }
        )
        if hostname is not UNSET:
            field_dict["hostname"] = hostname

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        instance_id = d.pop("instanceId")

        last_seen_at = datetime.datetime.fromisoformat(d.pop("lastSeenAt"))

        online = d.pop("online")

        service = d.pop("service")

        started_at = datetime.datetime.fromisoformat(d.pop("startedAt"))

        def _parse_hostname(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        hostname = _parse_hostname(d.pop("hostname", UNSET))

        task_instance_out = cls(
            instance_id=instance_id,
            last_seen_at=last_seen_at,
            online=online,
            service=service,
            started_at=started_at,
            hostname=hostname,
        )

        task_instance_out.additional_properties = d
        return task_instance_out

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
