"""TV communication service for Samsung Frame TV."""

from typing import Dict, Optional

from ping3 import ping
from samsungtvws import SamsungTVWS

from ..core.exceptions import TVConnectionError
from ..core.logging import get_logger
from ..core.models import TVDevice


class TVService:
    """Service for communicating with Samsung Frame TV."""

    def __init__(self, device: TVDevice):
        self.device = device
        self.logger = get_logger(__name__)
        self._tv_connection: Optional[SamsungTVWS] = None

    @property
    def tv(self) -> SamsungTVWS:
        """Get or create TV connection."""
        if self._tv_connection is None:
            self._tv_connection = SamsungTVWS(
                host=self.device.ip,
                port=8002,
                token=self.device.token,
                timeout=10
            )

        return self._tv_connection

    def test_connection(self) -> bool:
        """Test connection to the TV."""
        try:
            delay = ping(self.device.ip)
            if delay is None:
                self.logger.debug("TV not online", tv_ip=self.device.ip, error=str(e))
                return False

            # Try to get device info as a connection test
            info = self.tv.rest_device_info()
            print(info)
            self.logger.debug("Connected to TV", device_info=info, tv_ip=self.device.ip)
            return True
        except Exception as e:
            self.logger.error("Failed to connect to TV", tv_ip=self.device.ip, error=str(e))
            return False

    def upload_image(self, image_data: bytes, filename: str) -> bool:
        """Upload image to Samsung Frame TV."""
        try:
            if not self.test_connection():
                raise TVConnectionError("Cannot connect to TV")

            self.logger.info("Uploading image to Samsung Frame TV",
                           filename=filename,
                           tv_ip=self.device.ip,
                           image_size=len(image_data))

            # Upload the image
            uploaded_id = self.tv.art().upload(image_data, file_type="JPEG", matte="none")
            self.tv.art().select_image(uploaded_id, show=self.tv.art().get_artmode() == "on")
            self.logger.info("Successfully uploaded image", filename=filename)
            return True
        except Exception as e:
            self.logger.error("Upload failed", filename=filename, error=str(e))
            raise TVConnectionError(f"Failed to upload image: {e}")

    def get_device_info(self) -> Dict:
        """Get TV device information."""
        try:
            return self.tv.rest_device_info()
        except Exception as e:
            raise TVConnectionError(f"Failed to get device info: {e}")

    def get_art_mode_status(self) -> Dict:
        """Get current art mode status."""
        try:
            return self.tv.art().get_current()
        except Exception as e:
            self.logger.warning("Failed to get art mode status", error=str(e))
            return {}

    def set_art_mode(self, artwork_id: Optional[str] = None) -> bool:
        """Set TV to art mode, optionally with specific artwork."""
        try:
            art_api = self.tv.art()

            if artwork_id:
                # Set specific artwork
                result = art_api.select_image(artwork_id)
                self.logger.info("Set artwork", artwork_id=artwork_id)
            else:
                # Just enable art mode
                result = art_api.set_current("on")
                self.logger.info("Enabled art mode")

            return result

        except Exception as e:
            self.logger.error("Failed to set art mode",
                            artwork_id=artwork_id,
                            error=str(e))
            return False

    def get_artwork_list(self) -> list:
        """Get list of available artworks on TV."""
        try:
            return self.tv.art().get_list()
        except Exception as e:
            self.logger.warning("Failed to get artwork list", error=str(e))
            return []

    def delete_artwork(self, artwork_id: str) -> bool:
        """Delete artwork from TV."""
        try:
            result = self.tv.art().delete(artwork_id)
            if result:
                self.logger.info("Deleted artwork", artwork_id=artwork_id)
            return result
        except Exception as e:
            self.logger.error("Failed to delete artwork",
                            artwork_id=artwork_id,
                            error=str(e))
            return False
