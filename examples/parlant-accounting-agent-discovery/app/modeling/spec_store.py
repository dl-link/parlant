from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping

from app.config import project_config

SPEC_VERSION = "1.0"


@dataclass
class SpecStore:
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def set_value(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        cursor: Dict[str, Any] = self.data
        for idx, part in enumerate(parts):
            if idx == len(parts) - 1:
                cursor[part] = value
            else:
                cursor = cursor.setdefault(part, {})  # type: ignore[assignment]

    def merge(self, incoming: Mapping[str, Any]) -> None:
        self.data = merge_dicts(self.data, incoming)

    def snapshot(self) -> Dict[str, Any]:
        return merge_dicts(get_spec_template(), self.data)


_STORES: Dict[str, SpecStore] = {}


def get_store(session_id: str) -> SpecStore:
    if session_id not in _STORES:
        _STORES[session_id] = SpecStore(session_id=session_id)
    return _STORES[session_id]


def merge_dicts(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {**base}
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), Mapping):
            merged[key] = merge_dicts(base[key], value)  # type: ignore[index]
        else:
            merged[key] = value
    return merged


def get_spec_template() -> Dict[str, Any]:
    return {
        "spec_schema_version": SPEC_VERSION,
        "customer_profile": {
            "company_name": None,
            "industry": None,
            "country": "New Zealand",
            "currency": project_config.default_currency,
            "primary_contacts": [],
        },
        "current_stack": {
            "accounting_system": None,
            "bank_feeds": None,
            "document_sources": [],
            "api_access_available": None,
        },
        "problem_statement": {
            "top_pain_points": [],
            "current_process_description": None,
            "volume_metrics": {
                "invoices_per_month": None,
                "bank_transactions_per_month": None,
                "customers_in_ar": None,
                "suppliers_in_ap": None,
            },
        },
        "target_use_cases": [],
        "automation_preferences": {
            "automation_level": None,
            "approval_threshold": project_config.approval_threshold_default,
            "escalation_path": None,
            "failure_policy": None,
        },
        "rules_and_policies": {
            "accounting_policy_available": None,
            "chart_of_accounts_available": None,
            "tax_rules_notes": None,
            "compliance_requirements": [],
        },
        "integration_requirements": {
            "needs_writeback": None,
            "systems_to_integrate": [],
            "data_retention_policy": None,
            "deployment_environment": None,
        },
        "mvp_definition": {
            "recommended_mvp_use_case": None,
            "mvp_scope": [],
            "out_of_scope": [],
            "required_sample_data": [],
            "estimated_iterations": 3,
            "second_priority_use_case": None,
            "success_metrics": [],
        },
        "final_output": {},
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "project": project_config.name,
            "runtime": project_config.runtime,
        },
    }


