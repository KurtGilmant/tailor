"""Identifiants ULID : 26 caractères, triables par date de création, sans dépendance."""

import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    chars = []
    for _ in range(26):
        value, index = divmod(value, 32)
        chars.append(_CROCKFORD[index])
    return "".join(reversed(chars))
