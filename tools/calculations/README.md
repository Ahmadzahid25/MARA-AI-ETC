# Deterministic calculation formula library

Implemented (Milestone 3): `calculate()` — permission check (Finance/Risk
agents only), timeout (2s), retry (1), and typed-error/audit-log behavior
per §6.2's calculation row, wrapping `tools/calculations/formulas.py`'s
versioned registry (`get_formula()`, `known_formula_ids()`).

Every formula (`dscr`, `loan_to_value`, `current_ratio`, `debt_to_equity`,
`gross_profit_margin`, `repayment_capacity`, `composite_risk_score`) is
real, decided arithmetic — genuine engineering, not a vendor/model choice,
so unlike `tools/ocr` there is no injectable-with-no-default seam here.
Each carries an explicit `version` string from day one
(docs/architecture/14-roadmap.md §14.5: "calculation-formula versioning
discipline must be established now") — a changed formula definition is a
new registry entry under a bumped version, never a mutation in place, so a
workflow that already cited "dscr v1" keeps meaning exactly that.

See [06-tool-architecture.md](../../docs/architecture/06-tool-architecture.md)
for the full specification this module implements. Do not add code here
without a corresponding entry in that document, per
docs/repo-audit/05-development-guidelines.md §5.5.
