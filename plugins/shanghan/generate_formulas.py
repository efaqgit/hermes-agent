#!/usr/bin/env python3
"""Batch-generate Shanghan & Jingui formulas using Hermes auxiliary LLM.

Runs in batches, each batch generates ~15 formulas. Merges into shanghan_logic_db.json.
Usage: python3 generate_formulas.py [--batches N] [--start N]
"""
import json, os, sys, argparse, time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, "shanghan_logic_db.json")
SYMPTOM_MAP_PATH = os.path.join(PLUGIN_DIR, "server.py")

# Load current DB
with open(DB_PATH, "r", encoding="utf-8") as f:
    db = json.load(f)
existing_names = {f["formula_name"] for f in db["formulas"]}

# Load symptom keys from server.py's SYMPTOM_MAP
symptom_keys = []
with open(SYMPTOM_MAP_PATH, "r", encoding="utf-8") as f:
    content = f.read()
    import re
    matches = re.findall(r"'(\w+)':\s*'[^']*'", content)
    symptom_keys = list(set(matches))

BATCH_PROMPT = """你是一位精通《傷寒論》、《金匱要略》的經方資料庫架構師。
請生成以下方劑的結構化 JSON 數據。

【可用症狀鍵值 (ONLY use these keys)】:
{symptom_keys}

【已存在的方劑 (DO NOT duplicate)】:
{existing}

【本批次需要生成的方劑】:
{batch_list}

【JSON Schema (每個方劑必須嚴格遵守)】:
{{
  "formula_name": "方劑中文名",
  "category": "傷寒論-X經" or "金匱要略-雜病" or "金匱要略-婦人雜病",
  "critical": ["key1"],  // 必中症狀，1-2個最關鍵的，缺此則絕不可能是此方
  "must_have": {{"symptom_key": weight}},  // 主症，weight 0.4~1.0，3-5個
  "should_have": {{"symptom_key": weight}},  // 兼症，weight 0.1~0.3，2-4個
  "forbidden": ["key1", "key2"],  // 禁忌症狀，2-4個
  "ingredients": ["藥物 劑量"],
  "source_clause": [{{"clause_number": "N", "text": "原文條文"}}]
}}

【重要約束】:
1. symptom key 必須從上方可用清單中選擇，不可自創！
2. must_have 的 weight 總和應在 1.5~3.0 之間
3. critical 必須是 must_have 中最關鍵的 1-2 個 key
4. forbidden 要符合中醫辨證邏輯（寒證禁熱症 etc.）
5. source_clause 的 text 必須是《傷寒論》或《金匱要略》原文
6. 請直接輸出 JSON array，不要有任何其他文字

輸出格式：[{{...}}, {{...}}, ...]"""

