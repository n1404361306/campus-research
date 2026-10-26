"""Read-only campus tools loaded through DeerFlow's existing tool configuration."""

from math import ceil
from typing import Annotated

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class FeatureEstimate(BaseModel):
    """One feature and its supplied, estimated effort; not measured performance."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ] = Field(description="功能名称，例如登录、发布失物、搜索。")
    estimated_hours: int = Field(
        strict=True,
        ge=1,
        le=2000,
        description="用户提供或明确同意的预计工时，单位小时，必须为正整数。",
    )


class ScheduleInput(BaseModel):
    """Validated arguments exposed to the model as JSON Schema."""

    model_config = ConfigDict(extra="forbid")

    features: list[FeatureEstimate] = Field(
        min_length=1,
        max_length=30,
        description="1到30项功能及各自预计工时；不能把猜测伪装为用户输入。",
    )
    hours_per_week: int = Field(
        strict=True, ge=1, le=80, description="每周可用于本项目的小时数，1到80的整数。"
    )
    deadline_weeks: int = Field(
        strict=True, ge=1, le=104, description="距离截止还有多少周，1到104的整数。"
    )
    buffer_percent: int = Field(
        default=20,
        strict=True,
        ge=0,
        le=100,
        description="额外预留工时的百分比，默认20，范围0到100。",
    )


@tool("estimate_project_schedule", args_schema=ScheduleInput)
def estimate_project_schedule(
    features: list[FeatureEstimate],
    hours_per_week: int,
    deadline_weeks: int,
    buffer_percent: int = 20,
) -> dict:
    """Estimate a single student's project schedule from supplied feature hours.

    Use when checking whether a campus project fits a deadline. Ask for missing
    effort estimates, weekly availability and deadline; do not invent them.
    This deterministic arithmetic is advisory, not a prediction or guarantee.
    It does not search, change todos, or write files. Features execute serially.
    """
    base_hours = sum(feature.estimated_hours for feature in features)
    buffer_hours = ceil(base_hours * buffer_percent / 100)
    total_hours = base_hours + buffer_hours
    estimated_weeks = ceil(total_hours / hours_per_week)
    capacity_hours = hours_per_week * deadline_weeks

    return {
        "base_hours": base_hours,
        "buffer_percent": buffer_percent,
        "buffer_hours": buffer_hours,
        "total_hours": total_hours,
        "estimated_weeks": estimated_weeks,
        "capacity_hours": capacity_hours,
        "fits_deadline": total_hours <= capacity_hours,
        "shortfall_hours": max(0, total_hours - capacity_hours),
        "assumptions": "基于输入工时的单人顺序开发估算，额外工时与周数向上取整；不自动估计功能难度，不保证按期完成。",
    }
