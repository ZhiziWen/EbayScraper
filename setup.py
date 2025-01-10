"""
Setup script for eBay LEGO Price Scraper

This script will:
1. Check if conda is installed
2. Create and activate a conda environment
3. Install all required packages
4. Install Chrome WebDriver if needed
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, shell=True):
    """Run a shell command and print output."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error message: {e.stderr}")
        return False

def check_conda():
    """Check if conda is installed."""
    return run_command("conda --version", shell=True)

def create_conda_env():
    """Create conda environment from environment.yml."""
    if not os.path.exists("environment.yml"):
        print("Error: environment.yml not found!")
        return False
    
    # Create conda environment
    print("\nCreating conda environment...")
    if run_command("conda env create -f environment.yml"):
        print("Conda environment created successfully!")
        return True
    return False

def install_pip_packages():
    """Install additional pip packages if needed."""
    packages = [
        "selenium",
        "webdriver-manager",
        "beautifulsoup4",
        "pandas",
        "python-dateutil",
        "flask",
        "requests"
    ]
    
    print("\nInstalling pip packages...")
    for package in packages:
        print(f"\nInstalling {package}...")
        if not run_command(f"pip install {package}"):
            print(f"Warning: Failed to install {package}")

def setup_project():
    """Main setup function."""
    print("Setting up eBay LEGO Price Scraper...")
    
    # Check if conda is installed
    if not check_conda():
        print("Error: conda is not installed. Please install Anaconda or Miniconda first.")
        return False
    
    # Create conda environment
    if not create_conda_env():
        print("Error: Failed to create conda environment.")
        return False
    
    # Create necessary directories
    Path("data").mkdir(exist_ok=True)
    
    print("\nSetup completed successfully!")
    print("\nTo start using the scraper:")
    print("1. Activate the conda environment:")
    print("   conda activate ebay-scraper")
    print("2. Run the scraper:")
    print("   python src/scraper.py")
    
    return True

if __name__ == "__main__":
    setup_project() 