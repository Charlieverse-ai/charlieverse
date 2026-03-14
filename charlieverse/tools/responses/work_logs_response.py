"""Response from work log list/search tools."""

from pydantic import BaseModel

from charlieverse.tools.responses.work_log_summary import WorkLogSummary


class WorkLogsResponse(BaseModel):
    """Returned by list_work_logs and search_work_logs."""

    work_logs: list[WorkLogSummary]
