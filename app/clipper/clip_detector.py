"""
Clip Detector - Automatically finds highlight moments in videos.
Uses audio peaks, subtitle keywords, and scene changes.
"""
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from loguru import logger


class ClipDetector:
    """
    Detects highlight moments in videos.
    
    Detection methods:
    1. Audio energy peaks (crowd noise, commentator excitement)
    2. Subtitle keyword matching (GOAL, TOUCHDOWN, etc.)
    3. Chapter markers (if available)
    4. Scene change detection
    """
    
    # Keywords that indicate highlight moments in football/soccer
    HIGHLIGHT_KEYWORDS = [
        "goal", "goal!", "goooal", "amazing", "incredible", "unbelievable",
        "what a strike", "beautiful", "brilliant", "spectacular",
        "red card", "yellow card", "penalty", "foul", "injury",
        "substitution", "offside", "var", "review",
        "touchdown", "touchdown!", "quarterback", "interception",
        "homerun", "home run", "slam dunk", "buzzer beater",
        "knockout", "submission", "finish", "complete",
    ]
    
    # Excitement indicators (commentator getting loud)
    EXCITEMENT_PHRASES = [
        "oh my god", "omg", "unbelievable", "incredible", "amazing",
        "look at that", "what a moment", "history", "iconic",
        "listen to this crowd", "hear that roar",
    ]
    
    def __init__(self):
        pass
    
    def detect_from_subtitles(
        self,
        subtitle_path: str,
        clip_duration: int = 30,
        max_clips: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Detect highlight moments from subtitle file.
        
        Args:
            subtitle_path: Path to VTT/SRT subtitle file
            clip_duration: Desired clip duration in seconds
            max_clips: Maximum number of clips to detect
            
        Returns:
            List of clip timestamps with confidence scores
        """
        if not Path(subtitle_path).exists():
            logger.warning(f"Subtitle file not found: {subtitle_path}")
            return []
        
        # Parse subtitles
        subtitles = self._parse_vtt(subtitle_path)
        
        if not subtitles:
            logger.warning("No subtitles parsed")
            return []
        
        # Score each subtitle segment
        scored_segments = []
        for sub in subtitles:
            text = sub.get("text", "").lower()
            score = self._score_segment(text)
            
            if score > 0:
                scored_segments.append({
                    "start": sub.get("start", 0),
                    "end": sub.get("end", 0),
                    "text": sub.get("text", ""),
                    "score": score,
                    "keywords": self._extract_keywords(text),
                })
        
        # Group nearby high-scoring segments
        clips = self._group_segments(scored_segments, clip_duration)
        
        # Sort by score and limit
        clips.sort(key=lambda x: x["confidence"], reverse=True)
        return clips[:max_clips]
    
    def _parse_vtt(self, subtitle_path: str) -> List[Dict[str, Any]]:
        """Parse VTT subtitle file."""
        subtitles = []
        
        try:
            with open(subtitle_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Remove WEBVTT header
            if "WEBVTT" in content:
                content = content.split("WEBVTT", 1)[1]
            
            # Parse timestamps
            lines = content.strip().split("\n")
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines and index numbers
                if not line or line.isdigit():
                    i += 1
                    continue
                
                # Check for timestamp line
                if "-->" in line:
                    times = line.split(" --> ")
                    if len(times) == 2:
                        start = self._parse_timestamp(times[0].strip())
                        end = self._parse_timestamp(times[1].strip())
                        
                        # Collect text until next timestamp
                        text_lines = []
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if not next_line or "-->" in next_line or next_line.isdigit():
                                break
                            text_lines.append(next_line)
                            i += 1
                        
                        text = " ".join(text_lines)
                        
                        subtitles.append({
                            "start": start,
                            "end": end,
                            "text": text,
                        })
                
                i += 1
            
        except Exception as e:
            logger.error(f"Failed to parse VTT: {e}")
        
        return subtitles
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse VTT/SRT timestamp to seconds."""
        try:
            # Handle formats: 00:00:00.000 or 00:00:00,000
            timestamp = timestamp.replace(",", ".")
            
            if ":" in timestamp:
                parts = timestamp.split(":")
                if len(parts) == 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
                elif len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
            
            # Just seconds
            return float(timestamp)
            
        except Exception:
            return 0.0
    
    def _score_segment(self, text: str) -> int:
        """Score a subtitle segment for highlight potential."""
        score = 0
        text_lower = text.lower()
        
        # Check for highlight keywords
        for keyword in self.HIGHLIGHT_KEYWORDS:
            if keyword in text_lower:
                score += 2
        
        # Check for excitement phrases (higher weight)
        for phrase in self.EXCITEMENT_PHRASES:
            if phrase in text_lower:
                score += 5
        
        # Bonus for exclamation marks (excitement indicator)
        score += text.count("!") * 2
        
        # Bonus for uppercase words (commentator shouting)
        words = text.split()
        uppercase_count = sum(1 for word in words if word.isupper() and len(word) > 1)
        score += uppercase_count
        
        return score
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract matched keywords from text."""
        text_lower = text.lower()
        found = []
        
        for keyword in self.HIGHLIGHT_KEYWORDS + self.EXCITEMENT_PHRASES:
            if keyword in text_lower:
                found.append(keyword)
        
        return found
    
    def _group_segments(
        self,
        segments: List[Dict[str, Any]],
        clip_duration: int,
        gap_threshold: int = 10,
    ) -> List[Dict[str, Any]]:
        """Group nearby high-scoring segments into clips."""
        if not segments:
            return []
        
        # Sort by start time
        segments.sort(key=lambda x: x["start"])
        
        clips = []
        current_group = [segments[0]]
        
        for seg in segments[1:]:
            last_seg = current_group[-1]
            
            # Check if this segment is close to the current group
            if seg["start"] - last_seg["end"] <= gap_threshold:
                current_group.append(seg)
            else:
                # Finalize current clip
                clip = self._create_clip_from_group(current_group, clip_duration)
                clips.append(clip)
                current_group = [seg]
        
        # Don't forget last group
        if current_group:
            clip = self._create_clip_from_group(current_group, clip_duration)
            clips.append(clip)
        
        return clips
    
    def _create_clip_from_group(
        self,
        group: List[Dict[str, Any]],
        target_duration: int,
    ) -> Dict[str, Any]:
        """Create a clip definition from a group of segments."""
        start_time = group[0]["start"]
        end_time = group[-1]["end"]
        
        natural_duration = end_time - start_time
        
        # Adjust to target duration if needed
        if natural_duration < target_duration:
            # Extend slightly
            padding = (target_duration - natural_duration) / 2
            start_time = max(0, start_time - padding)
            end_time = end_time + padding
        elif natural_duration > target_duration * 1.5:
            # Too long, center on highest scored segment
            best_seg = max(group, key=lambda x: x["score"])
            start_time = max(0, best_seg["start"] - target_duration / 2)
            end_time = start_time + target_duration
        
        total_score = sum(s["score"] for s in group)
        all_keywords = []
        for s in group:
            all_keywords.extend(s["keywords"])
        
        return {
            "start": start_time,
            "end": end_time,
            "duration": end_time - start_time,
            "confidence": total_score,
            "keywords": list(set(all_keywords)),
            "segment_count": len(group),
            "preview_text": group[0]["text"][:100] if group else "",
        }
    
    def detect_from_chapters(
        self,
        chapters: List[Dict[str, Any]],
        clip_duration: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Detect clips from chapter markers.
        
        Args:
            chapters: List of chapter dicts with title/start_time/end_time
            clip_duration: Target clip duration
            
        Returns:
            List of clip definitions
        """
        clips = []
        
        for chapter in chapters:
            title = chapter.get("title", "").lower()
            
            # Score chapter by title
            score = self._score_segment(title)
            
            if score > 0:
                start = chapter.get("start_time", 0)
                end = chapter.get("end_time", start + clip_duration)
                
                # Adjust duration
                if end - start > clip_duration:
                    end = start + clip_duration
                
                clips.append({
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "confidence": score,
                    "keywords": self._extract_keywords(title),
                    "chapter_title": chapter.get("title"),
                })
        
        return clips
    
    def detect_from_audio_peaks(
        self,
        audio_path: str,
        clip_duration: int = 30,
        threshold_db: float = -20.0,
        max_clips: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Detect highlight moments from audio energy peaks.
        
        Args:
            audio_path: Path to audio file
            clip_duration: Target clip duration
            threshold_db: Minimum dB level for peak detection
            max_clips: Maximum clips to return
            
        Returns:
            List of clip definitions
        """
        try:
            import librosa
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            
            # Compute RMS energy
            hop_length = 512
            rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
            
            # Convert to dB
            rms_db = librosa.amplitude_to_db(rms, ref=np.max)
            
            # Find peaks above threshold
            peaks = []
            for i in range(1, len(rms_db) - 1):
                if rms_db[i] > threshold_db:
                    if rms_db[i] > rms_db[i-1] and rms_db[i] > rms_db[i+1]:
                        time_sec = i * hop_length / sr
                        peaks.append({
                            "time": time_sec,
                            "energy": float(rms_db[i]),
                        })
            
            # Group nearby peaks and create clips
            clips = self._group_peaks_to_clips(
                peaks, 
                clip_duration,
                max_clips
            )
            
            return clips
            
        except ImportError:
            logger.warning("librosa not installed - install with: pip install librosa")
            return []
        except Exception as e:
            logger.error(f"Audio peak detection failed: {e}")
            return []
    
    def _group_peaks_to_clips(
        self,
        peaks: List[Dict[str, Any]],
        clip_duration: int,
        max_clips: int,
    ) -> List[Dict[str, Any]]:
        """Group audio peaks into clip definitions."""
        if not peaks:
            return []
        
        # Sort by energy
        peaks.sort(key=lambda x: x["energy"], reverse=True)
        
        clips = []
        used_times = set()
        
        for peak in peaks:
            if len(clips) >= max_clips:
                break
            
            peak_time = peak["time"]
            
            # Check if this peak is too close to an existing clip
            too_close = False
            for clip in clips:
                if abs(peak_time - clip["start"]) < clip_duration:
                    too_close = True
                    break
            
            if not too_close:
                start = max(0, peak_time - clip_duration / 2)
                end = peak_time + clip_duration / 2
                
                clips.append({
                    "start": start,
                    "end": end,
                    "duration": clip_duration,
                    "confidence": peak["energy"],
                    "keywords": ["audio_peak"],
                    "preview_text": f"Audio peak at {peak_time:.1f}s",
                })
        
        return clips