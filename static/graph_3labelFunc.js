import { processReviewerData } from './graph_func.js';

export function updateNetworkInstance(container, data, options, rawData) {
    if (window.networkInstance) {
        // Stop physics engine to avoid residual animations
        window.networkInstance.setOptions({ physics: { enabled: false } });
        // Completely clear old data
        window.networkInstance.setData({ nodes: [], edges: [] });
        // Set new data and options
        window.networkInstance.setData(data);
        window.networkInstance.setOptions({ ...options, physics: { enabled: true } });
        // Force redraw
        window.networkInstance.redraw();
    } else {
        window.networkInstance = new vis.Network(container, data, options);
        window.networkInstance.on('click', function(properties) {
            if (properties.nodes.length > 0) {
                const nodeId = properties.nodes[0];
                const nodeData = new vis.DataSet(data.nodes).get(nodeId);
                const selectedHWs = Array.from(document.getElementById('hw-select').selectedOptions)
                                        .map(opt => opt.value);
                const reviewerRecords = selectedHWs.flatMap(hwName => 
                    rawData[hwName]?.filter(a => a.Reviewer_Name === nodeId) || []
                );
                console.log("Review tasks:", reviewerRecords);
            }
        });
    }
}

export function generateGraph(rawData, mode, hwNames) {
    const container = document.getElementById('review-graph');
    if (!container) return;

    // Data processing
    const { nodes, links } = processReviewerData(rawData, mode, hwNames);

    // Node size calculation - Changed to Assignment level participation rate (consistent with bubble chart)
    const allCompletionRates = nodes.map(n => {
        // Calculate how many Assignments have valid reviews
        const assignmentCount = n.feedbacks.length; // Total assigned Assignments
        const completedAssignments = n.feedbacks.filter(fb => fb !== "").length; // Completed Assignments
        return assignmentCount > 0 ? completedAssignments / assignmentCount : 0;
    });
    const minRate = Math.min(...allCompletionRates);
    const maxRate = Math.max(...allCompletionRates);
    const sizeScale = (rate) => 15 + (rate * 35); // Range of 15-50

    // Node color rules (4 levels)
    const colorConfig = {
        relevance: { 
            colors: ["#FFEEB7", "#FFD753", "#F1BC0D", "#D4A302"], 
            title: 'Relevance Score' 
        },
        concreteness: { 
            colors: ["#CFFFCA", "#95ED65", "#54AF23", "#327111"], 
            title: 'Concreteness Score' 
        },
        constructive: { 
            colors: ["#F1DCFF", "#C78EED", "#9444CA", "#590A8E"], 
            title: 'Constructive Score' 
        },
        all: {
            colors: ["#F0F0F0", "#E0E0E0", "#757575", "#424242"],
            title: 'Overall Performance Score'
        }
    };

    // Node styles
    const visNodes = nodes.map(n => {
        // Assignment level participation rate calculation (consistent with bubble chart)
        const assignmentCount = n.feedbacks.length; // Total assigned Assignments
        const completedAssignments = n.feedbacks.filter(fb => fb !== "").length; // Completed Assignments
        const completionRate = assignmentCount > 0 ? completedAssignments / assignmentCount : 0;
        
        // Keep original score calculation logic (for color)
        const totalFeedbacks = n.feedbacks.filter(fb => fb !== "").length;
        let score;
        
        // Score calculation logic
        if (mode === 'all') {
            // All mode: Calculate average of three label scores
            if (totalFeedbacks > 0) {
                const relevanceScore = n.labelCounts.relevance / totalFeedbacks;
                const concretenessScore = n.labelCounts.concreteness / totalFeedbacks;
                const constructiveScore = n.labelCounts.constructive / totalFeedbacks;
                score = (relevanceScore + concretenessScore + constructiveScore) / 3;
                
                // Debug info: Only show detailed calculation for first 3 nodes
                if (n.id === 'D1018525' || Math.random() < 0.05) {
                    console.log(`[All Mode] Reviewer ${n.id}:`);
                    console.log(`  Total assigned Assignments: ${assignmentCount}`);
                    console.log(`  Completed Assignments: ${completedAssignments}`);
                    console.log(`  Review participation rate: ${(completionRate * 100).toFixed(1)}%`);
                    console.log(`  Valid review Rounds: ${totalFeedbacks}`);
                    console.log(`  Relevance labels: ${n.labelCounts.relevance} (score: ${relevanceScore.toFixed(3)})`);
                    console.log(`  Concreteness labels: ${n.labelCounts.concreteness} (score: ${concretenessScore.toFixed(3)})`);
                    console.log(`  Constructive labels: ${n.labelCounts.constructive} (score: ${constructiveScore.toFixed(3)})`);
                    console.log(`  All mode score: ${score.toFixed(3)}`);
                }
            } else {
                score = 0;
            }
        } else {
            // Single label mode
            score = totalFeedbacks > 0 ? n.labelCounts[mode] / totalFeedbacks : 0;
        }
        
        // 4-level color calculation
        let color;
        if (score >= 0.75) color = colorConfig[mode].colors[3];      // Darkest (75% and above)
        else if (score >= 0.5) color = colorConfig[mode].colors[2]; // Dark (50-75%)
        else if (score >= 0.25) color = colorConfig[mode].colors[1]; // Light (25-50%)
        else color = colorConfig[mode].colors[0];                   // Lightest (below 25%)

        return {
            id: n.id,
            label: n.id,
            value: sizeScale(completionRate), // Use Assignment level participation rate for size
            color: { background: color, border: color },
            borderWidth: 0,
            shape: "dot",
            title: `Reviewer: ${n.id}\n${colorConfig[mode].title}: ${Math.round(score * 100)}%\nReview participation rate: ${Math.round(completionRate * 100)}%`
        };
    });

    // Edge styles
    const visEdges = links.map(e => ({
        from: e.from,
        to: e.to,
        color: { color: e.completedAll ? "#73BEFF" : "#ff6b6b", highlight: e.completedAll ? "#73BEFF" : "#ff6b6b" },
        dashes: !e.completedAll,
        arrows: "to",
        width: 1.5
    }));

    // Create DataSet and options
    const data = { nodes: new vis.DataSet(visNodes), edges: new vis.DataSet(visEdges) };
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
                iterations: 100,
                fit: true
            },
            barnesHut: {
                gravitationalConstant: -2000,
                springLength: 150,
                damping: 0.5
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200
        }
    };

    // Update instance
    updateNetworkInstance(container, data, options, rawData);
}

export function generateRelevanceGraph(rawData, hwNames = ['HW1']) {
    generateGraph(rawData, 'relevance', hwNames);
}

export function generateConcretenessGraph(rawData, hwNames = ['HW1']) {
    generateGraph(rawData, 'concreteness', hwNames);
}

export function generateConstructiveGraph(rawData, hwNames = ['HW1']) {
    generateGraph(rawData, 'constructive', hwNames);
}

export function generateAllGraph(rawData, hwNames = ['HW1']) {
    generateGraph(rawData, 'all', hwNames);
}
