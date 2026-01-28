from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from rembg import remove, new_session
from PIL import Image, ImageFilter, ImageEnhance
import io
import base64
from typing import Dict, Optional, Tuple
import logging
import numpy as np
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Background Removal API - Enhanced & Stable",
    description="API to remove background from images with maximum quality and stability",
    version="2.0.0"
)

# Add CORS middleware to allow demo page to work
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global session cache for better performance and stability
MODEL_SESSIONS = {}

def get_model_session(model_name: str):
    """Get or create a cached model session for stability"""
    if model_name not in MODEL_SESSIONS:
        try:
            logger.info(f"Creating new session for model: {model_name} (this may take 20-30 seconds on first load)")
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Model {model_name} loading timed out after 60 seconds")
            
            # Set timeout for model loading
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # 60 second timeout
            
            try:
                MODEL_SESSIONS[model_name] = new_session(model_name)
                signal.alarm(0)  # Cancel timeout
                logger.info(f"Model {model_name} loaded successfully")
            except TimeoutError as te:
                signal.alarm(0)
                logger.error(f"Timeout loading {model_name}: {te}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to create session for {model_name}: {e}")
            raise
    return MODEL_SESSIONS[model_name]

def preprocess_image(image: Image.Image, max_size: int = 4000) -> Tuple[Image.Image, Tuple[int, int]]:
    """
    Preprocess image for optimal quality and stability
    - Resize if too large (prevents memory issues)
    - Convert to RGB if needed
    - Enhance if image quality is poor
    Returns: (processed_image, original_size)
    """
    original_size = image.size
    
    # Convert to RGB if needed (handle all color modes)
    if image.mode not in ('RGB', 'RGBA'):
        logger.info(f"Converting image from {image.mode} to RGB")
        if image.mode == 'P' and 'transparency' in image.info:
            image = image.convert('RGBA')
        else:
            image = image.convert('RGB')
    
    # Resize if too large for stability
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        logger.info(f"Resizing image from {image.size} to {new_size} for stability")
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    return image, original_size

def postprocess_image(image: Image.Image, original_size: Tuple[int, int], refine: bool = True) -> Image.Image:
    """
    Post-process the background-removed image for perfect results
    - Resize back to original dimensions
    - Refine edges
    - Remove artifacts
    """
    # Resize back to original size if needed
    if image.size != original_size:
        logger.info(f"Resizing result back to original size: {original_size}")
        image = image.resize(original_size, Image.Resampling.LANCZOS)
    
    if refine:
        # Apply subtle edge refinement
        # Get alpha channel
        if image.mode == 'RGBA':
            # Slight blur on alpha channel to smooth edges
            r, g, b, a = image.split()
            # Apply very slight gaussian blur to alpha for smoother edges
            a = a.filter(ImageFilter.GaussianBlur(radius=0.5))
            image = Image.merge('RGBA', (r, g, b, a))
    
    return image

