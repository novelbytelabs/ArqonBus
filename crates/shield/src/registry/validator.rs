//! Protobuf payload validator.
//!
//! Validates message payloads against Protobuf FileDescriptorSet schemas.

use anyhow::Result;

/// Validation result containing error details.
#[derive(Debug, Clone)]
pub struct ValidationError {
    pub field: String,
    pub message: String,
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Field '{}': {}", self.field, self.message)
    }
}

/// Validate a payload against a Protobuf FileDescriptorSet.
///
/// For now, this is a stub that checks if the payload is valid Protobuf wire format.
/// Full schema validation requires parsing the FileDescriptorSet and matching message types.
pub fn validate_payload(schema_bytes: &[u8], payload: &[u8]) -> Result<(), Vec<ValidationError>> {
    // Basic validation: check if payload is non-empty
    if payload.is_empty() {
        return Err(vec![ValidationError {
            field: "payload".to_string(),
            message: "Empty payload".to_string(),
        }]);
    }

    // Check if schema is non-empty
    if schema_bytes.is_empty() {
        return Err(vec![ValidationError {
            field: "schema".to_string(),
            message: "Empty schema".to_string(),
        }]);
    }

    // TODO: Full Protobuf validation would require:
    // 1. Parse FileDescriptorSet from schema_bytes using prost-reflect
    // 2. Identify expected message type from subject mapping
    // 3. Decode payload using dynamic message
    // 4. Validate required fields are present

    // For MVP, we just check basic wire format (first byte should be valid field tag)
    // Protobuf field tags use varint encoding, first byte should have bits set
    let first_byte = payload[0];
    let wire_type = first_byte & 0x07;

    // Wire types 0-5 are valid, 6 and 7 are reserved/deprecated
    if wire_type > 5 {
        return Err(vec![ValidationError {
            field: "payload".to_string(),
            message: format!("Invalid wire type: {}", wire_type),
        }]);
    }

    Ok(())
}

/// Subject to schema mapping.
#[derive(Clone, Debug)]
pub struct SubjectSchemaMapping {
    pub subject_prefix: String,
    pub schema_id: String,
}

/// Get schema ID for a given subject.
pub fn get_schema_id(subject: &str, mappings: &[SubjectSchemaMapping]) -> Option<String> {
    for mapping in mappings {
        if subject.starts_with(&mapping.subject_prefix) {
            return Some(mapping.schema_id.clone());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_pass() {
        // Valid Protobuf-like payload (field 1, wire type 0 = varint)
        let schema = b"mock schema";
        let payload = vec![0x08, 0x96, 0x01]; // field 1, varint 150
        let result = validate_payload(schema, &payload);
        assert!(result.is_ok());
    }

    #[test]
    fn test_validation_fail_empty_payload() {
        let schema = b"mock schema";
        let payload: Vec<u8> = vec![];
        let result = validate_payload(schema, &payload);
        assert!(result.is_err());
        let errors = result.unwrap_err();
        assert_eq!(errors[0].field, "payload");
    }

    #[test]
    fn test_validation_fail_invalid_wire_type() {
        let schema = b"mock schema";
        // Wire type 7 is invalid
        let payload = vec![0x07];
        let result = validate_payload(schema, &payload);
        assert!(result.is_err());
    }

    #[test]
    fn test_get_schema_id() {
        let mappings = vec![
            SubjectSchemaMapping {
                subject_prefix: "events.user.".to_string(),
                schema_id: "v1.events.user".to_string(),
            },
            SubjectSchemaMapping {
                subject_prefix: "events.order.".to_string(),
                schema_id: "v1.events.order".to_string(),
            },
        ];

        assert_eq!(
            get_schema_id("events.user.created", &mappings),
            Some("v1.events.user".to_string())
        );
        assert_eq!(
            get_schema_id("events.order.placed", &mappings),
            Some("v1.events.order".to_string())
        );
        assert_eq!(get_schema_id("other.topic", &mappings), None);
    }
}
