"""Cost-control rate limit for synchronous AI Coach replies."""

from rest_framework.throttling import UserRateThrottle


class AICoachRateThrottle(UserRateThrottle):
    scope = "ai_coach"
