"""Telemetry event handlers for ArqonBus.

This module provides event handlers for processing and formatting
telemetry events before they are broadcast.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid

from ..utils.logging import get_logger

logger = get_logger(__name__)


class TelemetryEventHandler:
    """Processes and validates telemetry events.
    
    Handles event validation, enrichment, formatting, and filtering
    before events are broadcast to telemetry clients.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize telemetry event handler.
        
        Args:
            config: Configuration dictionary with handler settings
        """
        self.config = config or {}
        self.validation_schema = self.config.get("validation_schema", {})
        self.event_enrichers = self.config.get("event_enrichers", [])
        self.processing_stats = {
            "events_processed": 0,
            "events_validated": 0,
            "events_filtered": 0,
            "events_enriched": 0,
            "processing_errors": 0
        }
    
    async def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a telemetry event through the pipeline.
        
        Args:
            event: Raw event data
            
        Returns:
            Processed and validated event
        """
        try:
            self.processing_stats["events_processed"] += 1
            
            # Validate event
            event = await self._validate_event(event)
            
            # Enrich event with additional metadata
            event = await self._enrich_event(event)
            
            # Format event for broadcast
            event = await self._format_event(event)
            
            self.processing_stats["events_validated"] += 1
            
            return event
            
        except Exception as e:
            self.processing_stats["processing_errors"] += 1
            logger.error(f"Error processing telemetry event: {e}")
            # Return a minimal valid event to prevent pipeline failure
            return await self._create_fallback_event(event, str(e))
    
    async def _validate_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Validate event structure and required fields.
        
        Args:
            event: Event to validate
            
        Returns:
            Validated event
            
        Raises:
            ValueError: If event validation fails
        """
        if not isinstance(event, dict):
            raise ValueError("Event must be a dictionary")
        
        # Required fields
        required_fields = ["event_type", "timestamp"]
        for field in required_fields:
            if field not in event:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate event type
        event_type = event["event_type"]
        if not isinstance(event_type, str) or not event_type:
            raise ValueError("Event type must be a non-empty string")
        
        # Validate timestamp
        timestamp = event["timestamp"]
        if not isinstance(timestamp, str):
            raise ValueError("Timestamp must be a string")
        
        # Validate client_id if present
        if "client_id" in event:
            client_id = event["client_id"]
            if not isinstance(client_id, str) or not client_id.startswith("arq_"):
                raise ValueError("Client ID must be a string starting with 'arq_'")
        
        # Validate metadata
        if "metadata" in event:
            metadata = event["metadata"]
            if not isinstance(metadata, dict):
                raise ValueError("Metadata must be a dictionary")
        
        return event
    
    async def _enrich_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich event with additional metadata.
        
        Args:
            event: Event to enrich
            
        Returns:
            Enriched event
        """
        enriched_event = event.copy()
        
        # Add processing metadata
        enriched_event["event_id"] = str(uuid.uuid4())
        enriched_event["processing_time_ms"] = 0  # Will be updated by caller
        
        # Add server metadata
        enriched_event["server_version"] = "1.0.0"
        enriched_event["server_name"] = "arqonbus"
        
        # Add environment metadata if configured
        if self.config.get("environment_tags"):
            enriched_event["environment"] = self.config["environment_tags"]
        
        # Add custom enrichers
        for enricher_name in self.event_enrichers:
            try:
                enriched_event = await self._apply_enricher(enricher_name, enriched_event)
                self.processing_stats["events_enriched"] += 1
            except Exception as e:
                logger.warning(f"Event enricher {enricher_name} failed: {e}")
        
        return enriched_event
    
    async def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for broadcast.
        
        Args:
            event: Event to format
            
        Returns:
            Formatted event
        """
        formatted_event = event.copy()
        
        # Ensure timestamp is in ISO format
        if "timestamp" in formatted_event:
            try:
                # Parse and reformat timestamp
                dt = datetime.fromisoformat(formatted_event["timestamp"].replace('Z', '+00:00'))
                formatted_event["timestamp"] = dt.isoformat()
            except ValueError:
                # Use current timestamp if parsing fails
                formatted_event["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Add event schema version
        formatted_event["schema_version"] = "1.0"
        
        # Add broadcast metadata
        formatted_event["broadcast_ready"] = True
        formatted_event["formatted_at"] = datetime.now(timezone.utc).isoformat()
        
        return formatted_event
    
    async def _apply_enricher(self, enricher_name: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a specific event enricher.
        
        Args:
            enricher_name: Name of enricher to apply
            event: Event to enrich
            
        Returns:
            Enriched event
        """
        if enricher_name == "geolocation":
            return await self._add_geolocation(event)
        elif enricher_name == "user_agent":
            return await self._add_user_agent_parsing(event)
        elif enricher_name == "performance":
            return await self._add_performance_metrics(event)
        elif enricher_name == "security":
            return await self._add_security_context(event)
        else:
            logger.warning(f"Unknown event enricher: {enricher_name}")
            return event
    
    async def _add_geolocation(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Add geolocation data to event.
        
        Args:
            event: Event to enrich
            
        Returns:
            Event with geolocation data
        """
        # Placeholder for geolocation enrichment
        # In real implementation, this would use IP geolocation services
        if "client_ip" in event.get("metadata", {}):
            event["metadata"]["geolocation"] = {
                "country": "US",
                "region": "Unknown",
                "city": "Unknown"
            }
        return event
    
    async def _add_user_agent_parsing(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and add user agent information.
        
        Args:
            event: Event to enrich
            
        Returns:
            Event with parsed user agent data
        """
        metadata = event.get("metadata", {})
        user_agent = metadata.get("user_agent")
        
        if user_agent:
            # Basic user agent parsing
            parsed_ua = {
                "browser": "Unknown",
                "version": "Unknown",
                "os": "Unknown",
                "device": "Unknown"
            }
            
            # Simple parsing logic (in production, use a proper UA parser)
            if "Chrome" in user_agent:
                parsed_ua["browser"] = "Chrome"
            elif "Firefox" in user_agent:
                parsed_ua["browser"] = "Firefox"
            elif "Safari" in user_agent:
                parsed_ua["browser"] = "Safari"
            
            metadata["user_agent_parsed"] = parsed_ua
            event["metadata"] = metadata
        
        return event
    
    async def _add_performance_metrics(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Add performance metrics to event.
        
        Args:
            event: Event to enrich
            
        Returns:
            Event with performance metrics
        """
        # Add current server load and performance data
        import psutil
        
        try:
            performance_data = {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent
            }
            
            if "performance" not in event:
                event["performance"] = {}
            
            event["performance"].update(performance_data)
            
        except Exception as e:
            logger.warning(f"Failed to collect performance metrics: {e}")
        
        return event
    
    async def _add_security_context(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Add security context information.
        
        Args:
            event: Event to enrich
            
        Returns:
            Event with security context
        """
        metadata = event.get("metadata", {})
        
        # Add security flags
        security_context = {
            "tls_enabled": metadata.get("tls_enabled", False),
            "authentication_method": metadata.get("auth_method", "unknown"),
            "risk_level": "low"  # Default risk level
        }
        
        # Adjust risk level based on event type
        event_type = event.get("event_type")
        if event_type in ["client_disconnected", "authentication_failed", "rate_limit_exceeded"]:
            security_context["risk_level"] = "medium"
        elif event_type in ["security_violation", "suspicious_activity"]:
            security_context["risk_level"] = "high"
        
        event["security_context"] = security_context
        return event
    
    async def _create_fallback_event(self, original_event: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create a fallback event when processing fails.
        
        Args:
            original_event: Original event that failed
            error: Error that occurred
            
        Returns:
            Fallback event
        """
        return {
            "event_type": "event_processing_error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_event_type": original_event.get("event_type", "unknown"),
            "error": error,
            "fallback": True,
            "schema_version": "1.0",
            "event_id": str(uuid.uuid4())
        }
    
    def filter_events(self, events: List[Dict[str, Any]], filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Filter events based on criteria.
        
        Args:
            events: List of events to filter
            filters: Filter criteria
            
        Returns:
            Filtered list of events
        """
        if not filters:
            return events
        
        filtered_events = []
        
        for event in events:
            include_event = True
            
            # Filter by event type
            if "event_types" in filters:
                if event.get("event_type") not in filters["event_types"]:
                    include_event = False
            
            # Filter by time range
            if "start_time" in filters or "end_time" in filters:
                event_time = event.get("timestamp")
                if event_time:
                    try:
                        dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                        if "start_time" in filters and dt < filters["start_time"]:
                            include_event = False
                        if "end_time" in filters and dt > filters["end_time"]:
                            include_event = False
                    except ValueError:
                        pass  # Skip invalid timestamps
            
            # Filter by client ID
            if "client_ids" in filters:
                if event.get("client_id") not in filters["client_ids"]:
                    include_event = False
            
            # Filter by metadata values
            if "metadata_filters" in filters:
                metadata = event.get("metadata", {})
                for key, expected_value in filters["metadata_filters"].items():
                    if metadata.get(key) != expected_value:
                        include_event = False
                        break
            
            if include_event:
                filtered_events.append(event)
            else:
                self.processing_stats["events_filtered"] += 1
        
        return filtered_events
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get handler processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = self.processing_stats.copy()
        
        # Calculate derived metrics
        if stats["events_processed"] > 0:
            stats["validation_success_rate"] = stats["events_validated"] / stats["events_processed"]
            stats["enrichment_rate"] = stats["events_enriched"] / stats["events_processed"]
            stats["filter_rate"] = stats["events_filtered"] / stats["events_processed"]
            stats["error_rate"] = stats["processing_errors"] / stats["events_processed"]
        else:
            stats["validation_success_rate"] = 0.0
            stats["enrichment_rate"] = 0.0
            stats["filter_rate"] = 0.0
            stats["error_rate"] = 0.0
        
        return stats


class EventAggregationHandler:
    """Handles event aggregation and summarization."""
    
    def __init__(self, window_size: int = 300):
        """Initialize aggregation handler.
        
        Args:
            window_size: Time window in seconds for aggregation
        """
        self.window_size = window_size
        self.event_windows: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to aggregation window.
        
        Args:
            event: Event to add
        """
        event_type = event.get("event_type", "unknown")
        event_time = event.get("timestamp")
        
        if event_time not in self.event_windows:
            self.event_windows[event_time] = []
        
        self.event_windows[event_time].append(event)
    
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics for current window.
        
        Returns:
            Dictionary with aggregated metrics
        """
        metrics = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_client": {},
            "time_range": {
                "start": None,
                "end": None
            }
        }
        
        for event_time, events in self.event_windows.items():
            metrics["total_events"] += len(events)
            
            # Update time range
            if not metrics["time_range"]["start"] or event_time < metrics["time_range"]["start"]:
                metrics["time_range"]["start"] = event_time
            if not metrics["time_range"]["end"] or event_time > metrics["time_range"]["end"]:
                metrics["time_range"]["end"] = event_time
            
            # Count by type
            for event in events:
                event_type = event.get("event_type", "unknown")
                metrics["events_by_type"][event_type] = metrics["events_by_type"].get(event_type, 0) + 1
                
                # Count by client
                client_id = event.get("client_id", "unknown")
                metrics["events_by_client"][client_id] = metrics["events_by_client"].get(client_id, 0) + 1
        
        return metrics