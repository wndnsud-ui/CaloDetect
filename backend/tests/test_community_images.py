"""DB 작업 승인과 무관하게 검증 가능한 공개 사본의 개인정보 제거 경계."""
import io

import pytest
from PIL import Image, PngImagePlugin, TiffImagePlugin

from backend.app.services.community_images import sanitize_image, save_sanitized_copy


def test_jpeg_gps_exif_comment_removed_and_orientation_applied():
    original = Image.new('RGB', (12, 8), 'green')
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = 'private caption'
    exif[34853] = {1: 'N', 2: (TiffImagePlugin.IFDRational(37), TiffImagePlugin.IFDRational(0), TiffImagePlugin.IFDRational(0))}
    buffer = io.BytesIO()
    original.save(buffer, format='JPEG', exif=exif, icc_profile=b'private ICC', comment=b'private comment')
    with Image.open(io.BytesIO(buffer.getvalue())) as source:
        assert source.getexif().get_ifd(34853)
    content, suffix = sanitize_image(buffer.getvalue())
    assert suffix == '.jpg'
    with Image.open(io.BytesIO(content)) as clean:
        assert clean.format == 'JPEG' and clean.size == (8, 12)
        assert not clean.getexif()
        assert not {'exif', 'icc_profile', 'comment', 'xmp'} & clean.info.keys()
    assert b'private' not in content


def test_png_metadata_removed_without_losing_alpha():
    original = Image.new('RGBA', (8, 8), (20, 40, 60, 100))
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('Location', 'private GPS location')
    metadata.add_itxt('XML:com.adobe.xmp', 'private XMP')
    buffer = io.BytesIO()
    original.save(buffer, format='PNG', pnginfo=metadata, icc_profile=b'private ICC')
    content, suffix = sanitize_image(buffer.getvalue())
    with Image.open(io.BytesIO(content)) as clean:
        assert suffix == '.png' and clean.format == 'PNG'
        assert clean.getpixel((0, 0)) == (20, 40, 60, 100)
        assert not clean.info


@pytest.mark.parametrize('content', [b'', b'not an image', b'x' * (10 * 1024 * 1024 + 1)], ids=['empty', 'invalid', 'oversized'])
def test_invalid_input_rejected(content):
    with pytest.raises(ValueError):
        sanitize_image(content)


def test_unsupported_format_rejected():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4)).save(buffer, format='GIF')
    with pytest.raises(ValueError):
        sanitize_image(buffer.getvalue())


def test_copy_uses_new_name_and_preserves_original(tmp_path):
    source = tmp_path / 'private-original.png'
    Image.new('RGB', (4, 4), 'red').save(source)
    before = source.read_bytes()
    destination = save_sanitized_copy(source, tmp_path / 'community')
    assert destination.name != source.name and destination.parent.name == 'community'
    assert source.read_bytes() == before
    assert destination.exists()


def test_invalid_image_creates_no_file(tmp_path):
    source = tmp_path / 'broken.png'
    source.write_bytes(b'bad')
    with pytest.raises(ValueError):
        save_sanitized_copy(source, tmp_path / 'community')
    assert not (tmp_path / 'community').exists()
