"""
debt_calculator.py — 债务模块核心金融计算工具
支持：
  - 等额本息（equal_installment）：每月还款金额固定，利息逐期递减，本金逐期递增
  - 等额本金（equal_principal）：每月归还本金固定，利息逐期递减，月供逐期减少
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from dateutil.relativedelta import relativedelta


@dataclass
class PeriodDetail:
    period_no: int
    due_date: date
    payment_amount: float     # 月供总额
    principal_amount: float   # 本期还本金
    interest_amount: float    # 本期还利息
    remaining_balance: float  # 还完本期后剩余本金


def calc_monthly_payment_equal_installment(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> float:
    """
    等额本息月供公式：
        r = annual_rate / 100 / 12
        M = P * r * (1+r)^n / ((1+r)^n - 1)
    当利率为 0 时退化为等额本金（均摊）。
    """
    r = annual_rate / 100 / 12
    if r == 0:
        return round(principal / term_months, 2)
    factor = math.pow(1 + r, term_months)
    monthly = principal * r * factor / (factor - 1)
    return round(monthly, 2)


def calc_monthly_payment_equal_principal(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> float:
    """
    等额本金首期月供：
        首期 = P/n + P * r
    （仅供展示，等额本金每期月供不同）
    """
    r = annual_rate / 100 / 12
    first = principal / term_months + principal * r
    return round(first, 2)


def generate_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
    repay_method: str,
    first_repay_date: date,
) -> list[PeriodDetail]:
    """
    生成完整还款计划表。

    参数：
        principal        — 贷款本金
        annual_rate      — 年化利率（如 3.85 表示 3.85%）
        term_months      — 还款总期数（月）
        repay_method     — "equal_installment" 或 "equal_principal"
        first_repay_date — 首期还款日期

    返回：
        PeriodDetail 列表，长度等于 term_months
    """
    r = annual_rate / 100 / 12
    schedule: list[PeriodDetail] = []
    balance = principal

    if repay_method == "equal_installment":
        # 等额本息：月供固定
        monthly = calc_monthly_payment_equal_installment(principal, annual_rate, term_months)

        for i in range(1, term_months + 1):
            interest = round(balance * r, 2)
            # 最后一期处理浮点误差，将所有剩余本金一次性还清
            if i == term_months:
                principal_part = round(balance, 2)
                payment = round(principal_part + interest, 2)
            else:
                principal_part = round(monthly - interest, 2)
                payment = monthly

            balance = round(balance - principal_part, 2)
            # 防止最后一期因浮点出现负数余额
            if balance < 0:
                balance = 0.0

            due_date = first_repay_date + relativedelta(months=i - 1)
            schedule.append(PeriodDetail(
                period_no=i,
                due_date=due_date,
                payment_amount=payment,
                principal_amount=principal_part,
                interest_amount=interest,
                remaining_balance=balance,
            ))

    elif repay_method == "equal_principal":
        # 等额本金：每月归还本金固定，利息逐期递减
        principal_per_period = round(principal / term_months, 2)

        for i in range(1, term_months + 1):
            interest = round(balance * r, 2)
            if i == term_months:
                principal_part = round(balance, 2)
            else:
                principal_part = principal_per_period
            payment = round(principal_part + interest, 2)
            balance = round(balance - principal_part, 2)
            if balance < 0:
                balance = 0.0

            due_date = first_repay_date + relativedelta(months=i - 1)
            schedule.append(PeriodDetail(
                period_no=i,
                due_date=due_date,
                payment_amount=payment,
                principal_amount=principal_part,
                interest_amount=interest,
                remaining_balance=balance,
            ))

    else:
        raise ValueError(f"不支持的还款方式：{repay_method}")

    return schedule
