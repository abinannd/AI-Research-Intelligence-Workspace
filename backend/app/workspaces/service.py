from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, Workspace


def list_workspaces(db: Session, user: User) -> list[Workspace]:
    return (
        db.query(Workspace)
        .filter(Workspace.user_id == user.id)
        .order_by(Workspace.created_at.desc())
        .all()
    )


def create_workspace(db: Session, user: User, name: str) -> Workspace:
    ws = Workspace(user_id=user.id, name=name.strip())
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def get_owned_workspace(db: Session, user: User, workspace_id: str) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.user_id == user.id).one_or_none()
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws
