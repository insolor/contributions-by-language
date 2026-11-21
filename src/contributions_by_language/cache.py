import json
from collections import Counter
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote

from filelock import FileLock
from pydantic import BaseModel, NonNegativeInt, ValidationError


class MonthRecord(BaseModel):
    month: date
    counts: dict[str, NonNegativeInt]


class MonthCache:
    def __init__(self, login: str) -> None:
        cwd = Path.cwd()
        root = next(
            (path for path in (cwd, *cwd.parents) if (path / ".git").exists()),
            cwd,
        )
        self.directory = root / "cache" / f"github-{quote(login.casefold(), safe='')}"

    def get(self, month: date) -> Counter[str] | None:
        record = self._read_year(month.year).get(month)
        return Counter(record.counts) if record is not None else None

    def _read_year(self, year: int) -> dict[date, MonthRecord]:
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

    def put(self, month: date, counts: Counter[str]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{month.year:04}.jsonl"
        with FileLock(path.with_suffix(".lock"), timeout=30):
            records = self._read_year(month.year)
            records[month] = MonthRecord(month=month, counts=dict(counts))
            data = "".join(
                json.dumps(
                    records[key].model_dump(mode="json"),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
                for key in sorted(records)
            )
            self._replace(path, data)

    def _replace(self, path: Path, data: str) -> None:
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
