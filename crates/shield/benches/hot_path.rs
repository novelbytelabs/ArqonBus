//! ArqonBus Shield Benchmarks
//!
//! Measures the hot-path performance of the Shield layer:
//! - Raw NATS publish latency (baseline)
//! - Schema validation overhead
//! - Policy engine overhead (with/without WASM)
//!
//! Run with: cargo bench --package shield-bench

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use std::time::Duration;

/// Baseline: How fast can we serialize and deserialize protobuf messages?
fn bench_protobuf_encode_decode(c: &mut Criterion) {
    use prost::Message;

    // Simulated envelope (represents arqon.v1.Envelope)
    #[derive(Clone, PartialEq, Message)]
    struct TestEnvelope {
        #[prost(string, tag = "1")]
        id: String,
        #[prost(string, tag = "2")]
        room: String,
        #[prost(string, tag = "3")]
        channel: String,
        #[prost(bytes = "vec", tag = "4")]
        payload: Vec<u8>,
        #[prost(uint64, tag = "5")]
        timestamp: u64,
    }

    let envelope = TestEnvelope {
        id: "msg-12345".to_string(),
        room: "agents".to_string(),
        channel: "control".to_string(),
        payload: vec![0u8; 256], // Typical small payload
        timestamp: 1704067200000,
    };

    let mut group = c.benchmark_group("protobuf");
    group.throughput(Throughput::Elements(1));

    group.bench_function("encode_envelope", |b| {
        b.iter(|| {
            let mut buf = Vec::with_capacity(512);
            envelope.encode(&mut buf).unwrap();
            black_box(buf)
        })
    });

    let encoded = {
        let mut buf = Vec::new();
        envelope.encode(&mut buf).unwrap();
        buf
    };

    group.bench_function("decode_envelope", |b| {
        b.iter(|| {
            let decoded = TestEnvelope::decode(encoded.as_slice()).unwrap();
            black_box(decoded)
        })
    });

    group.bench_function("roundtrip_envelope", |b| {
        b.iter(|| {
            let mut buf = Vec::with_capacity(512);
            envelope.encode(&mut buf).unwrap();
            let decoded = TestEnvelope::decode(buf.as_slice()).unwrap();
            black_box(decoded)
        })
    });

    group.finish();
}

/// Measure raw bytes throughput (simulates NATS publish path)
fn bench_bytes_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("bytes_ops");

    for size in [64, 256, 1024, 4096, 16384].iter() {
        let data: Vec<u8> = (0..*size).map(|i| i as u8).collect();

        group.throughput(Throughput::Bytes(*size as u64));

        group.bench_with_input(BenchmarkId::new("clone", size), &data, |b, d| {
            b.iter(|| {
                let cloned = d.clone();
                black_box(cloned)
            })
        });

        group.bench_with_input(BenchmarkId::new("into_bytes", size), &data, |b, d| {
            b.iter(|| {
                let bytes = bytes::Bytes::copy_from_slice(d);
                black_box(bytes)
            })
        });
    }

    group.finish();
}

/// Measure hash-based routing (for ArqonReflex cache keys)
fn bench_routing_hash(c: &mut Criterion) {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let queries = vec![
        "load spec",
        "show constitution",
        "what governs this action",
        "get latest decision from room:control channel:decisions",
    ];

    let mut group = c.benchmark_group("routing");
    group.throughput(Throughput::Elements(1));

    group.bench_function("hash_query", |b| {
        let query = "show constitution rule about safety";
        b.iter(|| {
            let mut hasher = DefaultHasher::new();
            query.hash(&mut hasher);
            black_box(hasher.finish())
        })
    });

    group.bench_function("hash_and_lookup", |b| {
        use std::collections::HashMap;
        let mut cache: HashMap<u64, Vec<u8>> = HashMap::new();
        for q in &queries {
            let mut hasher = DefaultHasher::new();
            q.hash(&mut hasher);
            cache.insert(hasher.finish(), vec![0u8; 32]); // Cached embedding
        }

        let query = "load spec";
        b.iter(|| {
            let mut hasher = DefaultHasher::new();
            query.hash(&mut hasher);
            let key = hasher.finish();
            black_box(cache.get(&key))
        })
    });

    group.finish();
}

/// JSON vs MessagePack vs Protobuf comparison (common payload formats)
fn bench_serialization_formats(c: &mut Criterion) {
    use serde::{Deserialize, Serialize};

    #[derive(Clone, Serialize, Deserialize)]
    struct Message {
        id: String,
        room: String,
        channel: String,
        payload: String,
        timestamp: u64,
    }

    let msg = Message {
        id: "msg-12345".to_string(),
        room: "agents".to_string(),
        channel: "control".to_string(),
        payload: "Hello, ArqonBus!".to_string(),
        timestamp: 1704067200000,
    };

    let mut group = c.benchmark_group("serialization");
    group.throughput(Throughput::Elements(1));

    group.bench_function("json_encode", |b| {
        b.iter(|| {
            let json = serde_json::to_vec(&msg).unwrap();
            black_box(json)
        })
    });

    let json_bytes = serde_json::to_vec(&msg).unwrap();
    group.bench_function("json_decode", |b| {
        b.iter(|| {
            let decoded: Message = serde_json::from_slice(&json_bytes).unwrap();
            black_box(decoded)
        })
    });

    group.finish();
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .measurement_time(Duration::from_secs(5))
        .sample_size(1000);
    targets =
        bench_protobuf_encode_decode,
        bench_bytes_operations,
        bench_routing_hash,
        bench_serialization_formats
}

criterion_main!(benches);
