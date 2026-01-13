import { generateAllLabelsGraph } from "./graph_func.js";
import { 
    generateRelevanceGraph,
    generateConcretenessGraph,
    generateConstructiveGraph,
    generateAllGraph,
} from './graph_3labelFunc.js';
// Simplified import - only keep required functions
// Note: We no longer use analysis chart functionality, but keep import to avoid errors



let currentMode = 'all';
let rawData = null;
let currentHW = []; // Will be dynamically loaded from JSON file
let bubbleChartManager = null; // Bubble Chart manager



export function updateGraphMode(mode, hwNames = [...currentHW]) {
    if (!rawData) return;
    currentMode = mode;
    currentHW = [...hwNames]; // Deep copy to avoid reference issues

    // Update button active state
    console.log(`🔵 Updating button state, mode: ${mode}`);
    document.querySelectorAll('.switch-btn').forEach((btn, index) => {
        btn.classList.remove('active');
        console.log(`Remove active state from button ${index}`);
    });
    
    // Add active class to current mode button
    const modeButtons = {
        'all': 0,
        'relevance': 1,
        'concreteness': 2,
        'constructive': 3
    };
    
    const buttons = document.querySelectorAll('.switch-btn');
    const targetIndex = modeButtons[mode];
    console.log(`Target button index: ${targetIndex}, total buttons: ${buttons.length}`);
    
    if (buttons[targetIndex]) {
        buttons[targetIndex].classList.add('active');
        console.log(`✅ Added active state to button ${targetIndex}`);
    } else {
        console.error(`❌ Cannot find button at index ${targetIndex}`);
    }

    switch(mode) {
        case 'all':
            console.log(`Switching to All mode (3-label score average) (${hwNames.join(',')})`);
            generateAllGraph(rawData, hwNames);
            break;
        case 'relevance':
            console.log(`Switching to relevance (${hwNames.join(',')})`);
            generateRelevanceGraph(rawData, hwNames);
            break;
        case 'concreteness':
            console.log(`Switching to concreteness (${hwNames.join(',')})`);
            generateConcretenessGraph(rawData, hwNames);
            break;
        case 'constructive':
            console.log(`Switching to constructive (${hwNames.join(',')})`);
            generateConstructiveGraph(rawData, hwNames);
            break;
    }
    updateBubbleChartOnly(hwNames); // Only update bubble chart, no analysis charts

}

window.updateGraphMode = updateGraphMode;

