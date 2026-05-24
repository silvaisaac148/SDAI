import asyncio
import logging
import json
import os
import sys
from unittest.mock import MagicMock, patch
import pytest

from app.db.batch_writer import EventBatchWriter
from app.utils.logger import StructuredFormatter, setup_logger

@pytest.mark.asyncio
async def test_batch_writer_enqueue_and_flush():
    """Verify that EventBatchWriter enqueues packets and flushes them on exit."""
    writer = EventBatchWriter(batch_size=10, flush_interval=0.1)
    
    # Mock both get_client and execute_with_retry to avoid real network queries
    with patch("app.db.batch_writer.get_client", return_value=MagicMock()), \
         patch("app.db.batch_writer.execute_with_retry") as mock_execute:
         
        # Start writer
        writer.start()
        
        # Enqueue 5 items
        for i in range(5):
            await writer.enqueue({"src_ip": f"10.0.0.{i}", "protocol": "TCP"})
            
        assert writer.queue.qsize() == 5
        
        # Stop and flush
        await writer.stop()
        
        # Queue should be empty now
        assert writer.queue.qsize() == 0
        
        # execute_with_retry should have been called once to insert the batch
        mock_execute.assert_called_once()
        
        # Get the lambda function passed to execute_with_retry
        called_lambda = mock_execute.call_args[0][0]
        
        # Verify the lambda invokes .table("events").insert() with the batch
        mock_client = MagicMock()
        called_lambda(mock_client)
        mock_client.table.assert_called_once_with("events")
        mock_client.table().insert.assert_called_once()
        inserted_list = mock_client.table().insert.call_args[0][0]
        assert len(inserted_list) == 5
        assert inserted_list[0]["src_ip"] == "10.0.0.0"
        assert inserted_list[4]["src_ip"] == "10.0.0.4"


def test_structured_formatter_console():
    """Verify that StructuredFormatter prints human-readable logs when json_format is False."""
    formatter = StructuredFormatter(json_format=False)
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Intrusion attempt blocked!",
        args=(),
        exc_info=None
    )
    # Mock record extra
    record.extra = {"src_ip": "192.168.1.50"}  # type: ignore
    
    output = formatter.format(record)
    assert "INFO" in output
    assert "Intrusion attempt blocked!" in output
    assert "192.168.1.50" in output
    # Verify no raw JSON curly braces at the start
    assert not output.strip().startswith("{")

def test_structured_formatter_json():
    """Verify that StructuredFormatter outputs valid JSON when json_format is True."""
    formatter = StructuredFormatter(json_format=True)
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=100,
        msg="Port scanning detected",
        args=(),
        exc_info=None
    )
    record.extra = {"threat_type": "port_scan", "severity": "media"}  # type: ignore
    
    output = formatter.format(record)
    # Verify valid JSON
    parsed = json.loads(output)
    assert parsed["level"] == "WARNING"
    assert parsed["message"] == "Port scanning detected"
    assert parsed["threat_type"] == "port_scan"
    assert parsed["severity"] == "media"
    assert "timestamp" in parsed
    assert parsed["line"] == 100

def test_setup_logger_custom_level():
    """Verify setup_logger respects requested levels and formats."""
    custom_logger = setup_logger("test_custom", level="DEBUG")
    assert custom_logger.level == logging.DEBUG
    assert len(custom_logger.handlers) == 1
    assert isinstance(custom_logger.handlers[0].formatter, StructuredFormatter)
