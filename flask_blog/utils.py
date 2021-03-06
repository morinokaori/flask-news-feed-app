from datetime import datetime
from typing import Union

import feedparser
from flask import flash

from flask_blog import db
from flask_blog.models import Entry, WebSite

feedMaxCount = 3


def get_feed_of_month(website: WebSite) -> Union[list, None]:
    """feedから現在月のデータを取得、entry listを返す

    Args:
        website (WebSite): [description]

    Returns:
        Union[list,None]: [description]
    """
    f = feedparser.parse(website.feedurl)
    # 最新データが取得済データと同じ場合空を返す
    # if f.feed.get("updated_parsed", None) is None:
    #     return None, None
    if (website.updated_at == time_to_datetime(f.entries[0]["published_parsed"]) and not Entry.query.filter_by(sitename=website.name).first()):
        return None, None
    entries = []
    month = None
    for n, feedentry in enumerate(f.entries):
        if n == 0:
            month = feedentry["published_parsed"].tm_mon
        else:
            if feedentry["published_parsed"].tm_mon != month:
                break
        entry = Entry(feedentry.title, feedentry.link, website.id, datetime(*feedentry["published_parsed"][:6]))
        if not Entry.query.filter(Entry.title == feedentry.title, Entry.website.name == website.name).first():
            return None, None
        entries.append(entry)
    dt = time_to_datetime(f.entries[0]["published_parsed"])
    return entries, dt


def create_entries(website: WebSite, flash_enabled=True) -> None:
    entries, dt = get_feed_of_month(website)
    if not entries:
        return
    try:
        db.session.add_all(entries)
        website.updated_at = dt
        db.session.add(website)
        db.session.commit()
        if flash_enabled:
            flash(f"{website.nme}の記事が{len(entries)}件追加されました")
    except Exception:
        # db.session.close()
        pass
    else:
        if flash_enabled:
            flash(f"{website.name}の記事は追加されませんでした")
        # db.session.close()


def get_feed(website: WebSite) -> list:
    """feedから最新データを取得、entry listを返す

    Args:
        website (WebSite): [description]

    Returns:
        list: [description]
    """
    f = feedparser.parse(website.feedurl)
    # 最新データが取得済データと同じ場合空を返す
    if f.feed.get("updated_parsed", None) == None:
        return []
    if (
        website.updated_at == time_to_datetime(f.feed.updated_parsed)
        and Entry.query.filter_by(sitename=website.name).first() is not None
    ):
        return []
    entries = []
    for n, entry in enumerate(f.entries):
        if n > feedMaxCount:
            break
        entries.append(
            Entry(entry.title, entry.link, website.name, str_to_datetime(entry.updated))
        )
    return entries


def get_feedurl(url: str) -> Union[str, None]:
    """urlからfeedurlを検索して返す
    ※url, feedurlにアクセスする

    Args:
        url (str): siteurl
    Returns:
        str: feedurl
    """
    import re
    import requests
    from bs4 import BeautifulSoup
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    hrefs = {link["href"] for link in soup.find_all("link") if link.has_attr('title') and re.compile("(RSS|Atom)", re.IGNORECASE).search(link["title"])}
    if not hrefs:
        return None
    for href in hrefs:
        r = requests.get(href)
        if 'application/rss+xml' in r.headers['Content-Type']:
            return href
    return


def time_to_datetime(time):
    t = time
    return datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)


def str_to_datetime(strtime: str) -> datetime:
    """文字列時刻をdatetimeに変換
    Fri, 08 Jan 2021 11:00:00 +0900

    Args:
        strtime (str): [description]

    Returns:
        datetime: [description]
    """
    import re

    try:
        dt = datetime.strptime(strtime, "%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        day, time, _ = re.split("[T|+]", strtime)
        year, mon, mday = map(int, day.split("-"))
        hour, min, sec = map(int, time.split(":"))
        dt = datetime(year, mon, mday, hour, min, sec)
    return dt


def get_day_of_week(dt: datetime) -> datetime:
    w_list = ["月", "火", "水", "木", "金", "土", "日"]
    return w_list[dt.weekday()]


def datetime_to_str(dt: datetime) -> datetime:
    return r"{}/{}/{}({}) {}:{}".format(
        dt.year, dt.month, dt.day, get_day_of_week(dt), dt.hour, dt.minute
    )
