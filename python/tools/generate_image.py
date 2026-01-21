"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    IMAGE GENERATION TOOL                                     ║
║                                                                              ║
║  Unified tool for AI image generation with provider fallback.               ║
║  Supports: OpenAI DALL-E, Google Imagen                                     ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import base64
import os
import time
from typing import Any, Optional

import aiohttp

from python.helpers.tool import Tool, Response
from python.helpers import settings
from python.helpers.print_style import PrintStyle


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
        # Get API key
        api_key = settings.get("image_gen_openai_api_key")
        if not api_key:
            # Fall back to main OpenAI key
            api_key = settings.get("api_keys", {}).get("openai")
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            return {
                "status": "error",
                "provider": "openai",
                "error": "OpenAI API key not configured"
            }
        
        model = settings.get("image_gen_openai_model", "dall-e-3")
        
        # Prepare request
        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "prompt": prompt,
            "n": n if model == "dall-e-2" else 1,  # DALL-E 3 only supports n=1
            "size": size,
            "quality": quality,
        }
        
        if style and model == "dall-e-3":
            payload["style"] = style
        
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
        api_key = settings.get("image_gen_google_api_key")
        if not api_key:
            api_key = os.environ.get("GOOGLE_API_KEY")
        
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

    def _format_success(self, result: dict, prompt: str) -> str:
        """Format successful generation result."""
        images = result.get("images", [])
        provider = result.get("provider", "unknown")
        model = result.get("model", "")
        latency = result.get("latency_ms", 0)
        fallback = result.get("fallback_used", False)
        revised = result.get("revised_prompt", "")
        
        output = f"## ✅ Image Generated\n\n"
        output += f"**Provider:** {provider}"
        if model:
            output += f" ({model})"
        output += "\n"
        
        if fallback:
            output += "**Note:** Fallback provider was used\n"
        
        output += f"**Generation time:** {latency}ms\n\n"
        
        if revised and revised != prompt:
            output += f"**Revised prompt:** {revised}\n\n"
        
        output += "### Generated Images\n\n"
        for i, img in enumerate(images, 1):
            if img.startswith("data:"):
                output += f"![Generated Image {i}]({img})\n\n"
            else:
                output += f"**Image {i}:** [View Image]({img})\n\n"
                output += f"![Generated Image {i}]({img})\n\n"
        
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
