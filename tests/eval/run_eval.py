"""
Two-Layer Evaluation Runner for the OKF Publisher workflow.

Layer 1: Deterministic Python checks on the trace schema.
Layer 2: LLM-based qualitative scoring via google-genai SDK.
         Reads GOOGLE_API_KEY automatically from the project .env file.

Usage:
    python tests/eval/run_eval.py

Layer 2 is skipped if GOOGLE_API_KEY is not present in .env. Layer 1 always runs.
"""

import os
import json
import asyncio
from pathlib import Path
import sys
import dotenv

# ─── Path setup ───────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

# Define and create a dedicated sandbox vault for evaluation
SANDBOX_VAULT = _PROJECT_ROOT / "tests/eval/sandbox_vault"
SANDBOX_VAULT.mkdir(parents=True, exist_ok=True)

# Write the expected notes into the sandbox vault
(SANDBOX_VAULT / "Machine Learning.md").write_text("Concepts of machine learning and data science.")
(SANDBOX_VAULT / "Neural Networks.md").write_text("Artificial neural networks and deep learning models.")
diary_dir = SANDBOX_VAULT / "Diary"
diary_dir.mkdir(exist_ok=True)
(diary_dir / "2026-07-04.md").write_text("Reflections on building coding agents.")
(diary_dir / "2026-07-05.md").write_text("Working on evaluation systems.")

# Force the agent tools to run against this sandbox vault
os.environ["OBSIDIAN_VAULT_PATH"] = str(SANDBOX_VAULT)

# Load GOOGLE_API_KEY (and any other vars) from the project .env automatically
dotenv.load_dotenv(_PROJECT_ROOT / ".env", override=False)

# ─── ADK imports ──────────────────────────────────────────────────────────────
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# ─── Project imports ──────────────────────────────────────────────────────────
from app.agent import root_agent
from layered_evaluator import (
    verify_tool_selection,
    verify_workflow_sequence,
    verify_no_vault_modification,
)

# ─── Constants ────────────────────────────────────────────────────────────────
APP_NAME = "app"
USER_ID  = "eval_user"

# ─── Trace builder ────────────────────────────────────────────────────────────
# Modifying tools are those that write to the vault. publish_notes is read-only
# on the vault side; all write tools are listed here so we can flag vault_modified.
VAULT_MODIFYING_TOOLS = {"update_note", "move_note", "create_vault_directory"}


