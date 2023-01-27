from dataclasses import dataclass
import datetime
import logging
from typing import Optional

from yt_dlp import YoutubeDL, utils


logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    extractor: Optional[str]
    id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    upload_date: Optional[str]
    uploader: Optional[str]
    duration: Optional[int]


def try_get_metadata(url):
    try:
        with YoutubeDL({}) as ydl:
            res = ydl.extract_info(url, download=False, process=False)
    except utils.DownloadError:
        return None

    if res["extractor"] in {"generic",                  # unreliable
                            "youtube:search_url"        # uninteresting
                            }:
        return None

    attrs = {k: res.get(k, None) for k in ["extractor",
                                           "id",
                                           "title",
                                           "description",
                                           "upload_date",
                                           "uploader",
                                           "duration"]}

    return VideoMetadata(**attrs)