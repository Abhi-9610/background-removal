# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** The first run will download the U2-Net model (~176MB) automatically.

### Step 2: Start the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Step 3: Test the API

Open your browser and go to:
- **Swagger UI**: http://localhost:8000/docs
- Try uploading an image directly from the web interface!

---

## 📋 Quick Tests

### Using curl (Command Line)

```bash
# Test health check
curl http://localhost:8000/health

# Remove background (saves as PNG)
curl -X POST "http://localhost:8000/remove-background-binary" \
  -F "file=@your_image.jpg" \
  --output result.png
```

### Using Python Client

```bash
# Run the example client
python client_example.py
```

### Run Test Suite

```bash
python test_api.py
```

---

## 🐳 Docker (Alternative)

### Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

### Using Docker Directly

```bash
# Build
docker build -t background-removal-api .

# Run
docker run -p 8000:8000 background-removal-api
```

---

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/remove-background` | POST | Remove background (JSON with both images) |
| `/remove-background-binary` | POST | Remove background (binary PNG) |

---

## 💡 Usage Examples

### Python with requests

```python
import requests

url = "http://localhost:8000/remove-background"
files = {"file": open("photo.jpg", "rb")}
response = requests.post(url, files=files)

result = response.json()
print(result['message'])
```

### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/remove-background', {
  method: 'POST',
  body: formData
})
  .then(res => res.json())
  .then(data => console.log(data));
```

### cURL

```bash
curl -X POST http://localhost:8000/remove-background \
  -F "file=@image.jpg" \
  -o response.json
```

---

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Use a different port
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Model Download Issues

If the model doesn't download automatically:

```python
# Run this once
python -c "from rembg import remove; from PIL import Image; import io; remove(Image.new('RGB', (1, 1)))"
```

### Memory Issues

For large images, consider adding:

```python
# In main.py, add max file size
from fastapi import File, UploadFile

@app.post("/remove-background")
async def remove_background(file: UploadFile = File(..., max_length=10_000_000)):
    # 10MB limit
```

---

## 📊 Performance Tips

1. **Use binary endpoint** for faster responses when you only need the processed image
2. **Resize large images** before processing for faster results
3. **Deploy with multiple workers** for production:
   ```bash
   uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

---

## 🎯 Next Steps

- Check out the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8000/docs
- Test with your own images!

---

Need help? Check the logs or API documentation at `/docs`
