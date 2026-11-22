import json
from collections import Counter
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote

from filelock import FileLock
from pydantic import BaseModel, NonNegativeInt, ValidationError


class MonthRecord(BaseModel):
    """Store a month's public and optional private counts by language."""

    month: date
    counts: dict[str, NonNegativeInt]
    private_counts: dict[str, NonNegativeInt] | None = None


class MonthCache:
    """Read and update a user's yearly JSONL cache files."""

    def __init__(self, login: str) -> None:
        """Locate the user's cache relative to the current Git checkout."""
        cwd = Path.cwd()
        root = next(
            (path for path in (cwd, *cwd.parents) if (path / ".git").exists()),
            cwd,
        )
        account = f"github-{quote(login.casefold(), safe='')}"
        self.directory = root / "cache" / account

    def get(self, month: date, *, include_private: bool = False) -> Counter[str] | None:
        """Return cached counts, or None if the requested data was not cached."""
        record = self._read_year(month.year).get(month)
        if record is None:
            return None
        counts = Counter(record.counts)
        if include_private:
            if record.private_counts is None:
                return None
            counts.update(record.private_counts)
        return counts

    def _read_year(self, year: int) -> dict[date, MonthRecord]:
        """Load valid month records from the given year's cache file."""
        path = self.directory / f"{year:04}.jsonl"
        try:
            lines = path.read_bytes().splitlines()
        except FileNotFoundError:
            return {}
        records = {}
        for line in lines:
            try:
                record = MonthRecord.model_validate_json(line, strict=True)
            except ValidationError:
                continue
            if record.month.year == year and record.month.day == 1:
                records[record.month] = record
        return records

    def put(
        self,
        month: date,
        counts: Counter[str],
        *,
        private_counts: Counter[str] | None = None,
    ) -> None:
        """Save monthly counts while retaining any previously cached private counts."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{month.year:04}.jsonl"
        with FileLock(path.with_suffix(".lock"), timeout=30):
            records = self._read_year(month.year)
            previous = records.get(month)
            stored_private_counts = (
                dict(private_counts) if private_counts is not None else None
            )
            if private_counts is None and previous is not None:
                stored_private_counts = previous.private_counts
            records[month] = MonthRecord(
                month=month, counts=dict(counts), private_counts=stored_private_counts
            )
            data = "".join(
                json.dumps(
                    records[key].model_dump(mode="json", exclude_none=True),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
                for key in sorted(records)
            )
            self._replace(path, data)

    def _replace(self, path: Path, data: str) -> None:
        """Atomically replace a cache file with the serialized records."""
        with NamedTemporaryFile(
            dir=self.directory, suffix=".tmp", delete=False
        ) as file:
            temporary_path = Path(file.name)
            try:
                file.write(data.encode("utf-8"))
                file.close()
                temporary_path.replace(path)
            finally:
                file.close()
                temporary_path.unlink(missing_ok=True)
