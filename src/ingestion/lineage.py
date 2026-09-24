"""Data lineage tracking — source traceability for imported values."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class FieldLineage:
    """Lineage record for a single imported value."""
    canonical_field: str
    source_file: str
    source_sheet: str
    source_label: str    # original label before normalization
    period_label: str
    import_timestamp: datetime
    statement_type: str
    value: Optional[float]


@dataclass
class ImportLineage:
    """Complete lineage for one import event."""
    import_id: int
    company_id: int
    source_file: str
    file_hash: str
    statement_type: str
    import_timestamp: datetime
    fields: list[FieldLineage] = field(default_factory=list)

    def add(self, canonical_field: str, source_sheet: str, source_label: str,
            period_label: str, value: Optional[float]) -> None:
        self.fields.append(FieldLineage(
            canonical_field=canonical_field,
            source_file=self.source_file,
            source_sheet=source_sheet,
            source_label=source_label,
            period_label=period_label,
            import_timestamp=self.import_timestamp,
            statement_type=self.statement_type,
            value=value,
        ))

    def find(self, canonical_field: str, period_label: str) -> Optional[FieldLineage]:
        for f in self.fields:
            if f.canonical_field == canonical_field and f.period_label == period_label:
                return f
        return None
