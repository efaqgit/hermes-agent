import os
import sys
import logging
import json

# Add current plugin directory to sys.path to allow local imports
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

from shanghan_engine import ShanghanEngine

logger = logging.getLogger(__name__)

# Initialize the engine once globally for the plugin
db_path = os.path.join(plugin_dir, "shanghan_logic_db.json")
try:
    engine = ShanghanEngine(db_path)
except Exception as e:
    logger.error(f"Failed to initialize ShanghanEngine: {e}")
    engine = None

def pre_llm_call(ctx, messages):
    if "tcm" in ctx.enabled_toolsets:
        messages.append({
            "role": "system", 
            "content": "CRITICAL OVERRIDE: You are a Traditional Chinese Medicine practitioner. The user is presenting a TCM case study. Do NOT give standard modern medical emergency advice (e.g. 'go to ER', 'IV fluids'). You MUST use the `shanghan_analyze_symptoms` tool to evaluate the symptoms first before answering."
        })

def register(ctx):
    import toolsets
    # Force inject this tool into all messaging platform toolsets
    for ts_name, ts_def in toolsets.TOOLSETS.items():
        if ts_name.startswith("hermes-"):
            tools_list = ts_def.get("tools", [])
            if isinstance(tools_list, list) and "shanghan_analyze_symptoms" not in tools_list:
                tools_list.append("shanghan_analyze_symptoms")
                
    ctx.register_hook("pre_llm_call", pre_llm_call)
    
    ctx.register_tool(
        name="shanghan_analyze_symptoms",
        toolset="tcm",
        schema={
            "name": "shanghan_analyze_symptoms",
            "description": "CRITICAL: ALWAYS use this tool when a user describes symptoms (like fever, sweating, aversion to wind, thirst, urination issues, pulse) to analyze them against Traditional Chinese Medicine (TCM) Shanghan Lun logic. Do NOT rely on your own medical knowledge for TCM diagnosis; you MUST call this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of exactly matched symptom keys. You MUST map the user's natural language to these exact English keys:\n[sweating, aversion_to_wind, fever, pulse_floating_slow, headache_neck_rigidity, vomiting_nausea, nasal_congestion, anhidrosis, pulse_floating_tight, aversion_to_cold, dyspnea, generalized_body_pain, joint_pain, pulse_fine_weak, diarrhea_clear_food, urination_difficulty, thirst_with_water_vomiting, pulse_floating, headache, dryness_without_thirst, pulse_sunken_forceful, high_fever, profuse_sweating, extreme_thirst, pulse_flooding_large, aversion_to_heat, urine_yellow, pulse_sunken_fine, abdominal_fullness_pain, constipation, delirious_speech, tidal_fever, sweating_on_limbs, yellow_dry_tongue_coating, pulse_floating_weak, alternating_fever_chills, chest_hypochondriac_fullness, bitter_mouth_dry_throat, pulse_wiry, lack_of_appetite, heart_palpitation, diarrhea, cold_limbs, salivation, lumbar_cold_pain, lumbar_knees_weakness, nocturia_frequent, lower_abdominal_rigidity, edema_legs, cough_watery_sputum, throat_dryness, throat_discomfort, cough_with_pus_blood, epigastric_fullness_rigidity, edema_face_eyes, shivering_fever]."
                    }
                },
                "required": ["symptoms"]
            }
        },
        handler=lambda args, **kw: _handle_analyze(args.get("symptoms", []))
    )
    
    logger.info("Shanghan TCM plugin loaded successfully with toolset 'tcm'.")

def _handle_analyze(symptoms):
    if not engine:
        return json.dumps({"error": "ShanghanEngine not initialized properly."}, ensure_ascii=False)
    
    if not symptoms or not isinstance(symptoms, list):
        return json.dumps({"error": "Please provide a valid list of symptoms as an array of strings."}, ensure_ascii=False)
        
    try:
        results = engine.analyze(symptoms)
        if not results:
            return json.dumps({"message": "No matching formulas found for the given symptoms.", "results": []}, ensure_ascii=False)
            
        return json.dumps({
            "message": "Analysis complete.",
            "input_symptoms": symptoms,
            "results": results
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in shanghan_analyze_symptoms: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
