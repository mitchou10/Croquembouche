from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.run_out_file_decision_type_0 import RunOutFileDecisionType0
from ..models.run_out_findstatus import RunOutFindstatus
from ..models.run_out_ocrstatus import RunOutOcrstatus
from ..models.run_out_status import RunOutStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.consumption_out import ConsumptionOut
    from ..models.detection_out import DetectionOut
    from ..models.document_out import DocumentOut
    from ..models.ocr_page import OcrPage
    from ..models.page_out import PageOut
    from ..models.run_out_template_versions import RunOutTemplateVersions


T = TypeVar("T", bound="RunOut")


@_attrs_define
class RunOut:
    """One use of an analysis. Whoever can open the analysis sees who ran it, when and how it went; what it found is for
    the person who ran it alone, an administrator included.

    """

    date: datetime.date
    has_result: bool
    id: str
    matches: int
    status: RunOutStatus
    user_id: str
    user_name: str
    consumption: ConsumptionOut | None | Unset = UNSET
    detections: list[DetectionOut] | None | Unset = UNSET
    file_decision: None | RunOutFileDecisionType0 | Unset = UNSET
    file_name: None | str | Unset = UNSET
    find_status: RunOutFindstatus | Unset = RunOutFindstatus.NONE
    ocr: list[OcrPage] | None | Unset = UNSET
    ocr_status: RunOutOcrstatus | Unset = RunOutOcrstatus.NONE
    pages: list[PageOut] | None | Unset = UNSET
    screenshot: DocumentOut | None | Unset = UNSET
    template_versions: RunOutTemplateVersions | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415
        from ..models.document_out import DocumentOut  # noqa: PLC0415

        date = self.date.isoformat()

        has_result = self.has_result

        id = self.id

        matches = self.matches

        status = self.status.value

        user_id = self.user_id

        user_name = self.user_name

        consumption: dict[str, Any] | None | Unset
        if isinstance(self.consumption, Unset):
            consumption = UNSET
        elif isinstance(self.consumption, ConsumptionOut):
            consumption = self.consumption.to_dict()
        else:
            consumption = self.consumption

        detections: list[dict[str, Any]] | None | Unset
        if isinstance(self.detections, Unset):
            detections = UNSET
        elif isinstance(self.detections, list):
            detections = []
            for detections_type_0_item_data in self.detections:
                detections_type_0_item = detections_type_0_item_data.to_dict()
                detections.append(detections_type_0_item)

        else:
            detections = self.detections

        file_decision: None | str | Unset
        if isinstance(self.file_decision, Unset):
            file_decision = UNSET
        elif isinstance(self.file_decision, RunOutFileDecisionType0):
            file_decision = self.file_decision.value
        else:
            file_decision = self.file_decision

        file_name: None | str | Unset
        if isinstance(self.file_name, Unset):
            file_name = UNSET
        else:
            file_name = self.file_name

        find_status: str | Unset = UNSET
        if not isinstance(self.find_status, Unset):
            find_status = self.find_status.value

        ocr: list[dict[str, Any]] | None | Unset
        if isinstance(self.ocr, Unset):
            ocr = UNSET
        elif isinstance(self.ocr, list):
            ocr = []
            for ocr_type_0_item_data in self.ocr:
                ocr_type_0_item = ocr_type_0_item_data.to_dict()
                ocr.append(ocr_type_0_item)

        else:
            ocr = self.ocr

        ocr_status: str | Unset = UNSET
        if not isinstance(self.ocr_status, Unset):
            ocr_status = self.ocr_status.value

        pages: list[dict[str, Any]] | None | Unset
        if isinstance(self.pages, Unset):
            pages = UNSET
        elif isinstance(self.pages, list):
            pages = []
            for pages_type_0_item_data in self.pages:
                pages_type_0_item = pages_type_0_item_data.to_dict()
                pages.append(pages_type_0_item)

        else:
            pages = self.pages

        screenshot: dict[str, Any] | None | Unset
        if isinstance(self.screenshot, Unset):
            screenshot = UNSET
        elif isinstance(self.screenshot, DocumentOut):
            screenshot = self.screenshot.to_dict()
        else:
            screenshot = self.screenshot

        template_versions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.template_versions, Unset):
            template_versions = self.template_versions.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "date": date,
                "hasResult": has_result,
                "id": id,
                "matches": matches,
                "status": status,
                "userId": user_id,
                "userName": user_name,
            }
        )
        if consumption is not UNSET:
            field_dict["consumption"] = consumption
        if detections is not UNSET:
            field_dict["detections"] = detections
        if file_decision is not UNSET:
            field_dict["fileDecision"] = file_decision
        if file_name is not UNSET:
            field_dict["fileName"] = file_name
        if find_status is not UNSET:
            field_dict["findStatus"] = find_status
        if ocr is not UNSET:
            field_dict["ocr"] = ocr
        if ocr_status is not UNSET:
            field_dict["ocrStatus"] = ocr_status
        if pages is not UNSET:
            field_dict["pages"] = pages
        if screenshot is not UNSET:
            field_dict["screenshot"] = screenshot
        if template_versions is not UNSET:
            field_dict["templateVersions"] = template_versions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.consumption_out import ConsumptionOut  # noqa: PLC0415
        from ..models.detection_out import DetectionOut  # noqa: PLC0415
        from ..models.document_out import DocumentOut  # noqa: PLC0415
        from ..models.ocr_page import OcrPage  # noqa: PLC0415
        from ..models.page_out import PageOut  # noqa: PLC0415
        from ..models.run_out_template_versions import RunOutTemplateVersions  # noqa: PLC0415

        d = dict(src_dict)
        date = datetime.date.fromisoformat(d.pop("date"))

        has_result = d.pop("hasResult")

        id = d.pop("id")

        matches = d.pop("matches")

        status = RunOutStatus(d.pop("status"))

        user_id = d.pop("userId")

        user_name = d.pop("userName")

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

        def _parse_detections(data: object) -> list[DetectionOut] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                detections_type_0 = []
                _detections_type_0 = data
                for detections_type_0_item_data in _detections_type_0:
                    detections_type_0_item = DetectionOut.from_dict(detections_type_0_item_data)

                    detections_type_0.append(detections_type_0_item)

                return detections_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[DetectionOut] | None | Unset, data)

        detections = _parse_detections(d.pop("detections", UNSET))

        def _parse_file_decision(data: object) -> None | RunOutFileDecisionType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                file_decision_type_0 = RunOutFileDecisionType0(data)

                return file_decision_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunOutFileDecisionType0 | Unset, data)

        file_decision = _parse_file_decision(d.pop("fileDecision", UNSET))

        def _parse_file_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        file_name = _parse_file_name(d.pop("fileName", UNSET))

        _find_status = d.pop("findStatus", UNSET)
        find_status: RunOutFindstatus | Unset
        if isinstance(_find_status, Unset):
            find_status = UNSET
        else:
            find_status = RunOutFindstatus(_find_status)

        def _parse_ocr(data: object) -> list[OcrPage] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                ocr_type_0 = []
                _ocr_type_0 = data
                for ocr_type_0_item_data in _ocr_type_0:
                    ocr_type_0_item = OcrPage.from_dict(ocr_type_0_item_data)

                    ocr_type_0.append(ocr_type_0_item)

                return ocr_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[OcrPage] | None | Unset, data)

        ocr = _parse_ocr(d.pop("ocr", UNSET))

        _ocr_status = d.pop("ocrStatus", UNSET)
        ocr_status: RunOutOcrstatus | Unset
        if isinstance(_ocr_status, Unset):
            ocr_status = UNSET
        else:
            ocr_status = RunOutOcrstatus(_ocr_status)

        def _parse_pages(data: object) -> list[PageOut] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                pages_type_0 = []
                _pages_type_0 = data
                for pages_type_0_item_data in _pages_type_0:
                    pages_type_0_item = PageOut.from_dict(pages_type_0_item_data)

                    pages_type_0.append(pages_type_0_item)

                return pages_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[PageOut] | None | Unset, data)

        pages = _parse_pages(d.pop("pages", UNSET))

        def _parse_screenshot(data: object) -> DocumentOut | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                screenshot_type_0 = DocumentOut.from_dict(data)

                return screenshot_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(DocumentOut | None | Unset, data)

        screenshot = _parse_screenshot(d.pop("screenshot", UNSET))

        _template_versions = d.pop("templateVersions", UNSET)
        template_versions: RunOutTemplateVersions | Unset
        if isinstance(_template_versions, Unset):
            template_versions = UNSET
        else:
            template_versions = RunOutTemplateVersions.from_dict(_template_versions)

        run_out = cls(
            date=date,
            has_result=has_result,
            id=id,
            matches=matches,
            status=status,
            user_id=user_id,
            user_name=user_name,
            consumption=consumption,
            detections=detections,
            file_decision=file_decision,
            file_name=file_name,
            find_status=find_status,
            ocr=ocr,
            ocr_status=ocr_status,
            pages=pages,
            screenshot=screenshot,
            template_versions=template_versions,
        )

        run_out.additional_properties = d
        return run_out

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
