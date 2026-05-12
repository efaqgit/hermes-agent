"""Standalone Traditional Chinese Medicine (TCM) Shanghan Terminal Server.

An independent FastAPI server running on port 9300.
"""

import sys
import os
import json
import logging
import uvicorn
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Path resolution to import local modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from plugins.shanghan.shanghan_engine import ShanghanEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ShanghanDashboard")

app = FastAPI(
    title="Standalone TCM Shanghan Terminal",
    description="Independent Dashboard for Traditional Chinese Medicine (Shanghan Lun) logic matching.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(PLUGIN_DIR, "static")

# Ensure static directory exists
os.makedirs(STATIC_DIR, exist_ok=True)

# Initialize Engine
db_path = os.path.join(PLUGIN_DIR, "shanghan_logic_db.json")
try:
    engine = ShanghanEngine(db_path)
except Exception as e:
    logger.error(f"Failed to initialize ShanghanEngine: {e}")
    engine = None

class AnalyzeRequest(BaseModel):
    symptoms: List[str]

class ExtractRequest(BaseModel):
    description: str

SYMPTOM_MAP = {
    'abdominal_fullness_pain': '腹滿痛',
    'alcoholic_constitution': '嗜酒體質',
    'alternating_fever_chills': '寒熱往來',
    'anhidrosis': '無汗',
    'aversion_to_cold': '惡寒',
    'aversion_to_heat': '惡熱',
    'aversion_to_wind': '惡風',
    'bitter_mouth_dry_throat': '口苦咽乾',
    'chest_hypochondriac_fullness': '胸脇苦滿',
    'cold_limbs': '四肢厥冷',
    'constipation': '便秘',
    'cough_watery_sputum': '咳吐清水',
    'cough_with_fever_and_shivering': '咳而發熱惡寒',
    'cough_with_pus_blood': '咳吐膿血',
    'cough_with_yin_deficiency_dryness': '陰虛燥咳',
    'delirious_speech': '譫語',
    'diarrhea': '下利',
    'diarrhea_clear_food': '下利清穀',
    'diarrhea_clear_food_with_spleen_collapse': '脾陽虛衰下利清穀',
    'diarrhea_due_to_spleen_deficiency': '脾虛下利',
    'diarrhea_without_dry_feces': '熱結旁流',
    'dryness_without_thirst': '口乾不渴',
    'dyspnea': '氣喘',
    'edema_face_eyes': '頭面浮腫',
    'edema_legs': '下肢浮腫',
    'epigastric_fullness_rigidity': '心下痞硬',
    'extreme_thirst': '極度口渴',
    'extreme_thirst_with_dry_mouth': '口乾極渴',
    'fever': '發熱',
    'fever_with_yin_deficiency': '陰虛發熱',
    'generalized_body_pain': '周身疼痛',
    'headache': '頭痛',
    'headache_neck_rigidity': '頭痛項強',
    'heart_palpitation': '心悸',
    'heavy_water_phlegm_in_lung': '痰飲停肺',
    'high_fever': '高熱',
    'high_fever_with_extreme_thirst': '高熱大渴',
    'joint_pain': '關節疼痛',
    'lack_of_appetite': '不欲食',
    'lower_abdominal_rigidity': '少腹急結',
    'lumbar_cold_pain': '腰部冷痛',
    'lumbar_knees_weakness': '腰膝痠軟',
    'nasal_congestion': '鼻鳴',
    'no_qi_rush_after_purging': '下後氣不衝',
    'nocturia_frequent': '夜尿頻多',
    'profuse_sweating': '大汗出',
    'profuse_sweating_with_亡陽': '大汗亡陽',
    'pulse_fine_weak': '脈細弱',
    'pulse_floating': '脈浮',
    'pulse_floating_slow': '脈浮緩',
    'pulse_floating_tight': '脈浮緊',
    'pulse_floating_weak': '脈浮弱',
    'pulse_flooding_large': '脈洪大',
    'pulse_sunken_fine': '脈沉細',
    'pulse_sunken_forceful': '脈沉有力',
    'pulse_wiry': '脈弦',
    'red_tongue_scanty_coating': '舌紅少苔',
    'salivation': '多涎',
    'severe_diarrhea_clear_food': '完穀不化',
    'severe_interior_excess_with_dry_feces': '內實燥屎',
    'severe_postpartum_weakness': '產後大虛',
    'severe_yin_yang_deficiency_with_limb_spasms': '陰陽兩虛拘急',
    'shivering_fever': '惡寒發熱',
    'sweating': '汗出',
    'sweating_on_limbs': '手足汗出',
    'thirst_with_water_vomiting': '水逆(喝水即吐)',
    'throat_discomfort': '咽喉不適',
    'throat_dryness': '咽乾',
    'tidal_fever': '日晡潮熱',
    'tongue_red_with_no_coating': '舌紅無苔',
    'urination_difficulty': '小便不利',
    'urine_yellow': '尿黃',
    'vomiting_nausea': '嘔逆',
    'yellow_dry_tongue_coating': '舌苔黃燥',
    'yin_yang_collapse_cold_limbs': '陰陽暴脫四肢冰冷',
    'abdominal_mass': '腹中包塊/癥瘕',
    'blood_stasis_tongue': '舌有瘀點瘀斑',
    'chest_heat_irritability': '心中懊憹/虛煩',
    'dark_circles_under_eyes': '眼眶黯黑',
    'difficult_sticky_defecation': '大便黏滯不爽',
    'generalized_edema': '全身水腫',
    'menstrual_blood_dark_clots': '經血暗紅夾塊',
    'menstrual_irregularity': '月經不調',
    'postpartum_abdominal_pain': '產後腹痛',
    'shortness_of_breath_exertion': '動則氣短',
    'skin_scaling_dryness': '肌膚甲錯',
    'spontaneous_sweating_yang_def': '漏汗不止/自汗',
    'splash_sound_epigastric': '心下振水音',
    'stabbing_lower_abdomen': '少腹刺痛拒按',
    'throat_obstruction_globus': '咽中如有炙臠',
    'throbbing_below_heart': '心下逆滿/氣上衝',
    'uterine_bleeding_leakage': '崩漏下血'
}

# ─── FRONTEND STATIC ROUTING ──────────────────────────────────────────

@app.get("/")
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Frontend static/index.html is missing.</h2>")

@app.get("/{filename}")
async def get_static(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# ─── API ENDPOINTS ───────────────────────────────────────────────────

@app.get("/api/symptoms")
async def get_symptoms():
    """Retrieve the list of all available symptoms with Chinese translation."""
    result = []
    for en_key, zh_label in SYMPTOM_MAP.items():
        result.append({
            "key": en_key,
            "label": zh_label
        })
    # Sort alphabetically by Chinese pinyin/stroke conceptually, or just return
    return {"success": True, "data": result}

@app.post("/api/analyze")
async def analyze_symptoms(req: AnalyzeRequest):
    """Run Shanghan Engine analysis and use LLM to summarize."""
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized.")
        
    symptoms = req.symptoms
    if not symptoms:
        raise HTTPException(status_code=400, detail="No symptoms provided.")
        
    results = engine.analyze(symptoms)
    
    # 2. Get LLM synthesis using Hermes Auxiliary Client
    llm_analysis = ""
    try:
        if results:
            top_formulas = [f"{r['name']} (分數: {r['score']})" for r in results[:3]]
            
            zh_symptoms = [SYMPTOM_MAP.get(s, s) for s in symptoms]
            
            prompt = f"""請你扮演一位精通《傷寒雜病論》與《金匱要略》的經方派老中醫大師（如胡希恕、曹穎甫）。
患者目前的主要症狀為：{', '.join(zh_symptoms)}。

根據量化引擎比對出來的前幾名方劑為：
{chr(10).join(top_formulas)}

請根據以上資料，用繁體中文給出一段專業、極具臨床指導價值且深入淺出的「大師醫案分析、病機探討、與處方加減化裁指南」。
請特別注意以下「處方加減與變證法」的辨證施治思考：
1. 若最吻合方劑為「桂枝湯」，但患者主訴有「氣喘/咳嗽」，應提示化裁為「桂枝加厚朴杏子湯」。
2. 若最吻合方劑為「理中丸/理中湯」，但患者伴有「嘔吐/噁心」，應提示化裁為「理中加半夏生薑湯」。
3. 若患者有明顯「血瘀（舌有瘀斑、少腹刺痛或肌膚甲錯）」，請特別分析病因病位：是下焦實熱蓄血（桃核承氣湯），還是虛勞乾血（大黃䗪蟲丸），並給予明確的攻補兼施方針。
4. 結合歷史經典醫案（如胡希恕、曹穎甫醫案思考模型），分析其表裡寒熱，給出明確的服用禁忌與調護（如服桂枝湯後喝熱稀粥、避風寒等）。

不需要免責聲明，直接以老中醫大師的口吻進行系統性剖析。輸出格式請使用 Markdown，排版要精美、段落分明。
"""
            from agent.auxiliary_client import call_llm, extract_content_or_reasoning
            response = call_llm(
                task="curator",
                messages=[
                    {"role": "system", "content": "You are a professional Traditional Chinese Medicine practitioner from the Jingfang (Classical Formula) school."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            llm_analysis = extract_content_or_reasoning(response)
        else:
            llm_analysis = "根據您提供的症狀，系統目前無法匹配到完全吻合的經典方劑。建議您重新檢視症狀是否完整，或者這可能屬於較為複雜的變證，需要進一步四診合參。"
    except Exception as e:
        logger.error(f"Failed to generate LLM analysis: {e}")
        llm_analysis = f"*(AI 醫師分析暫時無法使用，請稍後再試。錯誤: {str(e)})*"

    return {
        "success": True,
        "input_symptoms": symptoms,
        "formulas": results,
        "llm_analysis": llm_analysis
    }

@app.post("/api/extract_symptoms")
async def extract_symptoms(req: ExtractRequest):
    """Analyze oral patient description and extract standard symptom keys + clinical questions."""
    description = req.description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="No description provided.")

    try:
        from agent.auxiliary_client import call_llm, extract_content_or_reasoning
        
        # Build prompt listing our standard mapping
        prompt = f"""請你扮演一位精通《傷寒論》與《金匱要略》的中醫大師助手。
你的任務是將病人的口語描述，轉化為具備「六經辨證」價值的標準化結構數據。

【可用標準症狀鍵值清單 (Standard Symptom Map)】:
{json.dumps(SYMPTOM_MAP, ensure_ascii=False)}

【患者口語主訴描述】:
"{description}"

【輸出格式要求】:
請你嚴格輸出 JSON 格式 (不可有額外文字說明，不可包裹在 markdown 區塊內)，格式必須包含且完全一致:
{{
  "extracted_keys": ["fever", "anhidrosis"], // 必須從上述可用標準症狀 Key 清單中挑選，不可自創 Key！若沒有則為空陣列。
  "logic_hints": "一句話說明病機研判與初步懷疑哪一經 (30字以內)",
  "missing_questions": ["精確追問 1", "精確追問 2", "精確追問 3"]
}}

【約束條件】:
1. "extracted_keys" 中填寫的英文 Key 必須與提供標準清單中完全一致！如果主訴中沒有對應標準症狀，不要隨意放入。
2. 對於「虛實、寒熱」等關鍵點（例如：腹痛喜按或拒按、口渴喜冷飲或熱飲）若未提及，必須在 "missing_questions" 中提出追問。
"""
        response = call_llm(
            task="curator",
            messages=[
                {"role": "system", "content": "You are a professional Traditional Chinese Medicine practitioner from the Jingfang (Classical Formula) school."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        llm_response = extract_content_or_reasoning(response)
        
        # Parse JSON defensively
        clean_res = llm_response.strip()
        if clean_res.startswith("```json"):
            clean_res = clean_res[7:]
        elif clean_res.startswith("```"):
            clean_res = clean_res[3:]
        if clean_res.endswith("```"):
            clean_res = clean_res[:-3]
        clean_res = clean_res.strip()
        
        parsed_data = json.loads(clean_res)
        return {
            "success": True,
            "extracted_keys": parsed_data.get("extracted_keys", []),
            "logic_hints": parsed_data.get("logic_hints", ""),
            "missing_questions": parsed_data.get("missing_questions", [])
        }
    except Exception as e:
        logger.error(f"Failed to extract symptoms from description: {e}")
        # Fallback graceful return
        return {
            "success": False,
            "detail": str(e),
            "extracted_keys": [],
            "logic_hints": "AI 提取暫時出現阻礙，請稍後重試。",
            "missing_questions": []
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9300)
