"""커뮤니티 공개용 사진 사본. 원본을 보존하고 픽셀만 재인코딩한다."""
import io
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000


def sanitize_image(content: bytes) -> tuple[bytes, str]:
    """JPEG/PNG 형식과 방향은 유지하고 EXIF/GPS/XMP/ICC/주석은 복사하지 않는다."""
    if not content or len(content) > MAX_BYTES:
        raise ValueError('사진은 10MB 이하의 JPG 또는 PNG여야 합니다.')
    try:
        with Image.open(io.BytesIO(content)) as original:
            format_ = original.format
            if format_ not in ('JPEG', 'PNG') or original.width * original.height > MAX_PIXELS:
                raise ValueError('unsupported image')
            oriented = ImageOps.exif_transpose(original)
            mode = 'RGBA' if format_ == 'PNG' and ('A' in oriented.getbands() or 'transparency' in oriented.info) else 'RGB'
            pixels = oriented.convert(mode)
            # convert/copy만으로는 info가 남을 수 있으므로 새 이미지에 픽셀만 붙인다.
            clean = Image.new(mode, pixels.size)
            clean.paste(pixels)
            output = io.BytesIO()
            clean.save(output, format=format_, **({'quality': 90} if format_ == 'JPEG' else {}))
            return output.getvalue(), '.jpg' if format_ == 'JPEG' else '.png'
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValueError('사진 사본을 만들 수 없습니다. JPG/PNG 파일을 확인해 주세요.') from None


def save_sanitized_copy(source_path, community_dir) -> Path:
    """소유권을 확인한 서버 원본 경로를 받는다. 반환 파일은 호출자의 rollback 정리 대상이다.

    DB 처리나 공개 권한 판정은 하지 않는다. 이번 함수가 만든 파일만 실패 시 제거한다.
    """
    source_path, community_dir = Path(source_path), Path(community_dir)
    with source_path.open('rb') as source:
        content = source.read(MAX_BYTES + 1)
    sanitized, suffix = sanitize_image(content)
    community_dir.mkdir(parents=True, exist_ok=True)
    destination = community_dir / f'{uuid4()}{suffix}'
    created = False
    try:
        with destination.open('xb') as output:
            created = True
            output.write(sanitized)
        return destination
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
