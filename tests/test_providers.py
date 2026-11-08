

def _capture(monkeypatch):
    import io
    import json

    sent = {}

    class _Reply(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        sent["body"] = json.loads(request.data)
        return _Reply(json.dumps({"response": "hello", "eval_count": 1}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return sent


def test_a_direct_answer_can_ask_the_model_not_to_reason_first(monkeypatch) -> None:
    """With reasoning on, the token budget was spent before any answer appeared."""
    from artemis.core.providers import OllamaProvider

    sent = _capture(monkeypatch)
    OllamaProvider().complete("hi", max_tokens=10, think=False)
    assert sent["body"]["think"] is False


def test_planning_leaves_reasoning_to_the_model(monkeypatch) -> None:
    """With reasoning off the planner produced steps with missing arguments."""
    from artemis.core.providers import OllamaProvider

    sent = _capture(monkeypatch)
    OllamaProvider().complete("hi", max_tokens=10)
    assert "think" not in sent["body"]
