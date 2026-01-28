# Background Removal API

A high-performance REST API for removing backgrounds from images using Python, FastAPI, and the rembg library.

## Features

- ✅ Remove backgrounds from images with high accuracy
- ✅ Returns both original and processed images
- ✅ Two response formats: JSON (base64) and binary
- ✅ Supports PNG, JPG, JPEG, and WebP formats
- ✅ Async/await for optimal performance
- ✅ Proper error handling and validation
- ✅ Health check endpoint
- ✅ API documentation with Swagger UI

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

The first time you run the API, rembg will automatically download the AI model (~176MB).

## Usage

### Start the API server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### 1. Root Endpoint
```
GET /
```
Returns API information and available endpoints.

### 2. Health Check
```
GET /health
```
Check if the API is running.

### 3. Remove Background (JSON Response)
```
POST /remove-background
```

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (image file)

**Response:**
```json
{
  "success": true,
  "original_image": {
    "data": "base64_encoded_image...",
    "format": "PNG",
    "size": {
      "width": 1920,
      "height": 1080
    }
  },
  "processed_image": {
    "data": "base64_encoded_image...",
    "format": "PNG",
    "size": {
      "width": 1920,
      "height": 1080
    }
  },
  "message": "Background removed successfully"
}
```

### 4. Remove Background (Binary Response)
```
POST /remove-background-binary
```

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (image file)

**Response:**
- Returns PNG image file with transparent background
- Content-Type: image/png

## Example Usage

### Using curl

**JSON Response:**
```bash
curl -X POST "http://localhost:8000/remove-background" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_image.jpg"
```

**Binary Response:**
```bash
curl -X POST "http://localhost:8000/remove-background-binary" \
  -F "file=@your_image.jpg" \
  --output result.png
```

### Using Python requests

```python
import requests

# Upload image
url = "http://localhost:8000/remove-background"
files = {"file": open("your_image.jpg", "rb")}
response = requests.post(url, files=files)

# Get result
result = response.json()
print(f"Success: {result['success']}")

# Decode and save images
import base64

# Save original
with open("original.png", "wb") as f:
    f.write(base64.b64decode(result['original_image']['data']))

# Save processed
with open("no_background.png", "wb") as f:
    f.write(base64.b64decode(result['processed_image']['data']))
```

### Using JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/remove-background', {
  method: 'POST',
  body: formData
})
  .then(response => response.json())
  .then(data => {
    console.log('Success:', data.success);
    
    // Display images
    document.getElementById('original').src = 
      `data:image/png;base64,${data.original_image.data}`;
    document.getElementById('processed').src = 
      `data:image/png;base64,${data.processed_image.data}`;
  });
```

## Supported Image Formats

- PNG
- JPG/JPEG
- WebP

## Performance

- Uses async/await for non-blocking I/O
- Efficient image processing with PIL
- AI-powered background removal with rembg (U2-Net model)
- Handles images of various sizes

## Error Handling

The API includes comprehensive error handling:
- Invalid file type validation
- File size checks
- Processing error recovery
- Detailed error messages

## Technical Details

- **Framework**: FastAPI (high-performance async framework)
- **Background Removal**: rembg (U2-Net deep learning model)
- **Image Processing**: Pillow (PIL)
- **Server**: Uvicorn (ASGI server)

## Notes

- Output images are always in PNG format to preserve transparency
- The API automatically handles RGBA and RGB color modes
- First run will download the AI model (~176MB)
- Processing time depends on image size and hardware

## License

MIT License
