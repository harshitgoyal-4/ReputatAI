from pathlib import Path

import pytest

from app.ai_engine.analyzer import AnalyzerError, MockReviewAnalyzer, NVIDIAReviewAnalyzer
from app.analytics.analytics import calculate_analytics, generate_business_insights
from app.ingestion.base_connector import FeedbackConnector
from app.ingestion.csv_loader import CSVConnector, load_reviews
from app.ingestion.normalizer import NormalizedFeedback
from app.main import _failed_record, get_analyzer
from app.response_engine.generator import (MockResponseGenerator, NVIDIAResponseGenerator, ResponseGenerator,
                                            ResponseGeneratorError, get_response_generator)


def review(text: str, rating: int = 3) -> dict[str, object]:
    return {"review_id": "test", "date": "2026-01-01", "rating": rating, "platform": "Test", "customer": "Tester", "review": text}


def test_positive_review_classification() -> None:
    assert MockReviewAnalyzer().analyze(review("Excellent and friendly service", 5)).sentiment == "positive"


def test_negative_review_classification() -> None:
    assert MockReviewAnalyzer().analyze(review("Worst broken product", 1)).sentiment == "negative"


def test_delivery_topic_detection() -> None:
    assert MockReviewAnalyzer().analyze(review("Delivery was late", 2)).topic == "delivery"


def test_refund_intent_detection() -> None:
    assert MockReviewAnalyzer().analyze(review("I want a refund", 2)).intent == "refund_request"


def test_severe_review_has_high_risk() -> None:
    result = MockReviewAnalyzer().analyze(review("This is fraud and unsafe", 1))
    assert result.risk_level in {"high", "critical"} and result.requires_escalation


def test_risk_score_is_bounded() -> None:
    result = MockReviewAnalyzer().analyze(review("Fraud scam unsafe police legal never again", 1))
    assert 0 <= result.risk_score <= 100


def test_pipeline_loads_valid_csv() -> None:
    result = load_reviews(Path("data/reviews.csv"))
    assert len(result.records) == 20 and not result.errors


def test_csv_connector_returns_normalized_feedback() -> None:
    result = CSVConnector(Path("data/reviews.csv")).fetch()
    assert isinstance(CSVConnector(Path("data/reviews.csv")), FeedbackConnector)
    assert len(result.records) == 20 and not result.errors
    first = result.records[0]
    assert first == NormalizedFeedback(
        id="1", date="2026-08-20", platform="Google", author="Customer A",
        text="Excellent service and very friendly staff.", rating=5,
    )
    assert first.to_legacy_record()["review_id"] == "1"


def test_csv_connector_rejects_invalid_rows(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    path.write_text(
        "review_id,date,rating,platform,customer,review\n"
        ",2026-01-01,5,Google,Customer,Missing id\n"
        "bad,2026-01-01,6,Google,Customer,Invalid rating\n"
        "good,2026-01-01,4,Google,Customer,Valid review\n",
        encoding="utf-8",
    )
    result = CSVConnector(path).fetch()
    assert [record.id for record in result.records] == ["good"]
    assert len(result.errors) == 2
    assert "review_id cannot be empty" in result.errors[0]
    assert "rating must be an integer from 1 to 5" in result.errors[1]


def test_csv_connector_requires_all_columns(tmp_path: Path) -> None:
    path = tmp_path / "missing-column.csv"
    path.write_text("review_id,date,review\n1,2026-01-01,Feedback\n", encoding="utf-8")
    result = CSVConnector(path).fetch()
    assert result.records == []
    assert result.errors == ["Missing required columns: rating, platform, customer"]


def test_analyzer_accepts_normalized_feedback() -> None:
    feedback = NormalizedFeedback(
        id="normalized", date="2026-01-01", platform="Survey", author="Tester",
        text="Excellent service", rating=5,
    )
    assert MockReviewAnalyzer().analyze(feedback).review_id == "normalized"


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content

    def create(self, **_: object) -> object:
        message = type("Message", (), {"content": self.content})()
        return type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})()


class FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = type("Chat", (), {"completions": FakeCompletions(content)})()


def nvidia_analyzer(monkeypatch: pytest.MonkeyPatch, content: str) -> NVIDIAReviewAnalyzer:
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_MODEL", "test-model")
    return NVIDIAReviewAnalyzer({"categories": ["delivery", "product_quality", "customer_support", "pricing", "refund", "staff", "general"]}, FakeClient(content))


def test_factory_selects_nvidia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_MODEL", "test-model")
    assert isinstance(get_analyzer("nvidia", {"categories": ["general"]}), NVIDIAReviewAnalyzer)


def test_valid_nvidia_response_is_validated_and_risk_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    content = '{"sentiment":"negative","sentiment_score":0.96,"emotion":"angry","topic":"delivery","intent":"complaint","summary":"Delivery was late.","recommended_action":"Investigate delivery."}'
    result = nvidia_analyzer(monkeypatch, content).analyze(review("My delivery was late", 1))
    assert result.risk_score == 85 and result.risk_level == "critical"


