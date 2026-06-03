"""
Updated subtitle generator using faster-whisper (FREE, open-source).

Model options (all zero-cost):
- faster-whisper-tiny: 39MB, ultra-fast, decent accuracy
- faster-whisper-base: 71MB, best speed/accuracy balance ⭐ RECOMMENDED  
- faster-whisper-small: 244MB, higher accuracy for thick accents
"""
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger


class SubtitleGenerator:
    """
    Generates subtitles with word-level timing using FREE models.
    
    Uses faster-whisper (CTranslate2-based) for 5x speedup over openai-whisper.
    Creates styled ASS/SRT files for dynamic on-screen captions.
    """
    
    # Model selection - all open-source, zero cost
    WHISPER_MODEL = "base"  # Options: "tiny", "base", "small", "medium", "large"
    
    def __init__(self, output_dir: str = "./temp/subtitles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_from_audio(
        self,
        audio_path: str,
        output_filename: Optional[str] = None,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """Generate subtitles from audio using faster-whisper."""
        try:
            segments = await self._run_faster_whisper(audio_path, language)
            
            if output_filename:
                output_path = self.output_dir / output_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(segments, f, indent=2)
                logger.info(f"Saved {len(segments)} subtitle segments")
            
            return segments
            
        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            return self._fallback_subtitles()
    
    async def _run_faster_whisper(
        self, 
        audio_path: str, 
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Run faster-whisper transcription.
        
        Zero cost, open-source, runs locally on CPU.
        Downloads model on first run (~71MB for base), then cached.
        """
        from faster_whisper import WhisperModel
        
        # Load model (cached after first download)
        model = WhisperModel(
            self.WHISPER_MODEL,
            device="cpu",  # Use "cuda" for GPU (10x faster)
            compute_type="int8",  # Quantized for speed
        )
        
        segments, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,  # Removes silence
        )
        
        logger.info(f"Transcribed with faster-whisper ({info.language})")
        
        result = []
        for segment in segments:
            result.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": [
                    {
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end,
                    }
                    for word in (segment.words or [])
                ]
            })
        
        return result
    
    def _fallback_subtitles(self) -> List[Dict[str, Any]]:
        """Return empty subtitles as fallback."""
        return []
    
    def create_ass_subtitle(
        self,
        segments: List[Dict[str, Any]],
        output_filename: str,
        style: str = "dynamic"
    ) -> str:
        """Create ASS subtitle file with advanced styling."""
        output_path = self.output_dir / output_filename
        
        ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
        
        if style == "dynamic":
            ass_content += """Style: MainFont,Arial Bold,64,&H00FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2.0,0,3,2.5,0,8,10,10,70,1
Style: Highlight,Arial Black,72,&H00FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2.0,0,3,3,0,8,10,10,70,1
"""
        
        ass_content += """
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        for segment in segments:
            start_time = self._seconds_to_ass_time(segment["start"])
            end_time = self._seconds_to_ass_time(segment["end"])
            text = self._split_subtitle_text(segment["text"])
            
            ass_content += f"Dialogue: 0,{start_time},{end_time},MainFont,,0,0,0,,{text}\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        logger.info(f"Created ASS subtitle: {output_path}")
        return str(output_path)
    
    def create_srt_subtitle(
        self,
        segments: List[Dict[str, Any]],
        output_filename: str
    ) -> str:
        """Create standard SRT subtitle file."""
        output_path = self.output_dir / output_filename
        
        srt_content = ""
        for i, segment in enumerate(segments, 1):
            start_time = self._seconds_to_srt_time(segment["start"])
            end_time = self._seconds_to_srt_time(segment["end"])
            text = segment["text"].strip()
            
            srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        logger.info(f"Created SRT subtitle: {output_path}")
        return str(output_path)
    
    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _split_subtitle_text(self, text: str, max_length: int = 40) -> str:
        """Split long subtitle text into multiple lines."""
        if len(text) <= max_length:
            return text.replace('\n', '\\N')
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_length:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\\N'.join(lines)