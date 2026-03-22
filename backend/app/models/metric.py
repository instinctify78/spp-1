from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    metric_type: Mapped[str] = mapped_column(String(64))
    # Metric types:
    #   ttft_ms          — time-to-first-token in milliseconds
    #   total_latency_ms — total generation time in milliseconds
    #   throughput_tps   — tokens per second
    #   peak_memory_mb   — peak memory usage in MB
    value: Mapped[float] = mapped_column(Float)
    step: Mapped[int | None] = mapped_column(Integer)    # token step for time-series; null for aggregates
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    run: Mapped["Run"] = relationship("Run", back_populates="metrics")  # type: ignore[name-defined]
