from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.task_instance_out import TaskInstanceOut
    from ..models.task_out_input_schema import TaskOutInputSchema
    from ..models.task_out_output_schema import TaskOutOutputSchema
    from ..models.task_out_parameters import TaskOutParameters


T = TypeVar("T", bound="TaskOut")


@_attrs_define
class TaskOut:
    """A task and one of its versions, with the instances that have it."""

    author: str
    created_at: datetime.datetime
    description: str
    input_schema: TaskOutInputSchema
    instances: list[TaskInstanceOut]
    name: str
    online: int
    output_schema: TaskOutOutputSchema
    parameters: TaskOutParameters
    version: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        author = self.author

        created_at = self.created_at.isoformat()

        description = self.description

        input_schema = self.input_schema.to_dict()

        instances = []
        for instances_item_data in self.instances:
            instances_item = instances_item_data.to_dict()
            instances.append(instances_item)

        name = self.name

        online = self.online

        output_schema = self.output_schema.to_dict()

        parameters = self.parameters.to_dict()

        version = self.version

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "author": author,
                "createdAt": created_at,
                "description": description,
                "inputSchema": input_schema,
                "instances": instances,
                "name": name,
                "online": online,
                "outputSchema": output_schema,
                "parameters": parameters,
                "version": version,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.task_instance_out import TaskInstanceOut  # noqa: PLC0415
        from ..models.task_out_input_schema import TaskOutInputSchema  # noqa: PLC0415
        from ..models.task_out_output_schema import TaskOutOutputSchema  # noqa: PLC0415
        from ..models.task_out_parameters import TaskOutParameters  # noqa: PLC0415

        d = dict(src_dict)
        author = d.pop("author")

        created_at = datetime.datetime.fromisoformat(d.pop("createdAt"))

        description = d.pop("description")

        input_schema = TaskOutInputSchema.from_dict(d.pop("inputSchema"))

        instances = []
        _instances = d.pop("instances")
        for instances_item_data in _instances:
            instances_item = TaskInstanceOut.from_dict(instances_item_data)

            instances.append(instances_item)

        name = d.pop("name")

        online = d.pop("online")

        output_schema = TaskOutOutputSchema.from_dict(d.pop("outputSchema"))

        parameters = TaskOutParameters.from_dict(d.pop("parameters"))

        version = d.pop("version")

        task_out = cls(
            author=author,
            created_at=created_at,
            description=description,
            input_schema=input_schema,
            instances=instances,
            name=name,
            online=online,
            output_schema=output_schema,
            parameters=parameters,
            version=version,
        )

        task_out.additional_properties = d
        return task_out

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