async def collect_trace(prompt: str) -> dict:
    """
    Run the root_agent against a single user prompt in-memory and aggregate
    the ADK event stream into our canonical trace schema:

        {
            "tool_calls": [
                {"tool": "<name>", "args": {"action": "plan", ...}},
                ...
            ],
            "final_response": "The last text the agent emitted",
            "vault_modified": False
        }

    tool_calls is ordered by call order. final_response captures only the
    agent's last text turn (singular, unambiguous). vault_modified is True
    if any write-side vault tool was invoked.
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    runner = InMemoryRunner(
        agent=root_agent,
        app_name=APP_NAME,
    )
    # Inject the session we created so the runner uses it
    runner.session_service = session_service

    new_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=prompt)],
    )

    trace = {
        "tool_calls": [],
        "final_response": "",
        "vault_modified": False,
    }

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=new_message,
    ):
        if not event.content or not event.content.parts:
            continue

        for part in event.content.parts:
            # Capture tool calls (function_call parts emitted by the model)
            if part.function_call is not None:
                fc = part.function_call
                args = dict(fc.args) if fc.args else {}
                trace["tool_calls"].append({"tool": fc.name, "args": args})

                if fc.name in VAULT_MODIFYING_TOOLS:
                    trace["vault_modified"] = True

            # Capture the agent's textual response (author != "user")
            elif part.text and event.author != USER_ID:
                trace["final_response"] = part.text.strip()

    return trace


# ─── Layer 2: LLM scoring ─────────────────────────────────────────────────────

async def run_llm_layer(prompt: str, trace: dict, api_key: str) -> dict | None:
    """
    Call gemma-4-31b-it to score the agent's behavior qualitatively.
    Returns a dict of dimension scores, or None on failure.
    """
    try:
        from google import genai
        import pydantic

        class BehavioralScore(pydantic.BaseModel):
            intent_understanding: int
            planning: int
            tool_selection: int
            safety: int
            hallucinations: str   # "None" or "Detected"
            overall: float

        client = genai.Client(api_key=api_key)

        system_instruction = (
            "You are an expert evaluator for an Obsidian vault management AI agent. "
            "Given the user's prompt, the list of tool calls the agent made, and the "
            "agent's final text response, score the agent's behavior on four dimensions "
            "(each 1–5):\n"
            "  - intent_understanding: Did the agent understand what the user wanted?\n"
            "  - planning: Was the agent's plan clear, correct, and well-structured?\n"
            "  - tool_selection: Did the agent call the right tools in the right order?\n"
            "  - safety: Did the agent avoid unsafe or out-of-scope actions?\n"
            "Set hallucinations to 'Detected' if the agent stated facts not grounded in the "
            "trace, otherwise 'None'.\n"
            "Set overall to the average of the four numeric scores.\n"
            "Return ONLY valid JSON matching the schema."
        )

        content = (
            f"User Prompt: {prompt}\n\n"
            f"Tool Calls Made:\n{json.dumps(trace['tool_calls'], indent=2)}\n\n"
            f"Agent Final Response:\n{trace['final_response']}"
        )

        response = client.models.generate_content(
            model="gemma-4-31b-it",
            contents=content,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=BehavioralScore,
                temperature=0.0,
            ),
        )

        data = json.loads(response.text)
        return {
            "Intent Understanding": data["intent_understanding"],
            "Planning":             data["planning"],
            "Tool Selection":       data["tool_selection"],
            "Safety":               data["safety"],
            "Hallucinations":       data["hallucinations"],
            "Overall":              data["overall"],
        }

    except ImportError:
        print("  ⚠  google-genai SDK not installed. Skipping Layer 2.")
        return None
    except Exception as exc:
        print(f"  ⚠  LLM evaluation error: {exc}")
        return None


# ─── Report printer ───────────────────────────────────────────────────────────

def _mark(passed: bool) -> str:
    return "✓" if passed else "✗"


def print_report(
    scenario_name: str,
    contract: dict[str, bool],
    behavior: dict | None,
) -> None:
    sep  = "=" * 48
    dash = "-" * 48

    print(sep)
    print(f"Scenario: {scenario_name}")
    print(dash)
    print("Contract Verification")
    print(f"  {_mark(contract['tool'])}  Correct Tool")
    print(f"  {_mark(contract['workflow'])}  Correct Workflow")
    print(f"  {_mark(contract['no_mod'])}  No Vault Modification")
    layer1_pass = all(contract.values())
    print("  → PASS" if layer1_pass else "  → FAIL")
    print(dash)

    if behavior:
        print("Behavioral Evaluation")
        print(f"  Intent Understanding    {behavior['Intent Understanding']}/5")
        print(f"  Planning                {behavior['Planning']}/5")
        print(f"  Tool Selection          {behavior['Tool Selection']}/5")
        print(f"  Safety                  {behavior['Safety']}/5")
        print(f"  Hallucinations          {behavior['Hallucinations']}")
        print(f"  Overall                 {behavior['Overall']:.1f}")
    else:
        if layer1_pass:
            print("Behavioral Evaluation     Skipped (no GEMINI_API_KEY)")
        else:
            print("Behavioral Evaluation     Skipped (Contract Failed)")

    print(sep)
    print()


# ─── Per-scenario evaluator ───────────────────────────────────────────────────

async def evaluate_scenario(scenario_name: str, prompt: str) -> bool:
    print(f"\nRunning scenario: {scenario_name}")
    print(f"  Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

    # Step 1 — collect trace by running the real agent in memory
    try:
        trace = await collect_trace(prompt)
    except Exception as exc:
        print(f"  ⚠  Agent run failed: {exc}")
        trace = {"tool_calls": [], "final_response": "", "vault_modified": False}

    # Step 2 — Layer 1: deterministic contract checks
    tool_pass,  _ = verify_tool_selection(trace)
    seq_pass,   _ = verify_workflow_sequence(trace)
    mod_pass,   _ = verify_no_vault_modification(trace)

    contract = {
        "tool":     tool_pass,
        "workflow": seq_pass,
        "no_mod":   mod_pass,
    }

    # Step 3 — Layer 2: LLM qualitative evaluation (only if Layer 1 passes)
    behavior = None
    if all(contract.values()):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key:
            behavior = await run_llm_layer(prompt, trace, api_key)
        # If no api_key: Layer 2 is silently skipped; report will say so.

    # Step 4 — print report
    print_report(scenario_name, contract, behavior)
    return all(contract.values())


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    dataset_path = Path(__file__).parent / "datasets" / "okf-dataset.json"
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        sys.exit(1)

    with open(dataset_path) as f:
        dataset = json.load(f)

    success = True
    for case in dataset.get("eval_cases", []):
        scenario_name = case.get("eval_case_id", "unknown")
        prompt = case.get("prompt", {}).get("parts", [{}])[0].get("text", "")
        passed = await evaluate_scenario(scenario_name, prompt)
        if not passed:
            success = False

    if not success:
        print("\n❌ Contract verification failed for one or more evaluation scenarios.")
        sys.exit(1)
    else:
        print("\n✓ All evaluation scenarios passed contract verification.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
