from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    task: Mapped[str] = mapped_column(String(64))   # perplexity | hellaswag | mmlu | ...
    score: Mapped[float] = mapped_column(Float)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    run: Mapped["Run"] = relationship("Run", back_populates="benchmark_results")  # type: ignore[name-defined]
