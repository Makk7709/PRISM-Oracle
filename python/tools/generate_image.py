"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    IMAGE GENERATION TOOL                                     ║
║                                                                              ║
║  Unified tool for AI image generation with provider fallback.               ║
║  Supports: OpenAI DALL-E, Google Imagen                                     ║
║                                                                              ║
║  Version: 1.1.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import base64
import os
import time
import uuid
from typing import Any, Optional

import aiohttp

from python.helpers.tool import Tool, Response
from python.helpers import settings, files
from python.helpers.print_style import PrintStyle

# Directory for saving generated images
GENERATED_IMAGES_DIR = "tmp/generated_images"


class GenerateImage(Tool):
    """
    Unified image generation tool with automatic provider selection and fallback.
    """

    async def execute(
        self,
        prompt: str = "",
        size: str = "",
        quality: str = "",
        n: int = 1,
        style: str = "",
        purpose: str = "",
        **kwargs
    ) -> Response:
        """
        Generate images using configured providers.
        
        Args:
            prompt: Description of the image to generate
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: Quality level (standard, hd)
            n: Number of images to generate
            style: Style preference (vivid, natural)
            purpose: Context (marketing, branding, etc.)
        """
        start_time = time.time()
        
        # Validate prompt
        if not prompt or not prompt.strip():
            return Response(
                message=self._format_error("Missing required argument: prompt"),
                break_loop=False
            )
        
        # Get settings
        current_settings = settings.get_settings()
        
        # Check if image generation is enabled
        if not current_settings.get("image_gen_enabled", True):
            return Response(
                message=self._format_error("Image generation is disabled in settings"),
                break_loop=False
            )
        
        # Get defaults from settings
        size = size or current_settings.get("image_gen_default_size", "1024x1024")
        quality = quality or current_settings.get("image_gen_default_quality", "standard")
        n = min(n, 4)  # Cap at 4 images
        
        # Determine providers
        primary = current_settings.get("image_gen_primary_provider", "openai")
        fallback = current_settings.get("image_gen_fallback_provider", "none")
        
        # SMART PROVIDER SELECTION: If OpenAI key is available, prefer it over Google
        # This ensures we use the best model (gpt-image-1) when possible
        openai_key = (
            current_settings.get("image_gen_openai_api_key") or
            current_settings.get("api_keys", {}).get("openai") or
            os.environ.get("API_KEY_OPENAI") or
            os.environ.get("OPENAI_API_KEY")
        )
        
        if openai_key and primary == "google":
            # Swap: use OpenAI as primary since we have the key
            PrintStyle(font_color="green").print(
                f"[Image Gen] OpenAI API key detected, using OpenAI (gpt-image-1) as primary"
            )
            primary, fallback = "openai", primary  # OpenAI first, Google as fallback
        
        PrintStyle(font_color="cyan").print(f"[Image Gen] Generating image with {primary}...")
        
        # Try primary provider
        result = await self._generate_with_provider(
            provider=primary,
            prompt=prompt,
            size=size,
            quality=quality,
            n=n,
            style=style,
            purpose=purpose,
            settings=current_settings
        )
        
        fallback_used = False
        
        # If primary failed and fallback is configured, try fallback
        if result.get("status") == "error" and fallback and fallback != "none" and fallback != primary:
            PrintStyle(font_color="yellow").print(
                f"Primary provider ({primary}) failed, trying fallback ({fallback})..."
            )
            PrintStyle(font_color="yellow").print(f"[Image Gen] Fallback: generating with {fallback}...")
            
            result = await self._generate_with_provider(
                provider=fallback,
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
                style=style,
                purpose=purpose,
                settings=current_settings
            )
            
            if result.get("status") == "success":
                fallback_used = True
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        result["latency_ms"] = latency_ms
        result["fallback_used"] = fallback_used
        
        # Download and save images locally for better display
        if result.get("status") == "success":
            images = result.get("images", [])
            local_images = []
            
            async with aiohttp.ClientSession() as session:
                for img in images:
                    if img.startswith("data:"):
                        # Base64 image - save locally
                        local_path = await self._save_base64_image(img)
                        local_images.append(local_path)
                    elif img.startswith("http"):
                        # URL image - download and save locally
                        local_path = await self._download_and_save_image(img, session)
                        local_images.append(local_path)
                    else:
                        local_images.append(img)
            
            result["local_images"] = local_images
        
        # Log result
        self._log_generation(result, prompt, purpose)
        
        # Format response
        if result.get("status") == "success":
            return Response(
                message=self._format_success(result, prompt),
                break_loop=False
            )
        else:
            return Response(
                message=self._format_error(result.get("error", "Unknown error")),
                break_loop=False
            )

    async def _generate_with_provider(
        self,
        provider: str,
        prompt: str,
        size: str,
        quality: str,
        n: int,
        style: str,
        purpose: str,
        settings: dict
    ) -> dict[str, Any]:
        """Generate image with specified provider."""
        try:
            if provider == "openai":
                return await self._generate_openai(
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=n,
                    style=style,
                    settings=settings
                )
            elif provider == "google":
                return await self._generate_google(
                    prompt=prompt,
                    size=size,
                    n=n,
                    settings=settings
                )
            else:
                return {
                    "status": "error",
                    "provider": provider,
                    "error": f"Unknown provider: {provider}"
                }
        except Exception as e:
            return {
                "status": "error",
                "provider": provider,
                "error": str(e)
            }

    async def _generate_openai(
        self,
        prompt: str,
        size: str,
        quality: str,
        n: int,
        style: str,
        settings: dict
    ) -> dict[str, Any]:
        """Generate image using OpenAI DALL-E."""
        # Get API key - try multiple sources
        api_key = settings.get("image_gen_openai_api_key")
        if not api_key:
            # Fall back to main OpenAI key from settings
            api_key = settings.get("api_keys", {}).get("openai")
        if not api_key:
            # Fall back to environment variables (both naming conventions)
            api_key = os.environ.get("API_KEY_OPENAI") or os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            return {
                "status": "error",
                "provider": "openai",
                "error": "OpenAI API key not configured"
            }
        
        model = settings.get("image_gen_openai_model", "gpt-image-1")
        
        PrintStyle(font_color="cyan").print(f"[Image Gen] Using OpenAI model: {model}")
        
        # Prepare request
        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Build payload based on model
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
        }
        
        # Model-specific parameters
        if model == "dall-e-2":
            payload["n"] = n  # DALL-E 2 supports multiple images
        elif model == "dall-e-3":
            payload["n"] = 1  # DALL-E 3 only supports n=1
            payload["quality"] = quality
            if style:
                payload["style"] = style
        elif model.startswith("gpt-image") or model.startswith("chatgpt-image"):
            # GPT-Image models (gpt-image-1, gpt-image-1.5, chatgpt-image-latest, etc.)
            payload["n"] = 1  # Only n=1 for newer models
            
            # Map quality: gpt-image uses low/medium/high/auto instead of standard/hd
            quality_map = {
                "standard": "medium",
                "hd": "high",
                "low": "low",
                "medium": "medium", 
                "high": "high",
                "auto": "auto",
            }
            payload["quality"] = quality_map.get(quality, "high")
            
            # GPT-Image models support more sizes
            if size not in ["1024x1024", "1792x1024", "1024x1792", "auto"]:
                payload["size"] = "1024x1024"  # Fallback to square
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=120) as response:
                if response.status != 200:
                    error_data = await response.json()
                    return {
                        "status": "error",
                        "provider": "openai",
                        "error": error_data.get("error", {}).get("message", f"HTTP {response.status}")
                    }
                
                data = await response.json()
                images = [img.get("url") or img.get("b64_json") for img in data.get("data", [])]
                
                return {
                    "status": "success",
                    "provider": "openai",
                    "model": model,
                    "images": images,
                    "revised_prompt": data.get("data", [{}])[0].get("revised_prompt")
                }

    async def _generate_google(
        self,
        prompt: str,
        size: str,
        n: int,
        settings: dict
    ) -> dict[str, Any]:
        """Generate image using Google Imagen."""
        # Get API key - try multiple sources
        api_key = settings.get("image_gen_google_api_key")
        if not api_key:
            # Fall back to environment variables (both naming conventions)
            api_key = os.environ.get("API_KEY_GOOGLE") or os.environ.get("GOOGLE_API_KEY")
        
        if not api_key:
            return {
                "status": "error",
                "provider": "google",
                "error": "Google API key not configured"
            }
        
        model = settings.get("image_gen_google_model", "imagen-3.0-generate-001")
        
        # Map size to aspect ratio
        aspect_ratio = "1:1"
        if size == "1792x1024":
            aspect_ratio = "16:9"
        elif size == "1024x1792":
            aspect_ratio = "9:16"
        
        # Prepare request for Vertex AI / Generative AI
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateImages"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        
        payload = {
            "prompt": prompt,
            "number_of_images": min(n, 4),
            "aspect_ratio": aspect_ratio,
            "safety_filter_level": "BLOCK_ONLY_HIGH",
            "person_generation": "ALLOW_ADULT"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=120) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "status": "error",
                        "provider": "google",
                        "error": f"HTTP {response.status}: {error_text[:200]}"
                    }
                
                data = await response.json()
                
                # Extract images from response
                images = []
                for img in data.get("generatedImages", []):
                    if "image" in img:
                        # Base64 encoded
                        images.append(f"data:image/png;base64,{img['image']['bytesBase64Encoded']}")
                    elif "uri" in img:
                        images.append(img["uri"])
                
                if not images:
                    return {
                        "status": "error",
                        "provider": "google",
                        "error": "No images returned"
                    }
                
                return {
                    "status": "success",
                    "provider": "google",
                    "model": model,
                    "images": images
                }

    async def _download_and_save_image(self, url: str, session: aiohttp.ClientSession) -> str:
        """Download image from URL and save locally, return local path."""
        try:
            async with session.get(url, timeout=60) as response:
                if response.status != 200:
                    PrintStyle(font_color="red").print(f"[Image Gen] Failed to download image: HTTP {response.status}")
                    return url  # Return original URL as fallback
                
                # Generate unique filename
                image_id = str(uuid.uuid4())[:8]
                timestamp = int(time.time())
                filename = f"generated_{timestamp}_{image_id}.png"
                
                # Ensure directory exists
                save_dir = files.get_abs_path(GENERATED_IMAGES_DIR)
                os.makedirs(save_dir, exist_ok=True)
                
                # Save image
                filepath = os.path.join(save_dir, filename)
                image_data = await response.read()
                
                with open(filepath, "wb") as f:
                    f.write(image_data)
                
                PrintStyle(font_color="green").print(f"[Image Gen] Image saved to: {filepath}")
                
                # Return path that can be served by Flask
                return f"img://{GENERATED_IMAGES_DIR}/{filename}"
                
        except Exception as e:
            PrintStyle(font_color="red").print(f"[Image Gen] Error downloading image: {e}")
            return url  # Return original URL as fallback

    async def _save_base64_image(self, base64_data: str) -> str:
        """Save base64 image locally, return local path."""
        try:
            # Remove data URL prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]
            
            # Generate unique filename
            image_id = str(uuid.uuid4())[:8]
            timestamp = int(time.time())
            filename = f"generated_{timestamp}_{image_id}.png"
            
            # Ensure directory exists
            save_dir = files.get_abs_path(GENERATED_IMAGES_DIR)
            os.makedirs(save_dir, exist_ok=True)
            
            # Save image
            filepath = os.path.join(save_dir, filename)
            image_data = base64.b64decode(base64_data)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            PrintStyle(font_color="green").print(f"[Image Gen] Image saved to: {filepath}")
            
            # Return path that can be served by Flask
            return f"img://{GENERATED_IMAGES_DIR}/{filename}"
            
        except Exception as e:
            PrintStyle(font_color="red").print(f"[Image Gen] Error saving base64 image: {e}")
            return base64_data  # Return original as fallback

    def _format_success(self, result: dict, prompt: str) -> str:
        """Format successful generation result."""
        images = result.get("images", [])
        local_images = result.get("local_images", [])  # Use local paths if available
        provider = result.get("provider", "unknown")
        model = result.get("model", "")
        latency = result.get("latency_ms", 0)
        fallback = result.get("fallback_used", False)
        
        # Prefer local images if available
        display_images = local_images if local_images else images
        
        # Build clean output - image will be displayed inline by UI
        output = "## ✅ Image générée avec succès\n\n"
        
        # Display images with download links
        for i, img in enumerate(display_images, 1):
            output += f"![Image {i}]({img})\n\n"
            # Add direct download link (convert img:// to /image_get URL)
            if img.startswith("img://"):
                download_url = img.replace("img://", "/image_get?path=")
                output += f"[⬇️ Télécharger l'image]({download_url})\n\n"
        
        # Add simple metadata
        output += f"*{provider}"
        if model:
            output += f" ({model})"
        output += f" • {latency}ms"
        if fallback:
            output += " • fallback"
        output += "*\n"
        
        return output

    def _format_error(self, error: str) -> str:
        """Format error message."""
        return f"## ❌ Image Generation Failed\n\n**Error:** {error}\n\n" \
               f"Please check your API keys in Settings → Image Generation, " \
               f"or try a different provider."

    def _log_generation(self, result: dict, prompt: str, purpose: str):
        """Log image generation for analytics."""
        status = result.get("status", "unknown")
        provider = result.get("provider", "unknown")
        latency = result.get("latency_ms", 0)
        fallback = result.get("fallback_used", False)
        
        log_msg = f"Image Generation: status={status}, provider={provider}, "
        log_msg += f"latency={latency}ms, fallback={fallback}, purpose={purpose}"
        
        if status == "success":
            PrintStyle(font_color="green").print(log_msg)
        else:
            PrintStyle(font_color="red").print(log_msg)
            PrintStyle(font_color="red").print(f"  Error: {result.get('error', 'unknown')}")
        
        # Log to agent context if available
        if self.agent and self.agent.context:
            self.agent.context.log.log(
                type="tool" if status == "success" else "error",
                heading="Image Generation",
                content=log_msg,
                kvps={
                    "status": status,
                    "provider": provider,
                    "latency_ms": latency,
                    "fallback_used": fallback,
                    "purpose": purpose,
                    "prompt_length": len(prompt)
                }
            )
