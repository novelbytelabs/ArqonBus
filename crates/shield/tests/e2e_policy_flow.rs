use shield::policy::engine::PolicyEngine;

#[tokio::test]
async fn e2e_block_empty_policy_denies_empty_payload_and_allows_non_empty() {
    let mut engine = PolicyEngine::new().expect("policy engine");
    let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
    engine
        .load_module(module_path)
        .expect("load block_empty policy");

    let denied = engine.validate(b"").await.expect("empty validation");
    let allowed = engine
        .validate(b"payload")
        .await
        .expect("non-empty validation");

    assert!(!denied);
    assert!(allowed);
}
