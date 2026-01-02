from __future__ import annotations

from typing import Any, Dict, List

import parlant.sdk as p

from app.modeling.spec_store import (
    SpecStore,
    get_spec_template,
    get_store,
    merge_dicts,
    persist_outputs,
)


def _ensure_store(context: p.ToolContext) -> SpecStore:
    return get_store(context.session_id)


@p.tool
async def save_answer(context: p.ToolContext, key: str, value: Any) -> p.ToolResult:
    store = _ensure_store(context)
    store.set_value(key, value)
    return p.ToolResult({"status": "saved", "key": key, "value": value})


def _derive_use_case_priority(spec_partial: Dict[str, Any]) -> List[Dict[str, Any]]:
    pain_points = (spec_partial.get("problem_statement") or {}).get("top_pain_points", [])
    system = (spec_partial.get("current_stack") or {}).get("accounting_system", "")
    ranking: List[Dict[str, Any]] = []

    def add(use_case: str, reason: str, priority: int) -> None:
        ranking.append(
            {
                "use_case": use_case,
                "priority": priority,
                "reason": reason,
                "success_metrics": [
                    "Cycle time reduction",
                    "Error rate reduction",
                    "Throughput increase",
                ],
            }
        )

    for idx, pain in enumerate(pain_points):
        if "recon" in pain.lower():
            add("Bank reconciliation", "User emphasized reconciliation pain", idx + 1)
        elif "invoice" in pain.lower() or "ap" in pain.lower():
            add("Invoice compliance review (AP)", "Invoices called out as pain", idx + 1)
        elif "month" in pain.lower():
            add("Month-end close checklist", "Month-end pain highlighted", idx + 1)

    if not ranking:
        add("Expense coding assistance", "Default recommendation to unblock discovery", 1)
        add("AR collections assistant", "Secondary option to validate priorities", 2)

    if system and system.lower() in {"xero", "quickbooks", "myob"}:
        ranking.insert(
            0,
            {
                "use_case": "GST/VAT review",
                "priority": 1,
                "reason": f"{system} supports GST/VAT automation",
                "success_metrics": ["No filing penalties", "Audit-ready workpapers"],
            },
        )

    for i, rec in enumerate(ranking, start=1):
        rec["priority"] = i
    return ranking[:5]


@p.tool
async def recommend_agent_types(context: p.ToolContext, spec_partial: Dict[str, Any]) -> p.ToolResult:
    store = _ensure_store(context)
    ranking = _derive_use_case_priority(spec_partial)
    store.set_value("target_use_cases", ranking)
    return p.ToolResult({"recommended": ranking})


def _build_scope_from_use_cases(target_use_cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    scope: List[str] = []
    success_metrics: List[str] = []
    required_data: List[str] = []

    for uc in target_use_cases[:2]:
        use_case = uc.get("use_case")
        if not use_case:
            continue
        scope.append(f"Workflow: {use_case}")
        required_data.append(f"Sample data for {use_case}")
        success_metrics.append(
            f"{use_case}: reduce handling time by 30% and cut errors by 20%"
        )

    if not scope:
        scope.append("Workflow: validate invoices against PO + bank statement")
        required_data.append("10 sample invoices + bank feeds")
        success_metrics.append("Reduce invoice review time by 30%")

    return {
        "mvp_scope": scope,
        "required_sample_data": required_data,
        "success_metrics": success_metrics,
        "out_of_scope": ["Tax/legal advice", "Posting without approvals unless confirmed"],
    }


@p.tool
async def generate_mvp_plan(context: p.ToolContext, spec_partial: Dict[str, Any]) -> p.ToolResult:
    store = _ensure_store(context)
    target_use_cases: List[Dict[str, Any]] = spec_partial.get("target_use_cases") or []
    automation_pref = (spec_partial.get("automation_preferences") or {}).get(
        "automation_level", "Human-in-the-loop"
    )
    scope = _build_scope_from_use_cases(target_use_cases)
    plan = {
        "recommended_mvp_use_case": target_use_cases[0]["use_case"]
        if target_use_cases
        else "Invoice compliance review (AP)",
        "second_priority_use_case": target_use_cases[1]["use_case"]
        if len(target_use_cases) > 1
        else None,
        "mvp_scope": scope["mvp_scope"],
        "out_of_scope": scope["out_of_scope"],
        "required_sample_data": scope["required_sample_data"],
        "estimated_iterations": 3,
        "success_metrics": scope["success_metrics"],
        "automation_level": automation_pref,
    }
    store.set_value("mvp_definition", plan)
    return p.ToolResult(plan)


def _fill_defaults(spec: Dict[str, Any]) -> Dict[str, Any]:
    filled = get_spec_template()
    filled = merge_dicts(filled, spec)

    auto = filled.get("automation_preferences", {})
    if auto.get("automation_level") == "Autopost with approvals":
        reqs = filled.setdefault("rules_and_policies", {}).setdefault(
            "compliance_requirements", []
        )
        if "Audit log required" not in reqs:
            reqs.append("Audit log required")
    return filled


@p.tool
async def finalize_spec(context: p.ToolContext, spec: Dict[str, Any]) -> p.ToolResult:
    store = _ensure_store(context)
    store.merge(spec)
    filled = _fill_defaults(store.snapshot())
    outputs = persist_outputs(filled, session_id=context.session_id)

    markdown = filled.get("final_output", {}).get("markdown")
    final_output = {
        "json_path": outputs["json"],
        "markdown_path": outputs["markdown"],
        "spec": filled,
    }
    if markdown:
        final_output["markdown"] = markdown

    store.set_value("final_output", final_output)
    return p.ToolResult(final_output)
