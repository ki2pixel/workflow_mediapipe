# -*- coding: utf-8 -*-
"""
Concurrency unit tests for WebhookService.
Verifies thread-safety of cache and state variables under concurrent access.
"""
import time
import threading
import pytest
from unittest import mock
import requests

from services.webhook_service import fetch_records, get_service_status

@pytest.fixture
def mock_requests_get():
    """Mock requests.get to return a consistent payload with a slight delay."""
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "source_url": "https://www.dropbox.com/scl/fi/xyz/video.mp4?rlkey=123",
            "provider": "dropbox",
            "created_at": "2025-10-17T12:34:13+02:00"
        }
    ]
    
    def delayed_get(*args, **kwargs):
        # Simulate network latency to amplify potential race conditions
        time.sleep(0.05)
        return mock_response
        
    with mock.patch('requests.get', side_effect=delayed_get) as mock_get:
        yield mock_get

def test_concurrent_webhook_fetches(mock_requests_get):
    """
    Given multiple threads calling WebhookService concurrently
    When fetch_records and get_service_status are invoked simultaneously
    Then all threads should succeed and return consistent cached data without raising exceptions
    """
    num_threads = 10
    results = [None] * num_threads
    exceptions = []

    # Reset cache to force real fetch
    import services.webhook_service as ws
    with ws._lock:
        ws._cache_data = None
        ws._cache_fetched_at = 0.0

    def worker(index):
        try:
            # Alternate calls between fetch_records and get_service_status
            if index % 2 == 0:
                results[index] = fetch_records()
            else:
                results[index] = fetch_records()
                status = get_service_status()
                assert status is not None
        except Exception as e:
            exceptions.append(e)

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    # Join all threads
    for t in threads:
        t.join()

    # Assert no exceptions occurred
    assert not exceptions, f"Concurrent execution raised exceptions: {exceptions}"
    
    # Assert all fetched rows are identical and not None
    first_result = results[0]
    assert first_result is not None
    assert len(first_result) == 1
    
    for r in results:
        assert r == first_result, "Concurrent threads returned inconsistent data"
        
    # Verify requests.get was called (cached should prevent it being called num_threads times)
    # The first thread(s) will fetch, others will hit the lock/cache depending on timing.
    # Due to the lock, the first thread entering the critical section of fetch_records will fetch,
    # and subsequent threads will find the cache populated and return immediately.
    assert mock_requests_get.call_count < num_threads
