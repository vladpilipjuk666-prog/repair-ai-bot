from constants import PRICE_STATUS_NONE, STATUS_NEW
from database import Request
from handlers.admin import _build_csv, _csv_safe


def _request() -> Request:
    return Request(
        id=1,
        number="R-00001",
        user_id=1,
        username="olena",
        client_name="=cmd|' /C calc'!A0",
        phone="+380671234567",
        device_type="laptop",
        device_model="ASUS X515",
        problem="+SUM(1,1)",
        service_method="dropoff",
        status=STATUS_NEW,
        price_status=PRICE_STATUS_NONE,
        photos_json="[]",
    )


def test_csv_safe_prefixes_formula_like_values():
    assert _csv_safe("=cmd") == "'=cmd"
    assert _csv_safe("+380671234567") == "'+380671234567"
    assert _csv_safe("  @user") == "'  @user"
    assert _csv_safe("Звичайний текст") == "Звичайний текст"
    assert _csv_safe(None) == ""


def test_csv_contains_headers_and_escaped_values():
    data = _build_csv([_request()])
    text = data.decode("utf-8-sig")

    assert "Номер;Створено;Статус" in text
    assert "'=cmd|' /C calc'!A0" in text
    assert "'+SUM(1,1)" in text
    assert data.startswith(b"\xef\xbb\xbf")
