"""Application automation (Phase 2): safety-bound auto-submission.

Never bypasses CAPTCHA, login, MFA, or anti-bot controls (blueprint section 28).
Only submits where per-source policy permits and no human step is required; otherwise
falls back to an assisted/action-required package.
"""