document.addEventListener("DOMContentLoaded", function () {
    // Initialize assignment label chart button events
    initHwLabelChartEvents();
    
    // Initialize Bubble Chart
    if (window.BubbleChartManager) {
        bubbleChartManager = new window.BubbleChartManager();
    }
    
    // Try to load data from pipeline output first, then fallback to static data
    async function loadData() {
        const dataSources = [
            "../output/final_result.json"       // Pipeline full data
        ];
        
        for (const source of dataSources) {
            try {
                const response = await fetch(source);
                if (response.ok) {
                    const data = await response.json();
                    console.log(`✅ Loaded data from: ${source}`);
                    return { data, source, isSummary: false };
                }
            } catch (e) {
                console.log(`❌ Failed to load from: ${source}`);
            }
        }
        throw new Error("No data source available");
    }
    
    // Convert summary format to display format
    function convertSummaryToDisplayFormat(summary) {
        const result = {};
        
        for (const [hwName, hwData] of Object.entries(summary)) {
            result[hwName] = [];
            const edges = hwData.edges || [];
            
            if (edges.length > 0) {
                const edgeMap = new Map();
                edges.forEach(edge => {
                    if (!edgeMap.has(edge.from)) {
                        edgeMap.set(edge.from, []);
                    }
                    edgeMap.get(edge.from).push(edge);
                });
                
                for (const [reviewerId, reviewerEdges] of edgeMap) {
                    const reviewerData = hwData.reviewers[reviewerId] || {};
                    
                    reviewerEdges.forEach(edge => {
                        const assignment = {
                            Assignment: hwName,
                            Reviewer: reviewerId,
                            Author: edge.to,
                            Round: []
                        };
                        
                        const roundCount = edge.rounds || 1;
                        for (let i = 0; i < roundCount; i++) {
                            const sampleFeedback = reviewerData.sampleFeedbacks?.[i % (reviewerData.sampleFeedbacks?.length || 1)];
                            assignment.Round.push({
                                Feedback: sampleFeedback?.feedback || "Valid feedback",
                                Relevance: i < (reviewerData.relevance || 0) ? 1 : 0,
                                Concreteness: i < (reviewerData.concreteness || 0) ? 1 : 0,
                                Constructive: i < (reviewerData.constructive || 0) ? 1 : 0
                            });
                        }
                        
                        result[hwName].push(assignment);
                    });
                }
                
                for (const [reviewerId, reviewerData] of Object.entries(hwData.reviewers)) {
                    if (!edgeMap.has(reviewerId) && reviewerData.validFeedbacks > 0) {
                        const assignment = {
                            Assignment: hwName,
                            Reviewer: reviewerId,
                            Author: "NULL",
                            Round: []
                        };
                        
                        for (let i = 0; i < reviewerData.validFeedbacks; i++) {
                            const sampleFeedback = reviewerData.sampleFeedbacks?.[i % (reviewerData.sampleFeedbacks?.length || 1)];
                            assignment.Round.push({
                                Feedback: sampleFeedback?.feedback || "Valid feedback",
                                Relevance: i < reviewerData.relevance ? 1 : 0,
                                Concreteness: i < reviewerData.concreteness ? 1 : 0,
                                Constructive: i < reviewerData.constructive ? 1 : 0
                            });
                        }
                        
                        result[hwName].push(assignment);
                    }
                }
            } else {
                for (const [reviewerId, reviewerData] of Object.entries(hwData.reviewers)) {
                    const assignment = {
                        Assignment: hwName,
                        Reviewer_: reviewerId,
                        Author: reviewerData.authors?.[0] || "NULL",
                        Round: []
                    };
                    
                    for (let i = 0; i < (reviewerData.validFeedbacks || 0); i++) {
                        const sampleFeedback = reviewerData.sampleFeedbacks?.[i % (reviewerData.sampleFeedbacks?.length || 1)];
                        assignment.Round.push({
                            Feedback: sampleFeedback?.feedback || "Valid feedback",
                            Relevance: i < (reviewerData.relevance || 0) ? 1 : 0,
                            Concreteness: i < (reviewerData.concreteness || 0) ? 1 : 0,
                            Constructive: i < (reviewerData.constructive || 0) ? 1 : 0
                        });
                    }
                    
                    if (reviewerData.authors?.length > 0) {
                        reviewerData.authors.forEach(author => {
                            result[hwName].push({ ...assignment, Author: author });
                        });
                    } else {
                        result[hwName].push(assignment);
                    }
                }
            }
        }
        
        return result;
    }
    
    loadData()
        .then(({ data, source, isSummary }) => {
            rawData = data;
            
            // Dynamically generate assignment options
            const hwKeys = Object.keys(data).sort(); // Get and sort assignment list
            console.log("📋 Assignments found in JSON file:", hwKeys);
            
            // Update global variable
            currentHW = [...hwKeys];
            
            // Dynamically generate select options
            const hwSelect = document.getElementById('hw-select');
            if (hwSelect) {
                // Clear existing options
                hwSelect.innerHTML = '';
                
                // Add new options
                hwKeys.forEach(hwKey => {
                    const option = document.createElement('option');
                    option.value = hwKey;
                    option.textContent = hwKey;
                    option.selected = true; // Select all by default
                    hwSelect.appendChild(option);
                });
                
                console.log(`✅ Dynamically generated ${hwKeys.length} assignment options`);
            }
            
            console.log("Sample data:", data.HW4?.[15]);
            console.log(`📦 Data source: ${source}${isSummary ? ' (summary mode - fast)' : ''}`);
            updateGraphMode('all', currentHW); // Pass currentHW during initialization
        })
        .catch(error => {
            console.error("Failed to load JSON:", error);
        });
});


