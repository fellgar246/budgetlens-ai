from __future__ import annotations

from typing import Annotated

from fastapi import Header

RequiredIdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128),
]
