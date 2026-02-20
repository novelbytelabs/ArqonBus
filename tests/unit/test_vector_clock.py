from arqonbus.protocol.time_semantics import vector_clock_compare, vector_clock_merge


def test_vector_clock_merge_takes_component_wise_max():
    merged = vector_clock_merge({"a": 1, "b": 4}, {"a": 3, "c": 2})
    assert merged == {"a": 3, "b": 4, "c": 2}


def test_vector_clock_compare_relations():
    assert vector_clock_compare({"a": 1}, {"a": 1}) == "equal"
    assert vector_clock_compare({"a": 1}, {"a": 2}) == "before"
    assert vector_clock_compare({"a": 3}, {"a": 2}) == "after"
    assert vector_clock_compare({"a": 2, "b": 1}, {"a": 1, "b": 2}) == "concurrent"
