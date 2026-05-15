document.addEventListener("DOMContentLoaded", () => {
    const symptomsContainer = document.getElementById("symptoms-container");
    const categoryTabsContainer = document.getElementById("category-tabs");
    const searchInput = document.getElementById("symptom-search");
    const btnAnalyze = document.getElementById("btn-analyze");
    const btnClearAll = document.getElementById("btn-clear-all");
    const selectedCount = document.getElementById("selected-count");
    const formulaResults = document.getElementById("formula-results");
    const aiAnalysisContent = document.getElementById("ai-analysis-content");
    const engineStatus = document.getElementById("engine-status");
    const btnAiExtract = document.getElementById("btn-ai-extract");
    const aiFreeText = document.getElementById("ai-free-text");
    const aiExtractNotes = document.getElementById("ai-extract-notes");

    let allSymptoms = [];
    let selectedKeys = new Set();
    let selectedCategory = "all"; // "all" or category keys
    let symptomKeyToLabel = {}; // Quick map from key to label

    // 🌿 Clinical Symptom Categorization Mapping (Covers all symptoms)
    const SYMPTOM_CATEGORIES = {
        "exterior": {
            "label": "表證寒熱",
            "icon": "🌡️",
            "keys": [
                "fever", "high_fever", "shivering_fever", "fever_with_yin_deficiency",
                "aversion_to_cold", "aversion_to_wind", "aversion_to_heat",
                "sweating", "anhidrosis", "profuse_sweating", "profuse_sweating_with_亡陽",
                "sweating_on_limbs", "tidal_fever", "alternating_fever_chills",
                "spontaneous_sweating_yang_def"
            ]
        },
        "respiration": {
            "label": "頭面呼吸",
            "icon": "🗣️",
            "keys": [
                "headache", "headache_neck_rigidity", "nasal_congestion",
                "throat_dryness", "throat_discomfort", "bitter_mouth_dry_throat",
                "dryness_without_thirst", "extreme_thirst", "extreme_thirst_with_dry_mouth",
                "dyspnea", "cough_watery_sputum", "cough_with_fever_and_shivering",
                "cough_with_pus_blood", "cough_with_yin_deficiency_dryness",
                "heavy_water_phlegm_in_lung", "high_fever_with_extreme_thirst",
                "throat_obstruction_globus", "chest_heat_irritability"
            ]
        },
        "digestion": {
            "label": "胸腹消化",
            "icon": "🍲",
            "keys": [
                "chest_hypochondriac_fullness", "epigastric_fullness_rigidity",
                "abdominal_fullness_pain", "lower_abdominal_rigidity",
                "lack_of_appetite", "vomiting_nausea", "constipation",
                "diarrhea", "diarrhea_clear_food", "severe_diarrhea_clear_food",
                "diarrhea_clear_food_with_spleen_collapse", "diarrhea_due_to_spleen_deficiency",
                "diarrhea_without_dry_feces", "severe_interior_excess_with_dry_feces",
                "delirious_speech", "throbbing_below_heart", "splash_sound_epigastric",
                "difficult_sticky_defecation", "thirst_with_water_vomiting"
            ]
        },
        "excretion": {
            "label": "肢體排泄",
            "icon": "🦵",
            "keys": [
                "cold_limbs", "yin_yang_collapse_cold_limbs", "edema_face_eyes",
                "edema_legs", "generalized_body_pain", "joint_pain",
                "lumbar_cold_pain", "lumbar_knees_weakness", "urination_difficulty",
                "urine_yellow", "nocturia_frequent", "heart_palpitation", "salivation",
                "no_qi_rush_after_purging", "severe_postpartum_weakness",
                "severe_yin_yang_deficiency_with_limb_spasms", "alcoholic_constitution",
                "generalized_edema", "shortness_of_breath_exertion", "yellow_skin_eyes_jaundice"
            ]
        },
        "gynecology": {
            "label": "婦科胎產",
            "icon": "🩺",
            "keys": [
                "menstrual_irregularity", "menstrual_blood_dark_clots", "uterine_bleeding_leakage",
                "postpartum_abdominal_pain", "abdominal_mass"
            ]
        },
        "pulse_tongue": {
            "label": "舌象脈象",
            "icon": "☯️",
            "keys": [
                "pulse_floating", "pulse_floating_tight", "pulse_floating_slow",
                "pulse_floating_weak", "pulse_wiry", "pulse_sunken_fine",
                "pulse_sunken_forceful", "pulse_fine_weak", "pulse_flooding_large",
                "red_tongue_scanty_coating", "yellow_dry_tongue_coating",
                "tongue_red_with_no_coating", "blood_stasis_tongue", "skin_scaling_dryness",
                "stabbing_lower_abdomen", "dark_circles_under_eyes"
            ]
        },
        "miscellaneous": {
            "label": "雜病癥瘕",
            "icon": "🦠",
            "keys": [
                "gallstones", "lipoma", "right_upper_quadrant_pain",
                "fatty_liver", "gout", "insomnia", "dizziness", "tinnitus"
            ]
        },
        "dermatology": {
            "label": "皮膚專科",
            "icon": "🧴",
            "keys": [
                "eczema", "urticaria", "psoriasis", "severe_itching",
                "skin_redness_swelling", "skin_exudation", "wind_wheals"
            ]
        }
    };

    // Fetch symptoms from API
    fetch("/api/symptoms")
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                allSymptoms = data.data.sort((a, b) => a.label.localeCompare(b.label, 'zh-TW'));
                
                // Build fast key-to-label map
                allSymptoms.forEach(sym => {
                    symptomKeyToLabel[sym.key] = sym.label;
                });

                renderCategoryTabs();
                filterAndRenderSymptoms();
            }
        })
        .catch(err => {
            symptomsContainer.innerHTML = `<div class="empty-state" style="color:var(--danger)">無法連接伺服器，請確認後端已啟動。</div>`;
            console.error("Fetch symptoms error:", err);
        });

    // Render Category Tab Buttons
    function renderCategoryTabs() {
        if (!categoryTabsContainer) return;
        categoryTabsContainer.innerHTML = "";
        
        // "All" tab
        const allTab = document.createElement("div");
        allTab.className = `category-tab ${selectedCategory === "all" ? "active" : ""}`;
        allTab.innerHTML = `🌟 全部`;
        allTab.addEventListener("click", () => {
            selectedCategory = "all";
            renderCategoryTabs();
            filterAndRenderSymptoms();
        });
        categoryTabsContainer.appendChild(allTab);
        
        // Structured categories
        Object.entries(SYMPTOM_CATEGORIES).forEach(([catKey, cat]) => {
            const tab = document.createElement("div");
            tab.className = `category-tab ${selectedCategory === catKey ? "active" : ""}`;
            tab.innerHTML = `${cat.icon} ${cat.label}`;
            tab.addEventListener("click", () => {
                selectedCategory = catKey;
                renderCategoryTabs();
                filterAndRenderSymptoms();
            });
            categoryTabsContainer.appendChild(tab);
        });
    }

    // Filter symptoms by active Category Tab AND Search Input
    function filterAndRenderSymptoms() {
        const searchTerm = searchInput.value.toLowerCase();
        let filtered = allSymptoms;
        
        // 1. Filter by category
        if (selectedCategory !== "all") {
            const allowedKeys = SYMPTOM_CATEGORIES[selectedCategory].keys;
            filtered = filtered.filter(sym => allowedKeys.includes(sym.key));
        }
        
        // 2. Filter by search input
        if (searchTerm) {
            filtered = filtered.filter(sym => 
                sym.label.toLowerCase().includes(searchTerm) || sym.key.toLowerCase().includes(searchTerm)
            );
        }
        
        renderSymptoms(filtered);
    }

    // Render selected sub-list of symptoms
    function renderSymptoms(symptoms) {
        symptomsContainer.innerHTML = "";
        if (symptoms.length === 0) {
            symptomsContainer.innerHTML = `<div class="empty-state" style="padding: 1rem 0;">無符合篩選的症狀</div>`;
            return;
        }

        symptoms.forEach(sym => {
            const pill = document.createElement("div");
            pill.className = "symptom-pill";
            if (selectedKeys.has(sym.key)) {
                pill.classList.add("selected");
            }
            pill.textContent = sym.label;
            pill.dataset.key = sym.key;
            
            pill.addEventListener("click", () => {
                if (selectedKeys.has(sym.key)) {
                    selectedKeys.delete(sym.key);
                    pill.classList.remove("selected");
                } else {
                    selectedKeys.add(sym.key);
                    pill.classList.add("selected");
                }
                updateUI();
            });
            
            symptomsContainer.appendChild(pill);
        });
    }

    // Search filter input listener
    searchInput.addEventListener("input", () => {
        filterAndRenderSymptoms();
    });

    // Reset/Clear All selected keys
    if (btnClearAll) {
        btnClearAll.addEventListener("click", () => {
            selectedKeys.clear();
            document.querySelectorAll(".symptom-pill.selected").forEach(pill => {
                pill.classList.remove("selected");
            });
            updateUI();
        });
    }

    // AI Free-Text Extract action
    if (btnAiExtract) {
        btnAiExtract.addEventListener("click", async () => {
            const description = aiFreeText.value.trim();
            if (!description) {
                alert("請先輸入患者的自由主訴口語描述。");
                return;
            }

            btnAiExtract.classList.add("extract-loading");
            btnAiExtract.disabled = true;
            aiExtractNotes.style.display = "none";

            try {
                const response = await fetch("/api/extract_symptoms", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ description })
                });
                const data = await response.json();

                if (data.success) {
                    selectedKeys.clear();
                    (data.extracted_keys || []).forEach(k => {
                        selectedKeys.add(k);
                    });

                    // Sync visual states of pills
                    document.querySelectorAll(".symptom-pill").forEach(pill => {
                        const pillKey = pill.dataset.key;
                        if (selectedKeys.has(pillKey)) {
                            pill.classList.add("selected");
                        } else {
                            pill.classList.remove("selected");
                        }
                    });

                    updateUI();

                    // Render pathological notes and missing questions
                    aiExtractNotes.style.display = "block";
                    let questionsHtml = "";
                    if (data.missing_questions && data.missing_questions.length > 0) {
                        questionsHtml = `
                            <div class="questions-title">🔍 老中醫推薦追問 (點擊可複製)：</div>
                            ${data.missing_questions.map(q => {
                                const escapedQ = q.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                                return `<div class="question-item" title="點擊自動複製追問問題" onclick="navigator.clipboard.writeText('${escapedQ}'); alert('已複製追問問題到剪貼簿：\\n${escapedQ}')">${q}</div>`;
                            }).join("")}
                        `;
                    }

                    aiExtractNotes.innerHTML = `
                        <div class="hints"><strong>病機初探:</strong> ${data.logic_hints || '無'}</div>
                        ${questionsHtml}
                    `;
                } else {
                    alert("AI 提取失敗: " + (data.detail || "未知錯誤"));
                }
            } catch (err) {
                console.error("AI Extract error:", err);
                alert("連線失敗，無法呼叫 AI 提取功能。");
            } finally {
                btnAiExtract.classList.remove("extract-loading");
                btnAiExtract.disabled = false;
            }
        });
    }

    function updateUI() {
        const count = selectedKeys.size;
        selectedCount.textContent = count;
        btnAnalyze.disabled = count === 0;
        if (btnClearAll) {
            btnClearAll.disabled = count === 0;
        }
    }

    // Analyze action
    btnAnalyze.addEventListener("click", async () => {
        if (selectedKeys.size === 0) return;
        
        btnAnalyze.classList.add("loading-state");
        btnAnalyze.disabled = true;
        if (btnClearAll) btnClearAll.disabled = true;
        engineStatus.textContent = "運算中...";
        engineStatus.classList.add("active");
        
        formulaResults.innerHTML = `<div class="empty-state">引擎正在比對《傷寒雜病論》資料庫...</div>`;
        aiAnalysisContent.innerHTML = `<div class="empty-state">AI 老中醫正在研讀醫案...</div>`;

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ symptoms: Array.from(selectedKeys) })
            });
            const data = await response.json();
            
            if (data.success) {
                renderResults(data.formulas);
                typewriterEffect(aiAnalysisContent, data.llm_analysis);
                engineStatus.textContent = "辨證完成";
            } else {
                formulaResults.innerHTML = `<div class="empty-state" style="color:var(--danger)">發生錯誤: ${data.detail || '未知錯誤'}</div>`;
                aiAnalysisContent.innerHTML = `<div class="empty-state" style="color:var(--danger)">分析中斷。</div>`;
                engineStatus.textContent = "辨證失敗";
                engineStatus.classList.remove("active");
            }
        } catch (err) {
            console.error("Analyze error:", err);
            formulaResults.innerHTML = `<div class="empty-state" style="color:var(--danger)">網路錯誤，無法連接後端伺服器。</div>`;
            aiAnalysisContent.innerHTML = `<div class="empty-state" style="color:var(--danger)">連線失敗。</div>`;
            engineStatus.textContent = "網路錯誤";
            engineStatus.classList.remove("active");
        } finally {
            btnAnalyze.classList.remove("loading-state");
            updateUI();
        }
    });

    // Render enriched results list with badges and symptom matches
    function renderResults(formulas) {
        formulaResults.innerHTML = "";
        if (!formulas || formulas.length === 0) {
            formulaResults.innerHTML = `<div class="empty-state">目前輸入的症狀無法匹配到任何經典方劑，請嘗試加入更多關鍵症狀，或檢查是否有互斥症狀。</div>`;
            return;
        }

        const maxScore = formulas[0].score;

        formulas.forEach((f, index) => {
            const isTop = index === 0;
            const pct = Math.min((f.score / (maxScore || 1)) * 100, 100);
            
            const card = document.createElement("div");
            card.className = `formula-card ${isTop ? 'top-match' : ''}`;
            
            // Extract Clause Text
            let sourceText = '';
            if (Array.isArray(f.source) && f.source.length > 0) {
                sourceText = f.source[0].text || '';
            } else if (typeof f.source === 'string') {
                sourceText = f.source;
            }
            const displaySource = sourceText ? sourceText.split('。')[0] : '無經典條文資訊';
            
            // Extract and translate matched lists
            const matchedMustCount = f.matched_must_have ? f.matched_must_have.length : 0;
            const matchedShouldCount = f.matched_should_have ? f.matched_should_have.length : 0;
            
            const mustLabels = (f.matched_must_have || []).map(k => symptomKeyToLabel[k] || k);
            const shouldLabels = (f.matched_should_have || []).map(k => symptomKeyToLabel[k] || k);
            
            // Render Badges Row
            let badgesHtml = '';
            if (f.category) {
                badgesHtml += `<span class="tag-meridian">${f.category}</span> `;
            }
            badgesHtml += `<span class="tag-must">主證: ${matchedMustCount}/${f.total_must_have || 0}</span> `;
            if (f.total_should_have > 0) {
                badgesHtml += `<span class="tag-should">兼證: ${matchedShouldCount}/${f.total_should_have || 0}</span> `;
            }
            badgesHtml += `<span class="tag-safe">🛡️ 安全</span> `;
            
            // Render Specific Symptoms Matches
            let matchedSymptomsHtml = '';
            if (mustLabels.length > 0 || shouldLabels.length > 0) {
                matchedSymptomsHtml += `<div class="matching-symptoms-list">`;
                mustLabels.forEach(lbl => {
                    matchedSymptomsHtml += `<span class="match-symptom-tag must">✔ 主: ${lbl}</span> `;
                });
                shouldLabels.forEach(lbl => {
                    matchedSymptomsHtml += `<span class="match-symptom-tag should">✔ 兼: ${lbl}</span> `;
                });
                matchedSymptomsHtml += `</div>`;
            }

            // Render Ingredients / Herbal Prescription Row
            let ingredientsHtml = '';
            if (Array.isArray(f.ingredients) && f.ingredients.length > 0) {
                ingredientsHtml += `<div class="detail-row ingredients-row"><span class="detail-label">藥方組成:</span> `;
                f.ingredients.forEach(ing => {
                    ingredientsHtml += `<span class="ingredient-tag">${ing}</span> `;
                });
                ingredientsHtml += `</div>`;
            }

            card.innerHTML = `
                <div class="formula-header">
                    <div class="formula-name">${f.name}</div>
                    <div class="formula-score">${f.score} 分</div>
                </div>
                
                <div class="formula-badges-row">
                    ${badgesHtml}
                </div>

                <div class="progress-bg">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>

                <div class="formula-details">
                    <div class="detail-row"><span class="detail-label">條文:</span> ${displaySource}。</div>
                    ${ingredientsHtml}
                    ${matchedSymptomsHtml}
                </div>
            `;
            
            formulaResults.appendChild(card);
            
            // Trigger reflow for animation
            void card.offsetWidth;
            setTimeout(() => {
                card.querySelector(".progress-bar").style.width = `${pct}%`;
            }, 100);
        });
    }

    function typewriterEffect(element, markdownText) {
        element.innerHTML = "";
        if (!markdownText) return;
        
        const htmlContent = window.marked ? window.marked.parse(markdownText) : markdownText;
        
        element.style.opacity = "0";
        element.innerHTML = htmlContent;
        
        let opacity = 0;
        const fade = setInterval(() => {
            opacity += 0.05;
            element.style.opacity = opacity;
            if (opacity >= 1) clearInterval(fade);
        }, 30);
    }

    // --- Book Upload UI Logic ---
    const dropzone = document.getElementById("book-upload-zone");
    const fileInput = document.getElementById("book-file-input");
    const uploadLoader = document.getElementById("upload-loader");
    
    if (dropzone && fileInput) {
        dropzone.addEventListener("click", () => fileInput.click());
        
        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });
        
        dropzone.addEventListener("dragleave", () => {
            dropzone.classList.remove("dragover");
        });
        
        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        
        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
            }
            // Reset input so the same file can be selected again if needed
            fileInput.value = "";
        });
    }

    async function handleFileUpload(file) {
        if (!file.name.endsWith('.txt') && !file.name.endsWith('.md') && !file.name.endsWith('.epub')) {
            alert("請上傳 .txt, .md 或 .epub 格式的檔案！");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        uploadLoader.style.display = "flex";

        try {
            const response = await fetch("/api/upload_book", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                alert(`✅ 醫書/醫案學習完成！\n已成功解析並擴充至知識庫。\n(本次新增 ${data.message.split('ingested ')[1].split(' chunks')[0]} 個知識片段)`);
            } else {
                alert("上傳失敗：" + (data.detail || "未知錯誤"));
            }
        } catch (err) {
            console.error("Upload error:", err);
            alert("上傳失敗，無法連接伺服器。");
        } finally {
            uploadLoader.style.display = "none";
        }
    }
});
