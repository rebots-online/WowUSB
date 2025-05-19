#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test runner for WowUSB-DS9 tests.
This script runs all the tests for WowUSB-DS9.
"""

import os
import sys
import unittest
import argparse
import importlib
import time

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def discover_tests():
    """
    Discover all test modules in the tests directory
    
    Returns:
        list: List of test module names
    """
    test_modules = []
    
    # Get the directory where this script is located
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find all Python files in the tests directory
    for filename in os.listdir(tests_dir):
        if filename.startswith("test_") and filename.endswith(".py"):
            module_name = filename[:-3]  # Remove .py extension
            test_modules.append(module_name)
    
    return test_modules

def run_tests(test_modules=None, verbose=False, failfast=False):
    """
    Run the specified test modules
    
    Args:
        test_modules (list, optional): List of test module names to run
        verbose (bool, optional): Whether to run tests in verbose mode
        failfast (bool, optional): Whether to stop on first failure
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # If no test modules specified, discover all test modules
    if test_modules is None:
        test_modules = discover_tests()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test modules to suite
    for module_name in test_modules:
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Add all tests from the module to the suite
            module_tests = loader.loadTestsFromModule(module)
            suite.addTest(module_tests)
            
            print(f"Added tests from {module_name}")
        except ImportError as e:
            print(f"Error importing {module_name}: {e}")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1, failfast=failfast)
    result = runner.run(suite)
    
    # Return True if all tests passed
    return result.wasSuccessful()

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run WowUSB-DS9 tests")
    parser.add_argument("--modules", nargs="+", help="Test modules to run")
    parser.add_argument("--verbose", action="store_true", help="Run tests in verbose mode")
    parser.add_argument("--failfast", action="store_true", help="Stop on first failure")
    args = parser.parse_args()
    
    # Print banner
    print("=" * 80)
    print("WowUSB-DS9 Test Runner")
    print("=" * 80)
    
    # Start time
    start_time = time.time()
    
    # Run tests
    success = run_tests(args.modules, args.verbose, args.failfast)
    
    # End time
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Print summary
    print("\n" + "=" * 80)
    print(f"Test run completed in {elapsed_time:.2f} seconds")
    print(f"Result: {'SUCCESS' if success else 'FAILURE'}")
    print("=" * 80)
    
    # Return exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
