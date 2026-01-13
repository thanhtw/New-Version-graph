#!/usr/bin/env python3
"""
Score-Review Correlation Analysis
Analyzes the relationship between student homework scores and their peer review activity.
"""

import json
import csv
import os
from pathlib import Path
from collections import defaultdict
import statistics

# Paths
PIPELINE_DIR = Path(__file__).parent.absolute()
SCORE_FILE = PIPELINE_DIR / "score" / "Score-By-HW.csv"
OUTPUT_DIR = PIPELINE_DIR / "output"
RESULT_FILE = OUTPUT_DIR / "final_result.json"


def load_score_data(score_file=SCORE_FILE):
    """Load student scores from CSV file."""
    scores = {}
    
    if not score_file.exists():
        print(f"Score file not found: {score_file}")
        return scores
    
    with open(score_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            student_id = row.get('ID', '').strip()
            if not student_id:
                continue
            
            scores[student_id] = {
                'name': row.get('Name', ''),
                'pre': safe_int(row.get('Pre', 0)),
                'midterm': safe_int(row.get('Midterm', 0)),
                'final': safe_int(row.get('Final', 0)),
                'hw_scores': {
                    'HW1': safe_int(row.get('HW1', 0)),
                    'HW2': safe_int(row.get('HW2', 0)),
                    'HW3': safe_int(row.get('HW3', 0)),
                    'HW4': safe_int(row.get('HW4', 0)),
                    'HW5': safe_int(row.get('HW5', 0)),
                    'HW6': safe_int(row.get('HW6', 0)),
                    'HW7': safe_int(row.get('HW7', 0)),
                }
            }
    
    print(f"Loaded scores for {len(scores)} students")
    return scores


def safe_int(value):
    """Safely convert value to int."""
    try:
        return int(float(value)) if value else 0
    except (ValueError, TypeError):
        return 0


def load_review_data(result_file=RESULT_FILE):
    """Load peer review data from final_result.json."""
    if not result_file.exists():
        print(f"Review data not found: {result_file}")
        return {}
    
    with open(result_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_review_activity(review_data):
    """
    Analyze review activity for each student.
    Returns dict with reviews given and received per student per HW.
    """
    students = defaultdict(lambda: {
        'reviews_given': defaultdict(list),
        'reviews_received': defaultdict(list),
        'total_given': 0,
        'total_received': 0,
        'quality_given': {'relevance': 0, 'concreteness': 0, 'constructive': 0},
        'quality_received': {'relevance': 0, 'concreteness': 0, 'constructive': 0}
    })
    
    for hw_name, assignments in review_data.items():
        if not isinstance(assignments, list):
            continue
            
        for assignment in assignments:
            reviewer = assignment.get('Reviewer') or assignment.get('reviewer', '')
            author = assignment.get('Author') or assignment.get('author', '')
            rounds = assignment.get('Round', [])
            
            if not reviewer:
                continue
            
            for round_data in rounds:
                feedback = round_data.get('Feedback') or round_data.get('feedback', '')
                if not feedback or not feedback.strip():
                    continue
                
                relevance = round_data.get('Relevance', 0) or round_data.get('relevance', 0)
                concreteness = round_data.get('Concreteness', 0) or round_data.get('concreteness', 0)
                constructive = round_data.get('Constructive', 0) or round_data.get('constructive', 0)
                
                # Record review given by reviewer
                students[reviewer]['reviews_given'][hw_name].append({
                    'to': author,
                    'feedback': feedback,
                    'relevance': relevance,
                    'concreteness': concreteness,
                    'constructive': constructive
                })
                students[reviewer]['total_given'] += 1
                if relevance == 1:
                    students[reviewer]['quality_given']['relevance'] += 1
                if concreteness == 1:
                    students[reviewer]['quality_given']['concreteness'] += 1
                if constructive == 1:
                    students[reviewer]['quality_given']['constructive'] += 1
                
                # Record review received by author
                if author and author != "NULL":
                    students[author]['reviews_received'][hw_name].append({
                        'from': reviewer,
                        'feedback': feedback,
                        'relevance': relevance,
                        'concreteness': concreteness,
                        'constructive': constructive
                    })
                    students[author]['total_received'] += 1
                    if relevance == 1:
                        students[author]['quality_received']['relevance'] += 1
                    if concreteness == 1:
                        students[author]['quality_received']['concreteness'] += 1
                    if constructive == 1:
                        students[author]['quality_received']['constructive'] += 1
    
    return dict(students)


def calculate_correlations(scores, review_activity):
    """Calculate correlations between scores and review metrics."""
    # Prepare data points for correlation analysis
    hw_correlations = {}
    hw_list = ['HW1', 'HW2', 'HW3', 'HW4', 'HW5', 'HW6', 'HW7']
    
    for hw in hw_list:
        data_points = []
        
        for student_id, score_data in scores.items():
            hw_score = score_data['hw_scores'].get(hw, 0)
            
            if student_id in review_activity:
                activity = review_activity[student_id]
                given_count = len(activity['reviews_given'].get(hw, []))
                received_count = len(activity['reviews_received'].get(hw, []))
                
                # Calculate individual quality scores for given reviews in this HW
                given_reviews = activity['reviews_given'].get(hw, [])
                quality_score = 0
                relevance_score = 0
                concreteness_score = 0
                constructive_score = 0
                
                if given_reviews:
                    total_quality = sum(
                        r['relevance'] + r['concreteness'] + r['constructive'] 
                        for r in given_reviews
                    )
                    quality_score = total_quality / (len(given_reviews) * 3) * 100
                    
                    # Individual label percentages
                    relevance_score = sum(r['relevance'] for r in given_reviews) / len(given_reviews) * 100
                    concreteness_score = sum(r['concreteness'] for r in given_reviews) / len(given_reviews) * 100
                    constructive_score = sum(r['constructive'] for r in given_reviews) / len(given_reviews) * 100
                
                data_points.append({
                    'student_id': student_id,
                    'name': score_data['name'],
                    'hw_score': hw_score,
                    'reviews_given': given_count,
                    'reviews_received': received_count,
                    'quality_score': round(quality_score, 2),
                    'relevance_score': round(relevance_score, 2),
                    'concreteness_score': round(concreteness_score, 2),
                    'constructive_score': round(constructive_score, 2)
                })
            else:
                data_points.append({
                    'student_id': student_id,
                    'name': score_data['name'],
                    'hw_score': hw_score,
                    'reviews_given': 0,
                    'reviews_received': 0,
                    'quality_score': 0,
                    'relevance_score': 0,
                    'concreteness_score': 0,
                    'constructive_score': 0
                })
        
        # Calculate correlation coefficient (Pearson)
        if len(data_points) > 1:
            hw_scores = [d['hw_score'] for d in data_points]
            given_counts = [d['reviews_given'] for d in data_points]
            quality_scores = [d['quality_score'] for d in data_points]
            relevance_scores = [d['relevance_score'] for d in data_points]
            concreteness_scores = [d['concreteness_score'] for d in data_points]
            constructive_scores = [d['constructive_score'] for d in data_points]
            
            hw_correlations[hw] = {
                'data_points': data_points,
                'correlation_given': calculate_pearson(hw_scores, given_counts),
                'correlation_quality': calculate_pearson(hw_scores, quality_scores),
                'correlation_relevance': calculate_pearson(hw_scores, relevance_scores),
                'correlation_concreteness': calculate_pearson(hw_scores, concreteness_scores),
                'correlation_constructive': calculate_pearson(hw_scores, constructive_scores),
                'stats': {
                    'avg_score': round(statistics.mean(hw_scores), 2),
                    'avg_given': round(statistics.mean(given_counts), 2),
                    'avg_quality': round(statistics.mean(quality_scores), 2),
                    'avg_relevance': round(statistics.mean(relevance_scores), 2),
                    'avg_concreteness': round(statistics.mean(concreteness_scores), 2),
                    'avg_constructive': round(statistics.mean(constructive_scores), 2),
                    'std_score': round(statistics.stdev(hw_scores), 2) if len(hw_scores) > 1 else 0,
                    'total_students': len(data_points)
                }
            }
    
    return hw_correlations


def calculate_pearson(x, y):
    """Calculate Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0
    
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    
    sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
    sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
    
    denominator = (sum_sq_x * sum_sq_y) ** 0.5
    
    if denominator == 0:
        return 0
    
    return round(numerator / denominator, 4)


def generate_analysis_report():
    """Generate complete analysis report."""
    print("Loading score data...")
    scores = load_score_data()
    
    print("Loading review data...")
    review_data = load_review_data()
    
    if not scores:
        return {"error": "No score data found"}
    
    if not review_data:
        return {"error": "No review data found. Please run the pipeline first."}
    
    print("Analyzing review activity...")
    review_activity = analyze_review_activity(review_data)
    
    print("Calculating correlations...")
    correlations = calculate_correlations(scores, review_activity)
    
    # Prepare summary
    summary = {
        'total_students': len(scores),
        'students_with_reviews': len([s for s in review_activity.values() if s['total_given'] > 0]),
        'total_reviews_given': sum(s['total_given'] for s in review_activity.values()),
        'total_reviews_received': sum(s['total_received'] for s in review_activity.values()),
    }
    
    # Prepare student details
    student_details = []
    for student_id, score_data in scores.items():
        activity = review_activity.get(student_id, {
            'total_given': 0,
            'total_received': 0,
            'quality_given': {'relevance': 0, 'concreteness': 0, 'constructive': 0},
            'reviews_given': {},
            'reviews_received': {}
        })
        
        # Calculate overall quality score
        total_given = activity['total_given']
        quality_pct = 0
        relevance_pct = 0
        concreteness_pct = 0
        constructive_pct = 0
        
        if total_given > 0:
            relevance_pct = round(activity['quality_given']['relevance'] / total_given * 100, 2)
            concreteness_pct = round(activity['quality_given']['concreteness'] / total_given * 100, 2)
            constructive_pct = round(activity['quality_given']['constructive'] / total_given * 100, 2)
            quality_pct = round((relevance_pct + concreteness_pct + constructive_pct) / 3, 2)
        
        # Calculate average HW score
        hw_scores = list(score_data['hw_scores'].values())
        avg_hw_score = round(sum(hw_scores) / len(hw_scores), 2) if hw_scores else 0
        
        # Calculate per-HW quality breakdown
        hw_quality = {}
        for hw in ['HW1', 'HW2', 'HW3', 'HW4', 'HW5', 'HW6', 'HW7']:
            given_reviews = activity['reviews_given'].get(hw, [])
            if given_reviews:
                hw_quality[hw] = {
                    'given': len(given_reviews),
                    'received': len(activity['reviews_received'].get(hw, [])),
                    'relevance': round(sum(r['relevance'] for r in given_reviews) / len(given_reviews) * 100, 2),
                    'concreteness': round(sum(r['concreteness'] for r in given_reviews) / len(given_reviews) * 100, 2),
                    'constructive': round(sum(r['constructive'] for r in given_reviews) / len(given_reviews) * 100, 2),
                    'quality': round(sum(r['relevance'] + r['concreteness'] + r['constructive'] for r in given_reviews) / (len(given_reviews) * 3) * 100, 2)
                }
            else:
                hw_quality[hw] = {
                    'given': 0,
                    'received': len(activity['reviews_received'].get(hw, [])),
                    'relevance': 0,
                    'concreteness': 0,
                    'constructive': 0,
                    'quality': 0
                }
        
        student_details.append({
            'id': student_id,
            'name': score_data['name'],
            'hw_scores': score_data['hw_scores'],
            'avg_hw_score': avg_hw_score,
            'midterm': score_data['midterm'],
            'final': score_data['final'],
            'reviews_given': activity['total_given'],
            'reviews_received': activity['total_received'],
            'quality_score': quality_pct,
            'relevance_score': relevance_pct,
            'concreteness_score': concreteness_pct,
            'constructive_score': constructive_pct,
            'quality_breakdown': activity['quality_given'],
            'hw_activity': hw_quality
        })
    
    # Sort by student ID
    student_details.sort(key=lambda x: x['id'])
    
    report = {
        'summary': summary,
        'correlations': correlations,
        'students': student_details,
        'generated_at': str(Path(__file__).stat().st_mtime)
    }
    
    # Save report
    output_file = OUTPUT_DIR / "score_review_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"Analysis report saved to: {output_file}")
    return report


if __name__ == "__main__":
    report = generate_analysis_report()
    if 'error' not in report:
        print(f"\n=== Analysis Summary ===")
        print(f"Total Students: {report['summary']['total_students']}")
        print(f"Students with Reviews: {report['summary']['students_with_reviews']}")
        print(f"Total Reviews Given: {report['summary']['total_reviews_given']}")
        
        print(f"\n=== Correlation by HW ===")
        for hw, data in report['correlations'].items():
            print(f"{hw}: Score-Given r={data['correlation_given']:.3f}, Score-Quality r={data['correlation_quality']:.3f}")
    else:
        print(f"Error: {report['error']}")
