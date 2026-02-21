from arqonbus.protocol.ids import is_valid_message_id


def test_is_valid_message_id_accepts_canonical_arq_format():
    assert is_valid_message_id("arq_1700000000000000000_7_c0ffee")


def test_is_valid_message_id_accepts_ulid_compat_format():
    assert is_valid_message_id("arq_01HZZZZZZZZZZZZZZZZZZZZZZZ")


def test_is_valid_message_id_rejects_invalid_formats():
    assert not is_valid_message_id("arq_invalid")
    assert not is_valid_message_id("arq_1700000000000000000_notint_c0ffee")
