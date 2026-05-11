document.addEventListener("DOMContentLoaded", () => {
    const symptomsContainer = document.getElementById("symptoms-container");
    const searchInput = document.getElementById("symptom-search");
    const btnAnalyze = document.getElementById("btn-analyze");
    const selectedCount = document.getElementById("selected-count");
    const formulaResults = document.getElementById("formula-results");
    const aiAnalysisContent = document.getElementById("ai-analysis-content");
    const engineStatus = document.getElementById("engine-status");

    let allSymptoms = [];
    let selectedKeys = new Set();

    // Fetch symptoms from API
    fetch("/api/symptoms")
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Sort by stroke or simply pinyin
                allSymptoms = data.data.sort((a, b) => a.label.localeCompare(b.label, 'zh-TW'));
                renderSymptoms(allSymptoms);
            }
        })
        .catch(err => {
            symptomsContainer.innerHTML = `<div class="empty-state" style="color:var(--danger)">無法連接伺服器，請確認後端已啟動。</div>`;
            console.error("Fetch symptoms error:", err);
        });

    function renderSymptoms(symptoms) {
        symptomsContainer.innerHTML = "";
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

    // Search filter
    searchInput.addEventListener("input", (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allSymptoms.filter(sym => 
            sym.label.toLowerCase().includes(term) || sym.key.toLowerCase().includes(term)
        );
        renderSymptoms(filtered);
    });

    function updateUI() {
        const count = selectedKeys.size;
        selectedCount.textContent = count;
        btnAnalyze.disabled = count === 0;
    }

    // Analyze action
    btnAnalyze.addEventListener("click", async () => {
        if (selectedKeys.size === 0) return;
        
        btnAnalyze.classList.add("loading-state");
        btnAnalyze.disabled = true;
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
            btnAnalyze.disabled = false;
        }
    });

    function renderResults(formulas) {
        formulaResults.innerHTML = "";
        if (!formulas || formulas.length === 0) {
            formulaResults.innerHTML = `<div class="empty-state">目前輸入的症狀無法匹配到任何經典方劑，請嘗試加入更多關鍵症狀，或檢查是否有互斥症狀。</div>`;
            return;
        }

        // Maximum score for percentage
        const maxScore = formulas[0].score;

        formulas.forEach((f, index) => {
            const isTop = index === 0;
            const pct = Math.min((f.score / (maxScore || 1)) * 100, 100);
            
            const card = document.createElement("div");
            card.className = `formula-card ${isTop ? 'top-match' : ''}`;
            
            let sourceText = '';
            if (Array.isArray(f.source) && f.source.length > 0) {
                sourceText = f.source[0].text || '';
            } else if (typeof f.source === 'string') {
                sourceText = f.source;
            }
            const displaySource = sourceText ? sourceText.split('。')[0] : '無經典條文資訊';
            
            card.innerHTML = `
                <div class="formula-header">
                    <div class="formula-name">${f.name}</div>
                    <div class="formula-score">${f.score} 分</div>
                </div>
                <div class="progress-bg">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>
                <div class="formula-details">
                    <div class="detail-row"><span class="detail-label">方義:</span> ${displaySource}</div>
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
});
