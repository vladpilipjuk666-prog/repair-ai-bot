from config import MAX_PHOTOS
from constants import (
    PRICE_STATUS_OFFERED,
    STATUS_ACCEPTED,
    STATUS_DONE,
    STATUS_NEW,
)
from database import Request
from keyboards import (
    admin_list_keyboard,
    admin_request_keyboard,
    main_menu_keyboard,
    my_requests_keyboard,
    price_offer_keyboard,
    request_detail_keyboard,
    review_followup_keyboard,
    review_keyboard,
)


def _request(status: str = STATUS_NEW) -> Request:
    return Request(
        id=123,
        number="R-00123",
        user_id=1,
        client_name="Олена",
        phone="+380671234567",
        device_type="laptop",
        problem="Не вмикається",
        service_method="dropoff",
        status=status,
        price=2500,
        price_status=PRICE_STATUS_OFFERED,
        photos_json="[]",
    )


def _all_callbacks(markup):
    for row in markup.inline_keyboard:
        for button in row:
            if button.callback_data:
                yield button.callback_data


def test_admin_keyboard_callback_lengths():
    for status in (STATUS_NEW, STATUS_ACCEPTED, STATUS_DONE):
        markup = admin_request_keyboard(_request(status))
        callbacks = list(_all_callbacks(markup))
        assert "admin:history:123" in callbacks
        for data in callbacks:
            assert len(data.encode("utf-8")) <= 64
            assert data.startswith("admin:")


def test_user_keyboards():
    request = _request()
    markup = request_detail_keyboard(request)
    data = list(_all_callbacks(markup))
    assert any(item.startswith("client:price_accept:") for item in data)
    assert any(item.startswith("my:cancel:") for item in data)

    list_markup = my_requests_keyboard([request])
    assert any(item == "my:view:123" for item in _all_callbacks(list_markup))

    review_markup = review_keyboard(123)
    callbacks = list(_all_callbacks(review_markup))
    assert len(callbacks) == 5
    assert all(len(item) <= 64 for item in callbacks)

    followup = list(_all_callbacks(review_followup_keyboard(123)))
    assert "review:text:123" in followup
    assert "review:skip:123" in followup
    assert all(len(item.encode("utf-8")) <= 64 for item in followup)

    offer = list(_all_callbacks(price_offer_keyboard(123, 2500)))
    assert "client:price_accept:123:2500" in offer
    assert "client:price_decline:123:2500" in offer
    assert all(len(item.encode("utf-8")) <= 64 for item in offer)


def test_main_menu_and_admin_list():
    callbacks = list(_all_callbacks(main_menu_keyboard(is_admin=True)))
    assert "admin:menu" in callbacks
    assert "menu:new" in callbacks

    list_markup = admin_list_keyboard(
        [_request()],
        "new",
        0,
        20,
    )
    assert any(item == "admin:view:123" for item in _all_callbacks(list_markup))
    assert all(len(item) <= 64 for item in _all_callbacks(list_markup))


def test_admin_photo_button():
    request = _request()
    request.photos_json = '["photo-1", "photo-2"]'

    callbacks = list(_all_callbacks(admin_request_keyboard(request)))

    assert "admin:photos:123" in callbacks
    assert all(len(item.encode("utf-8")) <= 64 for item in callbacks)


def test_max_photos_configured():
    assert 1 <= MAX_PHOTOS <= 10
