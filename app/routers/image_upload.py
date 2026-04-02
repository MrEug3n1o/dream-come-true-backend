import uuid
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_cloudinary_settings
from app.database import get_db
from app.models.models import Dream, User, UserRole

router = APIRouter(prefix="/images", tags=["Images"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class ImageUploadOut(BaseModel):
    image_url: str


def configure_cloudinary():
    cs = get_cloudinary_settings()
    cloudinary.config(
        cloud_name=cs.CLOUDINARY_CLOUD_NAME,
        api_key=cs.CLOUDINARY_API_KEY,
        api_secret=cs.CLOUDINARY_API_SECRET,
        secure=True,
    )


@router.post("", response_model=ImageUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an image to Cloudinary.
    Returns the secure URL to use as image_url when creating/updating a dream.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: jpeg, png, webp, gif",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB",
        )

    configure_cloudinary()

    try:
        public_id = f"dreams/{current_user.user_id}/{uuid.uuid4()}"
        result = cloudinary.uploader.upload(
            contents,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
        )
        image_url = result["secure_url"]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to upload image: {str(exc)}",
        )

    return {"image_url": image_url}


@router.post("/dreams/{dream_id}", response_model=ImageUploadOut)
async def upload_dream_image(
    dream_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an image and immediately attach it to a dream.
    Owner or admin only.
    """
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")

    if current_user.role != UserRole.ADMIN and dream.owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your dream")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: jpeg, png, webp, gif",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB",
        )

    configure_cloudinary()

    try:
        public_id = f"dreams/{current_user.user_id}/{uuid.uuid4()}"
        result = cloudinary.uploader.upload(
            contents,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
        )
        image_url = result["secure_url"]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to upload image: {str(exc)}",
        )

    dream.image_url = image_url
    db.commit()
    db.refresh(dream)

    return {"image_url": image_url}
