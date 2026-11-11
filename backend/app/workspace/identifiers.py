from typing import Annotated

from fastapi import Path

RecordID = Annotated[str, Path(min_length=1, max_length=36, pattern=r"^[A-Za-z0-9-]+$")]
