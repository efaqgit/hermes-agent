#!/usr/bin/env python3
"""Upgrade shanghan_logic_db.json from v1 to v2: add critical fields + new formulas."""
import json, os

DB = os.path.join(os.path.dirname(__file__), "shanghan_logic_db.json")
with open(DB, "r", encoding="utf-8") as f:
    data = json.load(f)

# Add critical fields to existing formulas
CRITICAL_MAP = {
    "桂枝湯": ["sweating"],
    "麻黃湯": ["anhidrosis"],
    "五苓散": ["urination_difficulty"],
    "白虎湯": ["extreme_thirst", "high_fever_with_extreme_thirst"],
    "大承氣湯": ["constipation", "abdominal_fullness_pain"],
    "小柴胡湯": ["alternating_fever_chills", "bitter_mouth_dry_throat"],
    "理中丸": ["diarrhea_clear_food", "diarrhea"],
    "四逆湯": ["cold_limbs", "yin_yang_collapse_cold_limbs"],
    "當歸四逆湯": ["cold_limbs"],
    "桃核承氣湯": ["lower_abdominal_rigidity"],
    "大黃䗪蟲丸": ["blood_stasis_tongue", "skin_scaling_dryness"],
    "當歸芍藥散": ["abdominal_fullness_pain", "menstrual_irregularity"],
    "溫經湯": ["menstrual_irregularity", "menstrual_blood_dark_clots"],
    "半夏厚朴湯": ["throat_obstruction_globus"],
    "小青龍湯": ["cough_watery_sputum"],
    "苓桂術甘湯": ["heart_palpitation", "splash_sound_epigastric"],
    "茵陳蒿湯": ["yellow_skin_eyes_jaundice"],
}
for f in data["formulas"]:
    name = f["formula_name"]
    if name in CRITICAL_MAP:
        f["critical"] = CRITICAL_MAP[name]

# Boost weight ranges for existing formulas (scale must_have up)
for f in data["formulas"]:
    mh = f.get("must_have", {})
    weights = list(mh.values())
    if weights:
        max_w = max(weights)
        if max_w <= 0.35:
            for k in mh:
                mh[k] = round(mh[k] * 2.5, 2)
        elif max_w <= 0.5:
            for k in mh:
                mh[k] = round(mh[k] * 2.0, 2)

