#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Build script for WowUSB-DS9 PyPI package.
This script builds the package and runs tests to verify it.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return its output"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: Command failed with code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def create_virtual_env(venv_dir):
    """Create a virtual environment"""
    print(f"Creating virtual environment in {venv_dir}")
    venv.create(venv_dir, with_pip=True)
    
    # Get the path to the Python executable in the virtual environment
    if os.name == 'nt':  # Windows
        python_exe = os.path.join(venv_dir, 'Scripts', 'python.exe')
    else:  # Unix-like
        python_exe = os.path.join(venv_dir, 'bin', 'python')
    
    # Upgrade pip
    run_command([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'])
    
    return python_exe

def build_package(project_dir):
    """Build the package"""
    print("Building package...")
    
    # Clean up previous builds
    dist_dir = os.path.join(project_dir, 'dist')
    build_dir = os.path.join(project_dir, 'build')
    egg_dir = os.path.join(project_dir, 'WowUSB_DS9.egg-info')
    
    for dir_path in [dist_dir, build_dir, egg_dir]:
        if os.path.exists(dir_path):
            print(f"Removing {dir_path}")
            shutil.rmtree(dir_path)
    
    # Build the package
    run_command([sys.executable, '-m', 'pip', 'install', '--upgrade', 'build'], cwd=project_dir)
    run_command([sys.executable, '-m', 'build'], cwd=project_dir)
    
    # Return the path to the wheel file
    wheel_files = list(Path(dist_dir).glob('*.whl'))
    if not wheel_files:
        print("Error: No wheel file found after build")
        sys.exit(1)
    
    return str(wheel_files[0])

def test_package(wheel_file):
    """Test the package in a virtual environment"""
    print(f"Testing package: {wheel_file}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a virtual environment
        venv_dir = os.path.join(temp_dir, 'venv')
        python_exe = create_virtual_env(venv_dir)
        
        # Install the package
        run_command([python_exe, '-m', 'pip', 'install', wheel_file])
        
        # Test importing the package
        test_script = os.path.join(temp_dir, 'test_import.py')
        with open(test_script, 'w') as f:
            f.write("""
import sys
try:
    import WowUSB
    print(f"Successfully imported WowUSB version {WowUSB.__version__}")
    sys.exit(0)
except Exception as e:
    print(f"Error importing WowUSB: {e}")
    sys.exit(1)
""")
        
        run_command([python_exe, test_script])
        print("Package import test passed!")

def main():
    """Main function"""
    # Get the project directory (parent of the script directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    print(f"Project directory: {project_dir}")
    
    # Build the package
    wheel_file = build_package(project_dir)
    
    # Test the package
    test_package(wheel_file)
    
    print("\nPackage build and test completed successfully!")
    print(f"Wheel file: {wheel_file}")
    print("\nTo install the package locally:")
    print(f"pip install {wheel_file}")
    print("\nTo upload to PyPI:")
    print(f"twine upload {os.path.join('dist', '*')}")

if __name__ == "__main__":
    main()
