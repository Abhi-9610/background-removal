"""
Simple client example for the Background Removal API
"""
import requests
import base64
from pathlib import Path


class BackgroundRemovalClient:
    """Client for interacting with the Background Removal API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def health_check(self) -> dict:
        """Check if the API is healthy"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def remove_background_json(self, image_path: str) -> dict:
        """
        Remove background and get JSON response with both images
        
        Args:
            image_path: Path to the input image
            
        Returns:
            Dictionary with original and processed images (base64 encoded)
        """
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{self.base_url}/remove-background",
                files=files
            )
        response.raise_for_status()
        return response.json()
    
    def remove_background_binary(self, image_path: str, output_path: str = None) -> bytes:
        """
        Remove background and get binary PNG response
        
        Args:
            image_path: Path to the input image
            output_path: Optional path to save the output image
            
        Returns:
            Binary PNG data
        """
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{self.base_url}/remove-background-binary",
                files=files
            )
        response.raise_for_status()
        
        if output_path:
            with open(output_path, "wb") as f:
                f.write(response.content)
        
        return response.content
    
    def save_result_images(self, result: dict, output_dir: str = "output"):
        """
        Save original and processed images from JSON response
        
        Args:
            result: JSON response from remove_background_json
            output_dir: Directory to save images
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save original
        original_data = base64.b64decode(result['original_image']['data'])
        original_file = output_path / f"original.{result['original_image']['format'].lower()}"
        with open(original_file, "wb") as f:
            f.write(original_data)
        print(f"Original saved to: {original_file}")
        
        # Save processed
        processed_data = base64.b64decode(result['processed_image']['data'])
        processed_file = output_path / "no_background.png"
        with open(processed_file, "wb") as f:
            f.write(processed_data)
        print(f"Processed saved to: {processed_file}")


def example_usage():
    """Example usage of the client"""
    
    # Initialize client
    client = BackgroundRemovalClient()
    
    # Check health
    print("Checking API health...")
    health = client.health_check()
    print(f"API Status: {health['status']}")
    
    # Example 1: JSON response
    print("\n=== Example 1: JSON Response ===")
    image_path = "your_image.jpg"  # Change this to your image path
    
    if Path(image_path).exists():
        result = client.remove_background_json(image_path)
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        
        # Save images
        client.save_result_images(result, output_dir="output")
    else:
        print(f"Please provide an image at: {image_path}")
    
    # Example 2: Binary response
    print("\n=== Example 2: Binary Response ===")
    if Path(image_path).exists():
        client.remove_background_binary(
            image_path,
            output_path="output/no_background_binary.png"
        )
        print("Binary output saved to: output/no_background_binary.png")
    else:
        print(f"Please provide an image at: {image_path}")


if __name__ == "__main__":
    try:
        example_usage()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Make sure the server is running.")
        print("Start the server with: python main.py")
    except Exception as e:
        print(f"Error: {e}")
