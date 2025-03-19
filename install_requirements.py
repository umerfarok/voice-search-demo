import os
import sys
import subprocess
import platform
import shutil
import urllib.request

def print_header(text):
    print("\n" + "=" * 60)
    print(f" {text} ".center(60, "="))
    print("=" * 60)

def print_step(text):
    print(f"\n👉 {text}")

def run_command(command, desc=None):
    if desc:
        print_step(desc)
    
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print("Command completed successfully!")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        print(f"Error details: {e.stderr}")
        return False, e.stderr
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, str(e)

def install_requirements():
    print_step("Installing dependencies with pip...")
    return run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def fix_model_cache():
    print_step("Clearing model cache...")
    user_home = os.path.expanduser("~")
    cache_dir = os.path.join(user_home, ".cache", "whisper")
    
    if os.path.exists(cache_dir):
        try:
            print(f"Removing cache directory: {cache_dir}")
            shutil.rmtree(cache_dir)
            print("✅ Cache cleared successfully")
            return True
        except Exception as e:
            print(f"❌ Error clearing cache: {str(e)}")
            return False
    else:
        print("No cache directory found.")
        return True

def main():
    print_header("E-Commerce Voice Search Demo - Installation Helper")
    
    print("\nThis script will help install dependencies and fix model loading issues.")
    print("System information:")
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    
    # First try installing requirements
    success, _ = install_requirements()
    
    if not success:
        print("\n⚠️ Requirements installation had issues. Continuing with fixes anyway.")
    
    # Try fixing model cache
    cache_fixed = fix_model_cache()
    
    # Create models directory
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)
    print(f"✅ Created models directory: {models_dir}")
    
    print_header("INSTALLATION COMPLETE")
    print("\nTry running the application again with:")
    print("  python app.py")
    print("\nIf you still have issues:")
    print("1. Make sure your network firewall allows Python to access the internet")
    print("2. If behind a proxy, set HTTP_PROXY and HTTPS_PROXY environment variables")
    print("3. Text search will still work even if voice search is disabled")

if __name__ == "__main__":
    main()
