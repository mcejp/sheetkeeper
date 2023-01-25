from datetime import datetime
import gzip
import json
import logging
import os
import sys
from urllib.parse import quote_plus, urlencode

import boto3
import requests

from extract_page_title import extract_page_title


BUCKET_NAME = os.environ["SHEETKEEPER_BUCKET"]
S3_ENDPOINT = os.environ["SHEETKEEPER_S3_ENDPOINT"]
RUN_TIMESTAMP = datetime.now().isoformat().replace(":", "-")

logger = logging.getLogger(__name__)


class SheetBest:
    def __init__(self, url, sheet=None):
        self._url = url
        self._sheet = sheet

        if sheet is not None:
            self._url += f"/tabs/{sheet}"

    def get(self):
        r = requests.get(self._url)
        r.raise_for_status()
        return r.json()

    def update(self, row_id, values) -> None:
        r = requests.patch(f"{self._url}/{row_id}", json=values)
        logging.debug("update -> reply %s", r.json())
        r.raise_for_status()


def backup_to_s3(bucket, filename, text):
    s3 = boto3.resource("s3", endpoint_url=S3_ENDPOINT, use_ssl=True)

    obj = s3.Object(bucket, filename)
    obj.put(Body=gzip.compress(text.encode()), StorageClass="ONEZONE_IA")


def autofill_titles(sheet, url_column: str, title_column: str):
    logger.info("Fetching %s", sheet._url)
    values = sheet.get()
    logger.info("Backing up to S3")
    backup_to_s3(bucket=BUCKET_NAME,
                 filename=f"{RUN_TIMESTAMP}-{sheet._sheet}.json.gz",
                 text=json.dumps(values))
    # sys.exit()
    logger.info(f"{len(values)} rows x {len(values[0])} cols")

    for row_number, row in enumerate(values):
        if len(row) >= 1:
            url = row[url_column]

            def is_empty(maybe_str):
                return maybe_str is None or not maybe_str.strip()

            if url and (url.startswith("http://") or url.startswith("https://")) and is_empty(row[title_column]):
                logger.info(f"Row {2 + row_number}: no comment for URL {url}; fetching")
                try:
                    title = extract_page_title(url)
                    logger.info(f"    => {repr(title)}")

                    if title:
                        # sys.exit()
                        title = title.removesuffix(" - YouTube")

                        # save it
                        sheet.update(row_number, {"Title": title})
                        # sys.exit()
                except requests.exceptions.ConnectionError as e:
                    logger.exception(e)



def main():
    logging.basicConfig(level=logging.INFO)

    # SHEETKEEPER_INPUTS="url1;sheet1;sheet2;sheet3;;url2;sheet1"
    for url_and_sheets in os.environ["SHEETKEEPER_INPUTS"].split(";;"):
        url, *sheets = url_and_sheets.split(";")

        for sheet in sheets:
            autofill_titles(SheetBest(url, sheet), "URL", "Title")


def handle(event, context):
    try:
        main()
        return {"body": "OK", "statusCode": 200}
    except Exception:
        logger.exception("Something went wrong")

        import traceback
        return {"body": traceback.format_exc(), "statusCode": 500}


if __name__ == '__main__':
    main()
