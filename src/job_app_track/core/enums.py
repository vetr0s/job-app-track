"""Canonical enum values, mirrored by CHECK constraints in the migrations.

The migration copy is frozen at its schema version. This copy is current and
drives input validation and, later, web form options.
"""

STATUSES = (
    "wishlist",
    "applied",
    "screen",
    "interview",
    "offer",
    "rejected",
    "accepted",
)

SOURCES = ("board", "referral", "recruiter", "cold", "event", "other")

INTERESTS = ("low", "medium", "high")

ARRANGEMENTS = ("onsite", "hybrid", "remote")

RELATIONSHIPS = ("recruiter", "referrer", "interviewer", "hiring_manager", "other")

INTERVIEW_KINDS = (
    "phone_screen",
    "technical",
    "system_design",
    "behavioral",
    "onsite",
    "hiring_manager",
    "hr",
    "other",
)

INTERVIEW_OUTCOMES = ("pending", "passed", "failed", "cancelled", "no_decision")