def test_malformed_nvidia_response_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AnalyzerError):
        nvidia_analyzer(monkeypatch, "not valid JSON").analyze(review("Hello"))


def test_nvidia_response_with_multiple_json_objects_uses_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    content = '{"review_id":"test","review":"echo"}\n{"sentiment":"positive","sentiment_score":0.9,"emotion":"happy","topic":"general","intent":"praise","summary":"Positive feedback.","recommended_action":"Thank the customer."}'
    result = nvidia_analyzer(monkeypatch, content).analyze(review("Great service", 5))
    assert result.sentiment == "positive" and result.risk_score == 0


def test_missing_nvidia_api_key_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_MODEL", "test-model")
    with pytest.raises(AnalyzerError, match="NVIDIA_API_KEY"):
        NVIDIAReviewAnalyzer({})


def test_failed_review_record_does_not_crash_pipeline() -> None:
    failed = _failed_record(review("Late delivery", 1), "nvidia", "bad response")
    assert failed["analysis_status"] == "failed" and failed["risk_score"] == 35


def test_max_reviews_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import max_reviews
    monkeypatch.setenv("MAX_REVIEWS", "3")
    assert max_reviews() == 3


def test_response_generator_uses_client_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYZER_MODE", "nvidia")
    generator = ResponseGenerator({"client": {"name": "Acme", "industry": "ecommerce"}, "response": {"tone": "warm", "style": "empathetic"}}, FakeClient("Thank you for your feedback."))
    result = generator.generate(review("Great service", 5), {"sentiment": "positive", "emotion": "happy", "topic": "general", "intent": "praise", "recommended_action": "Thank the customer.", "requires_escalation": False})
    assert result == "Thank you for your feedback."
    assert "Tone: warm" in generator._system_prompt()


def test_response_prompt_does_not_expose_internal_analysis() -> None:
    generator = ResponseGenerator({}, FakeClient("Draft"))
    prompt = generator._system_prompt().lower()
    assert "do not" in prompt and "reveal analysis" in prompt


def test_response_generator_handles_api_errors() -> None:
    class BrokenClient:
        class chat:
            class completions:
                @staticmethod
                def create(**_: object) -> object:
                    raise OSError("network unavailable")
    with pytest.raises(ResponseGeneratorError, match="Response generation failed"):
        ResponseGenerator({}, BrokenClient()).generate(review("Help", 1), {})


def test_mock_response_generation_makes_no_api_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYZER_MODE", "mock")
    result = ResponseGenerator({"response": {"request_contact_for_escalation": True}}, FakeClient("should not be used")).generate(
        review("This is unsafe", 1), {"sentiment": "negative", "topic": "delivery", "requires_escalation": True}
    )
    assert "contact" in result.lower() and "unsafe" not in result.lower()


def test_response_factory_selects_explicit_provider_without_global_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYZER_MODE", "nvidia")
    assert isinstance(get_response_generator("mock", {}, FakeClient("unused")), MockResponseGenerator)
    assert isinstance(get_response_generator("nvidia", {"response": {}}, FakeClient("Draft")), NVIDIAResponseGenerator)


def test_mock_response_respects_compensation_safety_and_does_not_claim_actions() -> None:
    generator = MockResponseGenerator({"client": {"name": "Acme"}, "response": {"allow_compensation_promises": False}})
    result = generator.generate(review("I want a refund and replacement", 1), {
        "sentiment": "negative", "topic": "refund", "intent": "refund_request", "risk_level": "critical",
        "requires_escalation": False,
    }).lower()
    for phrase in ("refund", "replacement", "voucher", "discount", "compensation", "issued", "shipped", "fixed"):
        assert phrase not in result


def test_mock_response_requests_contact_for_escalation() -> None:
    result = MockResponseGenerator({"response": {"request_contact_for_escalation": True}}).generate(
        review("This is unsafe", 1), {"sentiment": "negative", "topic": "delivery", "requires_escalation": True})
    assert "contact our support team" in result.lower()


def test_insights_require_supported_majorities_and_dates() -> None:
    records = [
        {**review("Good", 5), "review_id": "one", "date": "2026-01-01", "sentiment": "positive", "topic": "general", "risk_level": "low", "risk_score": 0, "requires_escalation": False},
        {**review("Great", 5), "review_id": "two", "date": "2026-01-02", "sentiment": "positive", "topic": "general", "risk_level": "low", "risk_score": 0, "requires_escalation": False},
        {**review("Okay", 3), "review_id": "three", "date": "not-a-date", "sentiment": "neutral", "topic": "delivery", "risk_level": "medium", "risk_score": 20, "requires_escalation": False},
    ]
    insights = generate_business_insights(records)
    assert any("predominantly positive" in insight for insight in insights)
    assert all("critical" not in insight.lower() for insight in insights)
    summary = calculate_analytics(records)
    assert summary["trend_data"] == [
        {"date": "2026-01-01", "reviews": 1, "negative_reviews": 0, "average_rating": 5.0},
        {"date": "2026-01-02", "reviews": 1, "negative_reviews": 0, "average_rating": 5.0},
    ]


