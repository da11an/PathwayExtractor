from playwright.sync_api import sync_playwright
import tempfile
import os

def save_html_as_png(html_content, output_png_path, width=1200, height=800):
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
