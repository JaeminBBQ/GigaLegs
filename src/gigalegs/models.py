"""Multi-user-ready schema (D8): every user-owned row has user_id."""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class PhaseState(Base):
    """Where the athlete is in the queue. One row per user."""

    __tablename__ = "phase_state"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    phase: Mapped[str] = mapped_column(String(20))  # onramp | program | deload | squat_block
    week: Mapped[str] = mapped_column(String(8))
    day: Mapped[int] = mapped_column(Integer)
    gate_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    bike_stage: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    phase: Mapped[str] = mapped_column(String(20))
    week: Mapped[str] = mapped_column(String(8))
    day: Mapped[int] = mapped_column(Integer)
    heavy: Mapped[bool] = mapped_column(Boolean, default=False)
    soreness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | done
    note: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sets: Mapped[list["SetLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SetLog.id"
    )


class SetLog(Base):
    __tablename__ = "set_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    exercise: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(20))
    set_index: Mapped[int] = mapped_column(Integer)
    prescribed_weight_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    prescribed_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpe_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpe_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    form_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    pain: Mapped[str | None] = mapped_column(String(120), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    session: Mapped[Session] = relationship(back_populates="sets")


class Ride(Base):
    __tablename__ = "rides"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    miles: Mapped[float] = mapped_column(Float)
    minutes: Mapped[int] = mapped_column(Integer)
    zone: Mapped[int] = mapped_column(Integer, default=2)
    commute: Mapped[str | None] = mapped_column(String(8), nullable=True)  # in | out | round
    elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class DayLog(Base):
    """Recovery and rest days, so 'something every day' is visible (D20)."""

    __tablename__ = "day_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(16))  # recovery | rest | smart_rest
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Metric(Base):
    """Morning soreness and bodyweight."""

    __tablename__ = "metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(16))  # soreness | bodyweight
    value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class XpEvent(Base):
    __tablename__ = "xp_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String(40))
    amount: Mapped[int] = mapped_column(Integer)
    ref: Mapped[str] = mapped_column(String(60), default="")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
