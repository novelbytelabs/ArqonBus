use metrics::{describe_counter, describe_histogram};
use metrics_exporter_prometheus::PrometheusBuilder;

pub fn init_metrics() {
    let builder = PrometheusBuilder::new().with_http_listener(([0, 0, 0, 0], 9090));
    builder
        .install()
        .expect("failed to install Prometheus recorder");

    // Register metrics
    describe_counter!(
        "shield_connections_total",
        "Total number of WebSocket connections accepted"
    );
    describe_histogram!(
        "shield_policy_duration_seconds",
        "Duration of Wasm policy execution"
    );
    describe_counter!(
        "shield_messages_total",
        "Total number of messages processed"
    );
}
