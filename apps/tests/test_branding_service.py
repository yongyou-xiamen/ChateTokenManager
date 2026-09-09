from types import SimpleNamespace

import pytest

from exceptions import ValidationError
from services import branding_service


def test_svg_rejects_script_content() -> None:
    content = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    with pytest.raises(ValidationError, match="不安全"):
        branding_service._validate_image(content, "svg", favicon=False)


def test_png_rejects_extension_only_spoof() -> None:
    with pytest.raises(ValidationError, match="PNG"):
        branding_service._validate_image(b"not-a-png", "png", favicon=False)


def test_square_logo_rejects_file_over_two_megabytes() -> None:
    content = branding_service.PNG_SIGNATURE + b"x" * (
        branding_service.MAX_SQUARE_LOGO_BYTES + 1
    )

    with pytest.raises(ValidationError, match="2MB"):
        branding_service._validate_image(content, "png", square_logo=True)


@pytest.mark.asyncio
async def test_branding_reports_square_logo(monkeypatch) -> None:
    async def get_branding_row(session, tenant_id=None):
        return SimpleNamespace(
            platform_name="测试平台",
            logo_path=None,
            square_logo_path="/tmp/square-logo.png",
            favicon_path=None,
        )

    monkeypatch.setattr(branding_service.branding_repo, "get", get_branding_row)
    monkeypatch.setattr(branding_service, "_asset_exists", lambda path: bool(path))

    branding = await branding_service.get_branding(object())

    assert branding["has_square_logo"] is True
