"""Unit tests for agents/finance_agent/finance_agent.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.finance_agent.finance_agent import (
    CalculationRequest,
    FinanceAgent,
    FinancialAssessmentParsingError,
    MissingSourceFigureError,
)
from shared.schemas.documents import (
    Citation,
    DocumentClassification,
    DocumentExtractionRecord,
    ExtractedField,
    ExtractionSource,
)
from shared.schemas.finance import FigureProvenance
from shared.schemas.knowledge import TrustTier


def _field(name: str, value: str, confidence: float = 0.95) -> ExtractedField:
    return ExtractedField(
        name=name,
        value=value,
        confidence=confidence,
        source=ExtractionSource.PDF_TEXT_LAYER,
        citation=Citation(document_id='doc-1', page=1),
    )


def _record(*fields: ExtractedField) -> DocumentExtractionRecord:
    return DocumentExtractionRecord(
        document_id='doc-1',
        classification=DocumentClassification(
            document_type='financial_statement', confidence=0.9
        ),
        fields=list(fields),
    )


async def _fake_assessor(figures):
    return 'Repayment capacity is adequate.', 0.9


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_traces_extracted_and_calculated_figures(self) -> None:
        record = _record(
            _field('net_operating_income', '12000'),
            _field('total_debt_service', '10000'),
        )
        agent = FinanceAgent(assessor=_fake_assessor)
        analysis = await agent.analyze(
            'doc-1',
            record,
            [
                CalculationRequest(
                    'dscr',
                    {
                        'net_operating_income': 'net_operating_income',
                        'total_debt_service': 'total_debt_service',
                    },
                )
            ],
        )

        provenances = {f.name: f.provenance for f in analysis.figures}
        assert provenances['net_operating_income'] == FigureProvenance.EXTRACTED
        assert provenances['total_debt_service'] == FigureProvenance.EXTRACTED
        assert provenances['dscr'] == FigureProvenance.CALCULATED

        dscr_figure = next(f for f in analysis.figures if f.name == 'dscr')
        assert dscr_figure.value == pytest.approx(1.2)
        assert dscr_figure.formula_id == 'dscr'
        assert dscr_figure.formula_version == 'v1'

        extracted_figure = next(
            f for f in analysis.figures if f.name == 'net_operating_income'
        )
        assert extracted_figure.source_citation == Citation(document_id='doc-1', page=1)

    @pytest.mark.asyncio
    async def test_missing_field_escalates(self) -> None:
        record = _record(_field('net_operating_income', '12000'))
        agent = FinanceAgent(assessor=_fake_assessor)

        with pytest.raises(MissingSourceFigureError):
            await agent.analyze(
                'doc-1',
                record,
                [
                    CalculationRequest(
                        'dscr',
                        {
                            'net_operating_income': 'net_operating_income',
                            'total_debt_service': 'total_debt_service',
                        },
                    )
                ],
            )

    @pytest.mark.asyncio
    async def test_low_confidence_field_escalates(self) -> None:
        record = _record(
            _field('net_operating_income', '12000', confidence=0.5),
            _field('total_debt_service', '10000'),
        )
        agent = FinanceAgent(assessor=_fake_assessor)

        with pytest.raises(MissingSourceFigureError):
            await agent.analyze(
                'doc-1',
                record,
                [
                    CalculationRequest(
                        'dscr',
                        {
                            'net_operating_income': 'net_operating_income',
                            'total_debt_service': 'total_debt_service',
                        },
                    )
                ],
            )

    @pytest.mark.asyncio
    async def test_no_calculations_still_runs_assessment(self) -> None:
        record = _record()
        agent = FinanceAgent(assessor=_fake_assessor)
        analysis = await agent.analyze('doc-1', record, [])
        assert analysis.figures == []
        assert analysis.assessment_confidence == 0.9

    @pytest.mark.asyncio
    async def test_product_query_attaches_citations(self) -> None:
        from shared.schemas.knowledge import (
            DocumentKind,
            PolicyCitation,
            RetrievalResult,
            RetrievedChunk,
            SensitivityClass,
        )

        chunk = RetrievedChunk(
            document_id='prod-1',
            version='v1',
            locator='2',
            text='Max grant amount is RM50,000.',
            relevance=0.8,
            document_kind=DocumentKind.PRODUCT_TERMS,
            sensitivity=SensitivityClass.INTERNAL,
            trust_tier=TrustTier.APPROVED,
        )

        class StubBackend:
            async def retrieve(self, query):
                assert query.filters.document_kinds == frozenset(
                    {DocumentKind.PRODUCT_TERMS}
                )
                return RetrievalResult(chunks=(chunk,))

        record = _record()
        agent = FinanceAgent(assessor=_fake_assessor, backend=StubBackend())
        analysis = await agent.analyze(
            'doc-1', record, [], product_query='grant loan limit'
        )

        assert analysis.product_term_citations == [
            PolicyCitation(
                document_id='prod-1',
                version='v1',
                locator='2',
                relevance=0.8,
                trust_tier=TrustTier.APPROVED,
            )
        ]

    @pytest.mark.asyncio
    async def test_default_assessor_calls_llm_with_finance_tier(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"assessment": "solid", "confidence": 0.88}')
            )
        ]
        mock_llm = MagicMock()
        mock_llm.complete_for_agent = AsyncMock(return_value=mock_response)

        agent = FinanceAgent(llm_client=mock_llm)
        analysis = await agent.analyze('doc-1', _record(), [])

        assert analysis.assessment == 'solid'
        assert analysis.assessment_confidence == pytest.approx(0.88)
        called_agent = mock_llm.complete_for_agent.call_args[0][0]
        assert called_agent.value == 'finance_agent'

    @pytest.mark.asyncio
    async def test_malformed_assessor_output_raises(self) -> None:
        # Exercise the parsing path directly via a malformed LLM response.
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='not json'))]
        mock_llm = MagicMock()
        mock_llm.complete_for_agent = AsyncMock(return_value=mock_response)

        agent = FinanceAgent(llm_client=mock_llm)
        with pytest.raises(FinancialAssessmentParsingError):
            await agent.analyze('doc-1', _record(), [])
