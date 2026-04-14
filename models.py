"""Asset data model and mapping helpers.

Version: 0.13.3
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Asset:
    """
    Object-Oriented Refactoring of Fab Asset.
    Provides mapped properties from the raw API response and centralizes the parsing logic.
    """
    raw_data: Dict[str, Any]

    @property
    def uid(self) -> str:
        return self.raw_data.get("listing", {}).get("uid", "")

    @property
    def title(self) -> str:
        return self.raw_data.get("listing", {}).get("title", "")

    @property
    def publisher(self) -> Dict[str, Any]:
        listing = self.raw_data.get("listing", {})
        return listing.get("publisher") or listing.get("user") or {}

    @property
    def seller_name(self) -> str:
        return self.publisher.get("sellerName", "")

    @property
    def seller_id(self) -> str:
        return self.publisher.get("sellerId", "")

    @property
    def seller_avatar_url(self) -> str:
        return self.publisher.get("profileImageUrl", "")

    @property
    def listing_type(self) -> str:
        return self.raw_data.get("listing", {}).get("listingType", "")

    @property
    def created_at(self) -> str:
        return self.raw_data.get("createdAt", "")

    @property
    def last_updated_at(self) -> str:
        return self.raw_data.get("listing", {}).get("lastUpdatedAt", "")

    @property
    def is_mature(self) -> bool:
        return self.raw_data.get("listing", {}).get("isMature", False)

    @property
    def status(self) -> str:
        return self.raw_data.get("status", "")

    @property
    def asset_formats(self) -> List[Dict[str, Any]]:
        return self.raw_data.get("listing", {}).get("assetFormats") or []

    @property
    def asset_format_names(self) -> str:
        names = []
        for fmt in self.asset_formats:
            fmt_type = fmt.get("assetFormatType") or {}
            if fmt_type.get("name"):
                names.append(fmt_type.get("name"))
        return ", ".join(names)

    @property
    def asset_format_codes(self) -> str:
        codes = []
        for fmt in self.asset_formats:
            fmt_type = fmt.get("assetFormatType") or {}
            if fmt_type.get("code"):
                codes.append(fmt_type.get("code"))
        return ", ".join(codes)

    @property
    def tags(self) -> str:
        tags_list = self.raw_data.get("listing", {}).get("tags", [])
        if isinstance(tags_list, list):
            return ", ".join(t.get("name", "") for t in tags_list if isinstance(t, dict))
        return ""

    @property
    def description(self) -> str:
        return self.raw_data.get("listing", {}).get("description", "")

    @property
    def average_rating(self) -> float:
        return self.raw_data.get("listing", {}).get("averageRating", 0)

    @property
    def review_count(self) -> int:
        return self.raw_data.get("listing", {}).get("reviewCount", 0)

    @property
    def starting_price(self) -> Dict[str, Any]:
        return self.raw_data.get("listing", {}).get("startingPrice") or {}

    @property
    def price(self) -> Any:
        return self.starting_price.get("price", "")

    @property
    def currency_code(self) -> str:
        return self.starting_price.get("currencyCode", "")

    @property
    def discounted_price(self) -> Any:
        return self.starting_price.get("discountedPrice", "")

    @property
    def licenses(self) -> str:
        entitlement = self.raw_data.get("entitlement") or {}
        lic_list = entitlement.get("licenses") or []
        return ", ".join(lic.get("name", "") for lic in lic_list if lic.get("name"))

    @property
    def engine_versions_list(self) -> List[str]:
        versions_set = set()
        for fmt in self.asset_formats:
            specs = fmt.get("technicalSpecs") or {}
            versions = specs.get("unrealEngineEngineVersions") or []
            for v in versions:
                clean_v = v.replace("UE_", "")
                versions_set.add(clean_v)
        return list(versions_set)

    @property
    def engine_versions(self) -> str:
        return ", ".join(sorted(self.engine_versions_list))

    @property
    def ue_max(self) -> str:
        evs = self.engine_versions_list
        if not evs:
            return ""
        try:
            sorted_versions = sorted(evs, key=lambda v: tuple(map(int, v.split('.'))))
            return sorted_versions[-1]
        except (ValueError, IndexError):
            return evs[-1]

    @property
    def thumbnails_list(self) -> List[Dict[str, Any]]:
        return self.raw_data.get("listing", {}).get("thumbnails") or []

    @property
    def media_count(self) -> int:
        return len(self.thumbnails_list)

    @property
    def image_count(self) -> int:
        return sum(len(t.get("images") or []) for t in self.thumbnails_list)

    @property
    def thumbnail_url(self) -> str:
        if not self.thumbnails_list:
            return ""
        first_images = self.thumbnails_list[0].get("images") or []
        for img in first_images:
            if img.get("width") == 320:
                return img.get("url", "")
        if first_images:
            return first_images[0].get("url", "")
        return ""

    @property
    def image_urls(self) -> List[str]:
        urls = []
        for th in self.thumbnails_list:
            imgs = th.get("images") or []
            if imgs:
                best_img = max(imgs, key=lambda x: x.get("width", 0))
                if best_img.get("url"):
                    urls.append(best_img.get("url"))
        return urls

    @property
    def can_download(self) -> bool:
        return self.raw_data.get("canRequestDownloadUrl", False)

    @property
    def fab_url(self) -> str:
        uid = self.uid
        if uid:
            return f"https://www.fab.com/listings/{uid}"
        return ""

    @property
    def details_fetched(self) -> bool:
        return self.raw_data.get("details_fetched", False)

    @property
    def details_updated_at(self) -> str:
        return self.raw_data.get("details_updated_at", "")

    @property
    def medias_list(self) -> List[Dict[str, Any]]:
        return self.raw_data.get("listing", {}).get("medias") or []

    @property
    def media_urls(self) -> List[str]:
        urls = []
        for media in self.medias_list:
            url = media.get("mediaUrl", "")
            if url:
                urls.append(url)
        return urls

    @property
    def technical_specs(self) -> str:
        for fmt in self.asset_formats:
            specs = fmt.get("technicalSpecs") or {}
            details_html = specs.get("technicalDetails", "")
            if details_html:
                return details_html
        return ""

    @property
    def has_detail_listing_payload(self) -> bool:
        """True when listing contains fields typically only returned by detail API."""
        listing = self.raw_data.get("listing") or {}
        if not isinstance(listing, dict):
            return False
        return any(key in listing for key in ("description", "medias", "reviewCount", "user"))

    @staticmethod
    def extract_detail_listing(details: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize detail payload shape from Fab API.

        Fab may return either {"listing": {...}} or directly {...}.
        """
        if not isinstance(details, dict):
            return {}
        nested_listing = details.get("listing")
        if isinstance(nested_listing, dict):
            return nested_listing
        return details

    def merge_detail_payload(self, details: Dict[str, Any]) -> bool:
        """Merge a detail API payload into the current raw asset."""
        detail_listing = self.extract_detail_listing(details)
        if not detail_listing:
            return False

        current_listing = self.raw_data.get("listing")
        if not isinstance(current_listing, dict):
            self.raw_data["listing"] = {}
        self.raw_data["listing"].update(detail_listing)

        if isinstance(details.get("listing"), dict):
            for key in ("capabilities", "licenses", "createdAt", "status"):
                if key in details and key not in self.raw_data:
                    self.raw_data[key] = details[key]

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Return the flattened dictionary structure used by the frontend."""
        return {
            "uid": self.uid,
            "title": self.title,
            "seller_name": self.seller_name,
            "seller_id": self.seller_id,
            "seller_avatar_url": self.seller_avatar_url,
            "listing_type": self.listing_type,
            "created_at": self.created_at,
            "last_updated_at": self.last_updated_at,
            "is_mature": self.is_mature,
            "status": self.status,
            "asset_formats": self.asset_format_names,
            "asset_format_codes": self.asset_format_codes,
            "tags": self.tags,
            "description": self.description,
            "average_rating": self.average_rating,
            "price": self.price,
            "currency_code": self.currency_code,
            "discounted_price": self.discounted_price,
            "media_count": self.media_count,
            "image_count": self.image_count,
            "licenses": self.licenses,
            "engine_versions": self.engine_versions,
            "ue_max": self.ue_max,
            "thumbnail_url": self.thumbnail_url,
            "image_urls": self.image_urls,
            "can_download": self.can_download,
            "fab_url": self.fab_url,
            "details_fetched": self.details_fetched,
            "details_updated_at": self.details_updated_at,
            "technical_specs": self.technical_specs,
            "media_urls": self.media_urls,
            "review_count": self.review_count,
        }
