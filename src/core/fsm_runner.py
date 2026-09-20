"""
FSM Execution Engine implementing Dependency Inversion (DIP) and Bounded Loops.
"""
import logging
from typing import Any, Dict, Optional
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ILLMClient, IToolGateway, ToolResult
from src.handlers.base_handler import BaseStateHandler

logger = logging.getLogger("FSMRunner")


class FSMRunner:
    """
    Coordinates state execution, tool dispatching, and deterministic transitions.
    """

    def __init__(
        self,
        llm_client: ILLMClient,
        tool_gateway: IToolGateway,
        handlers: Dict[AgentState, BaseStateHandler],
        global_max_steps: int = 15
    ):
        self._llm_client = llm_client
        self._tool_gateway = tool_gateway
        self._handlers = handlers
        self._global_max_steps = global_max_steps

    def run(self, context: AgentContext) -> AgentContext:
        """Executes the FSM loop until a terminal state is reached."""
        logger.info(f"Starting FSM Loop for namespace: {context.target_namespace}")

        while not context.state.is_terminal:
            if context.step_count >= self._global_max_steps:
                logger.warning(f"Exceeded global max steps ({self._global_max_steps}). Forcing FAILED.")
                context.transition_to(AgentState.FAILED)
                break

            handler = self._handlers.get(context.state)
            if not handler:
                raise ValueError(f"Unregistered state handler for state: {context.state}")

            if context.state_step_count >= context.max_steps_per_state:
                logger.warning(f"Exceeded budget for state {context.state.name}. Forcing FAILED.")
                context.transition_to(AgentState.FAILED)
                break

            current_state = context.state
            context.increment_turn()

            system_prompt = handler.build_system_prompt(context)
            user_prompt = handler.build_user_prompt(context)
            schema = handler.get_response_schema()

            decision = self._llm_client.generate_structured_decision(
                system_prompt, user_prompt, schema
            )

            tool_result = self._dispatch_tool_if_permitted(handler, decision, context)
            if tool_result:
                action_name = decision.get("action")
                context.blackboard[f"last_{action_name}_result"] = tool_result.output

            next_state = handler.evaluate_transition(context, decision, tool_result)
            context.record_step(current_state, next_state, decision, tool_result.output if tool_result else None)
            context.transition_to(next_state)

        logger.info(f"FSM Terminated in state: {context.state.name} after {context.step_count} steps.")
        return context

    def _dispatch_tool_if_permitted(
        self,
        handler: BaseStateHandler,
        decision: Dict[str, Any],
        context: AgentContext
    ) -> Optional[ToolResult]:
        """Safely invokes a tool with contextual argument resolution."""
        action_name = decision.get("action")
        if not action_name or action_name == "none":
            return None

        if action_name not in handler.allowed_tools:
            logger.warning(f"Security Alert: Action '{action_name}' not allowed in state {handler.state.name}")
            return ToolResult(
                success=False,
                output=None,
                error_message=f"Action '{action_name}' unauthorized in state {handler.state.name}"
            )

        args = dict(decision.get("action_args", {}) or {})
        # Contextual fallback for common required arguments
        if "namespace" not in args and context.target_namespace:
            args["namespace"] = context.target_namespace
        if "deployment_name" not in args and context.target_workload:
            args["deployment_name"] = context.target_workload
        if "pod_name" not in args and context.blackboard.get("unhealthy_pods"):
            pods = context.blackboard.get("unhealthy_pods")
            if isinstance(pods, list) and pods:
                args["pod_name"] = pods[0].get("pod_name")

        return self._tool_gateway.execute_tool(action_name, args)