def validate_result(original: Image.Image, processed: Image.Image) -> bool:
    """
    Validate that the background removal was successful
    Returns True if the result seems valid
    """
    try:
        # Check if processed image has alpha channel
        if processed.mode != 'RGBA':
            logger.warning("Processed image doesn't have alpha channel")
            return False
        
        # Check if there's actual transparency (not all opaque)
        alpha = np.array(processed.split()[3])
        unique_values = len(np.unique(alpha))
        
        if unique_values < 2:
            logger.warning("No transparency detected in result")
            return False
        
        # Check if too much of the image is transparent (might indicate over-removal)
        transparent_ratio = np.sum(alpha < 10) / alpha.size
        if transparent_ratio > 0.95:
            logger.warning(f"Too much transparency: {transparent_ratio:.2%}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return True  # Don't fail on validation errors


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the demo page"""
    demo_path = Path(__file__).parent / "demo.html"
    if demo_path.exists():
        return FileResponse(demo_path)
    return HTMLResponse("""
        <html>
            <body>
                <h1>Background Removal API</h1>
                <p>API is running! Demo page not found.</p>
                <p>Visit <a href="/docs">/docs</a> for API documentation.</p>
            </body>
        </html>
    """)

@app.get("/api")
async def api_info():
    """API endpoint information"""
    return {
        "message": "Background Removal API - Enhanced",
        "version": "2.0.0",
        "endpoints": {
            "/": "GET - Demo page",
            "/api": "GET - API information",
            "/health": "GET - Health check",
            "/remove-background": "POST - Remove background (JSON response)",
            "/remove-background-binary": "POST - Remove background (PNG file)",
            "/docs": "GET - Interactive API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "background-removal-api"}


@app.post("/remove-background")
async def remove_background(
    file: UploadFile = File(...),
    model: str = Form(default="isnet-general-use"),
    alpha_matting: bool = Form(default=True),
    alpha_matting_foreground_threshold: int = Form(default=232),
    alpha_matting_background_threshold: int = Form(default=50),
    alpha_matting_erode_size: int = Form(default=20),
    post_process_mask: bool = Form(default=True)
):
    """
    Remove background from uploaded image with advanced quality options
    
    Args:
        file: Image file (PNG, JPG, JPEG, WebP)
        model: AI model to use (default: u2net for reliability)
            - u2net: Fast, reliable, good quality (recommended)
            - isnet-general-use: Better quality, more accurate edges (slower first time)
            - u2net_human_seg: Optimized for human portraits
            - isnet-anime: Best for anime/cartoon images
        alpha_matting: Enable AI-powered alpha matting for smoother edges (default: True)
            Uses sophisticated matting algorithm for perfect edge detection
        alpha_matting_foreground_threshold: Foreground threshold (1-255, default: 240)
            Higher = more conservative (keeps more of subject)
        alpha_matting_background_threshold: Background threshold (1-255, default: 10)
            Lower = removes more background
        alpha_matting_erode_size: Edge smoothing size (1-20, default: 10)
            Controls transition smoothness between subject and background
        post_process_mask: Apply additional mask refinement (default: True)
            Further enhances edges using model predictions
    
    Returns:
        JSON with base64 encoded original and background-removed images
    """
    try:
        # Validate file type
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Read the uploaded file
        logger.info(f"Processing file: {file.filename} with model: {model}, alpha_matting: {alpha_matting}")
        contents = await file.read()
        
        # Validate file size
        file_size_mb = len(contents) / (1024 * 1024)
        if file_size_mb > 50:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file_size_mb:.1f}MB). Maximum size is 50MB."
            )
        logger.info(f"File size: {file_size_mb:.2f}MB")
        
        # Open image with PIL
        try:
            original_image = Image.open(io.BytesIO(contents))
            original_image.load()  # Force load to catch corrupt images
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or corrupt image file: {str(e)}"
            )
        
        logger.info(f"Original image: {original_image.size}, mode: {original_image.mode}")
        
        # Preprocess image for optimal quality and stability
        img_for_processing, original_size = preprocess_image(original_image)
        
        # Get or create model session (cached for stability)
        logger.info(f"Removing background with model: {model}, alpha_matting: {alpha_matting}")
        
        max_retries = 2
        output_image = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                
                session = get_model_session(model)
                output_image = remove(
                    img_for_processing,
                    session=session,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                    alpha_matting_background_threshold=alpha_matting_background_threshold,
                    alpha_matting_erode_size=alpha_matting_erode_size,
                    post_process_mask=post_process_mask
                )
                
                # Validate result
                if validate_result(img_for_processing, output_image):
                    logger.info("Background removal successful and validated")
                    break
                else:
                    logger.warning("Result validation failed, retrying...")
                    last_error = "Result validation failed"
                    continue
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Background removal attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Last attempt failed, try fallback with default model
                    logger.info("Trying fallback with default model...")
                    try:
                        output_image = remove(
                            img_for_processing,
                            alpha_matting=alpha_matting,
                            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                            alpha_matting_background_threshold=alpha_matting_background_threshold,
                            alpha_matting_erode_size=alpha_matting_erode_size,
                            post_process_mask=post_process_mask
                        )
                    except Exception as fallback_error:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Background removal failed: {fallback_error}"
                        )
        
        if output_image is None:
            raise HTTPException(
                status_code=500,
                detail=f"Background removal failed after {max_retries} attempts: {last_error}"
            )
        
        # Post-process for perfect results
        output_image = postprocess_image(output_image, original_size, refine=True)
        
        # Convert images to base64 for JSON response
        # Original image
        original_buffer = io.BytesIO()
        original_image.save(original_buffer, format=original_image.format or 'PNG')
        original_base64 = base64.b64encode(original_buffer.getvalue()).decode('utf-8')
        
        # Background-removed image (as PNG to support transparency)
        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format='PNG')
        output_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        logger.info("Background removal completed successfully")
        
        return {
            "success": True,
            "original_image": {
                "data": original_base64,
                "format": original_image.format or 'PNG',
                "size": {
                    "width": original_image.width,
                    "height": original_image.height
                }
            },
            "processed_image": {
                "data": output_base64,
                "format": "PNG",
                "size": {
                    "width": output_image.width,
                    "height": output_image.height
                }
            },
            "message": "Background removed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image: {str(e)}"
        )


@app.post("/remove-background-binary")
async def remove_background_binary(
    file: UploadFile = File(...),
    model: str = Form(default="isnet-general-use"),
    alpha_matting: bool = Form(default=True),
    alpha_matting_foreground_threshold: int = Form(default=232),
    alpha_matting_background_threshold: int = Form(default=50),
    alpha_matting_erode_size: int = Form(default=20),
    post_process_mask: bool = Form(default=True)
):
    """
    Remove background from uploaded image and return the processed image as binary
    
    Args:
        file: Image file (PNG, JPG, JPEG, WebP)
        model: AI model to use (u2net, isnet-general-use, u2net_human_seg, isnet-anime)
        alpha_matting: Enable AI-powered alpha matting for smoother edges
        alpha_matting_foreground_threshold: Foreground threshold (1-255)
        alpha_matting_background_threshold: Background threshold (1-255)
        alpha_matting_erode_size: Edge smoothing size (1-20)
        post_process_mask: Apply additional mask refinement
    
    Returns:
        PNG image with transparent background (perfect edges with AI matting)
    """
    try:
        # Validate file type
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Read the uploaded file
        logger.info(f"Processing file: {file.filename} with model: {model}, alpha_matting: {alpha_matting}")
        contents = await file.read()
        
        # Validate file size
        file_size_mb = len(contents) / (1024 * 1024)
        if file_size_mb > 50:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file_size_mb:.1f}MB). Maximum size is 50MB."
            )
        
        # Open and validate image
        try:
            input_image = Image.open(io.BytesIO(contents))
            input_image.load()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or corrupt image file: {str(e)}"
            )
        
        logger.info(f"Original image: {input_image.size}, mode: {input_image.mode}")
        
        # Preprocess image
        img_for_processing, original_size = preprocess_image(input_image)
        
        # Remove background with retry logic
        logger.info(f"Removing background with model: {model}, alpha_matting: {alpha_matting}")
        
        max_retries = 2
        output_image = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                
                session = get_model_session(model)
                output_image = remove(
                    img_for_processing,
                    session=session,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                    alpha_matting_background_threshold=alpha_matting_background_threshold,
                    alpha_matting_erode_size=alpha_matting_erode_size,
                    post_process_mask=post_process_mask
                )
                
                if validate_result(img_for_processing, output_image):
                    break
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    try:
                        output_image = remove(
                            img_for_processing,
                            alpha_matting=alpha_matting,
                            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                            alpha_matting_background_threshold=alpha_matting_background_threshold,
                            alpha_matting_erode_size=alpha_matting_erode_size,
                            post_process_mask=post_process_mask
                        )
                    except Exception as fallback_error:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Background removal failed: {fallback_error}"
                        )
        
        if output_image is None:
            raise HTTPException(
                status_code=500,
                detail="Background removal failed after multiple attempts"
            )
        
        # Post-process for perfect results
        output_image = postprocess_image(output_image, original_size, refine=True)
        
        # Convert to bytes
        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        
        logger.info("Background removal completed successfully")
        
        return StreamingResponse(
            output_buffer,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=no_bg_{file.filename.rsplit('.', 1)[0]}.png"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
