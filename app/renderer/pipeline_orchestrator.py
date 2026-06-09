"""
Pipeline Orchestrator - End-to-end automated video creation.

Coordinates all modules:
1. Competitor monitoring for source material
2. Clip sequence planning from scripts
3. Advanced editing with copyright-safe techniques
4. Enhanced rendering with social media presets
5. Double verification before output

Two workflows:
- create_video_from_brief(): Standard workflow (stock footage + TTS)
- create_video_with_cosmos(): Advanced workflow (source video + heavy edits)
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from app.core.copyright_checker import CopyrightSafetyChecker, RiskLevel, FairUseReport
from app.core.competitor_monitor import CompetitorMonitor, MonitoredUpload
from app.renderer.clip_sequence_planner import ClipSequencePlanner, SequencePlan, SmartClipAssembler
from app.renderer.advanced_clip_editor import AdvancedClipEditor
from app.renderer.video_renderer_enhanced import EnhancedVideoRenderer, SOCIAL_MEDIA_PRESETS
from app.renderer.tts_engine import TTSEngine
from app.renderer.subtitle_generator import SubtitleGenerator
from app.renderer.nvidia_cosmos_analyzer import NvidiaCosmosAnalyzer, RegenerationPipeline
from app.renderer.heavy_overlay_editor import HeavyOverlayEditor, HeavyEditConfig, ContentIDBypassTest
from app.models import ContentBrief


@dataclass
class PipelineConfig:
    """Configuration for video creation pipeline."""
    platform: str = "youtube_shorts"
    output_dir: str = "./outputs/pipeline"
    edit_style: str = "heavy_editing"
    analysis_engine: str = "cosmos"
    use_blender: bool = True
    use_manim: bool = True
    use_motion_canvas: bool = True
    require_verification: bool = True
    min_copyright_score: int = 70
    max_clip_duration: float = 5.0
    min_clip_duration: float = 2.0
    transition_duration: float = 0.3
    include_background_music: bool = True
    music_volume: float = 0.3
    skip_verification: bool = False


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    video_path: Optional[str]
    thumbnail_path: Optional[str]
    duration: float
    platform: str
    copyright_report: Optional[FairUseReport] = None
    quality_score: float = 0.0
    clips_used: int = 0
    sources_used: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PipelineOrchestrator:
    """Orchestrates end-to-end video creation pipeline."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        
        self.monitor = CompetitorMonitor()
        self.sequence_planner = ClipSequencePlanner(
            max_clip_duration=self.config.max_clip_duration,
            min_clip_duration=self.config.min_clip_duration,
        )
        self.clip_assembler = SmartClipAssembler()
        self.editor = AdvancedClipEditor()
        self.renderer = EnhancedVideoRenderer()
        self.tts_engine = TTSEngine()
        self.subtitle_generator = SubtitleGenerator()
        self.copyright_checker = CopyrightSafetyChecker()
        self.cosmos_analyzer = NvidiaCosmosAnalyzer()
        self.heavy_editor = HeavyOverlayEditor()
        self.regeneration_pipeline = RegenerationPipeline()
        
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_video_from_brief(
        self,
        brief: ContentBrief,
        source_materials: Optional[List[str]] = None,
    ) -> PipelineResult:
        """Standard workflow: Create video from content brief."""
        start_time = datetime.now()
        errors = []
        warnings = []
        logger.info(f"Starting pipeline for: {brief.topic}")
        
        try:
            # Planning
            sequence_plan = await self.sequence_planner.plan_from_script(
                script=brief.reel_script or "", audio_duration=30, topic=brief.topic,
            )
            
            # TTS
            tts_audio = await self.tts_engine.generate_speech(
                text=brief.reel_script or "", voice="commentator",
                output_filename=f"tts_{brief.id}.mp3",
            )
            
            # Subtitles
            subs = await self.subtitle_generator.generate_from_audio(audio_path=tts_audio)
            sub_path = self.subtitle_generator.create_ass_subtitle(
                segments=subs, output_filename=f"subs_{brief.id}.ass", style="dynamic",
            )
            
            # Source acquisition
            if not source_materials:
                uploads = await self.monitor.check_all_channels()
                for u in uploads[:5]:
                    await self.monitor.download_upload(u)
                await self.monitor.process_downloads()
                source_materials = [u.download_path for u in self.monitor.download_queue if u.download_path]
            
            # Editing
            if source_materials:
                edited = await self.editor.create_edited_sequence(
                    source_clips=[{"path": p} for p in source_materials],
                    sequence_plan=sequence_plan, audio_path=tts_audio,
                    output_filename=f"edited_{brief.id}.mp4",
                    edit_style=self.config.edit_style,
                )
            else:
                edited = tts_audio
            
            # Render
            final = await self.renderer.render_with_preset(
                input_path=edited, preset_name=self.config.platform,
                output_filename=f"final_{brief.id}.mp4",
            )
            
            # Verification
            report = None
            score = 0.0
            if not self.config.skip_verification:
                report = await self.copyright_checker.verify_fair_use(
                    video_path=final, source_materials=source_materials, script=brief.reel_script,
                )
                score = report.overall_score if report else 0
            
            return PipelineResult(
                success=True, video_path=final, thumbnail_path=None,
                duration=await self.renderer._get_media_duration(tts_audio),
                platform=self.config.platform, copyright_report=report, quality_score=score,
                clips_used=sequence_plan.clip_count, sources_used=source_materials or [],
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=errors, warnings=warnings,
            )
        except Exception as e:
            errors.append(str(e))
            return PipelineResult(
                success=False, video_path=None, thumbnail_path=None, duration=0,
                platform=self.config.platform, errors=errors, warnings=warnings,
            )
    
    async def create_video_with_cosmos(
        self,
        brief: ContentBrief,
        source_video_path: str,
        regenerate_elements: bool = True,
    ) -> PipelineResult:
        """
        Advanced workflow: NVIDIA Cosmos + Heavy Overlay editing.
        
        1. Cosmos3-Nano analyzes source structure
        2. Cosmos3-Nano-Reasoner infers creative decisions
        3. Generate Blender/Manim/Motion Canvas prompts
        4. Apply heavy transformative overlays
        5. ContentID bypass test
        6. Copyright verification
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        logger.info(f"Starting Cosmos pipeline for: {brief.topic}")
        
        try:
            # Stage 1: Cosmos Analysis
            analysis = await self.cosmos_analyzer.analyze_video_structure(
                video_path=source_video_path, analysis_depth="ultra",
            )
            logger.info(f"Cosmos: {analysis.scene_type}, {len(analysis.visual_elements)} elements")
            
            # Stage 2: Regenerate elements
            if regenerate_elements:
                regen = await self.regeneration_pipeline.regenerate_from_source(
                    source_video_path=source_video_path,
                    output_dir=str(self.output_dir / "regenerated"),
                    tools=["blender" if self.config.use_blender else None,
                           "manim" if self.config.use_manim else None,
                           "motion_canvas" if self.config.use_motion_canvas else None],
                )
                logger.info(f"Generated prompts: {regen['prompts_count']}")
            
            # Stage 3: TTS + Subtitles
            tts = await self.tts_engine.generate_speech(
                text=brief.reel_script or "", voice="commentator",
                output_filename=f"tts_{brief.id}.mp3",
            )
            subs = await self.subtitle_generator.generate_from_audio(audio_path=tts)
            sub_path = self.subtitle_generator.create_ass_subtitle(
                segments=subs, output_filename=f"subs_{brief.id}.ass", style="dynamic",
            )
            
            # Stage 4: Heavy Transformative Editing
            graphics = []
            for elem in analysis.visual_elements:
                if elem.get("type") in ["arrow_overlay", "tactical_board"]:
                    graphics.append({
                        "type": "arrow" if "arrow" in str(elem.get("type")) else "box",
                        "start_x": int(elem.get("position", {}).get("x", 0.3) * 1080),
                        "start_y": int(elem.get("position", {}).get("y", 0.6) * 1920),
                        "color": elem.get("colors", ["yellow"])[0].replace("#", ""),
                    })
            
            transformed = await self.heavy_editor.apply_transformative_layers(
                video_path=source_video_path, voiceover_path=tts,
                subtitle_path=sub_path, graphics_package=graphics if graphics else None,
                output_filename=f"transformed_{brief.id}.mp4",
            )
            
            # Stage 5: ContentID Bypass Test
            bypass = await ContentIDBypassTest.test_bypass_effectiveness(
                original_path=source_video_path, edited_path=transformed,
            )
            logger.info(f"Bypass: {bypass.get('bypass_probability', 0):.2f} - {bypass.get('recommendation', 'Unknown')}")
            
            if bypass.get("bypass_probability", 0) < 0.5:
                warnings.append(f"Low bypass score: {bypass.get('bypass_probability', 0):.2f}")
            
            # Stage 6: Final Render
            final = await self.renderer.render_with_preset(
                input_path=transformed, preset_name=self.config.platform,
                output_filename=f"final_{brief.id}.mp4",
            )
            
            # Stage 7: Verification
            report = None
            if not self.config.skip_verification:
                report = await self.copyright_checker.verify_fair_use(
                    video_path=final, source_materials=[source_video_path],
                    script=brief.reel_script,
                )
            
            return PipelineResult(
                success=True, video_path=final, thumbnail_path=None, duration=30.0,
                platform=self.config.platform, copyright_report=report,
                quality_score=report.overall_score if report else 0,
                clips_used=len(analysis.visual_elements), sources_used=[source_video_path],
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=errors, warnings=warnings,
            )
        except Exception as e:
            errors.append(str(e))
            return PipelineResult(
                success=False, video_path=None, thumbnail_path=None, duration=0,
                platform=self.config.platform, errors=errors, warnings=warnings,
            )
    
    async def preview_sequence(self, brief: ContentBrief) -> Dict[str, Any]:
        """Preview planned sequence."""
        plan = await self.sequence_planner.plan_from_script(
            script=brief.reel_script or "", audio_duration=30, topic=brief.topic,
        )
        preview_path = self.output_dir / f"preview_{brief.id}.json"
        await self.sequence_planner.export_plan(plan, str(preview_path))
        
        return {
            "brief_id": brief.id, "topic": brief.topic,
            "total_duration": plan.total_duration, "clip_count": plan.clip_count,
            "visual_rhythm": plan.visual_rhythm,
            "clips": [
                {"index": c.index, "start": c.start_time, "end": c.end_time,
                 "duration": c.duration, "visual_type": c.visual_type.value,
                 "narrative_role": c.narrative_role.value, "script_snippet": c.script_text[:50]}
                for c in plan.clips
            ],
            "preview_file": str(preview_path),
        }
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        return {
            "platform": self.config.platform, "edit_style": self.config.edit_style,
            "analysis_engine": self.config.analysis_engine,
            "verification_enabled": not self.config.skip_verification,
            "min_copyright_score": self.config.min_copyright_score,
            "regeneration_tools": {
                "blender": self.config.use_blender, "manim": self.config.use_manim,
                "motion_canvas": self.config.use_motion_canvas,
            },
            "monitored_channels": self.monitor.get_channel_stats(),
            "output_directory": str(self.output_dir),
        }