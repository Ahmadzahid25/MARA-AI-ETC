"""Unit tests for tools/calculations."""

from __future__ import annotations

import pytest

from shared.schemas import ToolInputError, ToolPermissionError
from tools.calculations.calculation_tool import calculate
from tools.calculations.formulas import get_formula, known_formula_ids


class TestFormulaRegistry:
    def test_known_formula_ids_includes_all_registered(self) -> None:
        assert known_formula_ids() == sorted(
            [
                'dscr',
                'loan_to_value',
                'current_ratio',
                'debt_to_equity',
                'gross_profit_margin',
                'repayment_capacity',
                'composite_risk_score',
            ]
        )

    def test_unknown_formula_id_raises(self) -> None:
        with pytest.raises(ToolInputError):
            get_formula('not_a_real_formula')

    def test_unknown_version_raises(self) -> None:
        with pytest.raises(ToolInputError):
            get_formula('dscr', version='v99')

    def test_defaults_to_latest_version(self) -> None:
        spec = get_formula('dscr')
        assert spec.version == 'v1'


class TestCalculate:
    def test_permission_denied_for_non_finance_risk_caller(self) -> None:
        with pytest.raises(ToolPermissionError):
            calculate(
                'dscr',
                {'net_operating_income': 100.0, 'total_debt_service': 50.0},
                caller_agent='market_agent',
            )

    def test_finance_agent_may_call(self) -> None:
        result = calculate(
            'dscr',
            {'net_operating_income': 120.0, 'total_debt_service': 100.0},
            caller_agent='finance_agent',
        )
        assert result.value == pytest.approx(1.2)
        assert result.formula_id == 'dscr'
        assert result.formula_version == 'v1'

    def test_risk_agent_may_call(self) -> None:
        result = calculate(
            'composite_risk_score',
            {'financial_risk': 0.2, 'compliance_risk': 0.1, 'market_risk': 0.5},
            caller_agent='risk_agent',
        )
        assert result.value == pytest.approx(0.2 * 0.4 + 0.1 * 0.4 + 0.5 * 0.2)

    def test_missing_required_input_raises(self) -> None:
        with pytest.raises(ToolInputError):
            calculate(
                'dscr', {'net_operating_income': 100.0}, caller_agent='finance_agent'
            )

    def test_division_by_zero_input_raises_tool_input_error_not_zero_division(
        self,
    ) -> None:
        with pytest.raises(ToolInputError):
            calculate(
                'dscr',
                {'net_operating_income': 100.0, 'total_debt_service': 0.0},
                caller_agent='finance_agent',
            )

    def test_composite_risk_score_rejects_out_of_range_component(self) -> None:
        with pytest.raises(ToolInputError):
            calculate(
                'composite_risk_score',
                {'financial_risk': 1.5, 'compliance_risk': 0.1, 'market_risk': 0.1},
                caller_agent='risk_agent',
            )

    def test_audit_log_captures_success(self) -> None:
        entries = []
        calculate(
            'loan_to_value',
            {'loan_amount': 50_000.0, 'collateral_value': 100_000.0},
            caller_agent='finance_agent',
            audit_sink=entries.append,
        )
        assert len(entries) == 1
        assert entries[0].tool_name == 'calculation'
        assert entries[0].outcome == 'success'

    def test_pinned_version_used(self) -> None:
        result = calculate(
            'dscr',
            {'net_operating_income': 100.0, 'total_debt_service': 100.0},
            caller_agent='finance_agent',
            version='v1',
        )
        assert result.formula_version == 'v1'
