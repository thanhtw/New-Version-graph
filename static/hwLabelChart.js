// All Assignment Label Frequency Statistics Chart - Node.js Version
const fs = require('fs');
const path = require('path');
const { createCanvas } = require('canvas');
const Chart = require('chart.js/auto');

// Load 3-label data
function load3LabelData() {
    try {
        const dataPath = path.join(__dirname, '../function/3labeled_processed_totalData.json');
        const rawData = fs.readFileSync(dataPath, 'utf8');
        return JSON.parse(rawData);
    } catch (error) {
        console.error('Error loading 3label data:', error);
        return null;
    }
}

// Calculate 3-label frequency for each assignment
function calculateHwLabelFrequency(data) {
    const hwStats = {};
    
    // Initialize statistics structure
    Object.keys(data).forEach(hwName => {
        hwStats[hwName] = {
            total: 0,
            relevance: 0,
            concreteness: 0,
            constructive: 0
        };
    });
    
    // Count label frequency for each assignment
    Object.entries(data).forEach(([hwName, hwData]) => {
        hwData.forEach(student => {
            if (student.Round && Array.isArray(student.Round)) {
                student.Round.forEach(round => {
                    // Only count rounds with complete data
                    if (round.Relevance !== undefined && round.Concreteness !== undefined && round.Constructive !== undefined) {
                        hwStats[hwName].total++;
                        if (round.Relevance === 1) hwStats[hwName].relevance++;
                        if (round.Concreteness === 1) hwStats[hwName].concreteness++;
                        if (round.Constructive === 1) hwStats[hwName].constructive++;
                    }
                });
            }
        });
    });
    
    // Calculate percentage
    const percentageStats = {};
    Object.entries(hwStats).forEach(([hwName, stats]) => {
        if (stats.total > 0) {
            percentageStats[hwName] = {
                relevance: (stats.relevance / stats.total) * 100,
                concreteness: (stats.concreteness / stats.total) * 100,
                constructive: (stats.constructive / stats.total) * 100,
                total: stats.total
            };
        } else {
            percentageStats[hwName] = {
                relevance: 0,
                concreteness: 0,
                constructive: 0,
                total: 0
            };
        }
    });
    
    return percentageStats;
}

// Create chart
function createHwLabelChart(stats) {
    // Create Canvas
    const canvas = createCanvas(800, 600);
    const ctx = canvas.getContext('2d');
    
    // Prepare data
    const hwNames = Object.keys(stats).sort(); // Sort assignment names
    const relevanceData = hwNames.map(hw => stats[hw].relevance);
    const concretenessData = hwNames.map(hw => stats[hw].concreteness);
    const constructiveData = hwNames.map(hw => stats[hw].constructive);
    
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hwNames,
            datasets: [
                {
                    label: 'Relevance',
                    data: relevanceData,
                    backgroundColor: 'rgba(255, 206, 84, 0.8)',
                    borderColor: 'rgba(255, 206, 84, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Concreteness',
                    data: concretenessData,
                    backgroundColor: 'rgba(75, 192, 192, 0.8)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Constructive',
                    data: constructiveData,
                    backgroundColor: 'rgba(153, 102, 255, 0.8)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: false,
            animation: false,
            plugins: {
                title: {
                    display: true,
                    text: 'All Assignment 3-Label Frequency Statistics',
                    font: {
                        size: 18,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 14
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Assignment Name',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        font: {
                            size: 12
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Frequency (%)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        font: {
                            size: 12
                        },
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            elements: {
                bar: {
                    borderWidth: 2
                }
            }
        }
    });
    
    return { chart, canvas };
}

// Save chart as PNG
function saveChartAsPNG(canvas, filename = 'hwLabelChart.png') {
    const outputPath = path.join(__dirname, filename);
    const buffer = canvas.toBuffer('image/png');
    fs.writeFileSync(outputPath, buffer);
    console.log(`Chart saved to: ${outputPath}`);
}

// Main execution function
async function initHwLabelChart() {
    console.log('Loading 3-label data...');
    
    const data = load3LabelData();
    if (!data) {
        console.error('Failed to load 3-label data');
        return;
    }
    
    console.log('Calculating label frequency statistics...');
    const stats = calculateHwLabelFrequency(data);
    console.log('Label frequency statistics result:', stats);
    
    // Create chart
    const { chart, canvas } = createHwLabelChart(stats);
    
    // Save as PNG
    saveChartAsPNG(canvas, 'hwLabelChart.png');
    
    // Display statistics summary
    displayStatsSummary(stats);
}

// Display statistics summary
function displayStatsSummary(stats) {
    console.log('\n=== Statistics Summary ===');
    console.log('Assignment\t\tRelevance (%)\tConcreteness (%)\tConstructive (%)\tTotal Reviews');
    console.log('---'.repeat(25));
    
    Object.entries(stats).sort().forEach(([hwName, data]) => {
        console.log(`${hwName}\t\t${data.relevance.toFixed(1)}%\t\t${data.concreteness.toFixed(1)}%\t\t${data.constructive.toFixed(1)}%\t\t${data.total}`);
    });
}

// Export functions
module.exports = { initHwLabelChart, calculateHwLabelFrequency, createHwLabelChart, saveChartAsPNG };

// If running this file directly
if (require.main === module) {
    initHwLabelChart();
}