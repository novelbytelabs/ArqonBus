//! Traffic mirroring (shadow traffic) implementation.
//!
//! Implements coherent sampling using consistent hashing on TraceID
//! per RFC-002 Section 2.2.

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// Configuration for a single mirroring rule.
#[derive(Clone, Debug)]
pub struct MirrorRule {
    /// Subject prefix to match (e.g., "in.t.default.*")
    pub prefix: String,
    /// Percentage of traffic to mirror (0.0 to 1.0)
    pub percent: f64,
}

/// Mirroring configuration.
#[derive(Clone, Debug, Default)]
pub struct MirrorConfig {
    pub enabled: bool,
    pub rules: Vec<MirrorRule>,
}

impl MirrorConfig {
    /// Find the mirror percentage for a given subject.
    pub fn get_percent(&self, subject: &str) -> Option<f64> {
        if !self.enabled {
            return None;
        }
        for rule in &self.rules {
            if subject_matches(&rule.prefix, subject) {
                return Some(rule.percent);
            }
        }
        None
    }
}

/// Check if a subject matches a prefix pattern.
/// Supports wildcards: `*` matches one token, `>` matches one or more tokens.
fn subject_matches(pattern: &str, subject: &str) -> bool {
    let pattern_parts: Vec<&str> = pattern.split('.').collect();
    let subject_parts: Vec<&str> = subject.split('.').collect();

    let mut p_idx = 0;
    let mut s_idx = 0;

    while p_idx < pattern_parts.len() && s_idx < subject_parts.len() {
        match pattern_parts[p_idx] {
            "*" => {
                // Match exactly one token
                p_idx += 1;
                s_idx += 1;
            }
            ">" => {
                // Match one or more remaining tokens
                return true;
            }
            token => {
                if token != subject_parts[s_idx] {
                    return false;
                }
                p_idx += 1;
                s_idx += 1;
            }
        }
    }

    // Both must be exhausted for exact match (unless pattern ended with >)
    p_idx == pattern_parts.len() && s_idx == subject_parts.len()
}

/// Determine if a trace should be mirrored using consistent hashing.
///
/// The same trace_id will always produce the same decision for a given percent.
pub fn should_mirror(trace_id: &str, percent: f64) -> bool {
    if percent <= 0.0 {
        return false;
    }
    if percent >= 1.0 {
        return true;
    }

    let mut hasher = DefaultHasher::new();
    trace_id.hash(&mut hasher);
    let hash = hasher.finish();

    // Normalize hash to [0.0, 1.0) range
    let normalized = (hash as f64) / (u64::MAX as f64);
    normalized < percent
}

/// Generate the shadow subject for a given original subject.
#[allow(dead_code)]
pub fn mirror_subject(original: &str) -> String {
    format!("shadow.{}", original)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_consistent_hashing() {
        // Same trace_id should always produce same result
        let trace_id = "abc123-def456";
        let percent = 0.5;
        let result1 = should_mirror(trace_id, percent);
        let result2 = should_mirror(trace_id, percent);
        let result3 = should_mirror(trace_id, percent);
        assert_eq!(result1, result2);
        assert_eq!(result2, result3);
    }

    #[test]
    fn test_mirror_subject() {
        assert_eq!(
            mirror_subject("in.t.default.room1"),
            "shadow.in.t.default.room1"
        );
        assert_eq!(
            mirror_subject("events.user.created"),
            "shadow.events.user.created"
        );
    }

    #[test]
    fn test_subject_matches() {
        assert!(subject_matches("in.t.default.*", "in.t.default.room1"));
        assert!(subject_matches("in.t.>", "in.t.default.room1.sub"));
        assert!(!subject_matches("in.t.default.*", "in.t.other.room1"));
        assert!(subject_matches(
            "events.user.created",
            "events.user.created"
        ));
        assert!(!subject_matches(
            "events.user.created",
            "events.user.deleted"
        ));
    }

    #[test]
    fn test_percentage_boundaries() {
        let trace_id = "test-trace";
        assert!(!should_mirror(trace_id, 0.0));
        assert!(should_mirror(trace_id, 1.0));
    }

    #[test]
    fn test_percentage_distribution() {
        // Statistical test: ~50% should be mirrored at 0.5
        let mut mirrored = 0;
        let total = 10000;
        for i in 0..total {
            if should_mirror(&format!("trace-{}", i), 0.5) {
                mirrored += 1;
            }
        }
        // Allow 5% tolerance
        let ratio = mirrored as f64 / total as f64;
        assert!(
            ratio > 0.45 && ratio < 0.55,
            "Expected ~50%, got {:.2}%",
            ratio * 100.0
        );
    }
}
