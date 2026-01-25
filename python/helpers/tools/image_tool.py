"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    IMAGE TOOL — Safe Image Generation                        ║
║                                                                              ║
║  Génération d'images via provider configuré (DALL-E, etc.).                  ║
║                                                                              ║
║  SÉCURITÉ:                                                                   ║
║  - Validation stricte du prompt                                              ║
║  - Blocage des contenus interdits                                            ║
║  - Logging de toutes les requêtes                                            ║
║  - Pas d'exécution de code arbitraire                                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("image_tool")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class ImageSize(str, Enum):
    """Tailles d'images supportées."""
    SMALL = "256x256"
    MEDIUM = "512x512"
    LARGE = "1024x1024"
    WIDE = "1792x1024"
    TALL = "1024x1792"


class ImageQuality(str, Enum):
    """Qualités d'images."""
    STANDARD = "standard"
    HD = "hd"


class ImageStyle(str, Enum):
    """Styles d'images."""
    VIVID = "vivid"
    NATURAL = "natural"


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT POLICY
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns interdits dans les prompts
BLOCKED_PATTERNS = [
    # Violence
    r"\b(kill|murder|blood|gore|violent|weapon|gun|knife)\b",
    r"\b(torture|abuse|harm|attack|assault)\b",
    
    # Contenu adulte
    r"\b(nude|naked|nsfw|porn|sexual|explicit)\b",
    r"\b(erotic|sensual|provocative)\b",
    
    # Contenu illégal
    r"\b(drug|cocaine|heroin|meth|illegal)\b",
    r"\b(hack|exploit|malware|virus)\b",
    
    # Discours haineux
    r"\b(racist|nazi|hate|supremacist)\b",
    r"\b(slur|offensive|discriminat)\b",
    
    # Personnes réelles (sans contexte approprié)
    r"\b(deepfake|impersonate)\b",
    
    # Médical dangereux
    r"\b(self.?harm|suicide|cutting)\b",
]

# Patterns qui nécessitent une validation
WARNING_PATTERNS = [
    r"\b(celebrity|politician|famous)\b",
    r"\b(child|minor|kid|teen)\b",
    r"\b(medical|surgery|hospital)\b",
]


def check_prompt_policy(prompt: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Vérifie qu'un prompt respecte la politique de contenu.
    
    Args:
        prompt: Le prompt à vérifier
        
    Returns:
        (is_allowed, rejection_reason, warnings)
    """
    prompt_lower = prompt.lower()
    warnings = []
    
    # Vérifier les patterns bloqués
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            match = re.search(pattern, prompt_lower, re.IGNORECASE)
            return False, f"Content policy violation: blocked term '{match.group()}'", []
    
    # Vérifier les patterns d'avertissement
    for pattern in WARNING_PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            match = re.search(pattern, prompt_lower, re.IGNORECASE)
            warnings.append(f"Sensitive term detected: '{match.group()}'")
    
    return True, None, warnings


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE REQUEST SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

class ImageRequest(BaseModel):
    """
    Requête de génération d'image.
    
    Le LLM soumet ce schéma JSON pour demander une image.
    """
    
    # Prompt
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        description="Description de l'image à générer"
    )
    
    # Options
    size: ImageSize = Field(ImageSize.LARGE, description="Taille de l'image")
    quality: ImageQuality = Field(ImageQuality.STANDARD)
    style: ImageStyle = Field(ImageStyle.NATURAL)
    n: int = Field(1, ge=1, le=4, description="Nombre d'images à générer")
    
    # Sécurité
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID unique de la requête"
    )
    
    # Contexte (pour audit)
    context: str = Field("", max_length=500, description="Contexte de la requête")
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt_content(cls, v):
        is_allowed, reason, _ = check_prompt_policy(v)
        if not is_allowed:
            raise ValueError(reason)
        return v


def validate_image_request(
    request_json: Union[str, Dict],
) -> Tuple[bool, Optional[ImageRequest], Optional[str], List[str]]:
    """
    Valide une requête d'image.
    
    Args:
        request_json: JSON string ou dict de la requête
        
    Returns:
        (is_valid, parsed_request, error_message, warnings)
    """
    try:
        if isinstance(request_json, str):
            data = json.loads(request_json)
        else:
            data = request_json
        
        request = ImageRequest(**data)
        
        # Vérifier la politique une seconde fois pour les warnings
        _, _, warnings = check_prompt_policy(request.prompt)
        
        return True, request, None, warnings
        
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON: {e}", []
    except Exception as e:
        return False, None, f"Validation error: {e}", []


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ImageResult:
    """Résultat de la génération d'une image."""
    success: bool
    file_paths: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)  # Si provider retourne URLs
    request_id: str = ""
    error: Optional[str] = None
    generation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)
    
    # Audit
    prompt_hash: str = ""  # Hash du prompt pour audit sans exposer le contenu
    
    def to_markdown_refs(self) -> List[str]:
        """Retourne des références markdown vers les images."""
        refs = []
        for i, path in enumerate(self.file_paths):
            name = Path(path).name
            refs.append(f"![Image {i+1}]({path})")
        return refs


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE TOOL
# ═══════════════════════════════════════════════════════════════════════════════

