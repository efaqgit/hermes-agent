import sys
from run_agent import AIAgent

# The toolset name is "tcm", let's use it. It's a plugin toolset so AIAgent should pick it up if discovery is run.
agent = AIAgent(
    enabled_toolsets=["tcm"],
    quiet_mode=False
)

msg = "My friend Eva 現在發燒、一直流汗、很怕吹風。可是奇怪的是，我非常口渴，喝水下去馬上就吐出來，而且尿不太出來。"
print("Sending message to agent...")
res = agent.run_conversation(user_message=msg)
print("\n--- AGENT RESPONSE ---")
print(res)
