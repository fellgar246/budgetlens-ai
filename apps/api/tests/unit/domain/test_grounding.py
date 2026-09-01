from __future__ import annotations

from budgetlens.domain.evidence import (
    GROUNDING_FAILED_MESSAGE,
    EvidenceRecord,
    extract_decimal_literals,
    verify_answer_grounding,
)


def test_grounding_rejects_unknown_citations_and_invented_figures() -> None:
    records = (
        EvidenceRecord(
            id="ev_1",
            tool="get_variance_summary",
            label="Resumen",
            data={"metrics": {"variance_amount": "30000.0000"}},
            figures=("30000.0000",),
        ),
    )
    ok = verify_answer_grounding(
        "La variación fue 30000.0000. Evidencia: ev_1.",
        records,
    )
    assert ok.ok is True
    bad_id = verify_answer_grounding("Según ev_9 el total es 30000.0000.", records)
    assert bad_id.ok is False
    assert "ev_9" in bad_id.missing_citations
    invented = verify_answer_grounding("La variación fue 99999.0000. Evidencia: ev_1.", records)
    assert invented.failed is True
    assert invented.unknown_figures
    assert GROUNDING_FAILED_MESSAGE.startswith("No pude verificar")
    assert "30000.0000" in extract_decimal_literals("variación 30000.0000 en enero")