// GO button
document.getElementById('hw-apply-btn').addEventListener('click', () => {
    const select = document.getElementById('hw-select');
    const selectedHWs = Array.from(select.selectedOptions).map(opt => opt.value);
    if (selectedHWs.length === 0) {
        alert("Please select at least one assignment!");
        return;
    }
    currentHW = [...selectedHWs];
    // Force regenerate chart with current mode
    updateGraphMode(currentMode, currentHW);
});

// Simplified function to only update bubble chart
function updateBubbleChartOnly(hwNames) {
    console.log("🫧 updateBubbleChartOnly called", hwNames);
    if (!rawData || !bubbleChartManager) return;
    
    try {
        console.log("Only updating bubble chart", { hwNames });
        
        // Prepare network data for Bubble Chart
        const networkData = prepareNetworkDataForBubbleChart(hwNames);
        if (networkData) {
            bubbleChartManager.updateData(networkData);
        }
    } catch (error) {
        console.error("Error updating bubble chart:", error);
    }
}

function updateAnalysisCharts(hwNames) {
    // This function is disabled - no longer processing analysis charts as HTML elements have been removed
    console.log("⚠️ updateAnalysisCharts called but disabled", hwNames);
    return;
}

// Prepare network data for Bubble Chart
function prepareNetworkDataForBubbleChart(hwNames) {
    if (!rawData) return null;

    const studentData = new Map();
    
    hwNames.forEach(hwName => {
        const hwData = rawData[hwName] || [];
        console.log(`Processing ${hwName}, total ${hwData.length} records`);
        
        hwData.forEach(assignment => {
            const reviewer = assignment.Reviewer || assignment.reviewer;
            const author = assignment.Author || assignment.author;
            
            // Ensure both students are in the data
            [reviewer, author].forEach(studentId => {
                if (studentId && !studentData.has(studentId)) {
                    studentData.set(studentId, {
                        id: studentId,
                        name: studentId,
                        validComments: 0,        // Completed assignment count (for review participation rate)
                        validRounds: 0,          // Valid round count (for label ratio calculation)
                        assignedTasks: 0,
                        relevanceCount: 0,
                        concretenessCount: 0,
                        constructiveCount: 0
                    });
                }
            });
            
            // Process reviewer data
            if (reviewer && studentData.has(reviewer)) {
                const reviewerData = studentData.get(reviewer);
                reviewerData.assignedTasks++;
                
                // Check if review task is completed (has any valid feedback)
                let hasValidFeedback = false;  // Whether this assignment has valid feedback
                let validRoundsCount = 0;       // Valid round count in this assignment
                let relevanceCount = 0;
                let concretenessCount = 0;
                let constructiveCount = 0;
                
                if (assignment.Round && assignment.Round.length > 0) {
                    assignment.Round.forEach(round => {
                        // Check if feedback content is valid
                        if (round.Feedback && round.Feedback.trim() !== "") {
                            hasValidFeedback = true;  // Mark this assignment has valid feedback
                            validRoundsCount++;       // Count valid rounds
                            
                            // Count labels
                            if (round.Relevance === 1) {
                                relevanceCount++;
                            }
                            if (round.Concreteness === 1) {
                                concretenessCount++;
                            }
                            if (round.Constructive === 1) {
                                constructiveCount++;
                            }
                        }
                    });
                }
                
                // If this assignment has valid feedback, count as completed review task
                if (hasValidFeedback) {
                    reviewerData.validComments++;
                }
                
                // Accumulate valid round count (for label ratio calculation)
                reviewerData.validRounds += validRoundsCount;
                
                reviewerData.relevanceCount += relevanceCount;
                reviewerData.concretenessCount += concretenessCount;
                reviewerData.constructiveCount += constructiveCount;
            }
        });
    });
    
    // Convert to node format
    const nodes = Array.from(studentData.values()).map(student => ({
        id: student.id,
        label: student.name,
        group: 'student',
        validComments: student.validComments,    // Completed assignment count (for review participation)
        validRounds: student.validRounds,        // Valid round count (for label ratio)
        assignedTasks: student.assignedTasks,
        relevanceCount: student.relevanceCount,
        concretenessCount: student.concretenessCount,
        constructiveCount: student.constructiveCount
    }));
    
    console.log(`Bubble Chart preparation complete: ${nodes.length} students`);
    console.log('First 5 students data:', nodes.slice(0, 5));
    
    return { nodes, edges: [] }; // Bubble Chart only needs node data
}

