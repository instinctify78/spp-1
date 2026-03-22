from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.metric import Metric
    from app.models.tensor_artifact import TensorArtifact


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # PENDING | RUNNING | COMPLETED | FAILED
    config: Mapped[dict] = mapped_column(JSON)           # Full RunConfig snapshot
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    metrics: Mapped[list["Metric"]] = relationship("Metric", back_populates="run", cascade="all, delete-orphan")
    tensor_artifacts: Mapped[list["TensorArtifact"]] = relationship(
        "TensorArtifact", back_populates="run", cascade="all, delete-orphan"
    )
