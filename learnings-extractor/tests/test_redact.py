from learnings_extractor.lib.redact import redact


def test_token_redacted():
    assert "sk-" not in redact("key is sk-ant-abcd1234efgh5678ijkl")


def test_clean_text_unchanged():
    assert redact("nothing secret here") == "nothing secret here"
