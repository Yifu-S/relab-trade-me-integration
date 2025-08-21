#!/usr/bin/env python3
"""
Setup script for Relab Trade Me Integration
This script helps set up the development environment.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required. Current version: {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_virtual_environment():
    """Create virtual environment"""
    if os.path.exists("venv"):
        print("✅ Virtual environment already exists")
        return True
    
    return run_command("python -m venv venv", "Creating virtual environment")

def install_dependencies():
    """Install Python dependencies"""
    # Determine the correct pip command
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix/Linux/Mac
        pip_cmd = "venv/bin/pip"
    
    return run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies")

def install_playwright():
    """Install Playwright browsers"""
    # Determine the correct playwright command
    if os.name == 'nt':  # Windows
        playwright_cmd = "venv\\Scripts\\playwright"
    else:  # Unix/Linux/Mac
        playwright_cmd = "venv/bin/playwright"
    
    return run_command(f"{playwright_cmd} install chromium", "Installing Playwright browsers")

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    print("📝 Creating .env file...")
    env_content = """# Relab Trade Me Integration Configuration
# Replace with your actual Relab credentials

RELAb_EMAIL=your_email@example.com
RELAb_PASSWORD=your_password
FLASK_SECRET_KEY=your_secret_key_here
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ .env file created successfully")
        print("⚠️  Please update .env file with your actual Relab credentials")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def check_extension_files():
    """Check if extension files exist"""
    extension_dir = Path("extension")
    required_files = [
        "manifest.json",
        "content.js",
        "content.css",
        "background.js",
        "popup.html",
        "popup.js"
    ]
    
    missing_files = []
    for file in required_files:
        if not (extension_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing extension files: {', '.join(missing_files)}")
        return False
    
    print("✅ All extension files present")
    return True

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Update .env file with your Relab credentials")
    print("2. Activate virtual environment:")
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\activate")
    else:  # Unix/Linux/Mac
        print("   source venv/bin/activate")
    print("3. Start the Flask server:")
    print("   python app.py")
    print("4. Install Chrome extension:")
    print("   - Open Chrome and go to chrome://extensions/")
    print("   - Enable 'Developer mode'")
    print("   - Click 'Load unpacked'")
    print("   - Select the 'extension' folder")
    print("5. Test the demo:")
    print("   python demo.py")
    print("\n🌐 The application will be available at: http://localhost:5000")

def main():
    """Main setup function"""
    print("🚀 Relab Trade Me Integration - Setup")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Install Playwright
    if not install_playwright():
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Check extension files
    if not check_extension_files():
        print("⚠️  Extension files missing. Please ensure all files are present.")
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
