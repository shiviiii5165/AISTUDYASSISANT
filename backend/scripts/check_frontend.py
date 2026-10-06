import httpx
import re

print("Fetching frontend HTML...")
r = httpx.get('https://learnbygenie.online/')
print(r.status_code)

# find all JS files
js_files = re.findall(r'src="(.*?\.js)"', r.text)
for f in js_files:
    url = f"https://learnbygenie.online{f}"
    print(f"Fetching {url}")
    js_content = httpx.get(url).text
    if "http://localhost:8000" in js_content:
        print("FOUND LOCALHOST URL IN JS BUNDLE!!!")
        print(js_content[js_content.find("http://localhost:8000") - 50 : js_content.find("http://localhost:8000") + 50])
