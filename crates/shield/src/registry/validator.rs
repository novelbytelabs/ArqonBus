//! Protobuf payload validator.
//!
//! Validates message payloads against Protobuf FileDescriptorSet schemas.

use anyhow::Result;
use prost::Message;
use prost_reflect::{DescriptorPool, DynamicMessage};
use prost_types::FileDescriptorSet;

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
pub fn validate_payload(schema_bytes: &[u8], payload: &[u8]) -> Result<(), Vec<ValidationError>> {
    let message_name = infer_first_message_name(schema_bytes).map_err(|e| vec![e])?;
    validate_payload_for_message(schema_bytes, payload, &message_name)
}

pub fn validate_payload_for_message(
    schema_bytes: &[u8],
    payload: &[u8],
    message_name: &str,
) -> Result<(), Vec<ValidationError>> {
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

    let pool = DescriptorPool::decode(schema_bytes).map_err(|e| {
        vec![ValidationError {
            field: "schema".to_string(),
            message: format!("Invalid descriptor set: {}", e),
        }]
    })?;

    let descriptor = pool.get_message_by_name(message_name).ok_or_else(|| {
        vec![ValidationError {
            field: "schema".to_string(),
            message: format!("Message '{}' not found in schema", message_name),
        }]
    })?;

    DynamicMessage::decode(descriptor, payload).map_err(|e| {
        vec![ValidationError {
            field: "payload".to_string(),
            message: format!("Schema decode failed: {}", e),
        }]
    })?;

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

fn infer_first_message_name(schema_bytes: &[u8]) -> Result<String, ValidationError> {
    let fds = FileDescriptorSet::decode(schema_bytes).map_err(|e| ValidationError {
        field: "schema".to_string(),
        message: format!("Invalid descriptor set: {}", e),
    })?;

    let file = fds.file.first().ok_or_else(|| ValidationError {
        field: "schema".to_string(),
        message: "Descriptor set contains no files".to_string(),
    })?;

    let msg = file.message_type.first().ok_or_else(|| ValidationError {
        field: "schema".to_string(),
        message: "Descriptor file contains no top-level messages".to_string(),
    })?;

    let msg_name = msg.name.clone().ok_or_else(|| ValidationError {
        field: "schema".to_string(),
        message: "Message has no name".to_string(),
    })?;

    let package = file.package.clone().unwrap_or_default();
    if package.is_empty() {
        Ok(msg_name)
    } else {
        Ok(format!("{}.{}", package, msg_name))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use prost_types::{
        field_descriptor_proto::{Label, Type},
        DescriptorProto, FieldDescriptorProto, FileDescriptorProto,
    };

    fn build_test_descriptor_set() -> Vec<u8> {
        let field = FieldDescriptorProto {
            name: Some("id".to_string()),
            number: Some(1),
            label: Some(Label::Optional as i32),
            r#type: Some(Type::String as i32),
            ..Default::default()
        };

        let message = DescriptorProto {
            name: Some("TestEnvelope".to_string()),
            field: vec![field],
            ..Default::default()
        };

        let file = FileDescriptorProto {
            name: Some("test_envelope.proto".to_string()),
            package: Some("arqon.test".to_string()),
            syntax: Some("proto3".to_string()),
            message_type: vec![message],
            ..Default::default()
        };

        let fds = FileDescriptorSet { file: vec![file] };
        fds.encode_to_vec()
    }

    #[test]
    fn test_validation_pass() {
        let schema = build_test_descriptor_set();
        // field #1 (string), len=3, "abc"
        let payload = vec![0x0A, 0x03, b'a', b'b', b'c'];
        let result = validate_payload(&schema, &payload);
        assert!(result.is_ok());
    }

    #[test]
    fn test_validation_fail_empty_payload() {
        let schema = build_test_descriptor_set();
        let payload: Vec<u8> = vec![];
        let result = validate_payload(&schema, &payload);
        assert!(result.is_err());
        let errors = result.unwrap_err();
        assert_eq!(errors[0].field, "payload");
    }

    #[test]
    fn test_validation_fail_invalid_payload_for_schema() {
        let schema = build_test_descriptor_set();
        // Invalid tag/wire payload for our test schema.
        let payload = vec![0xFF, 0xFF, 0xFF];
        let result = validate_payload(&schema, &payload);
        assert!(result.is_err());
    }

    #[test]
    fn test_validation_fail_message_not_found() {
        let schema = build_test_descriptor_set();
        let payload = vec![0x0A, 0x03, b'a', b'b', b'c'];
        let result = validate_payload_for_message(&schema, &payload, "arqon.test.DoesNotExist");
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
