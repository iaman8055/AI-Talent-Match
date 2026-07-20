import uuid

from fastapi import APIRouter, Depends, status

from src.api.deps import get_company_service, get_current_user, require_company_role, require_roles
from src.api.v1.companies.schemas import (
    CompanyInviteResponse,
    CompanyMemberResponse,
    CompanyResponse,
    CreateCompanyRequest,
    InviteMemberRequest,
    UpdateCompanyRequest,
)
from src.application.company.service import CompanyService
from src.domain.company.entities import CompanyMemberRole
from src.domain.user.entities import User, UserRole

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    body: CreateCompanyRequest,
    current_user: User = Depends(require_roles(UserRole.RECRUITER)),
    company_service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    company = company_service.create_company(body.name, current_user.id)
    return CompanyResponse.from_entity(company)


@router.get("/me", response_model=list[CompanyResponse])
def list_my_companies(
    current_user: User = Depends(get_current_user),
    company_service: CompanyService = Depends(get_company_service),
) -> list[CompanyResponse]:
    companies = company_service.list_my_companies(current_user.id)
    return [CompanyResponse.from_entity(company) for company in companies]


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: uuid.UUID,
    _member: object = Depends(require_company_role()),
    company_service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    return CompanyResponse.from_entity(company_service.get_company(company_id))


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: uuid.UUID,
    body: UpdateCompanyRequest,
    _member: object = Depends(
        require_company_role(CompanyMemberRole.OWNER, CompanyMemberRole.ADMIN)
    ),
    company_service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    return CompanyResponse.from_entity(
        company_service.update_company(company_id, body.name, body.match_threshold)
    )


@router.get("/{company_id}/members", response_model=list[CompanyMemberResponse])
def list_members(
    company_id: uuid.UUID,
    _member: object = Depends(require_company_role()),
    company_service: CompanyService = Depends(get_company_service),
) -> list[CompanyMemberResponse]:
    members = company_service.list_members(company_id)
    return [CompanyMemberResponse.from_entity(member) for member in members]


@router.post(
    "/{company_id}/members",
    response_model=CompanyInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    company_id: uuid.UUID,
    body: InviteMemberRequest,
    current_user: User = Depends(get_current_user),
    _member: object = Depends(
        require_company_role(CompanyMemberRole.OWNER, CompanyMemberRole.ADMIN)
    ),
    company_service: CompanyService = Depends(get_company_service),
) -> CompanyInviteResponse:
    invite = company_service.invite_member(company_id, body.email, body.role, current_user.id)
    return CompanyInviteResponse.from_entity(invite)
