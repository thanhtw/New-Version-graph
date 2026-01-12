import { revelanceGraph } from "./graph_3labelFunc.js";

document.addEventListener("DOMContentLoaded", function () {
    fetch("../function/3labeled_processed_totalData.json")
        .then(response => response.json())
        .then(rawData => {
            console.log("Raw data sample:", rawData.HW4?.[0]);
            try {
                // Call generateGraph directly, data processing is integrated inside the function
                revelanceGraph(rawData);
            }
            catch (err) {
                console.error("Error processing data:", err);
            }
        })
        .catch(error => {
            console.error("Failed to load JSON:", error);
        });
});

