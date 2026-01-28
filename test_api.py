"""
Test script for the Background Removal API
"""
import requests
import base64
from pathlib import Path
import time


def test_health_check():
    """Test the health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get("http://localhost:8000/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✓ Health check passed")


def test_root():
    """Test the root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    response = requests.get("http://localhost:8000/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✓ Root endpoint passed")


def test_remove_background_json(image_path: str):
    """Test background removal with JSON response"""
    print("\n=== Testing Background Removal (JSON) ===")
    
    if not Path(image_path).exists():
        print(f"⚠ Warning: Test image not found at {image_path}")
        print("Please provide a test image to test this endpoint")
        return
    
    start_time = time.time()
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post("http://localhost:8000/remove-background", files=files)
    
    elapsed_time = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        print(f"Original Image Size: {result['original_image']['size']}")
        print(f"Processed Image Size: {result['processed_image']['size']}")
        print(f"Processing Time: {elapsed_time:.2f} seconds")
        
        # Save images
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        # Save original
        original_data = base64.b64decode(result['original_image']['data'])
        original_path = output_dir / "original.png"
        with open(original_path, "wb") as f:
            f.write(original_data)
        print(f"✓ Original image saved to: {original_path}")
        
        # Save processed
        processed_data = base64.b64decode(result['processed_image']['data'])
        processed_path = output_dir / "no_background.png"
        with open(processed_path, "wb") as f:
            f.write(processed_data)
        print(f"✓ Processed image saved to: {processed_path}")
        
        print("✓ Background removal (JSON) passed")
    else:
        print(f"✗ Error: {response.text}")


def test_remove_background_binary(image_path: str):
    """Test background removal with binary response"""
    print("\n=== Testing Background Removal (Binary) ===")
    
    if not Path(image_path).exists():
        print(f"⚠ Warning: Test image not found at {image_path}")
        print("Please provide a test image to test this endpoint")
        return
    
    start_time = time.time()
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post("http://localhost:8000/remove-background-binary", files=files)
    
    elapsed_time = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        # Save binary image
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        output_path = output_dir / "no_background_binary.png"
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        print(f"Processing Time: {elapsed_time:.2f} seconds")
        print(f"✓ Processed image saved to: {output_path}")
        print("✓ Background removal (Binary) passed")
    else:
        print(f"✗ Error: {response.text}")


def test_invalid_file_type():
    """Test with invalid file type"""
    print("\n=== Testing Invalid File Type ===")
    
    # Create a dummy text file
    dummy_content = b"This is not an image"
    files = {"file": ("test.txt", dummy_content, "text/plain")}
    response = requests.post("http://localhost:8000/remove-background", files=files)
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 400
    print(f"Error Response: {response.json()}")
    print("✓ Invalid file type handling passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Background Removal API Test Suite")
    print("=" * 60)
    
    # Test basic endpoints
    try:
        test_health_check()
        test_root()
        test_invalid_file_type()
    except Exception as e:
        print(f"✗ Test failed: {e}")
    
    # Test with image (provide your own test image path)
    test_image_path = "test_image.jpg"  # Change this to your test image
    
    print("\n" + "=" * 60)
    print("Note: To test image processing endpoints, provide a test image")
    print(f"Update the 'test_image_path' variable to point to your image")
    print("=" * 60)
    
    try:
        test_remove_background_json(test_image_path)
        test_remove_background_binary(test_image_path)
    except Exception as e:
        print(f"✗ Test failed: {e}")
    
    print("\n" + "=" * 60)
    print("Test Suite Completed")
    print("=" * 60)
