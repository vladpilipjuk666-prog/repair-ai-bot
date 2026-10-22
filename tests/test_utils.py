from utils import (
    format_money,
    h,
    normalize_phone,
    parse_json_object,
    parse_price,
    plural_reviews,
    validate_ai_estimate,
)


def test_normalize_phone():
    assert normalize_phone("+380 67 123 45 67") == "+380671234567"
    assert normalize_phone("0671234567") == "+380671234567"
    assert normalize_phone("380671234567") == "+380671234567"
    assert normalize_phone("80671234567") == "+380671234567"
    assert normalize_phone("+48 123 456 789") == "+48123456789"
    assert normalize_phone("123") is None
    assert normalize_phone(None) is None


def test_parse_price():
    assert parse_price("2500") == 2500
    assert parse_price("2 500 грн") == 2500
    assert parse_price("0") == 0
    assert parse_price("abc") is None
    assert parse_price("-100") == 100
    assert parse_price("999999") is None


def test_parse_json_object_with_markdown():
    raw = """```json
    {"summary": "Тест", "price_min": 100, "price_max": 200}
    ```"""
    data = parse_json_object(raw)
    assert data == {"summary": "Тест", "price_min": 100, "price_max": 200}

    raw2 = 'Відповідь: {"summary": "Тест"} дякую'
    assert parse_json_object(raw2) == {"summary": "Тест"}
    assert parse_json_object("not json") is None
    assert parse_json_object(None) is None


def test_validate_ai_estimate():
    result = validate_ai_estimate(
        {
            "summary": "  Потрібна діагностика  ",
            "price_min": "2 500",
            "price_max": 1000,
            "eta": "1–2 дні",
            "confidence": "HIGH",
        }
    )
    assert result is not None
    assert result["summary"] == "Потрібна діагностика"
    assert result["price_min"] == 1000
    assert result["price_max"] == 2500
    assert result["confidence"] == "high"

    assert validate_ai_estimate({"summary": ""}) is None
    assert validate_ai_estimate(None) is None


def test_format_money():
    assert format_money(2500) == "2 500 грн"
    assert format_money(None) == "—"


def test_escape():
    assert h('<script>"x"</script>') == "&lt;script&gt;\"x\"&lt;/script&gt;"


def test_plural_reviews():
    assert plural_reviews(1) == "відгук"
    assert plural_reviews(2) == "відгуки"
    assert plural_reviews(5) == "відгуків"
    assert plural_reviews(11) == "відгуків"
