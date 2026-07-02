from traceshield_method.method.integrations.nemo_adapter import build_nemo_tool_action

try:
    from nemoguardrails.actions import action
except ImportError:
    def action(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


@action(is_system_action=True)
async def traceshield_check_tool_call(
    tool_name: str,
    args: dict | None = None,
    intent_frame: dict | None = None,
    step_id: int = 1,
    observation: str | None = None,
) -> dict:
    checker = build_nemo_tool_action()
    return await checker(tool_name, args, intent_frame, step_id, observation)
