use prost::Message;

#[test]
fn rust_decodes_python_generated_envelope_fixture() {
    let fixture = include_bytes!("fixtures/python_envelope.bin");
    let envelope = proto::v1::Envelope::decode(fixture.as_slice())
        .expect("fixture must decode with canonical arqon.v1.Envelope");

    assert_eq!(envelope.trace_id, "arq_01HZZZZZZZZZZZZZZZZZZZZZZZ");
    assert_eq!(envelope.tenant_id, "tenant-fixture");
    assert_eq!(envelope.room_id, "ops");
    assert_eq!(envelope.timestamp, 1771545600000);
    assert_eq!(
        envelope
            .headers
            .get("envelope_type")
            .map(String::as_str)
            .unwrap_or(""),
        "command"
    );
    match envelope.payload {
        Some(proto::v1::envelope::Payload::Cmd(cmd)) => {
            assert_eq!(cmd.r#type, "op.continuum.projector.status");
            assert!(!cmd.data.is_empty(), "command payload bytes must be present");
        }
        _ => panic!("fixture must use command payload variant"),
    }
}
