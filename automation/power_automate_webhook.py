"""
Sends the compiled IncidentReport to a Power Automate "When an HTTP request
is received" flow, which fans out to Teams/email per your flow's own logic.

This module cannot be end-to-end tested without a real Power Automate
tenant and flow URL - that's inherent to the integration, not something
mockable in a meaningful way. When POWER_AUTOMATE_WEBHOOK_URL is unset,
it runs in log-only mode so the rest of the pipeline stays runnable.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).resolve().parent.parent))
from agents.schemas import IncidentReport
from config.settings import settings

logger = logging.getLogger("gridguard.automation")
logging.basicConfig(level=logging.INFO)

SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]


def should_notify(report: IncidentReport) -> bool:
    threshold = settings.cfg["automation"]["notify_severity_threshold"]
    try:
        return SEVERITY_ORDER.index(report.severity) >= SEVERITY_ORDER.index(threshold)
    except ValueError:
        return True  # unknown severity label -> fail open to notifying


def send_incident_alert(report: IncidentReport) -> dict:
    """
    Returns a dict describing what happened, for logging/testing:
        {"sent": bool, "mode": "live" | "mock" | "skipped", "status_code": int | None}
    """
    if not should_notify(report):
        logger.info("Severity '%s' below threshold - not notifying.", report.severity)
        return {"sent": False, "mode": "skipped", "status_code": None}

    payload = report.model_dump()

    if not settings.power_automate_webhook_url:
        logger.info("POWER_AUTOMATE_WEBHOOK_URL not set - logging alert instead of sending.\n%s", payload)
        return {"sent": False, "mode": "mock", "status_code": None}

    try:
        resp = httpx.post(settings.power_automate_webhook_url, json=payload, timeout=10.0)
        resp.raise_for_status()
        logger.info("Sent incident alert to Power Automate (status %s).", resp.status_code)
        return {"sent": True, "mode": "live", "status_code": resp.status_code}
    except httpx.HTTPError as e:
        logger.error("Failed to send incident alert: %s", e)
        return {"sent": False, "mode": "live", "status_code": None}


if __name__ == "__main__":
    demo_report = IncidentReport(
        attack_type="Denial of Service",
        target="NAN-Gateway",
        severity="High",
        confidence=0.8,
        impact="Communication disruption",
        recommended_actions=["Isolate affected asset", "Notify on-call engineer"],
        root_cause="Elevated request rate consistent with DoS",
        knowledge_references=[],
    )
    print(send_incident_alert(demo_report))
