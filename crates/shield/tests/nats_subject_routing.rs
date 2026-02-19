use shield::handlers::socket::inbound_subject_for_tenant;

#[test]
fn tenant_subject_uses_expected_prefix_and_suffix() {
    let subject = inbound_subject_for_tenant("tenant-a");
    assert!(subject.starts_with("in.t."));
    assert!(subject.ends_with(".raw"));
    assert_eq!(subject, "in.t.tenant-a.raw");
}

#[test]
fn tenant_subject_normalizes_non_token_characters() {
    let subject = inbound_subject_for_tenant("tenant.with spaces");
    assert_eq!(subject, "in.t.tenant_with_spaces.raw");
}

#[test]
fn tenant_subject_isolation_by_tenant_id() {
    let a = inbound_subject_for_tenant("tenant-a");
    let b = inbound_subject_for_tenant("tenant-b");
    assert_ne!(a, b);
}
