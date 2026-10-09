import unreal

from agent_tools import registration

registration.register()

# A backgrounded editor throttles to ~3 fps: every MCP call takes ~1 s and PIE physics runs at
# 3 fps while the agent's terminal has focus. Turn that off for this session only. The per-user
# EditorSettings.ini usually stores the flag explicitly, so a project ini can't override it.
_perf = unreal.get_default_object(unreal.load_class(None, "/Script/UnrealEd.EditorPerformanceSettings"))
unreal.ToolsetLibrary.set_object_properties(_perf, '{"bThrottleCPUWhenNotForeground": false}')
