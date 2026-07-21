from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class Gate2BudgetError(RuntimeError):
    pass


@dataclass
class Gate2BudgetGuard:
    """阶段 A/B 的硬预算门：只允许 Fake Provider，实际费用必须为零。"""

    authorized_spend_usd: Decimal = Decimal("0")
    live_model_calls_authorized: bool = False
    spent_usd: Decimal = Decimal("0")

    def authorize(self, *, provider_name: str, estimated_cost_usd: Decimal) -> None:
        if not self.live_model_calls_authorized and provider_name != "FAKE":
            raise Gate2BudgetError("阶段 A/B 未授权任何真实模型 Provider")
        if estimated_cost_usd < 0:
            raise Gate2BudgetError("预计费用不能为负数")
        if self.spent_usd + estimated_cost_usd > self.authorized_spend_usd:
            raise Gate2BudgetError("预计费用超过阶段 A/B 的零美元硬上限")

    def record_actual_cost(self, actual_cost_usd: Decimal) -> None:
        if actual_cost_usd < 0:
            raise Gate2BudgetError("实际费用不能为负数")
        new_total = self.spent_usd + actual_cost_usd
        if new_total > self.authorized_spend_usd:
            raise Gate2BudgetError("实际费用超过阶段 A/B 的零美元硬上限")
        self.spent_usd = new_total
