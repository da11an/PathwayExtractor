import subprocess
import sys

def run_playwright_install():
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    except Exception as e:
        print("❌ Failed to install Playwright browsers:", e)

if __name__ == "__main__":
    run_playwright_install()
