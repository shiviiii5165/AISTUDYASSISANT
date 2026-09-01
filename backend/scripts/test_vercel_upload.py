import httpx
import sys

def test_vercel_upload():
    url = "http://localhost:8000/api/notes/image"
    # Wait, the url is `/_/backend/notes/image`? 
    # Let's check `backend/app/main.py` router includes.
    
    # We don't know the exact token, but we can see if it returns a 401 Unauthorized or a 500 Server Error
    files = {'file': ('test.png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDAT\x08\x99c\xf8\x0f\x04\x00\x09\xfb\x03\xfd\xe3U\xf2\x9c\x00\x00\x00\x00IEND\xaeB`\x82', 'image/png')}
    data = {'subject': 'General'}
    
    with httpx.Client(timeout=30.0) as client:
        try:
            resp = client.post(url, data=data, files=files)
            print("Status:", resp.status_code)
            print("Headers:", resp.headers)
            print("Response:", resp.text)
        except Exception as e:
            print("Request failed:", e)

if __name__ == "__main__":
    test_vercel_upload()
