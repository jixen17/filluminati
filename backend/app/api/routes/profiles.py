from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.profiles import profile_service as svc
from app.schemas.profile import ProfileCreate, ProfileOut, ProfileUpdate
from fastapi import HTTPException

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileCreate, db: Session = Depends(get_db)):
    return svc.create_profile(db, body)


@router.get("", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    return svc.list_profiles(db)


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    return svc.get_profile(db, profile_id)


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: str, body: ProfileUpdate, db: Session = Depends(get_db)):
    return svc.update_profile(db, profile_id, body)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: str,
    confirm: bool = Query(False, description="Must be true to delete"),
    db: Session = Depends(get_db),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Deleting a profile removes all its documents and tasks. Pass ?confirm=true.",
        )
    svc.delete_profile(db, profile_id)
    return Response(status_code=204)