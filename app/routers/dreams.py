import random
import uuid
from decimal import Decimal
from typing import Optional
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Dream, User, UserRole, PersonType, ParticipationFormat, DEFAULT_DREAM_IMAGE
from app.models.schemas import DreamOut, DreamOutWithOwner, DreamUpdate
from app.auth import get_current_user
from app.config import get_cloudinary_settings

router = APIRouter(prefix="/dreams", tags=["Dreams"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def _get_dream_or_404(dream_id: str, db: Session) -> Dream:
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")
    return dream


def _require_ownership_or_admin(dream: Dream, current_user: User):
    if current_user.role != UserRole.ADMIN and dream.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own dreams"
        )


def _upload_image(file: UploadFile, contents: bytes, user_id: str) -> str:
    cs = get_cloudinary_settings()
    cloudinary.config(
        cloud_name=cs.CLOUDINARY_CLOUD_NAME,
        api_key=cs.CLOUDINARY_API_KEY,
        api_secret=cs.CLOUDINARY_API_SECRET,
        secure=True,
    )
    public_id = f"dreams/{user_id}/{uuid.uuid4()}"
    result = cloudinary.uploader.upload(
        contents,
        public_id=public_id,
        resource_type="image",
        overwrite=False,
    )
    return result["secure_url"]


# ─── Public reads ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[DreamOut])
def list_dreams(
    participation_format: Optional[ParticipationFormat] = Query(None),
    person_type:          Optional[PersonType]           = Query(None),
    max_budget:           Optional[Decimal]              = Query(None),
    city:                 Optional[str]                  = Query(None),
    is_completed:         Optional[bool]                 = Query(None),
    sort_by:              Optional[str]                  = Query(None, description="'date' or 'budget'"),
    db: Session = Depends(get_db),
):
    """List all dreams with optional filtering. Public endpoint."""
    query = db.query(Dream)

    if participation_format:
        query = query.filter(Dream.participation_format == participation_format)
    if person_type:
        query = query.filter(Dream.person_type == person_type)
    if max_budget is not None:
        query = query.filter(Dream.target_budget <= max_budget)
    if city:
        query = query.filter(Dream.city.ilike(f"%{city}%"))
    if is_completed is not None:
        query = query.filter(Dream.is_completed == is_completed)

    if sort_by == "budget":
        query = query.order_by(Dream.target_budget.asc())
    else:
        query = query.order_by(Dream.created_at.desc())

    return query.all()


@router.get("/match", response_model=list[DreamOut])
def match_dreams(
    participation_format: ParticipationFormat = Query(...),
    person_type:          PersonType           = Query(...),
    max_budget:           Decimal              = Query(...),
    db: Session = Depends(get_db),
):
    """Smart Match: up to 3 random incomplete dreams. Public."""
    matches = (
        db.query(Dream)
        .filter(
            Dream.is_completed         == False,
            Dream.participation_format == participation_format,
            Dream.person_type          == person_type,
            Dream.target_budget        <= max_budget,
        )
        .all()
    )
    if not matches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No dreams match your criteria")
    return random.sample(matches, min(3, len(matches)))


@router.get("/{dream_id}", response_model=DreamOutWithOwner)
def get_dream(dream_id: str, db: Session = Depends(get_db)):
    """Get full details of a single dream. Public."""
    return _get_dream_or_404(dream_id, db)


# ─── Authenticated writes ─────────────────────────────────────────────────────

@router.post("", response_model=DreamOut, status_code=status.HTTP_201_CREATED)
async def create_dream(
    title:                str                  = Form(...),
    description:          str                  = Form(...),
    person_type:          PersonType           = Form(...),
    participation_format: ParticipationFormat  = Form(...),
    target_budget:        Decimal              = Form(...),
    city:                 str                  = Form(...),
    image:                Optional[UploadFile] = File(None),
    db:                   Session              = Depends(get_db),
    current_user:         User                 = Depends(get_current_user),
):
    """
    Create a dream. Accepts multipart/form-data.
    Image is optional — uses placeholder if omitted.
    """
    if target_budget <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Budget must be greater than 0")
    if target_budget > 15000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Budget cannot exceed 15000")

    image_url = DEFAULT_DREAM_IMAGE

    if image and image.filename:
        if image.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file type. Allowed: jpeg, png, webp, gif",
            )
        contents = await image.read()
        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image too large. Maximum size is 5MB",
            )
        try:
            image_url = _upload_image(image, contents, current_user.user_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to upload image: {str(exc)}",
            )

    dream = Dream(
        owner_id=current_user.user_id,
        title=title,
        description=description,
        person_type=person_type,
        participation_format=participation_format,
        target_budget=target_budget,
        city=city,
        image_url=image_url,
    )
    db.add(dream)
    db.commit()
    db.refresh(dream)
    return dream


@router.patch("/{dream_id}/complete", response_model=DreamOut)
def complete_dream(
    dream_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a dream as completed. Any authenticated user can do this
    except the dream owner (you can't complete your own dream).
    """
    dream = _get_dream_or_404(dream_id, db)

    if dream.is_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dream has already been completed"
        )

    if dream.owner_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot complete your own dream"
        )

    dream.is_completed = True
    db.commit()
    db.refresh(dream)
    return dream


@router.put("/{dream_id}", response_model=DreamOut)
def update_dream(
    dream_id: str,
    payload: DreamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update dream fields. Owner or admin only."""
    dream = _get_dream_or_404(dream_id, db)
    _require_ownership_or_admin(dream, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dream, field, value)

    db.commit()
    db.refresh(dream)
    return dream


@router.delete("/{dream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dream(
    dream_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dream. Owner or admin only."""
    dream = _get_dream_or_404(dream_id, db)
    _require_ownership_or_admin(dream, current_user)
    db.delete(dream)
    db.commit()
