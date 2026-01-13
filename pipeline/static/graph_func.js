import { updateNetworkInstance } from './graph_3labelFunc.js';

export function drawReviewerChart(reviewerData) {
    const ctx = document.getElementById("reviewerChart").getContext("2d");

    let reviewers = reviewerData.map(item => item.reviewer);
    let avgLabels = reviewerData.map(item => item.avgLabel);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: reviewers,  // 使用計算出來的 reviewers 名稱
            datasets: [{
                label: 'Reviewer 平均 Label',
                data: avgLabels,  // 使用計算出來的平均 label 數據
                backgroundColor: 'rgba(58, 150, 192, 0.6)',
                borderColor: 'rgb(65, 169, 210)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

export function calculateReviewerLabelAverages(assignments) {
    let reviewerStats = {};

    // 計算每個 Reviewer 的 Label 總和與數量
    assignments.forEach(assignment => {
        let reviewer = assignment.Reviewer?.trim().toUpperCase();  
        let rounds = assignment.Round;  

        if (!Array.isArray(rounds)) {
            console.warn(`⚠️ Reviewer: ${reviewer} 的 Round 不是陣列`, rounds);
            return;
        }

        if (!reviewerStats[reviewer]) {
            reviewerStats[reviewer] = { totalLabel: 0, count: 0 };
        }

        rounds.forEach(round => {
            let label = parseFloat(round.Label);
            if (!isNaN(label)) {
                reviewerStats[reviewer].totalLabel += label;
                reviewerStats[reviewer].count++;
            }
        });
    });

    // 計算平均值，並存回 assignments
    assignments.forEach(assignment => {
        let reviewer = assignment.Reviewer?.trim().toUpperCase();
        if (reviewerStats[reviewer] && reviewerStats[reviewer].count > 0) {
            assignment.avgLabel = reviewerStats[reviewer].totalLabel / reviewerStats[reviewer].count;
        } else {
            assignment.avgLabel = NaN;  // 若無有效數據，設為 NaN
        }
    });
    return assignments;  // 也可以選擇不回傳，直接修改原本的陣列
}

export function getAvgLabelQuality(rounds) {
    if (!Array.isArray(rounds) || rounds.length === 0) {
        console.warn("⚠️ getAvgLabelQuality: rounds 不是陣列或為空", rounds);
        return 0; // 記住，這個現在只影響顏色，而非大小
    }

    const validFeedbacks = rounds.filter(r => r.Feedback && r.Feedback.trim() !== "");

    if (validFeedbacks.length === 0) {
        console.warn("⚠️ 沒有有效的 Feedbacks，回傳最小值 0");
        return 0;
    }

    const totalLabel = validFeedbacks.reduce((sum, r) => sum + (parseFloat(r.Label) || 0), 0);
    const avgLabelQuality = totalLabel / validFeedbacks.length;

    console.log(`📊 計算結果: totalLabel=${totalLabel}, avgLabelQuality=${avgLabelQuality}`);

    return Math.max(0, Math.min(1, avgLabelQuality)); // 確保範圍 0~1
}

export function processReviewerData(rawData, mode = "all", hwNames = ['HW4']) {
    const nodesMap = new Map();
    const links = [];

    // 確保 hwNames 為陣列
    if (typeof hwNames === 'string') hwNames = [hwNames];

    hwNames.forEach(hwName => {
        const hwAssignments = rawData[hwName] || [];
        hwAssignments.forEach(assignment => {
            const authorId = assignment.Author;
            const reviewerId = assignment.Reviewer;
            const rounds = Array.isArray(assignment.Round) ? assignment.Round : [];

            // 初始化或取得節點
            if (!nodesMap.has(reviewerId)) {
                nodesMap.set(reviewerId, {
                    id: reviewerId,
                    totalRounds: 0,
                    meaningfulScore: 0,
                    feedbacks: [],
                    labelCounts: { relevance: 0, concreteness: 0, constructive: 0 }
                });
            }
            const node = nodesMap.get(reviewerId);
            node.totalRounds += rounds.length;

            // 處理每個回合
            // 在回合處理邏輯中，移除模式過濾（保持所有標籤原始值）
        rounds.forEach(round => {
            const feedback = (round.Feedback || "").trim();
            node.feedbacks.push(feedback);

            // 保留所有標籤原始值（不再根據模式過濾）
            const relevance = round.Relevance || 0;
            const concreteness = round.Concreteness || 0;
            const constructive = round.Constructive || 0;

            if (feedback !== "") {
                const WEIGHTS = { relevance: 30, concreteness: 30, constructive: 40 };
                const roundScore = 
                    (relevance * WEIGHTS.relevance) +
                    (concreteness * WEIGHTS.concreteness) +
                    (constructive * WEIGHTS.constructive);

                node.meaningfulScore += roundScore;
                node.labelCounts.relevance += relevance;
                node.labelCounts.concreteness += concreteness;
                node.labelCounts.constructive += constructive;
            }
        });


            // 建立邊（每個作業獨立紀錄）
            links.push({
                from: reviewerId,
                to: authorId,
                completedAll: rounds.length >= 3,
                hwName: hwName  // 新增作業名稱標記
            });
        });
    });

    // 計算最終分數
    const nodes = Array.from(nodesMap.values()).map(node => {
        const validRounds = node.feedbacks.filter(fb => fb !== "").length;
        const avgScore = validRounds > 0 ? node.meaningfulScore / validRounds : 0;
        return {
            ...node,
            meaningfulScore: Math.min(avgScore, 100),
            isFeedbackEmpty: node.feedbacks.every(fb => fb === "")
        };
    });

    return { nodes, links };
}

export function generateAllLabelsGraph(rawData, hwName = ['HW1']) {
    const container = document.getElementById('review-graph');
    if (!container) {
        console.error("找不到 #review-graph 元素");
        return;
    }
    // 1. 預處理資料
    const { nodes, links } = processReviewerData(rawData, 'all', hwName);

    // 2. 計算正規化比例尺
    const allScores = nodes.map(n => n.meaningfulScore);
    const minScore = Math.min(...allScores);
    const maxScore = Math.max(...allScores);
    const sizeScale = (value) => 5 + ((value - minScore) / (maxScore - minScore)) * 25;

    // 3. 節點樣式轉換
    const visNodes = nodes.map(n => {
        const labels = [
            n.labelCounts.relevance > 0,
            n.labelCounts.concreteness > 0,
            n.labelCounts.constructive > 0
        ];
        const labelCount = labels.filter(Boolean).length;

        // 顏色規則判斷和深度權重
        let color = "#FF86A4"; 
        let border = "#e6f3ff";
        let dashes = false;
        let colorDepth = 0; // 顏色深度權重，用於排序
        //  這是測試用粉紅色 FF86A4

        if (labelCount === 0) {  // 0個標籤、空評論
            color = n.isFeedbackEmpty ? "#f0f8ff" : "#e6f3ff";
            colorDepth = 0; // 最淺
            if (n.isFeedbackEmpty) {  // 空評論+ label 0,0,0
                border = "#62B0D8";  // 深藍色外誆
                dashes = true;  // 虛線
                colorDepth = 0;
            }
            else {
                color = "#BDEDFF";  // 非空評論+ label 0,0,0
                colorDepth = 1;
            }
        } else if (labelCount === 1) {  // 1個標籤
            color = "#94D6FF";
            colorDepth = 2;
        } else if (labelCount === 2) {  // 2個標籤
            color = "#46B1F4";
            colorDepth = 3;
        } else {  // 3個標籤
            color = "#0A6DAA";
            colorDepth = 4; // 最深
        }

        return {
            id: n.id,
            label: n.id,
            value: sizeScale(n.meaningfulScore), // 正規化後尺寸
            meaningfulScore: n.meaningfulScore, // 保留原始分數用於排序
            colorDepth: colorDepth, // 用於排序的顏色深度
            color: {
                background: color,
                border: dashes ? border : color,
                highlight: { background: color, border: border }
            },
            borderWidth: 2,
            borderWidthSelected: 2,
            shape: "dot",
            title: `審查者: ${n.id}\n品質分數: ${n.meaningfulScore.toFixed(1)}\n` +
            `標籤: 相關性(${labels[0] ? '✓' : '✗'}) 具體性(${labels[1] ? '✓' : '✗'}) 建設性(${labels[2] ? '✓' : '✗'})`,
            font: { size: 14 },
            shadow: true,
            margin: 10
        };
    });

    // 按顏色深度和氣泡大小排序 - 深色大氣泡在前（頂部）
    visNodes.sort((a, b) => {
        // 首先按顏色深度排序（深色在前）
        if (a.colorDepth !== b.colorDepth) {
            return b.colorDepth - a.colorDepth;
        }
        // 顏色深度相同時，按氣泡大小排序（大氣泡在前）
        return b.meaningfulScore - a.meaningfulScore;
    });

    // 為排序後的節點設置初始位置（Y軸從上到下）
    visNodes.forEach((node, index) => {
        const totalNodes = visNodes.length;
        const yPosition = -200 + (index / (totalNodes - 1)) * 400; // 從 -200 到 200 的範圍
        const xPosition = (Math.random() - 0.5) * 300; // X軸隨機分散
        
        node.x = xPosition;
        node.y = yPosition;
        node.physics = true; // 允許物理引擎調整，但初始位置已設定
    });

    // 4. 邊資料轉換
    // 在 generateGraph 的邊轉換部分
    const visEdges = links.map(e => ({
        from: e.from,
        to: e.to,
        color: {
            color: e.completedAll ? "#73BEFF" : "#ff6b6b",  // 藍色/紅色
            highlight: e.completedAll ? "#73BEFF" : "#ff6b6b"
        },
        dashes: !e.completedAll,  // 未完成時虛線
        arrows: "to",
        width: 1.5  // 統一寬度
    }));
      


    // 5. 建立 vis.js 網路圖
    const nodesDataSet = new vis.DataSet(visNodes);
    const edgesDataSet = new vis.DataSet(visEdges);
    const data = {
        nodes: nodesDataSet,
        edges: edgesDataSet
    };

    const options = {
        nodes: {
            scaling: {
                min: 20,
                max: 60,
                label: {
                    enabled: true,
                    min: 12,
                    max: 20
                }
            }
        },
        edges: {
            arrowStrikethrough: false,
            selectionWidth: 3
        },
        physics: {
            stabilization: {
                iterations: 150,
                fit: true
            },
            barnesHut: {
                gravitationalConstant: -3000,
                springLength: 200,
                springConstant: 0.04,
                damping: 0.6,
                centralGravity: 0.1
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200
        },
        layout: {
            improvedLayout: true,
            clusterThreshold: 150,
            hierarchical: {
                enabled: false
            }
        }
    };
    //let network;
    if (window.networkInstance) {
        window.networkInstance.setData(data);
        window.networkInstance.setOptions(options);
    }else {
        window.networkInstance = new vis.Network(container, data, options);
        
        // 綁定點擊事件
        window.networkInstance.on('click', function(properties) {
            if (properties.nodes.length > 0) {
                const nodeId = properties.nodes[0];
                const nodeData = nodesDataSet.get(nodeId);
                
                // 只查找已選擇的作業
                const selectedHWs = Array.from(document.getElementById('hw-select').selectedOptions)
                                        .map(opt => opt.value);
                const reviewerRecords = selectedHWs.flatMap(hwName => 
                    rawData[hwName]?.filter(a => a.Reviewer === nodeId) || []
                );
                
                console.log("選擇的作業:", selectedHWs);
                console.log("審查任務:", reviewerRecords);
            }
        });

    }
    updateNetworkInstance(container, data, options, rawData);

    //createOrUpdateNetwork(visNodes, visEdges);  改用 windowsworkInstance呼叫
}