

def test_ollama_is_asked_for_the_answer_not_for_hidden_reasoning(monkeypatch) -> None:
    """With reasoning on, the token budget was spent before any answer appeared."""
    import io
    import json

    from artemis.core.providers import OllamaProvider

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

    OllamaProvider().complete("hi", max_tokens=10)

    assert sent["body"]["think"] is False
