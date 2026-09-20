"""
Main CLI entrypoint for the Kubernetes FSM Agentic Loop.
"""
import argparse
import json
import logging
import os
import subprocess
import sys
from src.core.context import AgentContext, AgentState
from src.core.fsm_runner import FSMRunner
from src.handlers.triage_handler import TriageStateHandler
from src.handlers.investigate_handler import InvestigateStateHandler
from src.handlers.remediation_handler import RemediationStateHandler
from src.handlers.verify_handler import VerifyStateHandler
from src.clients.local_ollama_client import LocalOllamaClient
from src.clients.mcp_stdio_gateway import DirectMCPToolGateway
from src.clients.live_kubectl_gateway import LiveKubectlGateway
from tests.e2e.test_k8s_self_healing_e2e import ScriptedE2ELLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_windows_gateway_ip() -> str:
    """Discovers the Windows host IP address from WSL environment."""
    try:
        res = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, check=True)
        tokens = res.stdout.strip().split()
        if len(tokens) >= 3 and tokens[0] == "default" and tokens[1] == "via":
            return tokens[2]
    except Exception:
        pass
    return "127.0.0.1"


def resolve_endpoint(endpoint_arg: str) -> str:
    """Resolves the inference endpoint, defaulting to the Windows WSL gateway if needed."""
    if endpoint_arg:
        return endpoint_arg
    gateway_ip = get_windows_gateway_ip()
    return f"http://{gateway_ip}:11434/api/chat"


def parse_args():
    parser = argparse.ArgumentParser(description="Kubernetes FSM Self-Healing Agent")
    parser.add_argument("--namespace", default="production", help="Target Kubernetes namespace")
    parser.add_argument("--model", default="llama3.1:latest", help="Local LLM model name")
    parser.add_argument("--endpoint", default="", help="Custom model endpoint")
    parser.add_argument("--mock-llm", action="store_true", help="Run with scripted mock reasoning engine")
    parser.add_argument("--live-k8s", action="store_true", help="Run against a live Kubernetes cluster using kubectl")
    parser.add_argument("--kubeconfig", default="/etc/rancher/k3s/k3s.yaml", help="Path to kubeconfig file")
    return parser.parse_args()


def main():
    args = parse_args()
    endpoint = resolve_endpoint(args.endpoint)

    print("=" * 70)
    print("  KUBERNETES FSM AGENTIC SELF-HEALING ENGINE")
    print(f"  Target Namespace: {args.namespace}")
    print(f"  Cluster Mode:     {'Live K8s Cluster (kubectl)' if args.live_k8s else 'In-Memory Simulation'}")
    print(f"  Inference Mode:   {'Deterministic Mock LLM' if args.mock_llm else f'Local Model ({args.model} @ {endpoint})'}")
    print("=" * 70)

    if args.mock_llm:
        llm_client = ScriptedE2ELLM()
    else:
        llm_client = LocalOllamaClient(endpoint=endpoint, model=args.model)

    if args.live_k8s:
        tool_gateway = LiveKubectlGateway(kubeconfig=args.kubeconfig)
    else:
        tool_gateway = DirectMCPToolGateway()

    handlers = {
        AgentState.TRIAGE: TriageStateHandler(),
        AgentState.INVESTIGATE: InvestigateStateHandler(),
        AgentState.REMEDIATE: RemediationStateHandler(),
        AgentState.VERIFY: VerifyStateHandler()
    }

    runner = FSMRunner(
        llm_client=llm_client,
        tool_gateway=tool_gateway,
        handlers=handlers,
        global_max_steps=12
    )

    context = AgentContext(target_namespace=args.namespace)

    try:
        final_context = runner.run(context)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Execution interrupted: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print(f"  EXECUTION COMPLETE: Final State: {final_context.state.name}")
    print(f"  Total Steps: {final_context.step_count}")
    print("=" * 70)

    print("\n--- Diagnostic Blackboard ---")
    print(json.dumps(final_context.blackboard, indent=2))

    print("\n--- Execution Audit Trail ---")
    for step in final_context.execution_history:
        print(f"Step {step['step']}: {step['from_state']} ➔ {step['to_state']} | Action: {step['decision'].get('action')} | Reason: {step['decision'].get('reasoning')}")


if __name__ == "__main__":
    main()
