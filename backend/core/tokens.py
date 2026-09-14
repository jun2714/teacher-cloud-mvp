from rest_framework_simplejwt.tokens import RefreshToken


def blacklist_refresh(raw: str) -> None:
    token = str(raw or "").strip()
    if not token:
        return
    try:
        RefreshToken(token).blacklist()
    except Exception:
        return


def blacklist_user_tokens(user) -> None:
    try:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
    except Exception:
        return
    for item in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=item)
