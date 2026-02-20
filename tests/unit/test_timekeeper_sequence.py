from arqonbus.protocol.time_semantics import MonotonicSequenceGenerator


def test_monotonic_sequence_generator_increments_per_domain():
    gen = MonotonicSequenceGenerator()
    assert gen.next("tenant-a") == 1
    assert gen.next("tenant-a") == 2
    assert gen.next("tenant-a") == 3
    assert gen.current("tenant-a") == 3


def test_monotonic_sequence_generator_isolated_domains():
    gen = MonotonicSequenceGenerator()
    assert gen.next("tenant-a") == 1
    assert gen.next("tenant-b") == 1
    assert gen.next("tenant-a") == 2
    assert gen.current("tenant-b") == 1
