"""Deterministic calculation formula library — docs/architecture/
06-tool-architecture.md §6.2's calculation row:

    Input: Named formula ID + typed numeric inputs
    Output: Numeric result + formula version used
    Permissions: Finance, Risk agents
    Timeout: 2s
    Retries: 1
    Notes: "Deterministic, versioned formula library — never LLM-computed
    arithmetic for a figure that informs a decision"

**Milestone 3 slice.** Every formula here is a real, decided, versioned
implementation — unlike an OCR engine or embedding model, "how do you
compute a current ratio" is not a vendor choice this repo is waiting on;
it's ordinary financial arithmetic, and MARA's roadmap explicitly calls out
that "calculation-formula versioning discipline must be established now,
since retrofitting it after formulas are in use is costlier"
(docs/architecture/14-roadmap.md §14.5). Each formula therefore carries an
explicit ``version`` string from day one, and a formula is never mutated in
place — a changed definition is a new registry entry under a bumped
version, so a workflow that already cited "dscr v1" keeps meaning exactly
that even after "dscr v2" ships (mirrors §9.4's document-versioning
reasoning, applied to formulas instead of policy text).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from shared.schemas.tooling import ToolInputError


@dataclass(frozen=True)
class FormulaSpec:
    formula_id: str
    version: str
    required_inputs: tuple[str, ...]
    compute: Callable[[dict[str, float]], float]
    description: str


def _dscr(inputs: dict[str, float]) -> float:
    """Debt Service Coverage Ratio: can the business's operating income
    cover its total debt obligations? >= 1.0 means yes."""
    net_operating_income = inputs['net_operating_income']
    total_debt_service = inputs['total_debt_service']
    if total_debt_service == 0:
        raise ToolInputError('total_debt_service must not be zero')
    return net_operating_income / total_debt_service


def _ltv(inputs: dict[str, float]) -> float:
    """Loan-to-Value: what fraction of the collateral's value does the
    requested loan represent?"""
    loan_amount = inputs['loan_amount']
    collateral_value = inputs['collateral_value']
    if collateral_value <= 0:
        raise ToolInputError('collateral_value must be > 0')
    return loan_amount / collateral_value


def _current_ratio(inputs: dict[str, float]) -> float:
    """Current Ratio: short-term liquidity — current assets over current
    liabilities."""
    current_assets = inputs['current_assets']
    current_liabilities = inputs['current_liabilities']
    if current_liabilities == 0:
        raise ToolInputError('current_liabilities must not be zero')
    return current_assets / current_liabilities


def _debt_to_equity(inputs: dict[str, float]) -> float:
    """Debt-to-Equity: leverage — total liabilities over total equity."""
    total_liabilities = inputs['total_liabilities']
    total_equity = inputs['total_equity']
    if total_equity == 0:
        raise ToolInputError('total_equity must not be zero')
    return total_liabilities / total_equity


def _gross_profit_margin(inputs: dict[str, float]) -> float:
    """Gross Profit Margin: gross profit as a fraction of revenue."""
    gross_profit = inputs['gross_profit']
    revenue = inputs['revenue']
    if revenue == 0:
        raise ToolInputError('revenue must not be zero')
    return gross_profit / revenue


def _repayment_capacity(inputs: dict[str, float]) -> float:
    """Repayment Capacity Ratio: net disposable income over the proposed
    monthly installment — MARA's SME/grant repayment-affordability check
    (docs/architecture/05-agent-architecture.md §5.5)."""
    net_disposable_income = inputs['net_disposable_income']
    monthly_installment = inputs['monthly_installment']
    if monthly_installment <= 0:
        raise ToolInputError('monthly_installment must be > 0')
    return net_disposable_income / monthly_installment


def _composite_risk_score(inputs: dict[str, float]) -> float:
    """Weighted synthesis of the three component risk scores the Risk Agent
    consumes (docs/architecture/05-agent-architecture.md §5.6: "financial,
    compliance, market risk"), each expected on a 0.0 (lowest risk) to 1.0
    (highest risk) scale. Weights are an explicit, versioned decision —
    changing them is a new formula version, not a silent config edit, since
    a shifted weighting changes what "the same" risk rating means across
    cases decided before and after the change."""
    financial_risk = inputs['financial_risk']
    compliance_risk = inputs['compliance_risk']
    market_risk = inputs['market_risk']
    for name, value in (
        ('financial_risk', financial_risk),
        ('compliance_risk', compliance_risk),
        ('market_risk', market_risk),
    ):
        if not 0.0 <= value <= 1.0:
            raise ToolInputError(f'{name} must be within [0.0, 1.0], got {value}')
    weights = {'financial_risk': 0.4, 'compliance_risk': 0.4, 'market_risk': 0.2}
    return sum(inputs[name] * weight for name, weight in weights.items())


_FORMULA_VERSIONS: dict[str, list[FormulaSpec]] = {}


def _register(spec: FormulaSpec) -> None:
    _FORMULA_VERSIONS.setdefault(spec.formula_id, []).append(spec)


_register(
    FormulaSpec(
        'dscr',
        'v1',
        ('net_operating_income', 'total_debt_service'),
        _dscr,
        'Debt Service Coverage Ratio',
    )
)
_register(
    FormulaSpec(
        'loan_to_value',
        'v1',
        ('loan_amount', 'collateral_value'),
        _ltv,
        'Loan-to-Value ratio',
    )
)
_register(
    FormulaSpec(
        'current_ratio',
        'v1',
        ('current_assets', 'current_liabilities'),
        _current_ratio,
        'Current ratio (short-term liquidity)',
    )
)
_register(
    FormulaSpec(
        'debt_to_equity',
        'v1',
        ('total_liabilities', 'total_equity'),
        _debt_to_equity,
        'Debt-to-equity ratio (leverage)',
    )
)
_register(
    FormulaSpec(
        'gross_profit_margin',
        'v1',
        ('gross_profit', 'revenue'),
        _gross_profit_margin,
        'Gross profit margin',
    )
)
_register(
    FormulaSpec(
        'repayment_capacity',
        'v1',
        ('net_disposable_income', 'monthly_installment'),
        _repayment_capacity,
        'Repayment capacity ratio',
    )
)
_register(
    FormulaSpec(
        'composite_risk_score',
        'v1',
        ('financial_risk', 'compliance_risk', 'market_risk'),
        _composite_risk_score,
        'Weighted composite risk score (0.4/0.4/0.2 financial/compliance/market)',
    )
)


def get_formula(formula_id: str, version: str | None = None) -> FormulaSpec:
    """Look up a formula by ID, defaulting to its latest registered
    version. Raises ``ToolInputError`` for an unknown ID or version — never
    silently falls back to a different formula than the one requested."""

    versions = _FORMULA_VERSIONS.get(formula_id)
    if not versions:
        raise ToolInputError(
            f'Unknown formula_id {formula_id!r} (known: '
            f'{sorted(_FORMULA_VERSIONS)})'
        )
    if version is None:
        return versions[-1]
    for spec in versions:
        if spec.version == version:
            return spec
    raise ToolInputError(
        f'Unknown version {version!r} for formula_id {formula_id!r} (known: '
        f'{[s.version for s in versions]})'
    )


def known_formula_ids() -> list[str]:
    return sorted(_FORMULA_VERSIONS)
