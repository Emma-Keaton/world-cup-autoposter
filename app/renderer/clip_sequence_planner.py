"""
Clip Sequence Planner - Maps script/ narration to visual moments.

Analyzes TTS audio and script to determine:
- How many clips needed
- Duration of each clip
- Visual content type for each moment
- Transition points

This ensures the final video (30-60 seconds) flows coherently
while using copyright-safe 2-5 second individual clips.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.core.config import settings


class VisualType(str, Enum):
    """Type of visual content needed."""
    ACTION = "action"  # Direct footage of action
    REACTION = "reaction"  # Player/coach reactions
    CROWD = "crowd"  # Crowd shots
    WIDE = "wide"  # Wide stadium view
    CLOSEUP = "closeup"  # Close-up of players
    GRAPHIC = "graphic"  # Stats, text overlay
    STOCK = "stock"  # Stock footage
    TACTICAL = "tactical"  # Tactical board/diagram
    ARCHIVE = "archive"  # Historical footage


class NarrativeRole(str, Enum):
    """Role of clip in the narrative structure."""
    HOOK = "hook"  # Opening grabber (0-3s)
    SETUP = "setup"  # Context setting (3-8s)
    BUILD = "build"  # Build-up/tension (8-15s)
    CLIMAX = "climax"  # Key moment (15-25s)
    RESOLUTION = "resolution"  # Analysis/aftermath (25-35s)
    PAYOFF = "payoff"  # Conclusion/CTA (35-40s+)


@dataclass
class ClipPlan:
    """Plan for a single clip in the sequence."""
    index: int
    start_time: float  # In final video timeline
    end_time: float
    duration: float
    visual_type: VisualType
    narrative_role: NarrativeRole
    script_text: str  # Corresponding script portion
    keywords: List[str] = field(default_factory=list)
    source_hint: Optional[str] = None  # Suggested source (e.g., "goal_footage", "crowd_reaction")
    transition_in: str = "fade"
    transition_out: str = "fade"
    effects: List[str] = field(default_factory=list)  # zoom, slow_mo, etc.
    text_overlay: Optional[str] = None  # Text to overlay
    extra_data: Dict[str, Any] = field(default_factory=dict)  # Effect engine data (scores, teams, etc.)


@dataclass
class SequencePlan:
    """Complete plan for video sequence."""
    total_duration: float
    target_duration: float  # From TTS audio
    clip_count: int
    clips: List[ClipPlan] = field(default_factory=list)
    narrative_structure: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    visual_rhythm: str = ""  # Description of pacing


class ClipSequencePlanner:
    """
    Plans multi-clip sequences based on script/narrative analysis.

    Ensures:
    - Visual variety (no clip longer than 5 seconds)
    - Narrative coherence (hooks, builds, payoffs)
    - Copyright safety (short, varied, heavily-edited clips)
    - Platform optimization (vertical, pacing)
    """

    # Narrative structure timing (as % of total duration)
    NARRATIVE_TIMING = {
        NarrativeRole.HOOK: (0.0, 0.10),  # 0-10%
        NarrativeRole.SETUP: (0.10, 0.25),  # 10-25%
        NarrativeRole.BUILD: (0.25, 0.45),  # 25-45%
        NarrativeRole.CLIMAX: (0.45, 0.65),  # 45-65%
        NarrativeRole.RESOLUTION: (0.65, 0.85),  # 65-85%
        NarrativeRole.PAYOFF: (0.85, 1.0),  # 85-100%
    }

    # Visual type distribution targets
    VISUAL_DISTRIBUTION = {
        VisualType.ACTION: 0.35,  # 35% action footage
        VisualType.CROWD: 0.15,  # 15% crowd reactions
        VisualType.CLOSEUP: 0.15,  # 15% player close-ups
        VisualType.GRAPHIC: 0.10,  # 10% graphics/stats
        VisualType.WIDE: 0.10,  # 10% wide shots
        VisualType.TACTICAL: 0.10,  # 10% tactical analysis
        VisualType.ARCHIVE: 0.05,  # 5% historical
    }

    # Keywords mapping to visual types
    KEYWORD_VISUAL_MAP = {
        VisualType.ACTION: [
            "goal", "score", "shoot", "kick", "pass", "dribble", "save",
            "tackle", "header", "volley", "strike", "finish", "net",
            "touchdown", "quarterback", "interception", "slam dunk",
        ],
        VisualType.REACTION: [
            "celebration", "celebrate", "cheer", "emotion", "reaction",
            "hug", "kiss", "tears", "joy", "disappointment", "frustration",
        ],
        VisualType.CROWD: [
            "crowd", "fans", "stadium", "roar", "atmosphere", "supporters",
            "chanting", "wild", "erupt", "explode",
        ],
        VisualType.WIDE: [
            "stadium", "aerial", "wide", "overview", "panoramic",
            "drone", "from above",
        ],
        VisualType.CLOSEUP: [
            "close-up", "closeup", "face", "expression", "eyes",
            "feet", "boots", "ball", "detail",
        ],
        VisualType.GRAPHIC: [
            "statistics", "stats", "numbers", "data", "record",
            "history", "comparison", "vs", "versus",
        ],
        VisualType.TACTICAL: [
            "tactics", "formation", "strategy", "analysis", "breakdown",
            "movement", "positioning", "shape", "press", "defend",
        ],
        VisualType.ARCHIVE: [
            "history", "historical", "legend", "iconic", "classic",
            "throwback", "remember when", "years ago",
        ],
    }

    def __init__(self, max_clip_duration: float = 5.0, min_clip_duration: float = 2.0):
        """
        Initialize planner.

        Args:
            max_clip_duration: Maximum individual clip length (seconds)
            min_clip_duration: Minimum individual clip length (seconds)
        """
        self.max_clip_duration = max_clip_duration
        self.min_clip_duration = min_clip_duration

    async def plan_from_script(
        self,
        script: str,
        audio_duration: float,
        topic: Optional[str] = None,
    ) -> SequencePlan:
        """
        Create clip sequence plan from script.

        Args:
            script: Narration/script text
            audio_duration: Duration of TTS audio (seconds)
            topic: Content topic for context

        Returns:
            Complete sequence plan
        """
        # Analyze script structure
        sentences = self._split_script_into_sentences(script)

        # Map sentences to narrative structure
        sentence_roles = self._assign_narrative_roles(sentences, audio_duration)

        # Plan clips for each sentence
        clip_plans = []
        current_time = 0.0

        for i, (sentence, role, timing) in enumerate(sentence_roles):
            sentence_duration = timing[1] - timing[0]

            # Split long sentences into multiple clips
            sub_clips = self._plan_sentence_clips(
                sentence=sentence,
                start_time=current_time,
                duration=sentence_duration,
                narrative_role=role,
                index_base=len(clip_plans),
            )

            clip_plans.extend(sub_clips)
            current_time += sentence_duration

        # Build sequence plan
        sequence = SequencePlan(
            total_duration=audio_duration,
            target_duration=audio_duration,
            clip_count=len(clip_plans),
            clips=clip_plans,
            narrative_structure={
                role.value: (timing[0] * audio_duration, timing[1] * audio_duration)
                for role, timing in self.NARRATIVE_TIMING.items()
            },
            visual_rhythm=self._describe_rhythm(clip_plans),
        )

        logger.info(
            f"Sequence plan created: {sequence.clip_count} clips, "
            f"{sequence.total_duration:.1f}s total, "
            f"avg clip {sequence.total_duration/sequence.clip_count:.1f}s"
        )

        return sequence

    def _split_script_into_sentences(self, script: str) -> List[str]:
        """Split script into sentences."""
        # Simple sentence splitting on punctuation
        sentences = re.split(r'(?<=[.!?])\s+', script.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _assign_narrative_roles(
        self,
        sentences: List[str],
        audio_duration: float,
    ) -> List[Tuple[str, NarrativeRole, Tuple[float, float]]]:
        """Assign narrative roles and timing to sentences."""

        # Calculate cumulative word count for proportional timing
        total_words = sum(len(s.split()) for s in sentences)
        cumulative_words = 0

        sentence_roles = []
        for sentence in sentences:
            words = len(sentence.split())
            start_ratio = cumulative_words / total_words
            end_ratio = (cumulative_words + words) / total_words

            # Map ratio to narrative role
            role = self._ratio_to_role(start_ratio)

            sentence_roles.append((
                sentence,
                role,
                (start_ratio, end_ratio),
            ))

            cumulative_words += words

        return sentence_roles

    def _ratio_to_role(self, ratio: float) -> NarrativeRole:
        """Map timeline ratio to narrative role."""
        for role, (start, end) in self.NARRATIVE_TIMING.items():
            if start <= ratio < end:
                return role
        return NarrativeRole.PAYOFF

    def _plan_sentence_clips(
        self,
        sentence: str,
        start_time: float,
        duration: float,
        narrative_role: NarrativeRole,
        index_base: int = 0,
    ) -> List[ClipPlan]:
        """
        Plan one or more clips for a sentence.

        If sentence duration > max_clip_duration, split into multiple clips.
        """
        clips = []

        # Determine visual type from keywords
        visual_type = self._infer_visual_type(sentence)

        # Split if necessary
        if duration > self.max_clip_duration:
            # Split into multiple clips
            num_clips = int(duration / self.max_clip_duration) + 1
            clip_duration = duration / num_clips

            for i in range(num_clips):
                clip_start = start_time + (i * clip_duration)
                clip_index = index_base + i

                clips.append(ClipPlan(
                    index=clip_index,
                    start_time=clip_start,
                    end_time=clip_start + clip_duration,
                    duration=clip_duration,
                    visual_type=visual_type,
                    narrative_role=narrative_role,
                    script_text=sentence,
                    keywords=self._extract_keywords(sentence),
                    effects=self._suggest_effects(narrative_role, visual_type),
                    transition_in="fade" if i > 0 else "none",
                    transition_out="fade" if i < num_clips - 1 else "none",
                ))
        else:
            # Single clip is sufficient
            clips.append(ClipPlan(
                index=index_base,
                start_time=start_time,
                end_time=start_time + duration,
                duration=duration,
                visual_type=visual_type,
                narrative_role=narrative_role,
                script_text=sentence,
                keywords=self._extract_keywords(sentence),
                effects=self._suggest_effects(narrative_role, visual_type),
            ))

        return clips

    def _infer_visual_type(self, text: str) -> VisualType:
        """Infer visual type from text keywords."""
        text_lower = text.lower()

        # Score each visual type
        scores = {vt: 0 for vt in VisualType}

        for visual_type, keywords in self.KEYWORD_VISUAL_MAP.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[visual_type] += 1

        # Return highest scoring type
        if max(scores.values()) == 0:
            return VisualType.ACTION  # Default

        return max(scores, key=scores.get)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        text_lower = text.lower()
        found = []

        for keywords in self.KEYWORD_VISUAL_MAP.values():
            for keyword in keywords:
                if keyword in text_lower:
                    found.append(keyword)

        return list(set(found))

    def _suggest_effects(
        self,
        narrative_role: NarrativeRole,
        visual_type: VisualType,
    ) -> List[str]:
        """Suggest editing effects based on context.

        Tags are matched by the effects engine registry to auto-activate
        the corresponding BaseEffect subclasses.
        """
        effects = []

        # Role-based effects
        if narrative_role == NarrativeRole.HOOK:
            effects.append("zoom_in")
            effects.append("fast_pace")

        elif narrative_role == NarrativeRole.CLIMAX:
            effects.append("slow_motion")
            effects.append("dramatic_pause")

        elif narrative_role == NarrativeRole.BUILD:
            effects.append("speed_ramp")
            effects.append("quick_cuts")

        elif narrative_role == NarrativeRole.PAYOFF:
            effects.append("dramatic_pause")

        # Visual type-based effects
        if visual_type == VisualType.ACTION:
            effects.append("motion_blur")

        elif visual_type == VisualType.GRAPHIC:
            effects.append("text_overlay")

        elif visual_type == VisualType.TACTICAL:
            effects.append("freeze_frame")
            effects.append("arrow_overlay")

        elif visual_type == VisualType.CROWD:
            effects.append("dramatic_pause")

        elif visual_type == VisualType.REACTION:
            effects.append("dramatic_pause")
            effects.append("slow_motion")

        return effects[:3]  # Max 3 effects per clip

    def _describe_rhythm(self, clips: List[ClipPlan]) -> str:
        """Generate description of visual rhythm."""
        durations = [c.duration for c in clips]
        avg = sum(durations) / len(durations)
        min_d = min(durations)
        max_d = max(durations)

        if avg < 2.5:
            pace = "very fast"
        elif avg < 3.5:
            pace = "fast"
        elif avg < 5:
            pace = "moderate"
        else:
            pace = "slow"

        return (
            f"{pace} pacing ({avg:.1f}s avg clip), "
            f"range {min_d:.1f}-{max_d:.1f}s, "
            f"{len(clips)} clips total"
        )

    async def export_plan(self, plan: SequencePlan, output_path: str) -> None:
        """Export plan to JSON for use by other modules."""
        export_data = {
            "total_duration": plan.total_duration,
            "clip_count": plan.clip_count,
            "visual_rhythm": plan.visual_rhythm,
            "narrative_structure": {
                k: {"start": v[0], "end": v[1]}
                for k, v in plan.narrative_structure.items()
            },
            "clips": [
                {
                    "index": c.index,
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "duration": c.duration,
                    "visual_type": c.visual_type.value,
                    "narrative_role": c.narrative_role.value,
                    "script_text": c.script_text,
                    "keywords": c.keywords,
                    "source_hint": c.source_hint,
                    "transitions": {
                        "in": c.transition_in,
                        "out": c.transition_out,
                    },
                    "effects": c.effects,
                    "text_overlay": c.text_overlay,
                }
                for c in plan.clips
            ],
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported clip plan to {output_path}")

    async def load_plan(self, plan_path: str) -> SequencePlan:
        """Load plan from JSON file."""
        with open(plan_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        clips = [
            ClipPlan(
                index=c["index"],
                start_time=c["start_time"],
                end_time=c["end_time"],
                duration=c["duration"],
                visual_type=VisualType(c["visual_type"]),
                narrative_role=NarrativeRole(c["narrative_role"]),
                script_text=c["script_text"],
                keywords=c.get("keywords", []),
                source_hint=c.get("source_hint"),
                transition_in=c.get("transitions", {}).get("in", "fade"),
                transition_out=c.get("transitions", {}).get("out", "fade"),
                effects=c.get("effects", []),
                text_overlay=c.get("text_overlay"),
            )
            for c in data.get("clips", [])
        ]

        plan = SequencePlan(
            total_duration=data["total_duration"],
            target_duration=data.get("target_duration", data["total_duration"]),
            clip_count=data["clip_count"],
            clips=clips,
            narrative_structure={
                k: (v["start"], v["end"])
                for k, v in data.get("narrative_structure", {}).items()
            },
            visual_rhythm=data.get("visual_rhythm", ""),
        )

        return plan


class SmartClipAssembler:
    """
    Assembles actual video clips based on sequence plan.

    Takes a SequencePlan and available source materials,
    then creates the optimal mapping and edit decision list.
    """

    def __init__(self):
        """Initialize assembler."""
        pass

    async def assemble_from_sources(
        self,
        plan: SequencePlan,
        source_clips: List[Dict[str, Any]],
        stock_assets: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Map plan clips to actual source materials.

        Args:
            plan: Sequence plan from ClipSequencePlanner
            source_clips: Available source clips with metadata
            stock_assets: Optional stock footage assets

        Returns:
            Assembly instructions with clip mappings
        """
        assembled = {
            "plan": plan,
            "clip_mappings": [],
            "gaps": [],  # Moments without matching footage
            "total_coverage": 0.0,
        }

        for planned_clip in plan.clips:
            # Find best matching source
            match = self._find_best_match(
                planned_clip=planned_clip,
                sources=source_clips,
                stock=stock_assets or [],
            )

            if match:
                assembled["clip_mappings"].append({
                    "planned": planned_clip,
                    "source": match,
                    "edit_instructions": self._generate_edit_instructions(
                        planned_clip, match,
                    ),
                })
                assembled["total_coverage"] += planned_clip.duration
            else:
                assembled["gaps"].append({
                    "clip": planned_clip,
                    "reason": "No matching source found",
                })

        assembled["coverage_percent"] = (
            assembled["total_coverage"] / plan.total_duration * 100
        ) if plan.total_duration > 0 else 0

        logger.info(
            f"Assembly complete: {len(assembled['clip_mappings'])} clips mapped, "
            f"{assembled['coverage_percent']:.0f}% coverage"
        )

        return assembled

    def _find_best_match(
        self,
        planned_clip: ClipPlan,
        sources: List[Dict[str, Any]],
        stock: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Find best matching source clip for planned clip."""

        # Score each source
        scored = []

        for source in sources:
            score = self._score_match(planned_clip, source)
            if score > 0:
                scored.append((score, source))

        # Also score stock assets
        for asset in stock:
            score = self._score_stock_match(planned_clip, asset)
            if score > 0:
                scored.append((score, asset))

        if not scored:
            return None

        # Return best match
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _score_match(
        self,
        planned: ClipPlan,
        source: Dict[str, Any],
    ) -> float:
        """Score how well a source matches a planned clip."""
        score = 0.0

        # Visual type match (highest weight)
        source_type = source.get("visual_type", "")
        if source_type == planned.visual_type.value:
            score += 10.0

        # Keyword matches
        source_keywords = set(source.get("keywords", []))
        planned_keywords = set(planned.keywords)
        if planned_keywords & source_keywords:
            score += len(planned_keywords & source_keywords) * 2.0

        # Narrative role compatibility
        source_role = source.get("narrative_role", "")
        if source_role == planned.narrative_role.value:
            score += 3.0

        # Duration appropriateness
        source_duration = source.get("duration", 0)
        if source_duration >= planned.duration:
            score += 2.0  # Enough footage
        elif source_duration >= planned.duration * 0.5:
            score += 1.0  # At least half

        return score

    def _score_stock_match(
        self,
        planned: ClipPlan,
        asset: Dict[str, Any],
    ) -> float:
        """Score stock asset match."""
        score = 0.0

        # Stock is good for certain visual types
        stock_friendly_types = [
            VisualType.CROWD,
            VisualType.WIDE,
            VisualType.STOCK,
            VisualType.ARCHIVE,
        ]

        if planned.visual_type in stock_friendly_types:
            score += 5.0

        # Keyword matching
        asset_keywords = set(asset.get("tags", []))
        planned_keywords = set(planned.keywords)
        matches = planned_keywords & asset_keywords
        score += len(matches) * 1.5

        # Fallback for gaps
        if planned.visual_type == VisualType.GRAPHIC:
            score += 3.0  # Use as placeholder

        return score

    def _generate_edit_instructions(
        self,
        planned: ClipPlan,
        source: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate editing instructions for this clip."""

        source_duration = source.get("duration", 30)
        source_start = source.get("start_time", 0)

        # Determine where to cut from source
        if source_duration > planned.duration:
            # Source is longer - select best portion
            cut_start = source_start + (source_duration - planned.duration) / 2
            cut_duration = planned.duration
        else:
            # Source is shorter - use all, possibly slow down
            cut_start = source_start
            cut_duration = source_duration

        return {
            "action": "extract",
            "source_path": source.get("path"),
            "cut_start": cut_start,
            "cut_duration": cut_duration,
            "target_position": planned.start_time,
            "effects": planned.effects,
            "transitions": {
                "in": planned.transition_in,
                "out": planned.transition_out,
            },
            "speed_ramp": cut_duration / planned.duration if planned.duration > 0 else 1.0,
            "text_overlay": planned.text_overlay,
        }