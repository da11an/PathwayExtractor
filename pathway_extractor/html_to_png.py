from playwright.sync_api import sync_playwright
import tempfile
import os
from pathlib import Path

def save_html_as_png(html_content, output_png_path, width=1200, height=800):
    """
    Save HTML content as a PNG image using Playwright.
    
    Args:
        html_content: HTML string to render
        output_png_path: Path where PNG should be saved (Path object or string)
        width: Viewport width in pixels
        height: Viewport height in pixels
    """
    # Convert Path object to string if needed, and ensure it's absolute
    if isinstance(output_png_path, Path):
        output_png_path = str(output_png_path.resolve())
    else:
        output_png_path = str(Path(output_png_path).resolve())
    
    # Ensure the parent directory exists
    output_dir = os.path.dirname(output_png_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        html_file = os.path.join(tmpdir, "temp.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto("file://" + html_file)
            page.screenshot(path=output_png_path, full_page=True)
            browser.close()

# Example usage:
# save_html_as_png(html_content, "student_report.png", width=1200, height=600)
