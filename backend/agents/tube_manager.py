"""YouTube upload monitor. Reads channel URLs and YouTube RSS feeds only."""
import datetime
import html.parser
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from agents import register
from core import store

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
CHANNELS_FILE = DATA / "channels.txt"
FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
ATOM = "{http://www.w3.org/2005/Atom}"
VIDEO = "{http://www.youtube.com/xml/schemas/2015}"
USER_AGENT = "ASGROUP-Command/1.0 (+YouTube RSS monitor)"


class _ChannelIdParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.channel_id = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs = dict(attrs)
            if attrs.get("itemprop") == "channelId":
                self.channel_id = attrs.get("content")


def _channel_id(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in (
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "music.youtube.com"):
        raise ValueError("expected a YouTube channel URL")
    match = re.match(r"^/channel/(UC[\w-]{22})", parsed.path)
    if match:
        return match.group(1)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        parser = _ChannelIdParser()
        parser.feed(response.read(1_000_000).decode("utf-8", errors="replace"))
    if not parser.channel_id or not re.fullmatch(r"UC[\w-]{22}", parser.channel_id):
        raise ValueError("could not resolve channel ID from page")
    return parser.channel_id


def _feed(channel_id):
    request = urllib.request.Request(
        FEED_URL.format(channel_id), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())
    entries = []
    for entry in root.findall(f"{ATOM}entry"):
        published = entry.findtext(f"{ATOM}published")
        if not published:
            continue
        timestamp = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
        title = entry.findtext(f"{ATOM}title") or "(untitled)"
        entries.append((timestamp, title))
    return sorted(entries, reverse=True)


@register("tube_manager", interval=21600)
def tube_manager(ctx):
    if not CHANNELS_FILE.exists():
        DATA.mkdir(parents=True, exist_ok=True)
        CHANNELS_FILE.write_text(
            "# One YouTube channel URL per line (channel, handle, or custom URL)\n",
            encoding="utf-8")
        return "no channels configured; add URLs to data/channels.txt"

    urls = [line.strip() for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]
    if not urls:
        return "no channels configured; add URLs to data/channels.txt"

    now = datetime.datetime.now(datetime.timezone.utc)
    recent_cutoff = now - datetime.timedelta(days=7)
    inactive_cutoff = now - datetime.timedelta(days=14)
    summaries = []
    pending = store.get_approvals("pending")
    for url in urls:
        label = url
        try:
            channel_id = _channel_id(url)
            entries = _feed(channel_id)
            recent = [entry for entry in entries if entry[0] >= recent_cutoff]
            latest = entries[0] if entries else None
            label = url.rstrip("/").split("/")[-1] or channel_id
            if recent:
                titles = "; ".join(entry[1] for entry in recent[:3])
                summaries.append(f"{label}: {len(recent)} new in 7d ({titles})")
            elif latest:
                summaries.append(f"{label}: no new videos in 7d; latest {latest[0].date().isoformat()}")
            else:
                summaries.append(f"{label}: feed has no uploads")
            if latest is None or latest[0] < inactive_cutoff:
                title = f"Channel may be dead: {label}"
                if not any(item["agent"] == "tube_manager" and item["title"] == title
                           for item in pending):
                    detail = (f"No uploads in the last 14 days for {url}.\n"
                              + (f"Latest upload: {latest[0].isoformat()} - {latest[1]}"
                                 if latest else "The channel feed contains no uploads."))
                    ctx.queue_approval(title, detail)
        except Exception as exc:
            summaries.append(f"{label}: check failed ({type(exc).__name__})")
            ctx.log(f"could not check {url}: {type(exc).__name__}: {exc}", kind="warn")

    ctx.log("YouTube channel check: " + " | ".join(summaries))
    return f"checked {len(urls)} channel(s): " + " | ".join(summaries)
