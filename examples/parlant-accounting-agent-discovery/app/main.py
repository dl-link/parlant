from __future__ import annotations

import asyncio
from pathlib import Path

import parlant.sdk as p

from app import config
from app.tools import spec_tools


async def add_guidelines(agent: p.Agent) -> None:
    await agent.create_guideline(
        condition="The user asks for tax or legal advice",
        action="Politely decline and refocus on gathering requirements",
    )
    await agent.create_guideline(
        condition="The user requests fully automatic posting",
        action="Confirm approval rules, audit logs, and escalation paths before agreeing",
    )
    await agent.create_guideline(
        condition="The user seems unsure which automation level to choose",
        action=(
            "Offer two options: conservative (human-in-the-loop) and aggressive"
            " (autopost with approvals)."
        ),
    )
    await agent.create_guideline(
        condition="After each answer is provided",
        action=(
            "Call save_answer to persist the field, then summarize and ask for"
            " confirmation before moving on."
        ),
        tools=[spec_tools.save_answer],
    )


async def create_discovery_journey(agent: p.Agent) -> p.Journey:
    journey = await agent.create_journey(
        title="Agent Discovery (Accounting)",
        description="Interviews a customer to design an accounting agent",
        conditions=[
            "User wants help deciding what accounting agent to build",
            "User wants automation suggestions for finance",
        ],
    )

    intro = await journey.initial_state.transition_to(
        chat_state=(
            "I’ll ask a few short questions to define your ideal accounting agent."
            " At the end, I’ll produce a clear Agent Requirements Spec + MVP plan."
            " First: which accounting area is most urgent for you?"
            " Choices: Accounts Payable (Invoices), Bank Reconciliation, Month-End"
            " Close, GST/VAT, Reporting & Insights, Other."
        )
    )

    collect_stack = await intro.target.transition_to(
        chat_state=(
            "What system do you use today for accounting (e.g., Xero, MYOB,"
            " QuickBooks, Excel-only)? Use save_answer with"
            " key='current_stack.accounting_system'."
        )
    )
    await collect_stack.target.transition_to(
        tool_state=spec_tools.save_answer,
        condition="Persist accounting system",
    )

    pain_points = await collect_stack.target.transition_to(
        chat_state=(
            "What are your top 3 pain points you want this agent to solve?"
            " (e.g., time, errors, compliance, staffing, slow month-end)."
            " Save to problem_statement.top_pain_points."
        )
    )
    await pain_points.target.transition_to(
        tool_state=spec_tools.save_answer,
        condition="Persist pain points",
    )

    volume = await pain_points.target.transition_to(
        chat_state=(
            "Roughly how much volume do you handle per month? (invoices/month,"
            " bank transactions/month, etc.) Provide any numbers you know."
            " Save to problem_statement.volume_metrics."
        )
    )
    await volume.target.transition_to(
        tool_state=spec_tools.save_answer,
        condition="Persist volume metrics",
    )

    use_case_tool = await volume.target.transition_to(
        tool_state=spec_tools.recommend_agent_types,
    )

    confirm_use_case = await use_case_tool.target.transition_to(
        chat_state=(
            "Based on what you told me, here are the top use cases I recommend."
            " Which ONE should we prioritize for the MVP, and which ONE is"
            " second priority? Save to mvp_definition.recommended_mvp_use_case"
            " and mvp_definition.second_priority_use_case."
        )
    )
    await confirm_use_case.target.transition_to(
        tool_state=spec_tools.save_answer,
        condition="Persist MVP priority",
    )

    automation_level = await confirm_use_case.target.transition_to(
        chat_state=(
            "How automated should it be? Choose one: (1) Advice only,"
            " (2) Human-in-the-loop (suggest + approve),"
            " (3) Autopost with approvals."
            " Save to automation_preferences.automation_level."
        )
    )
    await automation_level.target.transition_to(
        tool_state=spec_tools.save_answer,
        condition="Persist automation preference",
    )

    risk_controls = await automation_level.target.transition_to(
        chat_state=(
            "Any rules or controls it must follow? For example: approval"
            " thresholds, GST rules, audit logs, or ‘never post automatically’."
            " Save to rules_and_policies.compliance_requirements."
        )
    )
    await risk_controls.target.transition_to(
        tool_state=spec_tools.save_answer,
        condition="Persist compliance requirements",
    )

    integration = await risk_controls.target.transition_to(
        chat_state=(
            "Do you need it to write back into your accounting system (create"
            " bills/journals), or is a review + export report enough for now?"
            " Save to integration_requirements.needs_writeback."
        )
    )
    await integration.target.transition_to(
        tool_state=spec_tools.save_answer,
        condition="Persist integration need",
    )

    mvp_plan = await integration.target.transition_to(
        tool_state=spec_tools.generate_mvp_plan,
    )

    finalize = await mvp_plan.target.transition_to(
        tool_state=spec_tools.finalize_spec,
    )

    await finalize.target.transition_to(
        chat_state=(
            "Here is your Agent Requirements Spec and MVP plan. Please confirm"
            " if this is accurate or tell me what to change."
        )
    )

    return journey


async def main() -> None:
    Path(config.project_config.parlant_home).mkdir(parents=True, exist_ok=True)
    async with p.Server(port=config.server_config.port) as server:
        agent = await server.create_agent(
            name="AccountingAgentDesigner",
            description=(
                "A discovery assistant that interviews customers to define"
                " requirements for an accounting-focused AI agent."
            ),
            tags=["discovery", "accounting", "requirements", "agent-design"],
            provider_profile=config.server_config.provider_profile,
        )

        await add_guidelines(agent)
        await create_discovery_journey(agent)

        print(
            "Parlant server running on port"
            f" {config.server_config.port}. Playground:"
            f" {config.server_config.local_playground_url}"
        )
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
