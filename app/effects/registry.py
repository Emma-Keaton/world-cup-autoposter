"""Effect registry — discovers, registers, and dispatches effects."""

from typing import Dict, List, Optional, Type

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage


class EffectRegistry:
    """Central registry for all video effects.

    Usage:
        registry = get_registry()
        results = registry.build_effects_for_clip(ctx)
        filters = [f for r in results for f in r.filters]
    """

    def __init__(self) -> None:
        self._effects: Dict[str, BaseEffect] = {}
        self._registered_classes: List[Type[BaseEffect]] = []

    def register(self, effect_cls: Type[BaseEffect]) -> Type[BaseEffect]:
        """Register an effect class. Can be used as a decorator."""
        instance = effect_cls()
        self._effects[instance.name] = instance
        self._registered_classes.append(effect_cls)
        return effect_cls

    def get(self, name: str) -> Optional[BaseEffect]:
        return self._effects.get(name)

    def all_effects(self) -> List[BaseEffect]:
        return list(self._effects.values())

    def effects_by_stage(self, stage: EffectStage) -> List[BaseEffect]:
        return [e for e in self._effects.values() if e.stage == stage]

    def effects_matching_tags(self, tags: List[str]) -> List[BaseEffect]:
        return [e for e in self._effects.values() if e.matches(tags)]

    def build_effects_for_clip(self, ctx: EffectContext) -> List[EffectResult]:
        """Build all effects that match the clip's context (tags + stage=PER_CLIP)."""
        results: List[EffectResult] = []
        for effect in self.effects_by_stage(EffectStage.PER_CLIP):
            if effect.matches(ctx.effect_tags) or self._always_applies(effect, ctx):
                results.append(effect.build(ctx))
        return results

    def build_post_concat_effects(self, ctx: EffectContext) -> List[EffectResult]:
        """Build all POST_CONCAT stage effects."""
        results: List[EffectResult] = []
        for effect in self.effects_by_stage(EffectStage.POST_CONCAT):
            if effect.matches(ctx.effect_tags) or self._always_applies(effect, ctx):
                results.append(effect.build(ctx))
        return results

    @staticmethod
    def _always_applies(effect: BaseEffect, ctx: EffectContext) -> bool:
        """Some effects (style presets, emotion visuals) apply based on
        context attributes rather than explicit tags."""
        return False

    def compile_filter_chain(
        self,
        results: List[EffectResult],
        include_audio: bool = False,
    ) -> str:
        """Combine all EffectResult filters into a single FFmpeg -vf string."""
        all_filters: List[str] = []
        for r in results:
            all_filters.extend(r.pre_filters)
            all_filters.extend(r.filters)
        chain = ",".join(all_filters)
        if include_audio:
            audio_filters = [f for r in results for f in r.audio_filters]
            return chain, ",".join(audio_filters) if audio_filters else ""
        return chain


# Module-level singleton
_registry: Optional[EffectRegistry] = None


def get_registry() -> EffectRegistry:
    global _registry
    if _registry is None:
        _registry = EffectRegistry()
        _auto_register(_registry)
    return _registry


def _auto_register(registry: EffectRegistry) -> None:
    """Import and register all built-in effects."""
    # Import each skill module — each one calls registry.register() at load time
    from app.effects import (  # noqa: F401
        shot_visuals,
        motion_visuals,
        celebration_visuals,
        emotion_visuals,
        scream_visuals,
        animated_overlays,
        style_presets,
    )

    for module in [
        shot_visuals,
        motion_visuals,
        celebration_visuals,
        emotion_visuals,
        scream_visuals,
        animated_overlays,
        style_presets,
    ]:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseEffect)
                and attr is not BaseEffect
                and hasattr(attr, "name")
                and attr.name != "base"
            ):
                if attr.name not in registry._effects:
                    registry.register(attr)
