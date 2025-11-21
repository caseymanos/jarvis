"""
Backend health monitoring service.

Tracks system health metrics and publishes to Redis streams for real-time presence indicators.
"""

import asyncio
import psutil
import time
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.redis_streams import get_redis_service
from app.services.temporal_client import get_temporal_service


class HealthMonitor:
    """Monitors backend health and publishes metrics."""

    def __init__(self):
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_request_time: Optional[float] = None

    async def start_monitoring(self, interval_seconds: int = 5):
        """
        Start background health monitoring.

        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self.monitoring:
            print("Health monitoring already running")
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(
            self._monitor_loop(interval_seconds)
        )
        print(f"✓ Health monitoring started (interval: {interval_seconds}s)")

    async def stop_monitoring(self):
        """Stop background health monitoring."""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        print("✓ Health monitoring stopped")

    async def _monitor_loop(self, interval: int):
        """
        Background monitoring loop.

        Args:
            interval: Interval in seconds
        """
        redis_service = get_redis_service()

        while self.monitoring:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()

                # Publish each metric
                for metric_name, value in metrics.items():
                    await redis_service.publish_health_metric(
                        metric_name=metric_name,
                        value=value,
                        labels={"source": "backend"}
                    )

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(interval)

    async def collect_metrics(self) -> Dict[str, float]:
        """
        Collect current health metrics.

        Returns:
            Dictionary of metric names to values
        """
        metrics = {}

        # Uptime
        uptime_seconds = time.time() - self.start_time
        metrics["uptime_seconds"] = uptime_seconds

        # CPU usage
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics["cpu_percent"] = cpu_percent
        except Exception:
            metrics["cpu_percent"] = 0.0

        # Memory usage
        try:
            memory = psutil.virtual_memory()
            metrics["memory_percent"] = memory.percent
            metrics["memory_used_mb"] = memory.used / (1024 * 1024)
        except Exception:
            metrics["memory_percent"] = 0.0
            metrics["memory_used_mb"] = 0.0

        # Request metrics
        metrics["request_count"] = float(self.request_count)
        metrics["error_count"] = float(self.error_count)

        # Error rate
        if self.request_count > 0:
            metrics["error_rate"] = self.error_count / self.request_count
        else:
            metrics["error_rate"] = 0.0

        # Latency (time since last request)
        if self.last_request_time:
            idle_time = time.time() - self.last_request_time
            metrics["idle_time_seconds"] = idle_time
        else:
            metrics["idle_time_seconds"] = uptime_seconds

        # Service health checks
        redis_healthy = await self._check_redis_health()
        temporal_healthy = await self._check_temporal_health()

        metrics["redis_healthy"] = 1.0 if redis_healthy else 0.0
        metrics["temporal_healthy"] = 1.0 if temporal_healthy else 0.0

        # Overall health score (0.0 to 1.0)
        health_score = await self._calculate_health_score(
            cpu_percent=metrics["cpu_percent"],
            memory_percent=metrics["memory_percent"],
            error_rate=metrics["error_rate"],
            redis_healthy=redis_healthy,
            temporal_healthy=temporal_healthy
        )
        metrics["health_score"] = health_score

        return metrics

    async def _check_redis_health(self) -> bool:
        """Check if Redis is healthy."""
        try:
            redis_service = get_redis_service()
            if redis_service.redis:
                await redis_service.redis.ping()
                return True
        except Exception:
            pass
        return False

    async def _check_temporal_health(self) -> bool:
        """Check if Temporal is healthy."""
        temporal_service = get_temporal_service()
        return temporal_service.is_connected()

    async def _calculate_health_score(
        self,
        cpu_percent: float,
        memory_percent: float,
        error_rate: float,
        redis_healthy: bool,
        temporal_healthy: bool
    ) -> float:
        """
        Calculate overall health score.

        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            error_rate: Error rate (0.0 to 1.0)
            redis_healthy: Redis connection status
            temporal_healthy: Temporal connection status

        Returns:
            Health score from 0.0 (unhealthy) to 1.0 (healthy)
        """
        score = 1.0

        # Penalize high CPU usage
        if cpu_percent > 80:
            score -= 0.3
        elif cpu_percent > 60:
            score -= 0.15

        # Penalize high memory usage
        if memory_percent > 80:
            score -= 0.3
        elif memory_percent > 60:
            score -= 0.15

        # Penalize high error rate
        if error_rate > 0.1:
            score -= 0.4
        elif error_rate > 0.05:
            score -= 0.2

        # Penalize service unavailability
        if not redis_healthy:
            score -= 0.2

        # Temporal is optional, smaller penalty
        if not temporal_healthy:
            score -= 0.1

        return max(0.0, score)

    def record_request(self):
        """Record a request for metrics."""
        self.request_count += 1
        self.last_request_time = time.time()

    def record_error(self):
        """Record an error for metrics."""
        self.error_count += 1

    async def get_current_health(self) -> Dict[str, Any]:
        """
        Get current health status.

        Returns:
            Health status dictionary
        """
        metrics = await self.collect_metrics()

        return {
            "status": "healthy" if metrics["health_score"] >= 0.7 else "degraded" if metrics["health_score"] >= 0.4 else "unhealthy",
            "health_score": metrics["health_score"],
            "uptime_seconds": metrics["uptime_seconds"],
            "metrics": metrics,
            "services": {
                "redis": "healthy" if metrics["redis_healthy"] == 1.0 else "unhealthy",
                "temporal": "healthy" if metrics["temporal_healthy"] == 1.0 else "unhealthy"
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# Singleton instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create health monitor singleton."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
