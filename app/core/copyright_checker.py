"""
Copyright Safety Checker - Automated copyright risk assessment and mitigation.

Features:
- Fair use scoring engine
- Content ID avoidance techniques
- Audio fingerprinting comparison
- Visual similarity scoring
- Risk level classification
- Mitigation recommendations
"""
import asyncio
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not installed - audio fingerprinting disabled")

try:
    from PIL import Image
    import imagehash
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/imagehash not installed - visual fingerprinting disabled")


class RiskLevel(str, Enum):
    """Copyright risk classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FairUseFactor(str, Enum):
    """Four factors of fair use (US law)."""
    PURPOSE = "purpose_character"
    NATURE = "nature_of_work"
    AMOUNT = "amount_used"
    EFFECT = "market_effect"


@dataclass
class CopyrightCheck:
    """Result of a single copyright check."""
    name: str
    passed: bool
    score: float
    details: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class FairUseReport:
    """Comprehensive fair use analysis."""
    overall_score: float
    risk_level: RiskLevel
    factors: Dict[FairUseFactor, float] = field(default_factory=dict)
    checks: List[CopyrightCheck] = field(default_factory=list)
    approved: bool = False
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CopyrightSafetyChecker:
    """
    Automated copyright risk assessment for football content.
    """
    
    RISK_THRESHOLDS = {
        RiskLevel.LOW: 80,
        RiskLevel.MEDIUM: 60,
        RiskLevel.HIGH: 40,
        RiskLevel.CRITICAL: 0,
    }
    
    FACTOR_WEIGHTS = {
        FairUseFactor.PURPOSE: 0.35,
        FairUseFactor.NATURE: 0.15,
        FairUseFactor.AMOUNT: 0.25,
        FairUseFactor.EFFECT: 0.25,
    }
    
    def __init__(self):
        pass
    
    async def verify_fair_use(
        self,
        video_path: str,
        source_materials: Optional[List[str]] = None,
        script: Optional[str] = None,
        editing_metadata: Optional[Dict[str, Any]] = None,
    ) -> FairUseReport:
        """Comprehensive fair use verification."""
        
        checks = []
        factor_scores = {}
        
        # Check 1: Transformative content
        purpose_check = await self._check_transformative_elements(
            video_path, script, editing_metadata
        )
        checks.append(purpose_check)
        factor_scores[FairUseFactor.PURPOSE] = purpose_check.score
        
        # Check 2: Nature of work
        nature_check = await self._check_nature_of_work(source_materials)
        checks.append(nature_check)
        factor_scores[FairUseFactor.NATURE] = nature_check.score
        
        # Check 3: Amount used
        amount_check = await self._check_amount_used(
            video_path, source_materials, editing_metadata
        )
        checks.append(amount_check)
        factor_scores[FairUseFactor.AMOUNT] = amount_check.score
        
        # Check 4: Market effect
        effect_check = await self._check_market_effect(video_path)
        checks.append(effect_check)
        factor_scores[FairUseFactor.EFFECT] = effect_check.score
        
        # Check 5: Audio fingerprint
        if LIBROSA_AVAILABLE and source_materials:
            audio_check = await self._check_audio_fingerprint(
                video_path, source_materials
            )
            if audio_check:
                checks.append(audio_check)
        
        # Check 6: Visual similarity
        if PIL_AVAILABLE and source_materials:
            visual_check = await self._check_visual_similarity(
                video_path, source_materials
            )
            if visual_check:
                checks.append(visual_check)
        
        # Calculate weighted score
        weighted_score = sum(
            factor_scores[factor] * weight
            for factor, weight in self.FACTOR_WEIGHTS.items()
        )
        
        # Adjust for technical checks
        technical_checks = [c for c in checks if c.name in ["audio_fingerprint", "visual_similarity"]]
        if technical_checks:
            tech_avg = sum(c.score for c in technical_checks) / len(technical_checks)
            weighted_score = weighted_score * 0.7 + tech_avg * 0.3
        
        risk_level = self._score_to_risk(weighted_score)
        recommendations = self._generate_recommendations(checks, factor_scores)
        
        approved = (
            weighted_score >= 70 and
            all(c.score >= 50 for c in checks) and
            risk_level != RiskLevel.CRITICAL
        )
        
        return FairUseReport(
            overall_score=round(weighted_score, 1),
            risk_level=risk_level,
            factors=factor_scores,
            checks=checks,
            approved=approved,
            recommendations=recommendations,
            metadata={
                "video_path": str(video_path),
                "source_count": len(source_materials) if source_materials else 0,
            }
        )
    
    async def _check_transformative_elements(
        self,
        video_path: str,
        script: Optional[str],
        editing_metadata: Optional[Dict[str, Any]],
    ) -> CopyrightCheck:
        """Check if content is transformative."""
        
        score = 50.0
        details = []
        recommendations = []
        
        if script:
            script_words = len(script.split())
            if script_words > 50:
                score += 20
                details.append(f"Substantial narration ({script_words} words)")
            elif script_words > 20:
                score += 10
                details.append(f"Some narration ({script_words} words)")
            else:
                recommendations.append("Add more commentary narration")
        
        if editing_metadata:
            effects = editing_metadata.get("effects_applied", [])
            if "text_overlay" in effects:
                score += 10
            if "graphics" in effects:
                score += 10
            if "speed_ramp" in effects or "zoom" in effects:
                score += 5
        
        if script:
            analytical_keywords = ["analysis", "breakdown", "tactics", "why", "how"]
            script_lower = script.lower()
            analytical_count = sum(1 for kw in analytical_keywords if kw in script_lower)
            if analytical_count >= 3:
                score += 15
        
        return CopyrightCheck(
            name="transformative_elements",
            passed=score >= 70,
            score=min(100, score),
            details="; ".join(details) or "Limited transformative elements",
            recommendations=recommendations,
        )
    
    async def _check_nature_of_work(
        self,
        source_materials: Optional[List[str]],
    ) -> CopyrightCheck:
        """Check nature of source material."""
        
        score = 60.0
        details = []
        
        if source_materials:
            details.append("Source: Sports broadcast (factual content)")
            score += 10
        
        return CopyrightCheck(
            name="nature_of_work",
            passed=score >= 60,
            score=min(100, score),
            details="; ".join(details),
        )
    
    async def _check_amount_used(
        self,
        video_path: str,
        source_materials: Optional[List[str]],
        editing_metadata: Optional[Dict[str, Any]],
    ) -> CopyrightCheck:
        """Check proportion of original work used."""
        
        score = 50.0
        details = []
        recommendations = []
        
        if not source_materials:
            return CopyrightCheck(
                name="amount_used",
                passed=True,
                score=score,
                details="No source comparison possible",
            )
        
        video_duration = await self._get_duration(video_path)
        
        if editing_metadata:
            clips_used = editing_metadata.get("clip_count", 0)
            avg_clip_duration = editing_metadata.get("avg_clip_duration", 5.0)
            
            if avg_clip_duration <= 5.0:
                score += 25
                details.append(f"Short clips (avg {avg_clip_duration:.1f}s)")
            elif avg_clip_duration <= 10.0:
                score += 15
                details.append(f"Moderate clips (avg {avg_clip_duration:.1f}s)")
            else:
                score -= 10
                recommendations.append("Use shorter clips (3-5 seconds)")
            
            if clips_used >= 6:
                score += 15
            elif clips_used >= 3:
                score += 5
        
        if video_duration <= 60:
            score += 10
            details.append("Short-form content")
        
        return CopyrightCheck(
            name="amount_used",
            passed=score >= 60,
            score=max(0, min(100, score)),
            details="; ".join(details),
            recommendations=recommendations,
        )
    
    async def _check_market_effect(self, video_path: str) -> CopyrightCheck:
        """Check potential market effect."""
        
        score = 70.0
        details = ["Content is transformative (commentary/analysis)"]
        
        video_duration = await self._get_duration(video_path)
        if video_duration <= 60:
            score += 15
            details.append("Minimal market impact (short-form)")
        
        return CopyrightCheck(
            name="market_effect",
            passed=score >= 60,
            score=min(100, score),
            details="; ".join(details),
        )
    
    async def _check_audio_fingerprint(
        self,
        video_path: str,
        source_materials: List[str],
    ) -> Optional[CopyrightCheck]:
        """Compare audio fingerprint against sources."""
        
        if not LIBROSA_AVAILABLE:
            return None
        
        try:
            video_audio = await self._extract_audio(video_path)
            if not video_audio:
                return None
            
            video_fp = await self._compute_audio_fingerprint(str(video_audio))
            max_similarity = 0.0
            
            for source in source_materials:
                source_audio = await self._extract_audio(source)
                if source_audio:
                    source_fp = await self._compute_audio_fingerprint(str(source_audio))
                    similarity = self._compare_fingerprints(video_fp, source_fp)
                    max_similarity = max(max_similarity, similarity)
            
            if max_similarity < 0.3:
                score = 90
                details = "Audio significantly modified"
            elif max_similarity < 0.5:
                score = 70
                details = "Audio moderately modified"
            elif max_similarity < 0.7:
                score = 50
                details = "Some audio similarity"
            else:
                score = 30
                details = "High audio similarity - Content ID risk"
            
            return CopyrightCheck(
                name="audio_fingerprint",
                passed=score >= 60,
                score=score,
                details=details,
            )
        except Exception as e:
            logger.warning(f"Audio fingerprint check failed: {e}")
            return None
    
    async def _check_visual_similarity(
        self,
        video_path: str,
        source_materials: List[str],
    ) -> Optional[CopyrightCheck]:
        """Compare visual fingerprint against sources."""
        
        if not PIL_AVAILABLE:
            return None
        
        try:
            video_frames = await self._extract_keyframes(video_path)
            if not video_frames:
                return None
            
            video_hashes = [imagehash.phash(frame) for frame in video_frames[:5]]
            max_similarity = 0.0
            
            for source in source_materials:
                source_frames = await self._extract_keyframes(source)
                if source_frames:
                    source_hashes = [imagehash.phash(f) for f in source_frames[:5]]
                    for v_hash, s_hash in zip(video_hashes, source_hashes):
                        distance = v_hash - s_hash
                        similarity = 1 - (distance / (v_hash.hash_size ** 2))
                        max_similarity = max(max_similarity, similarity)
            
            if max_similarity < 0.4:
                score = 90
                details = "Visuals significantly modified"
            elif max_similarity < 0.6:
                score = 70
                details = "Visuals moderately modified"
            else:
                score = 50
                details = "Some visual similarity"
            
            return CopyrightCheck(
                name="visual_similarity",
                passed=score >= 60,
                score=score,
                details=details,
            )
        except Exception as e:
            logger.warning(f"Visual similarity check failed: {e}")
            return None
    
    async def _compute_audio_fingerprint(self, audio_path: str) -> Optional[np.ndarray]:
        """Compute spectral fingerprint."""
        if not LIBROSA_AVAILABLE:
            return None
        
        try:
            y, sr = librosa.load(audio_path, sr=16000, duration=30)
            spec = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
            centroid = librosa.feature.spectral_centroid(S=spec, sr=sr)[0]
            centroid_norm = (centroid - centroid.mean()) / (centroid.std() + 1e-8)
            fingerprint = np.digitize(centroid_norm, bins=np.linspace(-3, 3, 64))
            return fingerprint
        except Exception:
            return None
    
    def _compare_fingerprints(self, fp1: np.ndarray, fp2: np.ndarray) -> float:
        """Compare fingerprints."""
        if fp1 is None or fp2 is None:
            return 0.0
        
        try:
            min_len = min(len(fp1), len(fp2))
            correlation = np.corrcoef(fp1[:min_len], fp2[:min_len])[0, 1]
            return max(0, min(1, (correlation + 1) / 2))
        except Exception:
            return 0.0
    
    async def _get_duration(self, video_path: str) -> float:
        """Get video duration."""
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
            stdout, _ = await process.communicate()
            import json
            data = json.loads(stdout)
            return float(data.get("format", {}).get("duration", 0))
        except Exception:
            return 0.0
    
    async def _extract_audio(self, video_path: str) -> Optional[Path]:
        """Extract audio from video."""
        try:
            audio_path = Path(video_path).with_suffix(".audio.wav")
            cmd = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", str(audio_path)]
            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()
            return audio_path if audio_path.exists() else None
        except Exception:
            return None
    
    async def _extract_keyframes(self, video_path: str, max_frames: int = 5) -> List:
        """Extract keyframes."""
        if not PIL_AVAILABLE:
            return []
        
        try:
            duration = await self._get_duration(str(video_path))
            if duration <= 0:
                return []
            
            frames = []
            for i in range(max_frames):
                ts = (i + 1) * (duration / (max_frames + 1))
                frame_path = Path(video_path).parent / f"frame_{i}.jpg"
                
                cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", str(video_path), "-vframes", "1", str(frame_path)]
                process = await asyncio.create_subprocess_exec(*cmd)
                await process.communicate()
                
                if frame_path.exists():
                    frames.append(Image.open(frame_path))
                    frame_path.unlink()
            
            return frames
        except Exception:
            return []
    
    def _score_to_risk(self, score: float) -> RiskLevel:
        """Map score to risk level."""
        if score >= self.RISK_THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.LOW
        elif score >= self.RISK_THRESHOLDS[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        elif score >= self.RISK_THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _generate_recommendations(
        self,
        checks: List[CopyrightCheck],
        factor_scores: Dict[FairUseFactor, float],
    ) -> List[str]:
        """Generate recommendations."""
        recommendations = []
        
        for check in checks:
            if not check.passed:
                recommendations.extend(check.recommendations)
        
        if factor_scores.get(FairUseFactor.PURPOSE, 0) < 70:
            recommendations.append("Add more commentary and analysis")
        
        if factor_scores.get(FairUseFactor.AMOUNT, 0) < 70:
            recommendations.append("Use shorter clips (2-5 seconds)")
        
        return list(dict.fromkeys(recommendations))


class ContentIDAvoidance:
    """Content ID avoidance techniques."""
    
    @staticmethod
    async def apply_audio_modifications(audio_path: str, output_path: str) -> str:
        """Apply audio modifications."""
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-af", "asetrate=44100*1.122,atempo=0.89",
            output_path,
        ]
        
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.communicate()
        return output_path
    
    @staticmethod
    async def apply_visual_modifications(
        video_path: str,
        output_path: str,
        intensity: str = "heavy",
    ) -> str:
        """Apply visual modifications."""
        
        filters = {
            "light": "eq=saturation=1.1:contrast=1.05",
            "moderate": "eq=saturation=1.2:contrast=1.1:brightness=0.02,unsharp=5:5:0.5",
            "heavy": "eq=saturation=1.25:contrast=1.15:brightness=0.03,unsharp=5:5:0.8,colorbalance=rs=0.1:gs=0.05:bs=0.05",
        }
        
        filter_chain = filters.get(intensity, filters["heavy"])
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", filter_chain,
            "-c:a", "copy",
            output_path,
        ]
        
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.communicate()
        return output_path