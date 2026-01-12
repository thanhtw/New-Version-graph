#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from collections import defaultdict
import re

def comprehensive_data_check():
    """
    Comprehensive check of all students' relevance, specificity, and constructiveness label data
    """
    
    try:
        # Read processed data
        with open('3labeled_processed_totalData.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("=== Student Data Comprehensive Check Report ===\n")
        
        # Statistics variables
        student_stats = defaultdict(lambda: {
            'total_assignments': 0,
            'total_rounds': 0,
            'total_feedbacks': 0,
            'valid_feedbacks': 0,
            'empty_feedbacks': 0,
            'relevance_count': 0,
            'concreteness_count': 0,
            'constructive_count': 0,
            'suggestion_keywords': 0,
            'anomalies': []
        })
        
        # Keyword check - only check actual suggestion keywords
        suggestion_keywords = ['建議']
        
        total_rounds = 0
        total_assignments = 0
        
        # Iterate through all assignments and students
        for hw_key, assignments in data.items():
            total_assignments += len(assignments)
            print(f"Checking {hw_key}: {len(assignments)} assignments")
            
            for assignment in assignments:
                reviewer = assignment.get('Reviewer_Name') or assignment.get('reviewer')
                if not reviewer:
                    continue
                
                student_stats[reviewer]['total_assignments'] += 1
                rounds = assignment.get('Round', [])
                
                for round_data in rounds:
                    total_rounds += 1
                    student_stats[reviewer]['total_rounds'] += 1
                    
                    feedback = round_data.get('Feedback', '')
                    relevance = round_data.get('Relevance', 0)
                    concreteness = round_data.get('Concreteness', 0)
                    constructive = round_data.get('Constructive', 0)
                    
                    student_stats[reviewer]['total_feedbacks'] += 1
                    
                    # Check review content
                    if feedback and str(feedback).strip():
                        student_stats[reviewer]['valid_feedbacks'] += 1
                        feedback_str = str(feedback)
                        
                        # Check keywords
                        for keyword in suggestion_keywords:
                            if keyword in feedback_str:
                                student_stats[reviewer]['suggestion_keywords'] += 1
                                break
                        
                        # Anomaly check 1: Has suggestion keyword but constructive label is 0
                        if any(keyword in feedback_str for keyword in suggestion_keywords) and constructive == 0:
                            student_stats[reviewer]['anomalies'].append({
                                'type': 'missing_constructive_for_suggestion',
                                'hw': hw_key,
                                'feedback': feedback_str[:100] + '...' if len(feedback_str) > 100 else feedback_str,
                                'labels': f'R:{relevance},C:{concreteness},Ct:{constructive}'
                            })
                        
                        # Anomaly check 2: Very short review but has multiple labels
                        if len(feedback_str.strip()) <= 5 and (relevance + concreteness + constructive) >= 2:
                            student_stats[reviewer]['anomalies'].append({
                                'type': 'short_feedback_multiple_labels',
                                'hw': hw_key,
                                'feedback': feedback_str,
                                'labels': f'R:{relevance},C:{concreteness},Ct:{constructive}'
                            })
                        
                        # Anomaly check 3: Only says "good" but has specificity label
                        if feedback_str.strip().lower() in ['good', 'pass', '是', '是的', '讚', '棒'] and concreteness == 1:
                            student_stats[reviewer]['anomalies'].append({
                                'type': 'generic_feedback_with_concreteness',
                                'hw': hw_key,
                                'feedback': feedback_str,
                                'labels': f'R:{relevance},C:{concreteness},Ct:{constructive}'
                            })
                        
                        # Anomaly check 4: Detailed review but all labels are 0
                        if len(feedback_str.strip()) > 50 and relevance == 0 and concreteness == 0 and constructive == 0:
                            student_stats[reviewer]['anomalies'].append({
                                'type': 'detailed_feedback_no_labels',
                                'hw': hw_key,
                                'feedback': feedback_str[:100] + '...' if len(feedback_str) > 100 else feedback_str,
                                'labels': f'R:{relevance},C:{concreteness},Ct:{constructive}'
                            })
                    else:
                        student_stats[reviewer]['empty_feedbacks'] += 1
                        
                        # Anomaly check 5: Empty review but has labels
                        if relevance == 1 or concreteness == 1 or constructive == 1:
                            student_stats[reviewer]['anomalies'].append({
                                'type': 'empty_feedback_with_labels',
                                'hw': hw_key,
                                'feedback': '[Empty review]',
                                'labels': f'R:{relevance},C:{concreteness},Ct:{constructive}'
                            })
                    
                    # Accumulate label statistics
                    student_stats[reviewer]['relevance_count'] += relevance
                    student_stats[reviewer]['concreteness_count'] += concreteness
                    student_stats[reviewer]['constructive_count'] += constructive
        
        # Generate report
        print(f"Total checked: {len(student_stats)} students, {total_assignments} assignments, {total_rounds} rounds\n")
        
        # 1. Overall statistics
        print("=== Overall Label Distribution ===")
        total_relevance = sum(stats['relevance_count'] for stats in student_stats.values())
        total_concreteness = sum(stats['concreteness_count'] for stats in student_stats.values())
        total_constructive = sum(stats['constructive_count'] for stats in student_stats.values())
        total_valid_feedbacks = sum(stats['valid_feedbacks'] for stats in student_stats.values())
        
        print(f"Relevance labels: {total_relevance} ({total_relevance/total_rounds*100:.1f}%)")
        print(f"Concreteness labels: {total_concreteness} ({total_concreteness/total_rounds*100:.1f}%)")
        print(f"Constructive labels: {total_constructive} ({total_constructive/total_rounds*100:.1f}%)")
        print(f"Valid reviews: {total_valid_feedbacks} ({total_valid_feedbacks/total_rounds*100:.1f}%)")
        
        # 2. Problem student check
        print("\n=== Potentially Problematic Students ===")
        problem_students = []
        
        for student_id, stats in student_stats.items():
            problems = []
            
            # Check 1: No labels at all
            if stats['relevance_count'] == 0 and stats['concreteness_count'] == 0 and stats['constructive_count'] == 0:
                if stats['valid_feedbacks'] > 0:
                    problems.append(f"Has {stats['valid_feedbacks']} valid reviews but no labels")
            
            # Check 2: Abnormally high label ratio
            if stats['valid_feedbacks'] > 0:
                rel_ratio = stats['relevance_count'] / stats['valid_feedbacks']
                con_ratio = stats['concreteness_count'] / stats['valid_feedbacks']
                cst_ratio = stats['constructive_count'] / stats['valid_feedbacks']
                
                if rel_ratio > 3:  # Relevance ratio exceeds 300%
                    problems.append(f"Abnormally high relevance ratio: {rel_ratio:.1%}")
                if con_ratio > 2:  # Concreteness ratio exceeds 200%
                    problems.append(f"Abnormally high concreteness ratio: {con_ratio:.1%}")
                if cst_ratio > 1.5:  # Constructive ratio exceeds 150%
                    problems.append(f"Abnormally high constructive ratio: {cst_ratio:.1%}")
            
            # Check 3: Has suggestion keywords but very few constructive labels
            if stats['suggestion_keywords'] > 0 and stats['constructive_count'] < stats['suggestion_keywords'] * 0.5:
                problems.append(f"Has {stats['suggestion_keywords']} suggestion keywords but only {stats['constructive_count']} constructive labels")
            
            # Check 4: Has multiple anomaly records
            if len(stats['anomalies']) >= 3:
                problems.append(f"Has {len(stats['anomalies'])} anomaly records")
            
            if problems:
                problem_students.append({
                    'student': student_id,
                    'problems': problems,
                    'stats': stats
                })
        
        # Display top 10 problem students
        problem_students.sort(key=lambda x: len(x['problems']) + len(x['stats']['anomalies']), reverse=True)
        
        for i, student_info in enumerate(problem_students[:10]):
            student_id = student_info['student']
            problems = student_info['problems']
            stats = student_info['stats']
            
            print(f"\n{i+1}. Student {student_id}:")
            print(f"   Stats: {stats['valid_feedbacks']} valid reviews, R:{stats['relevance_count']}, C:{stats['concreteness_count']}, Ct:{stats['constructive_count']}")
            
            for problem in problems:
                print(f"   ⚠️  {problem}")
            
            if stats['anomalies']:
                print(f"   Anomaly records ({len(stats['anomalies'])}):")  
                for anomaly in stats['anomalies'][:3]:  # Only show first 3
                    print(f"      - {anomaly['type']}: {anomaly['feedback']} [{anomaly['labels']}]")
        
        # 3. Anomaly type statistics
        print("\n=== Anomaly Type Statistics ===")
        anomaly_types = defaultdict(int)
        for stats in student_stats.values():
            for anomaly in stats['anomalies']:
                anomaly_types[anomaly['type']] += 1
        
        for anomaly_type, count in sorted(anomaly_types.items(), key=lambda x: x[1], reverse=True):
            print(f"{anomaly_type}: {count} cases")
        
        # 4. Suggestion keyword check
        print("\n=== Suggestion Keyword Check ===")
        total_suggestion_keywords = sum(stats['suggestion_keywords'] for stats in student_stats.values())
        print(f"Total found {total_suggestion_keywords} suggestion keywords")
        
        # Check suggestion keyword vs constructive label correspondence
        suggestion_constructive_mismatch = 0
        for stats in student_stats.values():
            for anomaly in stats['anomalies']:
                if anomaly['type'] == 'missing_constructive_for_suggestion':
                    suggestion_constructive_mismatch += 1
        
        print(f"Cases with suggestion keyword but constructive label is 0: {suggestion_constructive_mismatch}")
        
        print(f"\nCheck complete! Found {len(problem_students)} students with potential data issues.")
        
        return {
            'total_students': len(student_stats),
            'problem_students': len(problem_students),
            'total_anomalies': sum(len(stats['anomalies']) for stats in student_stats.values()),
            'student_stats': dict(student_stats)
        }
        
    except Exception as e:
        print(f"Error occurred during check: {e}")
        return None

if __name__ == "__main__":
    comprehensive_data_check()
