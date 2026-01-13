#!/usr/bin/env python3
"""
Data Organizer for Review Data Pipeline
Organizes flat JSON records into structured format grouped by assignment.
"""

import json
from collections import defaultdict
from typing import Dict, List, Any


def organize_data(input_data: List[Dict]) -> Dict[str, List]:
    """
    Organize flat records into structured format grouped by assignment.
    
    Args:
        input_data: List of flat records
        
    Returns:
        Dictionary with assignments as keys
    """
    assignment_dict = defaultdict(lambda: defaultdict(lambda: {
        "Assignment": "",
        "Author": "",
        "Reviewer": "",
        "Round": []
    }))

    for record in input_data:
        assignment_name = record.get("Assignment", "Unknown")
        author = record.get("Author", "")
        reviewer = record.get("Reviewer", "")
        
        if not author or not reviewer:
            continue

        key = (author, reviewer)

        # Initialize structure
        if not assignment_dict[assignment_name][key]["Assignment"]:
            assignment_dict[assignment_name][key]["Assignment"] = assignment_name
            assignment_dict[assignment_name][key]["Author"] = author
            assignment_dict[assignment_name][key]["Reviewer"] = reviewer

        # Add Round data
        assignment_dict[assignment_name][key]["Round"].append({
            "Round": record.get("Round", 1),
            "Time": record.get("Time", ""),
            "Feedback": record.get("Feedback", ""),            
        })

    return {
        assignment: list(records.values()) 
        for assignment, records in assignment_dict.items()
    }


def filter_assignments(organized_data: Dict, start_hw: int, end_hw: int) -> Dict:
    """
    Filter data to include only specified homework range.
    
    Args:
        organized_data: Organized data dictionary
        start_hw: Starting homework number (e.g., 1 for HW1)
        end_hw: Ending homework number (e.g., 7 for HW7)
        
    Returns:
        Filtered dictionary
    """
    filtered_data = {}
    
    for hw in range(start_hw, end_hw + 1):
        key = f"HW{hw}"
        if key in organized_data:
            filtered_data[key] = organized_data[key]
    
    return filtered_data


def organize_json_file(input_path: str, output_path: str, hw_start: int = 1, hw_end: int = 7) -> dict:
    """
    Read JSON file, organize data, and save to output file.
    
    Returns:
        dict with organization statistics
    """
    print(f"Reading input file: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    
    print(f"Organizing {len(input_data)} records...")
    organized_data = organize_data(input_data)
    
    print(f"Filtering HW{hw_start} to HW{hw_end}...")
    filtered_data = filter_assignments(organized_data, hw_start, hw_end)
    
    print(f"Writing output file: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)
    
    # Calculate statistics
    total_assignments = sum(len(v) for v in filtered_data.values())
    hw_counts = {k: len(v) for k, v in filtered_data.items()}
    
    stats = {
        "input_records": len(input_data),
        "homework_count": len(filtered_data),
        "total_assignments": total_assignments,
        "hw_breakdown": hw_counts
    }
    
    print(f"Organized into {len(filtered_data)} homework sets with {total_assignments} assignments")
    return stats


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3:
        hw_start = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        hw_end = int(sys.argv[4]) if len(sys.argv) > 4 else 7
        organize_json_file(sys.argv[1], sys.argv[2], hw_start, hw_end)
    else:
        print("Usage: python data_organizer.py <input.json> <output.json> [hw_start] [hw_end]")
