from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200), default="Unknown")
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    resume_submissions: Mapped[list["ResumeSubmission"]] = relationship(back_populates="candidate")
    assessment_sessions: Mapped[list["AssessmentSession"]] = relationship(back_populates="candidate")


class ResumeSubmission(Base):
    __tablename__ = "resume_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(260), nullable=True)
    track: Mapped[str] = mapped_column(String(30), nullable=True)
    resume_text: Mapped[str] = mapped_column(Text)
    ats_score: Mapped[int] = mapped_column(Integer, nullable=True)
    ats_verdict: Mapped[str] = mapped_column(String(30), nullable=True)
    ats_payload: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="resume_submissions")
    assessment_sessions: Mapped[list["AssessmentSession"]] = relationship(back_populates="resume_submission")


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=True, index=True)
    resume_submission_id: Mapped[int] = mapped_column(ForeignKey("resume_submissions.id"), nullable=True, index=True)
    track: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(30), default="generated")
    violations: Mapped[int] = mapped_column(Integer, default=0)
    time_limit_sec: Mapped[int] = mapped_column(Integer, default=0)
    time_taken_sec: Mapped[int] = mapped_column(Integer, default=0)
    auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    mcq_score: Mapped[int] = mapped_column(Integer, default=0)
    subjective_score: Mapped[int] = mapped_column(Integer, default=0)
    penalty: Mapped[int] = mapped_column(Integer, default=0)
    final_score: Mapped[int] = mapped_column(Integer, default=0)
    verdict: Mapped[str] = mapped_column(String(30), nullable=True)
    assessment_payload: Mapped[str] = mapped_column(Text, nullable=True)
    result_payload: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="assessment_sessions")
    resume_submission: Mapped["ResumeSubmission"] = relationship(back_populates="assessment_sessions")
    answers: Mapped[list["AssessmentAnswer"]] = relationship(back_populates="assessment_session")


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_session_id: Mapped[int] = mapped_column(ForeignKey("assessment_sessions.id"), index=True)
    question_id: Mapped[int] = mapped_column(Integer)
    question_type: Mapped[str] = mapped_column(String(20))
    question_text: Mapped[str] = mapped_column(Text, nullable=True)
    selected_answer: Mapped[str] = mapped_column(String(10), nullable=True)
    correct_answer: Mapped[str] = mapped_column(String(10), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assessment_session: Mapped["AssessmentSession"] = relationship(back_populates="answers")