def test_insights_empty_dataset_is_deterministic() -> None:
    assert generate_business_insights([]) == ["No analyzed reviews are available yet."]


def test_analytics_handles_empty_data_and_generates_insights() -> None:
    assert calculate_analytics([])["average_rating"] == 0
    assert calculate_analytics([])["trend_data"] == []
    records = [
        {**review("Late delivery", 1), "sentiment": "negative", "topic": "delivery", "risk_level": "critical", "risk_score": 80, "requires_escalation": True},
        {**review("Great", 5), "review_id": "two", "sentiment": "positive", "topic": "general", "risk_level": "low", "risk_score": 0, "requires_escalation": False},
    ]
    insights = generate_business_insights(records)
    assert any("Delivery" in insight for insight in insights)


def test_custom_escalation_threshold_triggers() -> None:
    from app.risk_engine.risk import calculate_risk
    # Standard 3-star neutral review has score 10
    low_risk = calculate_risk(3, "neutral", "neutral", "feedback", "Okay", escalation_threshold=50)
    assert not low_risk.requires_escalation
    # Lower threshold to 10 triggers escalation
    triggered = calculate_risk(3, "neutral", "neutral", "feedback", "Okay", escalation_threshold=10)
    assert triggered.requires_escalation


def test_dynamic_custom_topic_schema() -> None:
    from app.ai_engine.schemas import ReviewAnalysis, SemanticReviewAnalysis
    analysis = SemanticReviewAnalysis(
        sentiment="neutral",
        sentiment_score=0.8,
        emotion="neutral",
        topic="custom_new_category",
        intent="feedback",
        summary="A review about something new.",
        recommended_action="Review.",
    )
    assert analysis.topic == "custom_new_category"


def test_reddit_connector_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ingestion.reddit_connector import RedditConnector

    fake_reddit_json = '{"data": [{"id": "p1", "title": "Terrible bug in checkout", "selftext": "Broken payment button", "author": "dev_user", "created_utc": 1700000000, "score": 10, "subreddit": "test", "permalink": "/r/test/comments/p1"}]}'

    class _FakeRedditResp:
        def __enter__(self):
            return self
        def __exit__(self, *args: object) -> None:
            pass
        def read(self) -> bytes:
            return fake_reddit_json.encode("utf-8")

    monkeypatch.setattr("app.ingestion.reddit_connector.urlopen", lambda req, timeout=8: _FakeRedditResp())
    conn = RedditConnector(query="test brand", subreddit="test", limit=5)
    res = conn.fetch()
    assert len(res.records) == 1
    rec = res.records[0]
    assert rec.id == "reddit_p1"
    assert rec.author == "dev_user"
    assert "Terrible bug" in rec.text
    assert rec.rating == 3


def test_appstore_connector_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ingestion.appstore_connector import AppStoreConnector

    fake_appstore_json = '{"feed": {"entry": [{"title": {"label": "App Meta"}}, {"id": {"label": "rev123"}, "title": {"label": "Love this app"}, "content": {"label": "Fast and clean"}, "im:rating": {"label": "5"}, "author": {"name": {"label": "John Doe"}}, "updated": {"label": "2026-02-15T00:00:00Z"}, "link": {"attributes": {"href": "https://apple.com/review"}}}]}}'

    class _FakeAppStoreResp:
        def __enter__(self):
            return self
        def __exit__(self, *args: object) -> None:
            pass
        def read(self) -> bytes:
            return fake_appstore_json.encode("utf-8")

    monkeypatch.setattr("app.ingestion.appstore_connector.urlopen", lambda req, timeout=12: _FakeAppStoreResp())
    conn = AppStoreConnector(app_id_or_name="324684580", country="us", limit=5)
    res = conn.fetch()
    assert len(res.records) == 1
    rec = res.records[0]
    assert rec.id == "appstore_rev123"
    assert rec.rating == 5
    assert rec.author == "John Doe"
    assert "Love this app" in rec.text


def test_hackernews_connector_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ingestion.hackernews_connector import HackerNewsConnector

    fake_hn_json = '{"hits": [{"objectID": "hn123", "title": "Show HN: ReputatAI Launch", "comment_text": "Really impressive reputation analytics dashboard and response engine.", "author": "tech_lead", "created_at": "2026-03-01T12:00:00Z", "points": 45}]}'

    class _FakeHNResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args: object) -> None:
            pass
        def read(self) -> bytes:
            return fake_hn_json.encode("utf-8")

    monkeypatch.setattr("app.ingestion.hackernews_connector.urlopen", lambda req, timeout=10: _FakeHNResponse())
    conn = HackerNewsConnector(query="ReputatAI", limit=5, use_relevance_filter=False)
    res = conn.fetch()
    assert len(res.records) == 1
    rec = res.records[0]
    assert rec.id == "hn_hn123"
    assert rec.author == "tech_lead"
    assert "impressive reputation analytics" in rec.text


def test_dashboard_imports_correctly() -> None:
    pytest.importorskip("streamlit")
    import frontend.dashboard  # noqa: F401