# New formulas to add
NEW = [
  {"formula_name":"葛根湯","category":"傷寒論-太陽經","critical":["headache_neck_rigidity","anhidrosis"],
   "must_have":{"fever":0.6,"anhidrosis":0.7,"headache_neck_rigidity":0.8,"aversion_to_cold":0.5},
   "should_have":{"generalized_body_pain":0.2,"diarrhea":0.2,"pulse_floating":0.15},
   "forbidden":["sweating","pulse_fine_weak"],
   "ingredients":["葛根 四兩","麻黃 三兩","桂枝 二兩","芍藥 二兩","甘草 二兩(炙)","生薑 三兩","大棗 十二枚"],
   "source_clause":[{"clause_number":"31","text":"太陽病，項背強几几，無汗惡風，葛根湯主之。"}]},
  {"formula_name":"真武湯","category":"傷寒論-少陰經","critical":["cold_limbs","edema_legs"],
   "must_have":{"cold_limbs":0.7,"edema_legs":0.6,"diarrhea":0.5,"pulse_sunken_fine":0.5},
   "should_have":{"dizziness":0.2,"heart_palpitation":0.2,"urination_difficulty":0.15,"generalized_body_pain":0.15},
   "forbidden":["high_fever","pulse_flooding_large"],
   "ingredients":["茯苓 三兩","芍藥 三兩","白朮 二兩","生薑 三兩","附子 一枚(炮)"],
   "source_clause":[{"clause_number":"316","text":"少陰病，二三日不已，至四五日，腹痛，小便不利，四肢沉重疼痛，自下利者，此為有水氣。其人或咳，或小便利，或下利，或嘔者，真武湯主之。"}]},
  {"formula_name":"四逆散","category":"傷寒論-少陰經","critical":["cold_limbs"],
   "must_have":{"cold_limbs":0.7,"chest_hypochondriac_fullness":0.5,"pulse_wiry":0.4},
   "should_have":{"lack_of_appetite":0.2,"abdominal_fullness_pain":0.15,"diarrhea":0.15},
   "forbidden":["pulse_sunken_fine","diarrhea_clear_food"],
   "ingredients":["柴胡 十分","枳實 十分","芍藥 十分","甘草 十分(炙)"],
   "source_clause":[{"clause_number":"318","text":"少陰病，四逆，其人或咳，或悸，或小便不利，或腹中痛，或泄利下重者，四逆散主之。"}]},
  {"formula_name":"白頭翁湯","category":"傷寒論-厥陰經","critical":["diarrhea","fever"],
   "must_have":{"diarrhea":0.6,"fever":0.5,"extreme_thirst":0.5},
   "should_have":{"abdominal_fullness_pain":0.2,"difficult_sticky_defecation":0.2,"urine_yellow":0.1},
   "forbidden":["cold_limbs","diarrhea_clear_food","pulse_sunken_fine"],
   "ingredients":["白頭翁 二兩","黃柏 三兩","黃連 三兩","秦皮 三兩"],
   "source_clause":[{"clause_number":"371","text":"熱利下重者，白頭翁湯主之。"}]},
  {"formula_name":"吳茱萸湯","category":"傷寒論-厥陰經","critical":["vomiting_nausea"],
   "must_have":{"vomiting_nausea":0.7,"headache":0.5,"cold_limbs":0.4},
   "should_have":{"diarrhea":0.2,"salivation":0.15,"pulse_fine_weak":0.15},
   "forbidden":["high_fever","constipation","pulse_flooding_large"],
   "ingredients":["吳茱萸 一升","人參 三兩","生薑 六兩","大棗 十二枚"],
   "source_clause":[{"clause_number":"309","text":"少陰病，吐利，手足逆冷，煩躁欲死者，吳茱萸湯主之。"}]},
  {"formula_name":"芍藥甘草湯","category":"傷寒論-太陽經","critical":["generalized_body_pain","joint_pain"],
   "must_have":{"generalized_body_pain":0.6,"joint_pain":0.5,"sweating":0.4},
   "should_have":{"cold_limbs":0.2,"pulse_fine_weak":0.15},
   "forbidden":["high_fever","pulse_flooding_large"],
   "ingredients":["芍藥 四兩","甘草 四兩(炙)"],
   "source_clause":[{"clause_number":"29","text":"傷寒，脈浮，自汗出，小便數，心煩，微惡寒，腳攣急，反與桂枝欲攻其表，此誤也。得之便厥、咽中乾、煩躁吐逆者，作甘草乾薑湯與之，以復其陽。若厥愈足溫者，更作芍藥甘草湯與之，其腳即伸。"}]},
  {"formula_name":"黃連阿膠湯","category":"傷寒論-少陰經","critical":["insomnia","chest_heat_irritability"],
   "must_have":{"insomnia":0.7,"chest_heat_irritability":0.6,"red_tongue_scanty_coating":0.4},
   "should_have":{"fever_with_yin_deficiency":0.2,"pulse_fine_weak":0.15,"tongue_red_with_no_coating":0.15},
   "forbidden":["cold_limbs","diarrhea_clear_food","aversion_to_cold"],
   "ingredients":["黃連 四兩","黃芩 二兩","芍藥 二兩","雞子黃 二枚","阿膠 三兩"],
   "source_clause":[{"clause_number":"303","text":"少陰病，得之二三日以上，心中煩，不得臥，黃連阿膠湯主之。"}]},
  {"formula_name":"豬苓湯","category":"傷寒論-陽明經","critical":["urination_difficulty"],
   "must_have":{"urination_difficulty":0.7,"fever":0.4,"insomnia":0.4,"extreme_thirst":0.4},
   "should_have":{"vomiting_nausea":0.15,"diarrhea":0.15,"cough_watery_sputum":0.1},
   "forbidden":["cold_limbs","pulse_sunken_fine"],
   "ingredients":["豬苓 一兩","茯苓 一兩","澤瀉 一兩","阿膠 一兩","滑石 一兩"],
   "source_clause":[{"clause_number":"223","text":"陽明病，汗出多而渴者，不可與豬苓湯，以汗多胃中燥，豬苓湯復利其小便故也。"},{"clause_number":"319","text":"少陰病，下利六七日，咳而嘔渴，心煩不得眠者，豬苓湯主之。"}]},
  {"formula_name":"麻杏甘石湯","category":"傷寒論-太陽經","critical":["dyspnea"],
   "must_have":{"dyspnea":0.7,"fever":0.5,"sweating":0.4},
   "should_have":{"cough_watery_sputum":0.2,"extreme_thirst":0.15},
   "forbidden":["anhidrosis","aversion_to_cold","pulse_floating_tight"],
   "ingredients":["麻黃 四兩","杏仁 五十個","甘草 二兩(炙)","石膏 半斤"],
   "source_clause":[{"clause_number":"63","text":"發汗後，不可更行桂枝湯，汗出而喘，無大熱者，可與麻黃杏仁甘草石膏湯。"}]},
  {"formula_name":"桂枝加芍藥湯","category":"傷寒論-太陰經","critical":["abdominal_fullness_pain"],
   "must_have":{"abdominal_fullness_pain":0.7,"diarrhea":0.4,"pulse_floating_slow":0.3},
   "should_have":{"sweating":0.15,"aversion_to_wind":0.15},
   "forbidden":["constipation","pulse_sunken_forceful","high_fever"],
   "ingredients":["桂枝 三兩","芍藥 六兩","甘草 二兩(炙)","生薑 三兩","大棗 十二枚"],
   "source_clause":[{"clause_number":"279","text":"本太陽病，醫反下之，因而腹滿時痛者，屬太陰也，桂枝加芍藥湯主之。"}]},
  {"formula_name":"炙甘草湯","category":"傷寒論-少陰經","critical":["heart_palpitation"],
   "must_have":{"heart_palpitation":0.7,"pulse_fine_weak":0.5,"shortness_of_breath_exertion":0.4},
   "should_have":{"insomnia":0.15,"sweating":0.15,"fever_with_yin_deficiency":0.1},
   "forbidden":["pulse_flooding_large","high_fever"],
   "ingredients":["甘草 四兩(炙)","生薑 三兩","桂枝 三兩","人參 二兩","生地黃 一斤","阿膠 二兩","麥門冬 半升","麻仁 半升","大棗 三十枚"],
   "source_clause":[{"clause_number":"177","text":"傷寒，脈結代，心動悸，炙甘草湯主之。"}]},
  {"formula_name":"大柴胡湯","category":"傷寒論-少陽經","critical":["alternating_fever_chills","chest_hypochondriac_fullness"],
   "must_have":{"alternating_fever_chills":0.5,"chest_hypochondriac_fullness":0.5,"vomiting_nausea":0.4,"constipation":0.3},
   "should_have":{"bitter_mouth_dry_throat":0.2,"pulse_wiry":0.15,"tidal_fever":0.15},
   "forbidden":["diarrhea_clear_food","pulse_fine_weak"],
   "ingredients":["柴胡 半斤","黃芩 三兩","芍藥 三兩","半夏 半升","生薑 五兩","枳實 四枚","大棗 十二枚","大黃 二兩"],
   "source_clause":[{"clause_number":"103","text":"太陽病，過經十餘日，反二三下之，後四五日，柴胡證仍在者，先與小柴胡湯。嘔不止、心下急、鬱鬱微煩者，為未解也，與大柴胡湯下之則愈。"}]},
  {"formula_name":"附子理中丸","category":"傷寒論-太陰經","critical":["diarrhea_clear_food","cold_limbs"],
   "must_have":{"diarrhea_clear_food":0.7,"cold_limbs":0.6,"abdominal_fullness_pain":0.4,"vomiting_nausea":0.3},
   "should_have":{"lack_of_appetite":0.2,"pulse_sunken_fine":0.15,"salivation":0.15},
   "forbidden":["high_fever","constipation","pulse_flooding_large"],
   "ingredients":["人參 三兩","白朮 三兩","乾薑 三兩","甘草 三兩(炙)","附子 一枚(炮)"],
   "source_clause":[{"clause_number":"396","text":"大病差後，喜唾，久不了了，胸上有寒，當以丸藥溫之，宜理中丸。(附子理中為加減方)"}]},
  {"formula_name":"黃芩湯","category":"傷寒論-少陽經","critical":["diarrhea"],
   "must_have":{"diarrhea":0.6,"abdominal_fullness_pain":0.5,"fever":0.4},
   "should_have":{"bitter_mouth_dry_throat":0.15,"pulse_wiry":0.15,"vomiting_nausea":0.1},
   "forbidden":["cold_limbs","diarrhea_clear_food"],
   "ingredients":["黃芩 三兩","芍藥 二兩","甘草 二兩(炙)","大棗 十二枚"],
   "source_clause":[{"clause_number":"172","text":"太陽與少陽合病，自下利者，與黃芩湯。"}]},
  {"formula_name":"竹葉石膏湯","category":"傷寒論-陽明經","critical":["fever_with_yin_deficiency","extreme_thirst"],
   "must_have":{"fever_with_yin_deficiency":0.6,"extreme_thirst":0.5,"shortness_of_breath_exertion":0.4},
   "should_have":{"vomiting_nausea":0.2,"red_tongue_scanty_coating":0.15,"pulse_fine_weak":0.15},
   "forbidden":["cold_limbs","aversion_to_cold","diarrhea_clear_food"],
   "ingredients":["竹葉 二把","石膏 一斤","半夏 半升","麥門冬 一升","人參 二兩","甘草 二兩(炙)","粳米 半升"],
   "source_clause":[{"clause_number":"397","text":"傷寒解後，虛羸少氣，氣逆欲吐，竹葉石膏湯主之。"}]},
]

# Deduplicate by name
existing_names = {f["formula_name"] for f in data["formulas"]}
for nf in NEW:
    if nf["formula_name"] not in existing_names:
        data["formulas"].append(nf)

data["version"] = "2.0.0"
data["last_updated"] = "2026-05-14"
data["architectural_coverage"] = f"v2.0: {len(data['formulas'])} formulas with critical gate, expanded weights"

with open(DB, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Upgraded to v2.0: {len(data['formulas'])} formulas total")
