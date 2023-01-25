from bs4 import BeautifulSoup
import requests


def extract_page_title(url: str):
    # headers per https://stackoverflow.com/a/62531222
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}

    # FIXME: need to also look at status code
    req = requests.get(url, headers=headers).text
    soup = BeautifulSoup(req, "html.parser")

    if soup.title and soup.title.string not in {"Blocked", "Attention Required! | Cloudflare"}:
        return soup.title.string
    else:
        return None