class ImageTool:
    """
    Outil de génération d'images via provider configuré.
    
    Usage:
        tool = ImageTool(output_dir="reports/job_123/assets")
        
        request = ImageRequest(
            prompt="A futuristic city skyline at sunset, digital art style",
            size=ImageSize.LARGE,
            quality=ImageQuality.HD,
        )
        
        result = await tool.generate(request)
        print(result.file_paths)
    """
    
    def __init__(
        self,
        output_dir: str = "images",
        provider: str = None,  # Auto-detect from settings
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.provider = provider
        self._provider_client = None
        
        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
    
    async def generate(self, request: ImageRequest) -> ImageResult:
        """
        Génère une image.
        
        Args:
            request: Requête validée
            
        Returns:
            ImageResult avec les chemins des fichiers
        """
        start_time = time.time()
        
        # Vérifier la politique
        is_allowed, reason, warnings = check_prompt_policy(request.prompt)
        if not is_allowed:
            self._log_audit(request, success=False, error=reason)
            return ImageResult(
                success=False,
                request_id=request.request_id,
                error=reason,
                prompt_hash=self._hash_prompt(request.prompt),
            )
        
        try:
            # Appeler le provider
            images = await self._call_provider(request)
            
            # Sauvegarder les images
            file_paths = []
            for i, image_data in enumerate(images):
                filename = f"image_{request.request_id[:8]}_{i}.png"
                file_path = self.output_dir / filename
                
                if isinstance(image_data, bytes):
                    file_path.write_bytes(image_data)
                elif isinstance(image_data, str) and image_data.startswith("http"):
                    # Télécharger depuis URL
                    file_path = await self._download_image(image_data, file_path)
                else:
                    continue
                
                file_paths.append(str(file_path))
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            self._log_audit(request, success=True, file_paths=file_paths)
            
            logger.info(
                f"Generated {len(file_paths)} image(s) in {generation_time_ms}ms "
                f"[{request.request_id}]"
            )
            
            return ImageResult(
                success=True,
                file_paths=file_paths,
                request_id=request.request_id,
                generation_time_ms=generation_time_ms,
                warnings=warnings,
                prompt_hash=self._hash_prompt(request.prompt),
            )
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            self._log_audit(request, success=False, error=str(e))
            
            return ImageResult(
                success=False,
                request_id=request.request_id,
                error=str(e),
                generation_time_ms=int((time.time() - start_time) * 1000),
                prompt_hash=self._hash_prompt(request.prompt),
            )
    
    async def _call_provider(self, request: ImageRequest) -> List[Any]:
        """
        Appelle le provider d'images configuré.
        
        Override cette méthode pour intégrer avec votre provider.
        """
        # Essayer d'utiliser le provider configuré dans les settings
        try:
            from python.helpers.settings import get_settings
            settings = get_settings()
            
            # Déterminer le provider
            provider_name = self.provider or settings.get("image_gen_model", "")
            
            if "dall-e" in provider_name.lower() or "openai" in provider_name.lower():
                return await self._call_openai(request)
            elif "stable" in provider_name.lower():
                return await self._call_stability(request)
            else:
                # Placeholder
                return await self._placeholder_generate(request)
                
        except Exception as e:
            logger.warning(f"Provider not configured, using placeholder: {e}")
            return await self._placeholder_generate(request)
    
    async def _call_openai(self, request: ImageRequest) -> List[Any]:
        """Appelle DALL-E via OpenAI."""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI()
            
            response = await client.images.generate(
                model="dall-e-3",
                prompt=request.prompt,
                size=request.size.value,
                quality=request.quality.value,
                n=request.n,
            )
            
            return [img.url for img in response.data]
            
        except ImportError:
            raise RuntimeError("openai package not installed")
    
    async def _call_stability(self, request: ImageRequest) -> List[Any]:
        """Appelle Stability AI."""
        raise NotImplementedError("Stability AI provider not yet implemented")
    
    async def _placeholder_generate(self, request: ImageRequest) -> List[bytes]:
        """Génère une image placeholder."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            images = []
            for i in range(request.n):
                # Créer une image placeholder
                width, height = map(int, request.size.value.split("x"))
                img = Image.new('RGB', (width, height), color='#f0f0f0')
                draw = ImageDraw.Draw(img)
                
                # Ajouter du texte
                text = f"Image Placeholder\n{request.request_id[:8]}\n{i+1}/{request.n}"
                
                # Centrer le texte
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                except:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (width - text_width) / 2
                y = (height - text_height) / 2
                
                draw.text((x, y), text, fill='#333333', font=font, align='center')
                
                # Convertir en bytes
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                images.append(buffer.getvalue())
            
            return images
            
        except ImportError:
            # Sans PIL, créer un fichier vide
            return [b"placeholder"] * request.n
    
    async def _download_image(self, url: str, dest_path: Path) -> Path:
        """Télécharge une image depuis une URL."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.read()
                dest_path.write_bytes(content)
        
        return dest_path
    
    def _hash_prompt(self, prompt: str) -> str:
        """Hash le prompt pour audit sans exposer le contenu."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    def _log_audit(
        self,
        request: ImageRequest,
        success: bool,
        file_paths: List[str] = None,
        error: str = None,
    ):
        """Log pour audit."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request.request_id,
            "prompt_hash": self._hash_prompt(request.prompt),
            "prompt_length": len(request.prompt),
            "size": request.size.value,
            "n": request.n,
            "success": success,
            "files_generated": len(file_paths) if file_paths else 0,
            "error": error,
        }
        self._audit_log.append(entry)
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Retourne le log d'audit."""
        return self._audit_log.copy()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

_tool_instance: Optional[ImageTool] = None


async def generate_image(
    request_json: Union[str, Dict],
    output_dir: str = "images",
) -> ImageResult:
    """
    Génère une image depuis une requête JSON.
    
    Usage:
        result = await generate_image({
            "prompt": "A beautiful sunset over mountains",
            "size": "1024x1024",
            "quality": "hd"
        })
    """
    # Valider
    is_valid, request, error, warnings = validate_image_request(request_json)
    if not is_valid:
        return ImageResult(success=False, error=error)
    
    # Générer
    global _tool_instance
    if _tool_instance is None or str(_tool_instance.output_dir) != output_dir:
        _tool_instance = ImageTool(output_dir)
    
    result = await _tool_instance.generate(request)
    result.warnings.extend(warnings)
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "ImageSize",
    "ImageQuality",
    "ImageStyle",
    "ImageRequest",
    "ImageResult",
    "ImageTool",
    "check_prompt_policy",
    "validate_image_request",
    "generate_image",
]
