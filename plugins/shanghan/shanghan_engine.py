import json

class ShanghanEngine:
    def __init__(self, db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.formulas = data.get('formulas', [])

    def analyze(self, user_symptoms):
        results = []
        for formula in self.formulas:
            name = formula['formula_name']
            criteria = formula
            
            # 1. 禁忌排除 (Forbidden)
            if any(s in user_symptoms for s in criteria.get('forbidden', [])):
                continue

            score = 0.0
            matched_must = []
            matched_should = []
            
            # 2. 必要症狀加權 (Must-have)
            for sym, weight in criteria.get('must_have', {}).items():
                if sym in user_symptoms:
                    score += weight
                    matched_must.append(sym)

            # 3. 輔助症狀加權 (Should-have)
            for sym, weight in criteria.get('should_have', {}).items():
                if sym in user_symptoms:
                    score += weight
                    matched_should.append(sym)
            
            if score > 0:
                results.append({
                    "name": name,
                    "score": round(score, 2),
                    "source": formula.get('source_clause', ''),
                    "category": formula.get('category', ''),
                    "matched_must_have": matched_must,
                    "total_must_have": len(criteria.get('must_have', {})),
                    "matched_should_have": matched_should,
                    "total_should_have": len(criteria.get('should_have', {})),
                    "ingredients": formula.get('ingredients', [])
                })

        return sorted(results, key=lambda x: x['score'], reverse=True)

# --- 測試執行區塊 ---
if __name__ == "__main__":
    # 1. 初始化引擎
    engine = ShanghanEngine("shanghan_logic_db.json")

    # 2. 模擬輸入症狀 (你可以修改這裡來測試不同的方劑)
    input_symptoms = ["發熱", "汗出", "惡風", "鼻鳴"]
    
    print(f"輸入症狀: {input_symptoms}")
    print("-" * 50)

    # 3. 執行推理
    output = engine.analyze(input_symptoms)

    # 4. 印出結果
    if not output:
        print("找不到匹配的方劑。")
    for i, res in enumerate(output, 1):
        print(f"{i}. 方劑: {res['name']} (匹配分: {res['score']})")
        print(f"   依據: {res['source']}\n")
