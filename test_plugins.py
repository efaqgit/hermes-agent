import sys
from hermes_cli import plugins
from model_tools import discover_builtin_tools
from tools.registry import registry

print("Discovering tools...")
discover_builtin_tools()

print("\nAll loaded plugins:")
for k, p in plugins._plugin_manager._plugins.items():
    print(f" - {k}")

print("\nRegistered Tools:")
for name, tool in registry.get_all_tools().items():
    print(f" - {name} (toolset: {tool.toolset})")