// Initialize assignment label frequency chart button events
function initHwLabelChartEvents() {
    console.log('Initializing assignment label chart button events...');
    
    // All comments chart buttons
    const generateBtn = document.getElementById('generateHwChart');
    const downloadBtn = document.getElementById('downloadHwChart');
    
    // Valid comments only chart buttons
    const generateValidBtn = document.getElementById('generateHwValidChart');
    const downloadValidBtn = document.getElementById('downloadHwValidChart');
    
    console.log('Button element check:', {
        generateBtn: !!generateBtn,
        downloadBtn: !!downloadBtn,
        generateValidBtn: !!generateValidBtn,
        downloadValidBtn: !!downloadValidBtn
    });
    
    let currentHwChart = null;
    let currentHwValidChart = null;
    
    // All comments chart event handling
    if (generateBtn) {
        generateBtn.addEventListener('click', async () => {
            console.log('Generating assignment label frequency chart (all comments)...');
            generateBtn.textContent = 'Generating...';
            generateBtn.disabled = true;
            
            try {
                currentHwChart = await generateHwLabelChart();
                if (currentHwChart) {
                    console.log('Chart generated successfully (all comments)');
                    downloadBtn.disabled = false;
                }
            } catch (error) {
                console.error('Failed to generate chart:', error);
                alert('Failed to generate chart. Check console for error details.');
            } finally {
                generateBtn.textContent = 'Generate Chart (All Comments)';
                generateBtn.disabled = false;
            }
        });
    }
    
    if (downloadBtn) {
        downloadBtn.disabled = true;
        downloadBtn.addEventListener('click', () => {
            if (currentHwChart) {
                saveChartAsPNG(currentHwChart, 'hwLabelChart_all.png');
            } else {
                alert('Please generate chart first');
            }
        });
    }
    
    // Valid comments only chart event handling
    if (generateValidBtn) {
        console.log('Binding valid comments chart generate button event');
        generateValidBtn.addEventListener('click', async () => {
            console.log('Valid comments chart generate button clicked');
            console.log('Generating assignment label frequency chart (valid comments only)...');
            generateValidBtn.textContent = 'Generating...';
            generateValidBtn.disabled = true;
            
            try {
                currentHwValidChart = await generateHwEnableLabelChart();
                if (currentHwValidChart) {
                    console.log('Chart generated successfully (valid comments only)');
                    downloadValidBtn.disabled = false;
                } else {
                    console.log('Chart generation failed: returned null');
                }
            } catch (error) {
                console.error('Failed to generate chart:', error);
                alert('Failed to generate chart. Check console for error details.');
            } finally {
                generateValidBtn.textContent = 'Generate Chart (Labeled Only)';
                generateValidBtn.disabled = false;
            }
        });
    } else {
        console.log('Warning: Valid comments chart generate button not found');
    }
    
    if (downloadValidBtn) {
        downloadValidBtn.disabled = true;
        downloadValidBtn.addEventListener('click', () => {
            if (currentHwValidChart) {
                saveChartAsPNG(currentHwValidChart, 'hwLabelChart_valid.png');
            } else {
                alert('Please generate chart first');
            }
        });
    }
}

