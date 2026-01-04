"""
Tests for Redis-based lockout event tracking.

Tests cover:
- increment_lockout_count: Adding lockout events to time window
- get_lockout_count: Retrieving count with automatic cleanup
- get_affected_accounts: Getting detailed account information
- get_ip_summary: Aggregating lockouts by IP address
- clear_lockout_tracking: Clearing all tracking data
- Window expiry behavior and time-based filtering
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.utils import timezone

from api.lockout_tracking import (
    clear_lockout_tracking,
    get_affected_accounts,
    get_ip_summary,
    get_lockout_count,
    increment_lockout_count,
)

pytestmark = pytest.mark.django_db


class MockRedisClient:
    """Mock Redis client that simulates sorted set operations."""

    def __init__(self):
        self.sorted_sets = {}
        self.hashes = {}
        self.expiry_times = {}

    def zadd(self, key, mapping):
        """Add members to sorted set."""
        if key not in self.sorted_sets:
            self.sorted_sets[key] = {}
        self.sorted_sets[key].update(mapping)
        return len(mapping)

    def zcard(self, key):
        """Get cardinality (count) of sorted set."""
        return len(self.sorted_sets.get(key, {}))

    def zremrangebyscore(self, key, min_score, max_score):
        """Remove members by score range."""
        if key not in self.sorted_sets:
            return 0

        original_count = len(self.sorted_sets[key])

        # Filter out items in the score range
        filtered = {}
        for member, score in self.sorted_sets[key].items():
            should_remove = False
            if min_score == "-inf" or score >= float(min_score):
                if max_score == "+inf" or score <= float(max_score):
                    should_remove = True
            if not should_remove:
                filtered[member] = score

        self.sorted_sets[key] = filtered
        return original_count - len(filtered)

    def zrangebyscore(self, key, min_score, max_score, withscores=False):
        """Get members in score range."""
        if key not in self.sorted_sets:
            return []

        cutoff = float(min_score) if min_score != "-inf" else float("-inf")
        members = [
            member
            for member, score in self.sorted_sets[key].items()
            if score >= cutoff
        ]
        # Encode to bytes like real Redis
        return [m.encode("utf-8") if isinstance(m, str) else m for m in members]

    def zrange(self, key, start, end):
        """Get range of members."""
        if key not in self.sorted_sets:
            return []
        members = list(self.sorted_sets[key].keys())
        # Encode to bytes like real Redis
        return [m.encode("utf-8") if isinstance(m, str) else m for m in members]

    def hset(self, key, mapping=None, **kwargs):
        """Set hash fields."""
        if mapping:
            self.hashes[key] = mapping.copy()
        return len(mapping) if mapping else 0

    def hgetall(self, key):
        """Get all hash fields."""
        data = self.hashes.get(key, {})
        # Return as bytes like real Redis
        return {
            k.encode("utf-8") if isinstance(k, str) else k: v.encode("utf-8")
            if isinstance(v, str)
            else v
            for k, v in data.items()
        }

    def expire(self, key, seconds):
        """Set expiry time."""
        self.expiry_times[key] = seconds
        return True

    def delete(self, *keys):
        """Delete keys."""
        for key in keys:
            self.sorted_sets.pop(key, None)
            self.hashes.pop(key, None)
            self.expiry_times.pop(key, None)
        return len(keys)

    def keys(self, pattern):
        """Find keys matching pattern."""
        return []


@pytest.fixture
def mock_redis():
    """Provide a mock Redis client for all tests."""
    mock_client = MockRedisClient()

    with patch("api.lockout_tracking.caches") as mock_caches:
        mock_cache = MagicMock()
        mock_cache.client.get_client.return_value = mock_client
        mock_caches.__getitem__.return_value = mock_cache
        yield mock_client


class TestIncrementLockoutCount:
    """Tests for increment_lockout_count function."""

    def test_increment_adds_event_to_window(self, mock_redis):
        """Test that incrementing adds a lockout event."""
        count = increment_lockout_count(
            username="testuser",
            email="test@example.com",
            ip_address="192.168.1.1",
            source="django-axes",
        )

        assert count == 1
        time_window = settings.LOCKOUT_MASS_WINDOW_MINUTES
        events_key = f"lockout_events:{time_window}m"
        assert len(mock_redis.sorted_sets[events_key]) == 1

    def test_increment_returns_current_count(self, mock_redis):
        """Test that increment returns the current count after adding."""
        count1 = increment_lockout_count(username="user1", source="django-axes")
        assert count1 == 1

        count2 = increment_lockout_count(username="user2", source="local-auth")
        assert count2 == 2

        count3 = increment_lockout_count(username="user3", source="django-axes")
        assert count3 == 3

    def test_increment_stores_detailed_information(self, mock_redis):
        """Test that detailed lockout information is stored."""
        increment_lockout_count(
            username="testuser",
            email="test@example.com",
            ip_address="10.0.0.1",
            source="django-axes",
        )

        accounts = get_affected_accounts()
        assert len(accounts) == 1
        assert accounts[0]["username"] == "testuser"
        assert accounts[0]["email"] == "test@example.com"
        assert accounts[0]["ip_address"] == "10.0.0.1"
        assert accounts[0]["source"] == "django-axes"

    def test_increment_handles_optional_fields(self, mock_redis):
        """Test that optional fields (email, IP) can be None."""
        count = increment_lockout_count(
            username="testuser",
            email=None,
            ip_address=None,
            source="local-auth",
        )

        assert count == 1

        accounts = get_affected_accounts()
        assert len(accounts) == 1
        assert accounts[0]["username"] == "testuser"
        assert accounts[0]["email"] == ""
        assert accounts[0]["ip_address"] == ""

    def test_increment_cleans_old_events(self, mock_redis):
        """Test that old events outside the window are automatically removed."""
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES
        events_key = f"lockout_events:{time_window_minutes}m"

        # Manually add an old event
        old_timestamp = (
            timezone.now() - timedelta(minutes=time_window_minutes + 1)
        ).timestamp()
        mock_redis.zadd(events_key, {f"{old_timestamp}:olduser": old_timestamp})

        assert mock_redis.zcard(events_key) == 1

        # Add a new event - should trigger cleanup
        increment_lockout_count(username="newuser", source="django-axes")

        # Verify old event was removed
        count = get_lockout_count()
        assert count == 1

        accounts = get_affected_accounts()
        assert len(accounts) == 1
        assert accounts[0]["username"] == "newuser"

    def test_increment_returns_zero_on_redis_error(self):
        """Test that increment returns 0 on Redis error to prevent blocking."""
        with patch("api.lockout_tracking.caches") as mock_caches:
            mock_cache = MagicMock()
            mock_cache.client.get_client.side_effect = Exception("Redis connection error")
            mock_caches.__getitem__.return_value = mock_cache

            count = increment_lockout_count(username="testuser", source="django-axes")
            assert count == 0


class TestGetLockoutCount:
    """Tests for get_lockout_count function."""

    def test_get_count_returns_zero_initially(self, mock_redis):
        """Test that count is zero when no lockouts have occurred."""
        count = get_lockout_count()
        assert count == 0

    def test_get_count_returns_current_events_in_window(self, mock_redis):
        """Test that count reflects events within the time window."""
        for i in range(5):
            increment_lockout_count(username=f"user{i}", source="django-axes")

        count = get_lockout_count()
        assert count == 5

    def test_get_count_excludes_expired_events(self, mock_redis):
        """Test that expired events are excluded from count."""
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES
        events_key = f"lockout_events:{time_window_minutes}m"

        # Add an old event
        old_timestamp = (
            timezone.now() - timedelta(minutes=time_window_minutes + 1)
        ).timestamp()
        mock_redis.zadd(events_key, {f"{old_timestamp}:olduser": old_timestamp})

        # Add a new event
        increment_lockout_count(username="newuser", source="django-axes")

        # Count should only include the new event
        count = get_lockout_count()
        assert count == 1

    def test_get_count_returns_zero_on_redis_error(self):
        """Test that get_count returns 0 on Redis error."""
        with patch("api.lockout_tracking.caches") as mock_caches:
            mock_cache = MagicMock()
            mock_cache.client.get_client.side_effect = Exception("Redis connection error")
            mock_caches.__getitem__.return_value = mock_cache

            count = get_lockout_count()
            assert count == 0


class TestGetAffectedAccounts:
    """Tests for get_affected_accounts function."""

    def test_get_accounts_returns_empty_list_initially(self, mock_redis):
        """Test that no accounts are returned when no lockouts have occurred."""
        accounts = get_affected_accounts()
        assert accounts == []

    def test_get_accounts_returns_all_locked_accounts(self, mock_redis):
        """Test that all locked accounts are returned."""
        increment_lockout_count(
            username="user1",
            email="user1@example.com",
            ip_address="192.168.1.1",
            source="django-axes",
        )
        increment_lockout_count(
            username="user2",
            email="user2@example.com",
            ip_address="192.168.1.2",
            source="local-auth",
        )
        increment_lockout_count(
            username="user3",
            email="user3@example.com",
            ip_address="192.168.1.3",
            source="django-axes",
        )

        accounts = get_affected_accounts()
        assert len(accounts) == 3

        usernames = [acc["username"] for acc in accounts]
        assert "user1" in usernames
        assert "user2" in usernames
        assert "user3" in usernames

    def test_get_accounts_includes_all_details(self, mock_redis):
        """Test that account details include all required fields."""
        increment_lockout_count(
            username="testuser",
            email="test@example.com",
            ip_address="10.0.0.1",
            source="django-axes",
        )

        accounts = get_affected_accounts()
        assert len(accounts) == 1

        account = accounts[0]
        assert "username" in account
        assert "email" in account
        assert "ip_address" in account
        assert "source" in account
        assert "lockout_time" in account

        assert account["username"] == "testuser"
        assert account["email"] == "test@example.com"
        assert account["ip_address"] == "10.0.0.1"
        assert account["source"] == "django-axes"

    def test_get_accounts_excludes_expired_events(self, mock_redis):
        """Test that expired events are not included in affected accounts."""
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES
        events_key = f"lockout_events:{time_window_minutes}m"

        # Add an old event
        old_timestamp = (
            timezone.now() - timedelta(minutes=time_window_minutes + 1)
        ).timestamp()
        member = f"{old_timestamp}:olduser"
        mock_redis.zadd(events_key, {member: old_timestamp})

        # Add a new event
        increment_lockout_count(username="newuser", source="django-axes")

        # Only new event should be in affected accounts
        accounts = get_affected_accounts()
        assert len(accounts) == 1
        assert accounts[0]["username"] == "newuser"

    def test_get_accounts_returns_empty_list_on_redis_error(self):
        """Test that get_accounts returns empty list on Redis error."""
        with patch("api.lockout_tracking.caches") as mock_caches:
            mock_cache = MagicMock()
            mock_cache.client.get_client.side_effect = Exception("Redis connection error")
            mock_caches.__getitem__.return_value = mock_cache

            accounts = get_affected_accounts()
            assert accounts == []


class TestGetIpSummary:
    """Tests for get_ip_summary function."""

    def test_get_ip_summary_returns_empty_list_initially(self, mock_redis):
        """Test that no IPs are returned when no lockouts have occurred."""
        ip_summary = get_ip_summary()
        assert ip_summary == []

    def test_get_ip_summary_aggregates_by_ip(self, mock_redis):
        """Test that lockouts are correctly aggregated by IP address."""
        increment_lockout_count(username="user1", ip_address="192.168.1.1", source="django-axes")
        increment_lockout_count(username="user2", ip_address="192.168.1.1", source="django-axes")
        increment_lockout_count(username="user3", ip_address="192.168.1.2", source="django-axes")
        increment_lockout_count(username="user4", ip_address="192.168.1.3", source="django-axes")

        ip_summary = get_ip_summary()
        assert len(ip_summary) == 3

        # Find the IP with 2 lockouts
        ip_1_1 = next(ip for ip in ip_summary if ip["address"] == "192.168.1.1")
        assert ip_1_1["count"] == 2

        # Other IPs should have 1 lockout each
        ip_1_2 = next(ip for ip in ip_summary if ip["address"] == "192.168.1.2")
        assert ip_1_2["count"] == 1

        ip_1_3 = next(ip for ip in ip_summary if ip["address"] == "192.168.1.3")
        assert ip_1_3["count"] == 1

    def test_get_ip_summary_sorted_by_count(self, mock_redis):
        """Test that IP summary is sorted by count descending."""
        increment_lockout_count(username="user1", ip_address="10.0.0.1", source="django-axes")

        increment_lockout_count(username="user2", ip_address="10.0.0.2", source="django-axes")
        increment_lockout_count(username="user3", ip_address="10.0.0.2", source="django-axes")
        increment_lockout_count(username="user4", ip_address="10.0.0.2", source="django-axes")

        increment_lockout_count(username="user5", ip_address="10.0.0.3", source="django-axes")
        increment_lockout_count(username="user6", ip_address="10.0.0.3", source="django-axes")

        ip_summary = get_ip_summary()

        # Should be sorted by count descending
        assert len(ip_summary) == 3
        assert ip_summary[0]["address"] == "10.0.0.2"
        assert ip_summary[0]["count"] == 3
        assert ip_summary[1]["address"] == "10.0.0.3"
        assert ip_summary[1]["count"] == 2
        assert ip_summary[2]["address"] == "10.0.0.1"
        assert ip_summary[2]["count"] == 1

    def test_get_ip_summary_excludes_empty_ips(self, mock_redis):
        """Test that lockouts without IP addresses are excluded from summary."""
        increment_lockout_count(username="user1", ip_address="192.168.1.1", source="django-axes")
        increment_lockout_count(username="user2", ip_address=None, source="local-auth")
        increment_lockout_count(username="user3", ip_address="", source="django-axes")

        ip_summary = get_ip_summary()

        # Only the one with a valid IP should be included
        assert len(ip_summary) == 1
        assert ip_summary[0]["address"] == "192.168.1.1"
        assert ip_summary[0]["count"] == 1


class TestClearLockoutTracking:
    """Tests for clear_lockout_tracking function."""

    def test_clear_removes_all_events(self, mock_redis):
        """Test that clear removes all lockout events."""
        increment_lockout_count(username="user1", source="django-axes")
        increment_lockout_count(username="user2", source="local-auth")
        increment_lockout_count(username="user3", source="django-axes")

        assert get_lockout_count() == 3

        result = clear_lockout_tracking()
        assert result is True

        assert get_lockout_count() == 0
        assert get_affected_accounts() == []

    def test_clear_removes_all_details(self, mock_redis):
        """Test that clear removes all lockout details."""
        increment_lockout_count(
            username="user1",
            email="user1@example.com",
            ip_address="192.168.1.1",
            source="django-axes",
        )

        assert len(get_affected_accounts()) == 1

        clear_lockout_tracking()

        assert get_affected_accounts() == []

    def test_clear_returns_false_on_redis_error(self):
        """Test that clear returns False on Redis error."""
        with patch("api.lockout_tracking.caches") as mock_caches:
            mock_cache = MagicMock()
            mock_cache.client.get_client.side_effect = Exception("Redis connection error")
            mock_caches.__getitem__.return_value = mock_cache

            result = clear_lockout_tracking()
            assert result is False


class TestWindowExpiryBehavior:
    """Tests for time window expiry behavior."""

    def test_events_expire_after_window(self, mock_redis):
        """Test that events automatically expire after the time window."""
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES
        events_key = f"lockout_events:{time_window_minutes}m"

        # Add event just outside the window (expired)
        expired_timestamp = (
            timezone.now() - timedelta(minutes=time_window_minutes, seconds=1)
        ).timestamp()
        mock_redis.zadd(events_key, {f"{expired_timestamp}:expireduser": expired_timestamp})

        # Add event just inside the window (valid)
        valid_timestamp = (
            timezone.now() - timedelta(minutes=time_window_minutes - 1)
        ).timestamp()
        mock_redis.zadd(events_key, {f"{valid_timestamp}:validuser": valid_timestamp})

        # Get count should exclude expired events
        count = get_lockout_count()
        assert count == 1

    def test_sliding_window_updates_correctly(self, mock_redis):
        """Test that the sliding window correctly tracks events."""
        increment_lockout_count(username="user1", source="django-axes")
        assert get_lockout_count() == 1

        increment_lockout_count(username="user2", source="django-axes")
        assert get_lockout_count() == 2

        count = get_lockout_count()
        assert count == 2

    def test_threshold_detection(self, mock_redis):
        """Test that threshold can be detected for mass lockout alerts."""
        threshold = settings.LOCKOUT_MASS_THRESHOLD

        # Add events up to threshold - 1
        for i in range(threshold - 1):
            increment_lockout_count(username=f"user{i}", source="django-axes")

        count = get_lockout_count()
        assert count < threshold

        # Add one more event to cross threshold
        increment_lockout_count(username=f"user{threshold}", source="django-axes")

        count = get_lockout_count()
        assert count >= threshold
