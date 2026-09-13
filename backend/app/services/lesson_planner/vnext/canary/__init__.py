"""
TeachGenie Lesson Planner VNext — Real Human Canary Infrastructure
==================================================================
Package providing privacy-safe, pseudonymous canary telemetry,
managed encrypted identity vault, structured authorization, complete
data lifecycle, idempotent retention scheduling, teacher canary workflows,
and gate-computed canary verdicts.
"""

from .pseudonyms import (
    IsolatedIdentityRegistry,
    ManagedIdentityStore,
    IdentityVault,
    generate_pseudonym,
    is_valid_pseudonym,
    ServiceTokenManager,
    VaultRole,
    VaultPermission,
    ServiceSecurityToken
)
from .authorization import (
    StructuredAuthorizationRecord,
    AuthorizationRegistry,
    AuthorizationScope,
    ActorCategory,
    AuthorizationStatus
)
from .lifecycle import (
    DataLifecycleManager,
    DataMinimizer,
    DataRetentionPolicy,
    BackupLifecycleManager,
    AuthorizationRevokedError
)
from .workflow import (
    TeacherCanaryWorkflowService,
    RealTeacherSession,
    PlanDecisionType,
    AdaptationDecisionType,
    ResourceFeedbackType
)
from .retention_scheduler import (
    DelayedRetentionCheck,
    IdempotentRetentionScheduler,
    RetentionCheckStatus
)
from .exports import CanaryDatasetExporter
from .inference_benchmark import InferenceBenchmarkService
from .verdict_engine import CanaryVerdictEngine, CanaryExecutionGates
from .controls import (
    CanaryKillSwitchRegistry,
    KillSwitchName,
    CanaryRollbackController
)
from .gates import (
    CanaryReleaseGate,
    GateDecision,
    CanaryReleaseGateReport
)

__all__ = [
    "IsolatedIdentityRegistry",
    "ManagedIdentityStore",
    "IdentityVault",
    "generate_pseudonym",
    "is_valid_pseudonym",
    "ServiceTokenManager",
    "VaultRole",
    "VaultPermission",
    "ServiceSecurityToken",
    "StructuredAuthorizationRecord",
    "AuthorizationRegistry",
    "AuthorizationScope",
    "ActorCategory",
    "AuthorizationStatus",
    "DataLifecycleManager",
    "DataMinimizer",
    "DataRetentionPolicy",
    "BackupLifecycleManager",
    "AuthorizationRevokedError",
    "TeacherCanaryWorkflowService",
    "RealTeacherSession",
    "PlanDecisionType",
    "AdaptationDecisionType",
    "ResourceFeedbackType",
    "DelayedRetentionCheck",
    "IdempotentRetentionScheduler",
    "RetentionCheckStatus",
    "CanaryDatasetExporter",
    "InferenceBenchmarkService",
    "CanaryVerdictEngine",
    "CanaryExecutionGates",
    "CanaryKillSwitchRegistry",
    "KillSwitchName",
    "CanaryRollbackController",
    "CanaryReleaseGate",
    "GateDecision",
    "CanaryReleaseGateReport"
]
