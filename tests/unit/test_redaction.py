from crossrepro.redact.engine import contains_high_risk_secret, redact_text


def test_redacts_email_without_marking_high_risk():
    result = redact_text("user=test@example.com")
    assert "test@example.com" not in result.text
    assert "[EMAIL_1]" in result.text
    assert result.to_report()["high_risk_matches"] == 0


def test_redacts_api_key_value_and_keeps_label():
    result = redact_text("api_key=TEST_ONLY_SECRET_123456")
    assert "TEST_ONLY_SECRET_123456" not in result.text
    assert "api_key=" in result.text
    assert "[API_KEY_ASSIGNMENT_1]" in result.text
    assert result.to_report()["high_risk_matches"] == 1


def test_redacts_bearer_value():
    result = redact_text("Authorization: Bearer abcdefghijklmnop")
    assert "abcdefghijklmnop" not in result.text
    assert "Authorization: Bearer " in result.text
    assert contains_high_risk_secret("Authorization: Bearer abcdefghijklmnop")
    assert not contains_high_risk_secret(result.text)


def test_redacts_multiline_private_key():
    value = "-----BEGIN PRIVATE KEY-----\nabcdefghi12345\n-----END PRIVATE KEY-----"
    result = redact_text(value)
    assert "BEGIN PRIVATE KEY" not in result.text
    assert "[PRIVATE_KEY_1]" in result.text
    assert result.matches[0].line == 1


def test_report_never_contains_original_secret():
    secret = "TEST_ONLY_SECRET_123456"
    result = redact_text(f"password={secret}")
    assert secret not in str(result.to_report())


def test_redacts_naked_openai_style_key():
    secret = "sk-abcdefghijklmnopqrstuvwx"
    result = redact_text(secret)
    assert secret not in result.text
    assert contains_high_risk_secret(secret)


def test_redacts_github_token():
    secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    result = redact_text(secret)
    assert secret not in result.text
    assert contains_high_risk_secret(secret)


def test_redacts_usernames_in_common_absolute_paths():
    text = r"C:\Users\alice\project /home/bob/project /Users/carol/project"
    result = redact_text(text)
    assert "alice" not in result.text
    assert "bob" not in result.text
    assert "carol" not in result.text
