#!/usr/bin/env python3

from base64 import b64decode
from datetime import datetime
import gzip
import json
import logging
import os

import boto3
import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build

from extract_page_title import extract_page_title
import ytdl


BUCKET_NAME = os.environ["SHEETKEEPER_BUCKET"]
S3_ENDPOINT = os.environ["SHEETKEEPER_S3_ENDPOINT"]
RUN_TIMESTAMP = datetime.now().isoformat().replace(":", "-")


logger = logging.getLogger(__name__)


def get_sheets_service():
    logging.info("Constructing Google Sheets service")

    account_info = json.loads(b64decode(os.environ["SHEETKEEPER_CREDENTIALS"]))
    creds = service_account.Credentials.from_service_account_info(account_info)

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    logging.info("Returning Google Sheets service")
    return sheet


def backup_to_s3(bucket, filename, text):
    s3 = boto3.resource("s3", endpoint_url=S3_ENDPOINT, use_ssl=True)

    obj = s3.Object(bucket, filename)
    obj.put(Body=gzip.compress(text.encode()), StorageClass="ONEZONE_IA")


def put_cell(spreadsheets, spreadsheet_id, sheet_prefix, row_number, column, value):
    body = {
        'values': [[value]]
    }

    result = spreadsheets.values().update(
        spreadsheetId=spreadsheet_id,
        range=sheet_prefix + column + str(1+row_number),
        valueInputOption="RAW",
        body=body
        ).execute()


def autofill_titles(spreadsheets, spreadsheet_id: str, sheet_prefix: str, url_column: str, note_column: str):
    assert len(url_column) == 1
    assert len(note_column) == 1

    assert ord(note_column) == ord(url_column) + 1

    logging.info("Fetch sheet %s -> %s", spreadsheet_id, sheet_prefix)
    result = spreadsheets.values().get(spreadsheetId=spreadsheet_id, range=sheet_prefix + url_column + ":" + note_column).execute()
    values = result.get('values', [])

    backup_to_s3(bucket=BUCKET_NAME,
                 filename=f"{RUN_TIMESTAMP}-{sheet_prefix[:-1]}.json.gz",
                 text=json.dumps(values))

    logger.info(f"{sheet_prefix} {len(values)} rows x {len(values[0])} cols")

    for row_number, row in enumerate(values):
        if len(row) >= 1:
            url = row[0]

            if url and (url.startswith("http://") or url.startswith("https://")) and (len(row) < 2 or not row[1].strip()):
                logger.info(f"{url_column}{1 + row_number}: no comment for URL {url}; fetching")

                try:
                    title = None

                    metadata = ytdl.try_get_metadata(url)
                    if metadata is not None:
                        logger.info(f"    => {metadata}")

                        title = metadata.title

                    if title is None:
                        title = extract_page_title(url)
                        logger.info(f"    => {title}")

                    if title is not None:
                        title = title.removesuffix(" - YouTube")

                        # save it
                        put_cell(spreadsheets,
                                 spreadsheet_id,
                                 sheet_prefix,
                                 row_number,
                                 note_column,
                                 title)
                except requests.exceptions.ConnectionError as e:
                    logger.exception("Failed to fetch video title")


def main():
    logging.basicConfig(level=logging.INFO)

    spreadsheets = get_sheets_service()

    # SHEETKEEPER_SHEETS="id1:sheet1:sheet2:sheet3::id2:sheet1"
    for id_and_sheets in os.environ["SHEETKEEPER_SHEETS"].split("::"):
        id_, *sheets = id_and_sheets.split(":")

        for sheet in sheets:
            autofill_titles(spreadsheets, id_, sheet + "!", "A", "B")


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
