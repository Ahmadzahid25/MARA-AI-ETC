"""Vertical-slice v1 wire contracts.

Frozen by docs/architecture/17-vertical-slice-execution-directive.md
§17.11 for the first end-to-end grant flow.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    APPLICANT = 'applicant'
    OFFICER = 'officer'
    ADMIN = 'admin'


class ApplicationStatus(str, Enum):
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    PROCESSING = 'PROCESSING'
    NEEDS_INFO = 'NEEDS_INFO'
    UNDER_REVIEW = 'UNDER_REVIEW'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'


class OfficerDecisionAction(str, Enum):
    APPROVE = 'approve'
    REJECT = 'reject'
    REQUEST_MORE_INFO = 'request_more_info'


class AuthRegisterInput(BaseModel):
    full_name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class AuthLoginInput(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class AuthTokenOutput(BaseModel):
    user_id: str
    role: UserRole
    access_token: str


class ApplicantProfileInput(BaseModel):
    full_name: str = Field(min_length=1)
    ic_number: str = Field(min_length=6)
    phone: str = Field(min_length=6)
    email: str = Field(min_length=3)
    state: str = Field(min_length=2)


class BusinessProfileInput(BaseModel):
    business_name: str = Field(min_length=1)
    ssm_number: str = Field(min_length=3)
    sector: str = Field(min_length=2)
    years_operating: int = Field(ge=0)
    monthly_revenue_avg: float = Field(ge=0)


class FinancingInput(BaseModel):
    scheme: str = Field(min_length=1)
    amount_requested: float = Field(gt=0)
    purpose: str = Field(min_length=1)
    tenure_months: int = Field(gt=0)


class ApplicationDocumentInput(BaseModel):
    doc_type: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    mime_type: str = Field(min_length=3)
    file_path: str = Field(min_length=1)


class CreateApplicationInput(BaseModel):
    applicant: ApplicantProfileInput
    business: BusinessProfileInput
    financing: FinancingInput
    documents: list[ApplicationDocumentInput] = Field(default_factory=list)


class CreateApplicationOutput(BaseModel):
    application_id: str
    status: ApplicationStatus


class ApplicationStatusOutput(BaseModel):
    application_id: str
    status: ApplicationStatus
    stage_log: list[str] = Field(default_factory=list)
    updated_at: datetime


class OfficerQueueItem(BaseModel):
    application_id: str
    applicant_name: str
    scheme: str
    amount_requested: float
    status: ApplicationStatus
    updated_at: datetime


class OfficerQueueOutput(BaseModel):
    items: list[OfficerQueueItem] = Field(default_factory=list)


class OfficerDecisionInput(BaseModel):
    action: OfficerDecisionAction
    reason: str = ''
    conditions: list[str] = Field(default_factory=list)


class OfficerDecisionOutput(BaseModel):
    application_id: str
    status: ApplicationStatus
    decision_recorded_at: datetime


class ApplicationDetailOutput(BaseModel):
    application_id: str
    status: ApplicationStatus
    applicant: ApplicantProfileInput
    business: BusinessProfileInput
    financing: FinancingInput
    documents: list[ApplicationDocumentInput] = Field(default_factory=list)
    ai_assessment: dict = Field(default_factory=dict)
    workflow: dict = Field(default_factory=dict)
