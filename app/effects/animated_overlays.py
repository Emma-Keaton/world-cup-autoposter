"""Skill 6: Animated Overlays — Data-driven graphics.

Generates lower-thirds, score bugs, stat bars, player cards, and
tournament brackets. Data-bound and animated in/out with professional timing.

Inspired by: Rive ViewModel data binding, Lottie segment playback,
GSAP timeline sequencing, Anime.js stagger, React Spring trail cascade.
"""

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType


class ScoreBugEffect(BaseEffect):
    """Animated score bug: team crests + names + score, spring slide-in/out."""

    name = "score_bug"
    label = "Score Bug"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.DATA_DRIVEN
    description = "Animated score display with slide-in/out"
    handled_tags = ["text_overlay"]

    def build(self, ctx: EffectContext) -> EffectResult:
        home = ctx.team_home or "HOME"
        away = ctx.team_away or "AWAY"
        score = f"{ctx.score_home}  -  {ctx.score_away}"
        # GSAP timeline: enter(0.3s) → hold → exit(0.3s)
        enter_end = 0.3
        exit_start = ctx.duration - 0.3
        # Slide from left: x starts off-screen, slides to left margin
        x_expr = (
            f"if(lt(T,{enter_end:.1f}),"
            f"-300+300*T/{enter_end:.1f},"  # Slide in
            f"if(gt(T,{exit_start:.1f}),"
            f"300*(T-{exit_start:.1f})/{ctx.duration - exit_start:.1f},"  # Slide out
            f"50))"  # Hold position
        )
        filters = [
            # Score text
            f"drawtext=text='{score}':fontsize=52:fontcolor=white"
            f":borderw=2:bordercolor=black:x='{x_expr}':y=80",
            # Home team name
            f"drawtext=text='{home}':fontsize=36:fontcolor=white"
            f":borderw=2:bordercolor=black:x='{x_expr}':y=30",
            # Away team name
            f"drawtext=text='{away}':fontsize=36:fontcolor=white"
            f":borderw=2:bordercolor=black:x='{x_expr}':y=140",
        ]
        return EffectResult(filters=filters)


class PlayerNamePlateEffect(BaseEffect):
    """Semi-transparent bar with name/number. Stagger: bar first, text second."""

    name = "player_nameplate"
    label = "Player Name Plate"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.DATA_DRIVEN
    description = "Animated player info card with stagger reveal"
    handled_tags = ["text_overlay"]

    def build(self, ctx: EffectContext) -> EffectResult:
        name = ctx.player_name or "PLAYER"
        number = ctx.player_number or 10
        # Stagger pattern (Anime.js): bar slides in first, text fades in 0.1s later
        bar_enter = 0.3
        text_enter = 0.4  # 0.1s after bar
        bar_exit = ctx.duration - 0.3
        text_exit = ctx.duration - 0.2

        bar_x = (
            f"if(lt(T,{bar_enter:.1f}),-400+400*T/{bar_enter:.1f},"
            f"if(gt(T,{bar_exit:.1f}),400*(T-{bar_exit:.1f})/0.3,50))"
        )
        text_alpha = (
            f"if(lt(T,{text_enter:.1f}),0,"
            f"if(gt(T,{text_exit:.1f}),max(1-(T-{text_exit:.1f})/0.2,0),1))"
        )
        filters = [
            # Background bar
            f"drawbox=x='{bar_x}':y=h-180:w=500:h=80:color=0x000000@0.7:t=fill",
            # Player name
            f"drawtext=text='{name}':fontsize=44:fontcolor=white"
            f":borderw=2:bordercolor=black"
            f":x='{bar_x}+20':y=h-170:alpha='{text_alpha}'",
            # Player number
            f"drawtext=text='#{number}':fontsize=36:fontcolor=yellow"
            f":borderw=2:bordercolor=black"
            f":x='{bar_x}+380':y=h-165:alpha='{text_alpha}'",
        ]
        return EffectResult(filters=filters)


