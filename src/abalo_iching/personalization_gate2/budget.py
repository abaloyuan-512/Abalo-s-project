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


@dataclass
class Gate2CalibrationBudgetGuard:
    """阶段 C 可见校准的硬预算门。

    账户余额由产品负责人在运行前声明；守门器同时执行阶段上限和失败复测预留。
    """

    declared_account_balance_usd: Decimal
    authorized_spend_usd: Decimal
    required_reserve_usd: Decimal = Decimal("7")
    stage_limit_usd: Decimal = Decimal("5")
    spent_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        values = (
            self.declared_account_balance_usd,
            self.authorized_spend_usd,
            self.required_reserve_usd,
            self.stage_limit_usd,
            self.spent_usd,
        )
        if any(value < 0 for value in values):
            raise Gate2BudgetError("阶段 C 预算字段不能为负数")
        usable_balance = self.declared_account_balance_usd - self.required_reserve_usd
        if self.authorized_spend_usd > self.stage_limit_usd:
            raise Gate2BudgetError("阶段 C 授权额度超过5美元阶段硬上限")
        if self.authorized_spend_usd > usable_balance:
            raise Gate2BudgetError("阶段 C 授权额度会动用至少7美元的失败复测预留")
        if self.spent_usd > self.authorized_spend_usd:
            raise Gate2BudgetError("阶段 C 已花费用超过授权额度")

    @property
    def remaining_usd(self) -> Decimal:
        return self.authorized_spend_usd - self.spent_usd

    def authorize(self, estimated_cost_usd: Decimal) -> None:
        if estimated_cost_usd < 0:
            raise Gate2BudgetError("预计费用不能为负数")
        if self.spent_usd + estimated_cost_usd > self.authorized_spend_usd:
            raise Gate2BudgetError("预计费用超过阶段 C 可用预算硬上限")

    def record_actual_cost(self, actual_cost_usd: Decimal) -> None:
        if actual_cost_usd < 0:
            raise Gate2BudgetError("实际费用不能为负数")
        new_total = self.spent_usd + actual_cost_usd
        if new_total > self.authorized_spend_usd:
            raise Gate2BudgetError("实际费用超过阶段 C 可用预算硬上限")
        self.spent_usd = new_total
