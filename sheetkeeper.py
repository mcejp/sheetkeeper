#!/usr/bin/env python3

from base64 import b64decode
from datetime import datetime, timedelta
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


def autofill_titles(spreadsheets, spreadsheet_id: str, sheet_prefix: str, url_column: str, duration_column: str, date_column: str, note_column: str):
    assert len(url_column) == 1
    assert len(note_column) == 1
    assert len(duration_column) == 1
    assert len(date_column) == 1

    assert ord(duration_column) == ord(url_column) + 1
    assert ord(date_column) == ord(duration_column) + 1
    assert ord(note_column) == ord(date_column) + 1

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

            have_duration = len(row) >= 2 and row[1].strip()
            have_date = len(row) >= 3 and row[2].strip()
            have_title = len(row) >= 4 and row[3].strip()

            if url and (url.startswith("http://") or url.startswith("https://")) and (not have_title or not have_duration or not have_date):
                logger.info(f"{url_column}{1 + row_number}: incomplete entry for URL {url}; fetching")

                try:
                    title = None
                    duration = None
                    date = None

                    if url.startswith("https://archive.org/"):
                        # work around yt-dlp bug
                        metadata = None
                    else:
                        metadata = ytdl.try_get_metadata(url)

                    if metadata is not None:
                        logger.info(f"    => {metadata}")

                        title = metadata.title
                        if metadata.duration is not None:
                            duration = timedelta(seconds=metadata.duration)
                        if metadata.upload_date is not None:
                            date = datetime.strptime(metadata.upload_date, '%Y%m%d')

                    if title is None:
                        title = extract_page_title(url)
                        logger.info(f"    => {title}")

                    if not have_title and title is not None:
                        title = title.removesuffix(" - YouTube")

                        # save it
                        put_cell(spreadsheets,
                                 spreadsheet_id,
                                 sheet_prefix,
                                 row_number,
                                 note_column,
                                 title)

                    if not have_duration and duration is not None:
                        # save it
                        put_cell(spreadsheets,
                                 spreadsheet_id,
                                 sheet_prefix,
                                 row_number,
                                 duration_column,
                                 str(duration))

                    if not have_date and date is not None:
                        # save it
                        put_cell(spreadsheets,
                                 spreadsheet_id,
                                 sheet_prefix,
                                 row_number,
                                 date_column,
                                 date.strftime("%Y-%m-%d"))
                except requests.exceptions.ConnectionError as e:
                    logger.exception("Failed to fetch video title")


def main():
    logging.basicConfig(level=logging.INFO)

    spreadsheets = get_sheets_service()

    # SHEETKEEPER_SHEETS="id1:sheet1:sheet2:sheet3::id2:sheet1"
    for id_and_sheets in os.environ["SHEETKEEPER_SHEETS"].split("::"):
        id_, *sheets = id_and_sheets.split(":")

        for sheet in sheets:
            autofill_titles(spreadsheets, id_, sheet + "!", url_column="A", duration_column="B", date_column="C", note_column="D")


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
