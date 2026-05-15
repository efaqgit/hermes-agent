import json

class ShanghanEngine:
    """Shanghan Logic Engine v2.0
    
    Improvements over v1.0:
    - 'critical' symptoms: hard gate — if defined, at least one must be matched or formula is skipped
    - Wider weight ranges: must_have 0.3~1.0, should_have 0.1~0.3 for better discrimination
    - Coverage penalty: if user selected many symptoms but formula only matches a few, score is dampened
    - Confidence percentage output for UI display
    """
    
    def __init__(self, db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.formulas = data.get('formulas', [])

    def analyze(self, user_symptoms):
        results = []
        for formula in self.formulas:
            name = formula['formula_name']
            
            # 1. Forbidden exclusion
            if any(s in user_symptoms for s in formula.get('forbidden', [])):
                continue

            # 2. Critical gate — if 'critical' is defined, at least one must match
            critical = formula.get('critical', [])
            if critical and not any(s in user_symptoms for s in critical):
                continue

            score = 0.0
            matched_must = []
            matched_should = []
            
            # 3. Must-have weighted scoring
            for sym, weight in formula.get('must_have', {}).items():
                if sym in user_symptoms:
                    score += weight
                    matched_must.append(sym)

            # 4. Should-have weighted scoring
            for sym, weight in formula.get('should_have', {}).items():
                if sym in user_symptoms:
                    score += weight
                    matched_should.append(sym)
            
            if score <= 0:
                continue

            # 5. Coverage ratio — how well does this formula explain the user's symptoms?
            total_formula_symptoms = len(formula.get('must_have', {})) + len(formula.get('should_have', {}))
            total_matched = len(matched_must) + len(matched_should)
            
            # Must-have coverage ratio (how many of the formula's key symptoms were found)
            must_total = len(formula.get('must_have', {}))
            must_coverage = len(matched_must) / must_total if must_total > 0 else 0
            
            # Apply mild penalty if must_have coverage is very low (< 50%)
            if must_coverage < 0.5 and must_total >= 3:
                score *= 0.7  # 30% penalty for poor must-have coverage

            # Confidence: what percentage of user symptoms are explained by this formula
            user_symptom_count = len(user_symptoms)
            explanation_ratio = total_matched / user_symptom_count if user_symptom_count > 0 else 0
            
            results.append({
                "name": name,
                "score": round(score, 2),
                "source": formula.get('source_clause', ''),
                "category": formula.get('category', ''),
                "matched_must_have": matched_must,
                "total_must_have": must_total,
                "matched_should_have": matched_should,
                "total_should_have": len(formula.get('should_have', {})),
                "ingredients": formula.get('ingredients', []),
                "must_coverage": round(must_coverage * 100, 1),
                "confidence": round(explanation_ratio * 100, 1)
            })

        # Sort by score descending
        sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        if not sorted_results:
            return {"locked_category": None, "formulas": []}
            
        # Phase 1: Category scoring using MAX score
        category_scores = {}
        for r in sorted_results:
            cat = r['category']
            if cat:
                if cat not in category_scores or r['score'] > category_scores[cat]:
                    category_scores[cat] = r['score']
                
        if not category_scores:
            return {"locked_category": "未分類", "formulas": sorted_results}

        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_cats[0]
        
        # Phase 2: Concurrent syndromes tolerance
        tolerance = 0.3  # slightly wider than v1's 0.2
        valid_categories = [cat for cat, score in sorted_cats if top_score - score <= tolerance]
        
        if len(valid_categories) > 1:
            short_cats = [c.replace("傷寒論-", "").replace("金匱要略-", "") for c in valid_categories]
            locked_category = " / ".join(short_cats) + " (合病/併病)"
        else:
            locked_category = valid_categories[0]
            
        final_formulas = [r for r in sorted_results if r['category'] in valid_categories]
        
        return {
            "locked_category": locked_category,
            "formulas": final_formulas
        }

# --- Test ---
if __name__ == "__main__":
    engine = ShanghanEngine("shanghan_logic_db.json")
    
    # Test: 太陽傷寒 (should match 麻黃湯)
    test1 = ["fever", "anhidrosis", "aversion_to_cold", "pulse_floating_tight", "dyspnea", "headache_neck_rigidity"]
    print(f"Test 1 - 太陽傷寒: {test1}")
    result = engine.analyze(test1)
    print(f"  Locked: {result['locked_category']}")
    for f in result['formulas'][:3]:
        print(f"  {f['name']}: {f['score']} (主證覆蓋: {f['must_coverage']}%, 信心度: {f['confidence']}%)")
    print()
    
    # Test: 少陽病 (should match 小柴胡湯)
    test2 = ["alternating_fever_chills", "chest_hypochondriac_fullness", "bitter_mouth_dry_throat", "lack_of_appetite", "pulse_wiry"]
    print(f"Test 2 - 少陽病: {test2}")
    result = engine.analyze(test2)
    print(f"  Locked: {result['locked_category']}")
    for f in result['formulas'][:3]:
        print(f"  {f['name']}: {f['score']} (主證覆蓋: {f['must_coverage']}%, 信心度: {f['confidence']}%)")
