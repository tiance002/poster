from app.agent import parse_analysis


def test_parse_analysis_requires_safe_structured_fields() -> None:
    result = parse_analysis(
        '{"summary":"Customer asks for an invoice.","category":"request",'
        '"risk_note":"No risk detected.","reply_draft":"We will send it shortly."}'
    )

    assert result.category == "request"
    assert result.reply_draft == "We will send it shortly."
