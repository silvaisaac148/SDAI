from typing import Optional, Callable, Any

from supabase import Client, create_client

from app.config import settings

_client: Optional[Client] = None


def get_client() -> Optional[Client]:
    """Lazy singleton. Returns None if credentials missing (Sprint 1 dev mode)."""
    global _client
    if _client is not None:
        return _client
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


def execute_with_retry(query_fn: Callable[[Client], Any]) -> Any:
    """Executes a Supabase query builder with a retry if a connection is terminated."""
    global _client
    client = get_client()
    if client is None:
        raise ValueError("Supabase client is not initialized")
    try:
        return query_fn(client).execute()
    except Exception as e:
        err_msg = str(e).lower()
        if "connectionterminated" in err_msg or "remoteprotocolerror" in err_msg or "terminated" in err_msg:
            # Connection terminated (HTTP/2 stream closed by peer). Reset singleton client to reconnect.
            _client = None
            new_client = get_client()
            if new_client is not None:
                return query_fn(new_client).execute()
        raise e

