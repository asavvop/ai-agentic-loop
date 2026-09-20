# Kubernetes FSM Agentic Loop & Self-Healing Engine

An enterprise-grade, Finite State Machine (FSM) driven agentic loop tailored for Kubernetes log diagnostics and autonomous self-healing. Built with strict adherence to **SOLID design principles**, **Clean Code practices**, **Test-Driven Development (TDD)**, and modular state handlers.

---

## Key Features

1. **Deterministic State Transitions (FSM)**:
   - Eliminates hallucination loops, infinite loops, and unguided reasoning common in naive ReAct loops.
   - Bounded turn budgets per state and global execution safeguards.
2. **Dual Mode Execution (Live Cluster + Offline Simulation)**:
   - **Live Mode**: Directly diagnoses and heals live pods in a real Kubernetes / K3s cluster via `kubectl`.
   - **Simulation Mode**: In-memory telemetry simulator for fast offline development and testing.
3. **Gated Tool Scoping & Parameter Filtering**:
   - Destructive or mutating remediation actions (`patch_deployment_resources`, `restart_deployment`) can only execute in the `REMEDIATE` state.
   - Robust Adapter Pattern with `inspect.signature` parameter filtering.
4. **Local Model Native (Zero Docker Runner Dependency)**:
   - Directly connects to local Ollama inference (`llama3.1:latest`) over HTTP with auto-detection of the WSL Windows gateway.
5. **Decoupled Architecture (SOLID)**:
   - High-level engine depends strictly on abstractions (`ILLMClient`, `IToolGateway`).
   - 100% testable via unit and E2E mocks without requiring active clusters or live LLMs.

---

## State Machine Workflow

```mermaid
stateDiagram-v2
    [*] --> TRIAGE : Cluster Telemetry Trigger
    
    TRIAGE --> INVESTIGATE : Unhealthy Workload Detected
    TRIAGE --> RESOLVED : All Pods Healthy (No Action Needed)
    
    INVESTIGATE --> REMEDIATE : Root Cause Isolated (OOM / Heap Space)
    INVESTIGATE --> FAILED : Max Budget Exceeded / Diagnosis Unknown
    
    REMEDIATE --> VERIFY : Remediation Applied
    REMEDIATE --> FAILED : Remediation Execution Failed
    
    VERIFY --> RESOLVED : Ready Replicas == Desired & Status == Healthy
    VERIFY --> INVESTIGATE : Workload Still Degraded (Retry)
    
    RESOLVED --> [*]
    FAILED --> [*]
```

---

## Directory Structure

```
code/ai-agentic-loop/
├── k8s/
│   └── failing_payment_service.yaml # Crashing pod deployment manifest (OOMKilled)
├── src/
│   ├── core/
│   │   ├── context.py               # AgentContext, AgentState, Blackboard
│   │   ├── interfaces.py            # ILLMClient, IToolGateway, ToolResult (DIP)
│   │   └── fsm_runner.py            # Core FSM Engine with loop budgets
│   ├── handlers/
│   │   ├── base_handler.py          # Abstract BaseStateHandler (LSP, OCP)
│   │   ├── triage_handler.py        # Triage & Workload Assessment
│   │   ├── investigate_handler.py   # Log analysis & root cause isolation
│   │   ├── remediation_handler.py   # Gated self-healing execution
│   │   └── verify_handler.py        # Post-remediation health validation
│   ├── clients/
│   │   ├── local_ollama_client.py   # Native local HTTP inference client
│   │   ├── mcp_stdio_gateway.py     # MCP Gateway adapter
│   │   └── live_kubectl_gateway.py  # Live cluster kubectl tool gateway
│   └── server/
│       ├── k8s_telemetry.py         # Telemetry repository & simulation model
│       └── mcp_k8s_server.py        # FastMCP Server with OpenTelemetry
├── tests/                           # 1-to-1 Mirrored Test Structure
│   ├── core/
│   │   ├── test_context.py
│   │   └── test_fsm_runner.py
│   ├── handlers/
│   │   ├── test_triage_handler.py
│   │   ├── test_investigate_handler.py
│   │   ├── test_remediation_handler.py
│   │   └── test_verify_handler.py
│   ├── clients/
│   │   └── test_local_ollama_client.py
│   └── e2e/
│       └── test_k8s_self_healing_e2e.py
├── main.py                          # CLI Entrypoint
└── README.md
```

---

## Usage

### 1. Run Automated Tests (TDD / E2E)
```bash
python -m pytest tests/ -v
```

### 2. Run Autonomous Simulation with Mock LLM
```bash
python main.py --mock-llm --namespace production
```

### 3. Run Autonomous Simulation with Local Ollama
```bash
python main.py --model llama3.1:latest
```

### 4. Run Against Live Kubernetes / K3s Cluster
```bash
# 1. Deploy failing workload
kubectl apply -f k8s/failing_payment_service.yaml

# 2. Run live self-healing agent
python main.py --live-k8s --namespace production --model llama3.1:latest
```
