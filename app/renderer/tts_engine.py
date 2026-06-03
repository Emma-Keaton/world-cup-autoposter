"""
Text-to-Speech engine using Edge-TTS (FREE, zero-cost).
Generates natural-sounding voiceovers for reels.

Edge-TTS uses Microsoft's Azure neural TTS via Edge browser API - completely free!
No API key required, no rate limits, excellent quality.
"""
import asyncio
import edge_tts
from pathlib import Path
from typing import Optional, List
from loguru import logger

from app.core.config import settings


class TTSEngine:
    """
    Text-to-Speech engine using Edge-TTS (FREE).
    
    Edge-TTS provides free, high-quality neural voiceovers
    with 100+ voices across multiple languages.
    
    Zero cost, zero setup, zero API keys.
    """
    
    # Football-appropriate voices (energetic, clear, sports commentator style)
    # All FREE via Microsoft Edge TTS API
    VOICE_OPTIONS = {
        # Male voices - US (best for football commentary)
        "male_1": "en-US-GuyNeural",       # Warm, professional (DEFAULT)
        "male_2": "en-US-DavisNeural",      # Deep, authoritative
        "male_3": "en-US-TonyNeural",       # Energetic, upbeat
        "commentator": "en-US-EricNeural",  # Sports broadcast style ⭐ RECOMMENDED
        # Male voices - UK
        "male_uk_1": "en-GB-RyanNeural",    # British, clear
        "male_uk_2": "en-GB-ThomasNeural",  # British, warm
        # Female voices - US
        "female_1": "en-US-AriaNeural",     # Clear, professional
        "female_2": "en-US-JennyNeural",    # Friendly
        "female_3": "en-US-MichelleNeural", # Energetic
        # Female voices - UK
        "female_uk_1": "en-GB-SoniaNeural", # British, clear
        # High-energy voices for viral content
        "energetic": "en-US-AndrewNeural",  # Dynamic, engaging
    }
    
    def __init__(self, output_dir: str = "./temp/audio"):
        """
        Initialize TTS engine.
        
        Args:
            output_dir: Directory for audio outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_speech(
        self,
        text: str,
        voice: str = "male_1",
        output_filename: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> str:
        """
        Generate speech from text.
        
        Args:
            text: Text to synthesize
            voice: Voice preset key (male_1, female_1, etc.)
            output_filename: Custom output filename
            rate: Speech rate (+10% faster, -10% slower)
            pitch: Pitch adjustment
            volume: Volume adjustment
            
        Returns:
            Path to generated audio file
        """
        voice_id = self.VOICE_OPTIONS.get(voice, self.VOICE_OPTIONS["male_1"])
        
        if not output_filename:
            import uuid
            output_filename = f"{uuid.uuid4()}.mp3"
        
        output_path = self.output_dir / output_filename
        
        # Prepare text with SSML for better pacing (important for 30s reels)
        ssml_text = self._optimize_for_short_form(text)
        
        try:
            communicate = edge_tts.Communicate(
                ssml_text,
                voice_id,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            
            await communicate.save(str(output_path))
            
            logger.info(f"Generated speech: {output_path} ({len(text)} chars, voice: {voice})")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise
    
    def _optimize_for_short_form(self, text: str) -> str:
        """
        Optimize text for short-form content (30 seconds).
        
        Adds pauses and emphasis for dramatic effect.
        
        Args:
            text: Original text
            
        Returns:
            SSML-optimized text
        """
        # Split into sentences
        sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
        
        # Build SSML with pauses
        ssml_parts = ['<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">']
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip('.')
            
            # Add emphasis to first sentence (hook)
            if i == 0:
                ssml_parts.append(f'<emphasis level="moderate">{sentence}.</emphasis>')
                ssml_parts.append('<break time="200ms"/>')
            
            # Add pauses between sentences
            elif i == len(sentences) - 1:
                # Last sentence - dramatic pause before
                ssml_parts.append(f'<break time="150ms"/>')
                ssml_parts.append(f'{sentence}.')
            
            else:
                ssml_parts.append(f'{sentence}.')
                ssml_parts.append('<break time="100ms"/>')
        
        ssml_parts.append('</speak>')
        
        return ' '.join(ssml_parts)
    
    async def estimate_duration(
        self,
        text: str,
        voice: str = "male_1",
        rate: str = "+0%"
    ) -> float:
        """
        Estimate audio duration for text.
        
        Args:
            text: Text to estimate
            voice: Voice preset
            rate: Speech rate
            
        Returns:
            Estimated duration in seconds
        """
        # Rough estimate: ~150 words per minute at normal rate
        words = len(text.split())
        
        # Adjust for rate
        rate_adjustment = 1.0
        if rate:
            if rate.startswith('+'):
                rate_adjustment = 1.0 - (float(rate.rstrip('%')) / 100)
            elif rate.startswith('-'):
                rate_adjustment = 1.0 + (float(rate.lstrip('-%')) / 100)
        
        # Base duration (words / 150 * 60 seconds)
        duration = (words / 150) * 60 * rate_adjustment
        
        # Add pauses (approximately 0.5s per sentence)
        sentences = text.count('.') + 1
        duration += sentences * 0.5
        
        return round(duration, 2)
    
    async def get_available_voices(self) -> List[Dict[str, str]]:
        """
        Get list of available voices.
        
        Returns:
            List of voice options with metadata
        """
        voices = []
        
        for key, voice_id in self.VOICE_OPTIONS.items():
            voices.append({
                "id": key,
                "voice_id": voice_id,
                "gender": "male" if "male" in key else "female",
                "locale": voice_id.split('-')[1] if '-' in voice_id else "US",
            })
        
        return voices
    
    async def batch_generate(
        self,
        texts: List[str],
        voice: str = "male_1",
        output_prefix: Optional[str] = None
    ) -> List[str]:
        """
        Generate speech for multiple texts.
        
        Args:
            texts: List of texts to synthesize
            voice: Voice preset
            output_prefix: Filename prefix
            
        Returns:
            List of generated audio paths
        """
        import uuid
        
        tasks = []
        output_paths = []
        
        for i, text in enumerate(texts):
            filename = f"{output_prefix}_{i}" if output_prefix else f"{uuid.uuid4()}"
            output_path = await self.generate_speech(text, voice, f"{filename}.mp3")
            output_paths.append(output_path)
        
        return output_paths