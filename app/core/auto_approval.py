"""
Auto-Approval Workflow Engine.
Automatically approves content based on configurable rules.
"""
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from loguru import logger


class ApprovalDecision(str, Enum):
    """Auto-approval decision."""
    AUTO_APPROVE = "auto_approve"
    AUTO_REJECT = "auto_reject"
    REQUIRE_REVIEW = "require_review"
    FAST_TRACK = "fast_track"


@dataclass
class ApprovalRule:
    """Rule for auto-approval."""
    name: str
    condition: Callable[[Dict], bool]
    decision: ApprovalDecision
    priority: int = 0
    description: str = ""


@dataclass
class ApprovalResult:
    """Result of approval evaluation."""
    decision: ApprovalDecision
    matched_rules: List[str]
    reason: str
    confidence: float  # 0.0 to 1.0


class AutoApprovalEngine:
    """
    Rules-based auto-approval system.
    
    Features:
    - Configurable approval rules
    - Priority-based rule evaluation
    - Confidence scoring
    - Fast-track for high-confidence content
    """
    
    def __init__(self):
        self._rules: List[ApprovalRule] = []
        self._setup_default_rules()
        logger.info("AutoApprovalEngine initialized")
    
    def _setup_default_rules(self):
        """Setup default approval rules."""
        
        # Rule 1: Breaking news auto-approve
        self.add_rule(ApprovalRule(
            name="breaking_news_auto_approve",
            condition=lambda content: (
                content.get("viral_score", 0) >= 8 and
                content.get("topic", "").lower() in ["breaking", "breaking_news", "urgent"]
            ),
            decision=ApprovalDecision.AUTO_APPROVE,
            priority=10,
            description="Auto-approve breaking news with high viral score"
        ))
        
        # Rule 2: Goal highlights auto-approve
        self.add_rule(ApprovalRule(
            name="goal_highlights_auto_approve",
            condition=lambda content: (
                content.get("content_category", "").lower() in ["goal", "goals", "highlight"]
            ),
            decision=ApprovalDecision.AUTO_APPROVE,
            priority=9,
            description="Auto-approve goal highlights"
        ))
        
        # Rule 3: High confidence fast-track
        self.add_rule(ApprovalRule(
            name="high_confidence_fast_track",
            condition=lambda content: content.get("confidence", 0) >= 0.9,
            decision=ApprovalDecision.FAST_TRACK,
            priority=8,
            description="Fast-track high confidence content"
        ))
        
        # Rule 4: Low quality auto-reject
        self.add_rule(ApprovalRule(
            name="low_quality_reject",
            condition=lambda content: (
                content.get("viral_score", 0) < 3 or
                content.get("confidence", 1) < 0.3
            ),
            decision=ApprovalDecision.AUTO_REJECT,
            priority=7,
            description="Reject low quality content"
        ))
        
        # Rule 5: Transfer news auto-approve
        self.add_rule(ApprovalRule(
            name="transfer_news_approve",
            condition=lambda content: (
                "transfer" in content.get("topic", "").lower() or
                "signing" in content.get("topic", "").lower()
            ),
            decision=ApprovalDecision.AUTO_APPROVE,
            priority=6,
            description="Auto-approve transfer news"
        ))
        
        # Rule 6: Controversial content requires review
        self.add_rule(ApprovalRule(
            name="controversial_review",
            condition=lambda content: (
                content.get("is_controversial", False) or
                any(word in content.get("topic", "").lower() for word in [
                    "scandal", "controversy", "investigation", "ban"
                ])
            ),
            decision=ApprovalDecision.REQUIRE_REVIEW,
            priority=5,
            description="Require review for controversial content"
        ))
    
    def add_rule(self, rule: ApprovalRule) -> None:
        """Add a custom approval rule."""
        self._rules.append(rule)
        # Sort by priority (higher first)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added approval rule: {rule.name} (priority {rule.priority})")
    
    def evaluate(self, content: Dict) -> ApprovalResult:
        """
        Evaluate content against all rules.
        
        Args:
            content: Content brief data
        
        Returns:
            Approval result with decision and matched rules
        """
        matched_rules = []
        decisions = []
        
        # Evaluate rules in priority order
        for rule in self._rules:
            try:
                if rule.condition(content):
                    matched_rules.append(rule.name)
                    decisions.append(rule.decision)
                    
                    # High priority rules short-circuit
                    if rule.priority >= 9:
                        break
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
                continue
        
        # Determine final decision
        if not decisions:
            final_decision = ApprovalDecision.REQUIRE_REVIEW
            reason = "No rules matched - manual review required"
            confidence = 0.5
        elif ApprovalDecision.AUTO_REJECT in decisions:
            final_decision = ApprovalDecision.AUTO_REJECT
            reason = f"Rejected by rules: {', '.join(matched_rules)}"
            confidence = 0.9
        elif ApprovalDecision.AUTO_APPROVE in decisions:
            final_decision = ApprovalDecision.AUTO_APPROVE
            reason = f"Auto-approved by rules: {', '.join(matched_rules)}"
            confidence = 0.85
        elif ApprovalDecision.FAST_TRACK in decisions:
            final_decision = ApprovalDecision.FAST_TRACK
            reason = f"Fast-tracked by rules: {', '.join(matched_rules)}"
            confidence = 0.95
        else:
            final_decision = ApprovalDecision.REQUIRE_REVIEW
            reason = f"Rules matched but require review: {', '.join(matched_rules)}"
            confidence = 0.6
        
        return ApprovalResult(
            decision=final_decision,
            matched_rules=matched_rules,
            reason=reason,
            confidence=confidence
        )
    
    def get_rules(self) -> List[Dict]:
        """Get all configured rules."""
        return [
            {
                "name": rule.name,
                "description": rule.description,
                "priority": rule.priority,
                "decision": rule.decision.value
            }
            for rule in self._rules
        ]
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        initial_count = len(self._rules)
        self._rules = [r for r in self._rules if r.name != rule_name]
        
        if len(self._rules) < initial_count:
            logger.info(f"Removed rule: {rule_name}")
            return True
        return False


# Global instance
_approval_engine: Optional[AutoApprovalEngine] = None


def get_approval_engine() -> AutoApprovalEngine:
    """Get the global approval engine instance."""
    global _approval_engine
    if _approval_engine is None:
        _approval_engine = AutoApprovalEngine()
    return _approval_engine


def auto_approve_content(content: Dict) -> ApprovalResult:
    """Convenience function to evaluate content for auto-approval."""
    engine = get_approval_engine()
    return engine.evaluate(content)