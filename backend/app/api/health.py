"""
Health monitoring API endpoints.

Provides backend health status and metrics for presence indicators.
"""

from fastapi import APIRouter
from app.services.health_monitor import get_health_monitor

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """
    Get basic health status.

    Returns:
        Basic health status
    """
    health_monitor = get_health_monitor()
    health = await health_monitor.get_current_health()

    return {
        "status": health["status"],
        "health_score": health["health_score"],
        "timestamp": health["timestamp"]
    }


@router.get("/detailed")
async def detailed_health():
    """
    Get detailed health metrics and service status.

    Returns:
        Comprehensive health information including:
        - Overall health status and score
        - System metrics (CPU, memory)
        - Request/error metrics
        - Service health (Redis, Temporal)
        - Uptime
    """
    health_monitor = get_health_monitor()
    return await health_monitor.get_current_health()


@router.get("/metrics")
async def health_metrics():
    """
    Get raw health metrics.

    Returns:
        Dictionary of all collected metrics
    """
    health_monitor = get_health_monitor()
    return await health_monitor.collect_metrics()


@router.get("/services")
async def service_status():
    """
    Get status of dependent services.

    Returns:
        Status of Redis, Temporal, and other services
    """
    health_monitor = get_health_monitor()
    health = await health_monitor.get_current_health()

    return {
        "services": health["services"],
        "overall_status": health["status"]
    }


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes/container readiness check.

    Returns:
        200 if ready to serve traffic, 503 if not ready
    """
    health_monitor = get_health_monitor()
    health = await health_monitor.get_current_health()

    # Consider ready if health score is above minimal threshold
    ready = health["health_score"] >= 0.5

    if ready:
        return {"ready": True, "health_score": health["health_score"]}
    else:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "health_score": health["health_score"],
                "message": "Backend not ready to serve traffic"
            }
        )


@router.get("/live")
async def liveness_check():
    """
    Kubernetes/container liveness check.

    Returns:
        200 if application is alive (even if degraded)
    """
    # Always return 200 if we can respond
    # This prevents Kubernetes from killing a degraded but functional pod
    return {"alive": True}
