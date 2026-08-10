"""Redis-backed caching helpers for the read-heavy dashboard / listing
endpoints (admin dashboard & stats, company dashboard, student drive
listings).

Strategy: a single "data version" counter lives in Redis. Every cached read
key embeds the current version plus the requesting user + full query
string, so results stay correctly scoped per user/query. Any write that
could change what a cached read returns (approvals, blacklist, drive
creation, applications, profile edits) bumps the version, which makes all
previously cached entries unreachable — the simplest correct invalidation
for a dataset this size, versus tracking per-resource keys individually.
Entries also expire after DEFAULT_TIMEOUT regardless.
"""

from flask import request
from flask_login import current_user

from extensions import cache

DEFAULT_TIMEOUT = 60
_VERSION_KEY = "ppa:cache:version"


def _get_version():
    version = cache.get(_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(_VERSION_KEY, version)
    return version


def bump_cache_version():
    """Call after any write that affects cached dashboard/listing data."""
    cache.set(_VERSION_KEY, _get_version() + 1)


def scoped_cache_key():
    """Cache key scoped to the current data version + user + full request
    path (including query string), so `cache.cached(key_prefix=...)` gives
    each user/query combination its own entry that dies on the next write."""
    user_id = current_user.id if current_user.is_authenticated else "anon"
    return f"v{_get_version()}:u{user_id}:{request.full_path}"
