from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TensorArtifact(Base):
    __tablename__ = "tensor_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    layer_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    shape: Mapped[list | None] = mapped_column(JSON)   # e.g. [1, 128, 4096]
    dtype: Mapped[str | None] = mapped_column(String(32))

    run: Mapped["Run"] = relationship("Run", back_populates="tensor_artifacts")  # type: ignore[name-defined]
