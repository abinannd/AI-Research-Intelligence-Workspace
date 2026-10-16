from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import WorkspaceIn, WorkspaceOut
from app.security import get_current_user
from app.workspaces.service import create_workspace, get_owned_workspace, list_workspaces

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
def get_workspaces(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[WorkspaceOut]:
    return [WorkspaceOut.model_validate(ws) for ws in list_workspaces(db, user)]


@router.post("", response_model=WorkspaceOut)
def post_workspace(
    body: WorkspaceIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    return WorkspaceOut.model_validate(create_workspace(db, user, body.name))


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    return WorkspaceOut.model_validate(get_owned_workspace(db, user, workspace_id))
