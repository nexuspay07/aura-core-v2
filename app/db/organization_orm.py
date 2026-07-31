"""ORM bridge over the canonical SQLAlchemy Core organizations table."""
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from app.db.database import Base
from app.db.organization_table import organization_table


if TYPE_CHECKING:
    from app.commercial.models import Subscription
    from app.commercial.models import UsageRecord, CreditNote, CreditNoteApplication, Refund


class Organization(Base):
    __table__ = organization_table
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="organization",
        lazy="select",
        passive_deletes=True,
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="organization", lazy="select", passive_deletes=True
    )
    billing_account: Mapped["BillingAccount | None"] = relationship("BillingAccount", back_populates="organization", uselist=False, lazy="select", passive_deletes=True)
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="organization", lazy="select", passive_deletes=True)
    credit_notes: Mapped[list["CreditNote"]] = relationship("CreditNote", back_populates="organization", lazy="select", passive_deletes=True)
    credit_note_applications: Mapped[list["CreditNoteApplication"]] = relationship("CreditNoteApplication", back_populates="organization", lazy="select", passive_deletes=True)
    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="organization", lazy="select", passive_deletes=True)
