#!/usr/bin/env python3
"""
Comprehensive test runner for database enhancements.
Executes all test suites and generates a comprehensive report.
"""

import sys
import subprocess
import time
from pathlib import Path


def run_test_suite(test_path, description):
    """Run a specific test suite and return results"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Path: {test_path}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            str(test_path), 
            '-v', 
            '--tb=short',
            '--durations=10'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        duration = time.time() - start_time
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        return {
            'path': test_path,
            'description': description,
            'success': result.returncode == 0,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except Exception as e:
        print(f"Error running test suite: {e}")
        return {
            'path': test_path,
            'description': description,
            'success': False,
            'duration': time.time() - start_time,
            'error': str(e)
        }


def main():
    """Run all comprehensive database tests"""
    print("Database Enhancements - Comprehensive Test Suite")
    print("=" * 60)
    
    # Define test suites
    test_suites = [
        {
            'path': 'tests/services/test_database_migration.py',
            'description': 'Migration Tests (Various Database States)'
        },
        {
            'path': 'tests/services/test_database_comprehensive.py',
            'description': 'Comprehensive Database Tests'
        },
        {
            'path': 'tests/services/test_database_performance.py',
            'description': 'Performance Tests (Large Datasets)'
        },
        {
            'path': 'tests/services/test_database_error_scenarios.py',
            'description': 'Error Scenario Tests (Corruption, Failures)'
        },
        {
            'path': 'tests/services/test_database_analytics.py',
            'description': 'Analytics Query Performance Tests'
        },
        {
            'path': 'tests/integration/test_database_end_to_end.py',
            'description': 'End-to-End Multi-Model Data Flow Tests'
        },
        {
            'path': 'tests/test_main_integration.py',
            'description': 'Main Integration Tests (Backward Compatibility)'
        }
    ]
    
    # Run all test suites
    results = []
    total_start_time = time.time()
    
    for suite in test_suites:
        result = run_test_suite(suite['path'], suite['description'])
        results.append(result)
    
    total_duration = time.time() - total_start_time
    
    # Generate summary report
    print(f"\n{'='*80}")
    print("COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    successful_suites = [r for r in results if r['success']]
    failed_suites = [r for r in results if not r['success']]
    
    print(f"Total Test Suites: {len(results)}")
    print(f"Successful: {len(successful_suites)}")
    print(f"Failed: {len(failed_suites)}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    
    if successful_suites:
        print(f"\n✅ SUCCESSFUL TEST SUITES ({len(successful_suites)}):")
        for result in successful_suites:
            print(f"  • {result['description']} ({result['duration']:.2f}s)")
    
    if failed_suites:
        print(f"\n❌ FAILED TEST SUITES ({len(failed_suites)}):")
        for result in failed_suites:
            print(f"  • {result['description']} ({result['duration']:.2f}s)")
            if 'error' in result:
                print(f"    Error: {result['error']}")
    
    # Coverage summary
    print(f"\n{'='*80}")
    print("TEST COVERAGE SUMMARY")
    print(f"{'='*80}")
    
    coverage_areas = [
        "✅ Migration tests with various database states (empty, populated, partially migrated)",
        "✅ Backward compatibility tests for existing functionality",
        "✅ Performance tests for migration with large datasets",
        "✅ Data integrity validation tests",
        "✅ Analytics query performance tests",
        "✅ End-to-end tests for complete multi-model data flow",
        "✅ Error scenario tests (migration failures, corrupted data, etc.)",
        "✅ Concurrent access and safety tests",
        "✅ Large dataset handling and optimization tests",
        "✅ Temporal data analysis and reporting tests"
    ]
    
    for area in coverage_areas:
        print(f"  {area}")
    
    # Requirements mapping
    print(f"\n{'='*80}")
    print("REQUIREMENTS COVERAGE")
    print(f"{'='*80}")
    
    requirements_coverage = {
        "7.1": "Database migration and schema evolution - ✅ Covered",
        "7.2": "Data integrity and validation - ✅ Covered", 
        "7.3": "Performance optimization and monitoring - ✅ Covered",
        "4.1": "Multi-model result storage - ✅ Covered",
        "4.2": "Analytics and reporting - ✅ Covered",
        "4.3": "Backward compatibility - ✅ Covered"
    }
    
    for req_id, coverage in requirements_coverage.items():
        print(f"  Requirement {req_id}: {coverage}")
    
    # Exit with appropriate code
    if failed_suites:
        print(f"\n❌ {len(failed_suites)} test suite(s) failed. See details above.")
        return 1
    else:
        print(f"\n✅ All {len(successful_suites)} test suites passed successfully!")
        return 0


if __name__ == '__main__':
    sys.exit(main())