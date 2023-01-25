## Sheetkeeper -- automated Google Sheets maintenance

### API providers

- **Chosen: [sheet.best](https://sheet.best/#pricing)**
  - 1 connection (= limited to 1 file, but unlimited sheets), 100 reqs/mo
  - no auth on free plan -- only URL secrecy
  - note just scanning 1 sheet will be up to 31 reqs/mo + 1 req per each row filled in

- [APISpreadsheets](https://apispreadsheets.com/)
  - 3 sheets (across unlimited files) x 1500 rows, 250 reqs/mo
  - no auth on free plan -- only URL secrecy
  - feels a little sketchy
  - requires sheet to have title row to be useful
  - update API is crap (1 row at a time? not clear)

- [SheetDB](https://sheetdb.io/pricing)
  - 2 APIs (= limited to 2 sheets), 500 reqs/mo
  - actually maybe limited to 2 _files_?
  - obsessed with key-value approach
    - requires title row
    - skips empty rows & doesn't expose row number
  - _useless_: PATCH endpoint doesn't work if value is an URL

- [Sheety](https://sheety.co/pricing)
  - totally useless (100 rows/sheet), 200 reqs/mo

- [Sheetsu](https://sheetsu.com/pricing)
  - totally useless

- Google Sheets official API
  - free and unlimited, but needs periodic manual re-authentication (?)


### Configuration

Environment variables:

- `SHEETKEEPER_INPUTS` (format: `url1;sheet1;sheet2;sheet3;;url2;sheet1`; URLs must be [sheet.best Connection URLs](https://sheetbestdocs.netlify.app/#generating-your-rest-api))

S3 options (used for backup of sheet contents):

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `SHEETKEEPER_BUCKET`
- `SHEETKEEPER_S3_ENDPOINT`


### Dependencies

- boto3
- bs4
- requests