class StatBarEffect(BaseEffect):
    """Horizontal stat comparison bars with trail cascade animation."""

    name = "stat_bars"
    label = "Stat Comparison Bars"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.DATA_DRIVEN
    description = "Animated stat bars with stagger reveal"
    handled_tags = ["text_overlay"]

    def build(self, ctx: EffectContext) -> EffectResult:
        stats = ctx.extra_data.get("stats", {
            "Possession": (58, 42),
            "Shots": (12, 8),
            "Passes": (450, 380),
        })
        # React Spring trail: each bar starts 0.15s after previous
        base_enter = 0.5
        stagger = 0.15
        filters = []
        bar_h = 40
        start_y = 300
        for i, (stat_name, (home_val, away_val)) in enumerate(stats.items()):
            enter_t = base_enter + i * stagger
            max_w = ctx.width * 0.35
            # Home bar (left-aligned, grows from center)
            h_pct = home_val / 100 if home_val <= 100 else home_val / max(home_val, away_val)
            a_pct = away_val / 100 if away_val <= 100 else away_val / max(home_val, away_val)
            h_width_expr = f"if(gt(T,{enter_t:.1f}),{max_w * h_pct:.0f}*(min((T-{enter_t:.1f})/0.5,1)),0)"
            a_width_expr = f"if(gt(T,{enter_t:.1f}),{max_w * a_pct:.0f}*(min((T-{enter_t:.1f})/0.5,1)),0)"
            y = start_y + i * (bar_h + 10)
            # Home bar (right-aligned from center)
            filters.append(
                f"drawbox=x=w/2-{h_width_expr}':y={y}:w='{h_width_expr}':h={bar_h}"
                f":color=0x1a4d2e@0.8:t=fill"
            )
            # Away bar (left-aligned from center)
            filters.append(
                f"drawbox=x=w/2+10:y={y}:w='{a_width_expr}':h={bar_h}"
                f":color=0x8b0000@0.8:t=fill"
            )
            # Stat label
            filters.append(
                f"drawtext=text='{stat_name}':fontsize=24:fontcolor=white"
                f":x=w/2-text_w/2:y={y + 8}"
                f":enable='gt(T,{enter_t:.1f})'"
            )
        return EffectResult(filters=filters)


class AnimatedSubtitleEffect(BaseEffect):
    """Enhanced ASS subtitle with word-by-word color highlight synced to TTS."""

    name = "animated_subtitle"
    label = "Animated Subtitle Style"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.DATA_DRIVEN
    description = "Word-by-word highlighted subtitles synced to narration"
    handled_tags = ["text_overlay"]

    def build(self, ctx: EffectContext) -> EffectResult:
        subtitle_path = ctx.extra_data.get("subtitle_path")
        if not subtitle_path:
            return EffectResult()
        # Escape path for FFmpeg
        escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")
        return EffectResult(
            filters=[
                f"subtitles='{escaped}':force_style='FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=60'"
            ],
        )


class TimerOverlayEffect(BaseEffect):
    """Match timer/clock overlay counting up or down."""

    name = "timer_overlay"
    label = "Timer/Clock Overlay"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.DATA_DRIVEN
    description = "Match time display in corner"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        start_minute = ctx.extra_data.get("start_minute", 0)
        # Counting up from start_minute
        time_expr = f"{start_minute}+T/60"
        # Format as MM:SS
        mins_expr = f"floor({time_expr})"
        secs_expr = f"floor(({time_expr}-floor({time_expr}))*60)"
        time_text = f"%{{mins_expr}}d:%{{secs_expr}}02d"
        return EffectResult(
            filters=[
                f"drawtext=text='%{{e\\:{mins_expr}\\:d}}\\:%{{e\\:{secs_expr}\\:d}}'"
                f":fontsize=40:fontcolor=white:borderw=2:bordercolor=black"
                f":x=w-tw-30:y=30"
            ],
        )


ALL_OVERLAY_EFFECTS = [
    ScoreBugEffect,
    PlayerNamePlateEffect,
    StatBarEffect,
    AnimatedSubtitleEffect,
    TimerOverlayEffect,
]