def spec_to_markdown(spec: Mapping[str, Any]) -> str:
    lines: List[str] = ["# Agent Requirements Spec", ""]
    cp = spec.get("customer_profile", {})
    lines.append("## Customer Profile")
    lines.append(f"- Company: {cp.get('company_name') or 'TBD'}")
    lines.append(f"- Industry: {cp.get('industry') or 'TBD'}")
    lines.append(f"- Country: {cp.get('country')}")
    lines.append(f"- Currency: {cp.get('currency')}")
    if cp.get("primary_contacts"):
        lines.append(f"- Contacts: {', '.join(cp['primary_contacts'])}")
    lines.append("")

    lines.append("## Current Stack")
    stack = spec.get("current_stack", {})
    lines.append(f"- Accounting System: {stack.get('accounting_system') or 'TBD'}")
    lines.append(f"- Bank Feeds: {stack.get('bank_feeds')}")
    lines.append(
        f"- Document Sources: {', '.join(stack.get('document_sources', [])) or 'TBD'}"
    )
    lines.append(f"- API Access: {stack.get('api_access_available')}")
    lines.append("")

    lines.append("## Problem Statement")
    ps = spec.get("problem_statement", {})
    pain = ps.get("top_pain_points") or []
    lines.append("- Top Pain Points: " + (", ".join(pain) or "TBD"))
    lines.append(
        "- Current Process: " + (ps.get("current_process_description") or "TBD")
    )
    volume = ps.get("volume_metrics") or {}
    if any(volume.values()):
        lines.append("- Volume Metrics:")
        for k, v in volume.items():
            lines.append(f"  - {k.replace('_', ' ').title()}: {v}")
    lines.append("")

    lines.append("## Target Use Cases")
    tucs = spec.get("target_use_cases") or []
    if tucs:
        for item in tucs:
            lines.append(
                f"- {item.get('use_case')} (priority {item.get('priority')})"
            )
            if item.get("success_metrics"):
                lines.append(
                    "  - Success metrics: " + ", ".join(item["success_metrics"])
                )
    else:
        lines.append("- TBD")
    lines.append("")

    lines.append("## Automation Preferences")
    ap = spec.get("automation_preferences", {})
    lines.append(f"- Automation Level: {ap.get('automation_level')}")
    lines.append(f"- Approval Threshold: {ap.get('approval_threshold')}")
    if ap.get("escalation_path"):
        lines.append(f"- Escalation Path: {ap['escalation_path']}")
    if ap.get("failure_policy"):
        lines.append(f"- Failure Policy: {ap['failure_policy']}")
    lines.append("")

    lines.append("## Rules & Policies")
    rp = spec.get("rules_and_policies", {})
    lines.append(
        "- Compliance Requirements: "
        + (", ".join(rp.get("compliance_requirements", [])) or "TBD")
    )
    if rp.get("tax_rules_notes"):
        lines.append(f"- Tax Rules: {rp['tax_rules_notes']}")
    lines.append("")

    lines.append("## Integration Requirements")
    ir = spec.get("integration_requirements", {})
    lines.append(f"- Needs Writeback: {ir.get('needs_writeback')}")
    lines.append(
        "- Systems to Integrate: "
        + (", ".join(ir.get("systems_to_integrate", [])) or "TBD")
    )
    if ir.get("deployment_environment"):
        lines.append(f"- Deployment: {ir['deployment_environment']}")
    if ir.get("data_retention_policy"):
        lines.append(f"- Data Retention: {ir['data_retention_policy']}")
    lines.append("")

    lines.append("## MVP Definition")
    mvp = spec.get("mvp_definition", {})
    lines.append(f"- Recommended MVP Use Case: {mvp.get('recommended_mvp_use_case')}")
    if mvp.get("second_priority_use_case"):
        lines.append(f"- Second Priority: {mvp['second_priority_use_case']}")
    lines.append("- MVP Scope: " + (", ".join(mvp.get("mvp_scope", [])) or "TBD"))
    if mvp.get("out_of_scope"):
        lines.append("- Out of Scope: " + ", ".join(mvp["out_of_scope"]))
    lines.append(
        "- Required Sample Data: "
        + (", ".join(mvp.get("required_sample_data", [])) or "TBD")
    )
    if mvp.get("success_metrics"):
        lines.append("- Success Metrics: " + ", ".join(mvp["success_metrics"]))
    lines.append(f"- Estimated Iterations: {mvp.get('estimated_iterations')}")

    lines.append("")
    lines.append("## Guardrails")
    lines.append("- Do not provide tax or legal advice; focus on requirements gathering.")
    lines.append(
        "- If autoposting is requested, confirm approvals/audit logging requirements first."
    )
    lines.append(
        "- Offer conservative (HITL) and aggressive (autopost with approvals) options when user is unsure."
    )

    return "\n".join(lines)


def persist_outputs(spec: Mapping[str, Any], session_id: str | None = None) -> Dict[str, str]:
    suffix = f"_{session_id}" if session_id else ""
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    json_path = outputs_dir / f"agent_spec{suffix}.json"
    md_path = outputs_dir / f"agent_spec{suffix}.md"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(spec_to_markdown(spec))

    return {"json": str(json_path), "markdown": str(md_path)}