ALL_FORMULAS = [
    # Batch 1: 太陽經變方與青龍湯系
    ["桂枝麻黃各半湯", "桂枝二麻黃一湯", "桂枝去芍藥加附子湯", "桂枝加芍藥生薑各一兩人參三兩湯", 
     "桂枝甘草湯", "桂枝甘草龍骨牡蠣湯", "桂枝去芍藥加蜀漆牡蠣龍骨救逆湯", "桂枝加大黃湯", 
     "桂枝附子湯", "桂枝附子去桂加白朮湯", "桂枝新加湯", "大青龍湯", "小青龍湯", "葛根黃芩黃連湯", "抵當丸"],
    # Batch 2: 陷胸湯系與少陽變方
    ["梔子甘草豉湯", "梔子生薑豉湯", "梔子乾薑湯", "梔子柏皮湯", "大陷胸湯", "大陷胸丸", "小陷胸湯", 
     "文蛤散", "柴胡加芒硝湯", "柴胡桂枝湯", "柴胡桂枝乾薑湯", "柴胡加龍骨牡蠣湯", "黃芩加半夏生薑湯", 
     "乾薑附子湯", "十棗湯"],
    # Batch 3: 雜方與百合病方
    ["蜜煎導方", "豬膽汁導方", "當歸四逆加吳茱萸生薑湯", "麻黃升麻湯", "苦酒湯", "燒褌散", "牡蠣澤瀉散", 
     "枳實梔子豉湯", "百合知母湯", "百合滑石散", "百合雞子湯", "百合洗方", "栝蔞牡蠣散", "百合滑石代赭湯", "甘草瀉心湯"],
    # Batch 4: 瀉心湯系與胸痹方
    ["半夏瀉心湯", "生薑瀉心湯", "赤小豆當歸散", "苦參湯", "奔豚湯", "苓桂甘棗湯", "栝蔞薤白半夏湯", 
     "枳實薤白桂枝湯", "人參湯", "薏苡附子散", "九痛丸", "桂枝生薑枳實湯", "烏頭赤石脂丸", "附子粳米湯", "大烏頭煎"],
    # Batch 5: 虛勞水氣與風濕方
    ["當歸生薑羊肉湯", "天雄散", "越婢湯", "越婢加半夏湯", "小青龍加石膏湯", "厚朴麻黃湯", "澤漆湯", 
     "苓甘五味薑辛湯", "桂枝去芍藥加麻黃細辛附子湯", "木防己去石膏加茯苓芒硝湯", "防己茯苓湯", "甘草麻黃湯", 
     "麻黃附子湯", "黃耆桂枝五物湯", "蛇床子散"],
    # Batch 6: 婦女胎產與胃氣方
    ["狼牙湯", "紅藍花酒", "當歸散", "白朮散", "葵子茯苓散", "枳實芍藥散", "竹葉湯", "白頭翁加甘草阿膠湯", 
     "豬膏髮煎", "大半夏湯", "乾嘔噯氣湯", "旋覆代赭湯", "橘皮竹茹湯", "橘皮大黃朴硝湯", "桃仁承氣湯"],
    # Batch 7: 雜病與後世經方變通
    ["薏苡附子敗醬散", "牡丹皮散", "瓜蔞薤白湯", "桂枝加當歸湯", "柴胡疏肝散", "逍遙散", "越鞠丸", 
     "平胃散", "保和丸", "二陳湯", "溫膽湯", "杞菊地黃丸", "六味地黃丸", "一貫煎", "補中益氣湯"],
    # Batch 8: 氣血雙補與婦女調理
    ["歸脾湯", "八珍湯", "十全大補湯", "泰山磐石散", "左歸丸", "右歸丸", "四君子湯", "四物湯", 
     "生脈散", "玉屏風散", "獨活寄生湯", "羌活勝濕湯", "完帶湯", "易黃湯", "天王補心丹"],
    # Batch 9: 更多經方加減變通方
    ["柏子養心丹", "越婢二朮湯", "越婢人參湯", "大柴胡加石膏湯", "小柴胡加桔梗湯", "小青龍加附子湯", 
     "麻黃加附子湯", "桂枝加苓朮湯", "茵陳五苓散", "豬苓散", "葶藶丸", "陷胸散", "小柴胡去黃芩加茯苓湯", 
     "柴胡去半夏加蔞實湯", "大黃牡丹湯"]
]

def generate_batch(batch_list, existing_names, symptom_keys):
    from agent.auxiliary_client import call_llm, extract_content_or_reasoning
    
    prompt = BATCH_PROMPT.format(
        symptom_keys=json.dumps(symptom_keys, ensure_ascii=False),
        existing=", ".join(sorted(existing_names)),
        batch_list=", ".join(batch_list)
    )
    
    response = call_llm(
        task="curator",
        messages=[
            {"role": "system", "content": "You are a TCM formula database architect. Output ONLY valid JSON arrays."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    raw = extract_content_or_reasoning(response)
    
    clean = raw.strip()
    if clean.startswith("```json"): clean = clean[7:]
    elif clean.startswith("```"): clean = clean[3:]
    if clean.endswith("```"): clean = clean[:-3]
    clean = clean.strip()
    
    return json.loads(clean)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=len(ALL_FORMULAS), help="Number of batches to process")
    parser.add_argument("--start", type=int, default=0, help="Starting batch index")
    args = parser.parse_args()
    
    global existing_names
    added_total = 0
    
    end = min(args.start + args.batches, len(ALL_FORMULAS))
    for i in range(args.start, end):
        batch = ALL_FORMULAS[i]
        needed = [name for name in batch if name not in existing_names]
        if not needed:
            print(f"  Batch {i+1}: all formulas already exist, skipping.")
            continue
            
        print(f"  Batch {i+1}/{len(ALL_FORMULAS)}: generating {len(needed)} formulas ({', '.join(needed[:3])}...)")
        
        try:
            formulas = generate_batch(needed, existing_names, symptom_keys)
            for f in formulas:
                name = f.get("formula_name", "")
                if name and name not in existing_names:
                    db["formulas"].append(f)
                    existing_names.add(name)
                    added_total += 1
            print(f"    ✅ Added {len(formulas)} formulas")
        except Exception as e:
            print(f"    ❌ Batch {i+1} failed: {e}")
        
        time.sleep(1)
    
    db["version"] = "2.2.0"
    db["last_updated"] = "2026-05-14"
    db["architectural_coverage"] = f"v2.2: {len(db['formulas'])} formulas (Full Shanghan + Jingui + Variations coverage)"
    
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 Done! Added {added_total} new formulas. Total: {len(db['formulas'])} formulas.")

if __name__ == "__main__":
    main()
