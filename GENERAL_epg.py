#!/usr/bin/env python3
"""
GENERAL_epg.py - our own guide for the Continuum general channels (Entertainment, News, Documentary, Movies, Music,
Shopping), so PlaylistLabs needs only OUR guides (31 Oct 2026, user's request: no external EPG sources).

What it does: downloads the epgshare01 country files (UK1, US2, CA2, PLEX1, DK1) - the same files SPORT_epg.py already
reads - keeps only the channels listed in CHANNELS, and writes them into ONE file, GENERAL_epg.xml.gz, under the
playlist's OWN tvg-ids (the ids already on the rows, e.g. bbcnews.uk, amc.us), with the playlist's channel name as the first
display-name. So the rows keep their ids; in PlaylistLabs just select the source "..General EPG" (our file) for them.

  CHANNELS      (our id = the row's tvg-id, playlist name, group, epgshare file, epgshare id)
  PLACEHOLDERS  channels no source has (CMT Music, Kiss, Magic ...): 2-hour blocks naming the channel for 24 h, like the
                other guides' empty channels, so the row isn't blank. They are replaced by real listings once one is added.
  Not here: the 15 rows already on our own guide ids (UK.BBCTwo, UK.Channel4/5, UK.BBCFour, UK.ITV4, IE.RTEOne/RTE2,
  IE.VirginMedia*, US.TBS/TNT/TLC/USANetwork) and the 7 Sky Cinema channels (UK.SkyCinema* in SPORT_epg.py).

Safeguard: if a source file can't be downloaded in a run, the channels it feeds are kept from the previous GENERAL_epg.xml.gz
(programmes not yet finished), like SPORT_epg.py's carry-over.

Usage:
    python3 GENERAL_epg.py                  # download the files, write GENERAL_epg.xml.gz
    python3 GENERAL_epg.py --local DIR      # read DIR/epg_ripper_<FILE>.xml.gz instead of downloading (testing)
"""

import argparse
import gzip
import html
import io
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

OUTPUT = "GENERAL_epg.xml.gz"
EPGSHARE_URL = "{scheme}://epgshare01.online/epgshare01/epg_ripper_{file}.xml.gz"
UA = "Mozilla/5.0 (GENERAL_epg.py)"
KEEP_PAST = timedelta(hours=3)        # programmes that ended longer ago than this are dropped
DAYS_AHEAD = 8                        # nothing further ahead than this (epgshare lists about 4 days anyway)
PLACEHOLDER_HOURS = 24                # like the events guide: PlaylistLabs keeps what it loads, so keep it short
PLACEHOLDER_SUB = "No schedule available"
PLACEHOLDER_DESC = ("{name}: no programmes are listed for this channel at the moment. The schedule will appear here "
                    "when a source for it is added.")
MAX_DESC = 350

# our id (the row's tvg-id), playlist name, group, epgshare file, epgshare id
CHANNELS = [
    ('animalplanet.uk', 'Animal Planet', 'Documentary', 'UK1', 'Animal.Planet.uk'),
    ('BBC.Earth.ca2', 'BBC Earth', 'Documentary', 'CA2', 'BBC.Earth.ca2'),
    ('courttv.uk', 'Court TV', 'Documentary', 'UK1', 'Court.TV.uk'),
    ('crime&investigation.uk', 'Crime Investigation', 'Documentary', 'UK1', 'Crime+Inv.HD.uk'),
    ('discovery.uk', 'Discovery', 'Documentary', 'UK1', 'Discovery.HD.uk'),
    ('discoveryscience.uk', 'Discovery Science', 'Documentary', 'UK1', 'Disc.Science.uk'),
    ('discoveryturbo.uk', 'Discovery Turbo', 'Documentary', 'UK1', 'Disc.Turbo.uk'),
    ('earthxtv.uk', 'EarthX TV', 'Documentary', 'UK1', 'EarthxTV.HD.uk'),
    ('foodnetwork.uk', 'Food Network', 'Documentary', 'UK1', 'Food.Network.uk'),
    ('skyhistory.uk', 'History', 'Documentary', 'UK1', 'Sky.HistoryHD.uk'),
    ('skyhistory2hd.uk', 'History 2', 'Documentary', 'UK1', 'SkyHistory2HD.uk'),
    ('investigationdiscovery.uk', 'ID', 'Documentary', 'UK1', 'ID.uk'),
    ('natgeowild.uk', 'Nat Geo Wild', 'Documentary', 'UK1', 'NatGeoWild.HD.uk'),
    ('nationalgeographic.uk', 'National Geographic', 'Documentary', 'UK1', 'Nat.Geo.HD.uk'),
    ('skyarts.uk', 'Sky Arts', 'Documentary', 'UK1', 'Sky.Arts.HD.uk'),
    ('skycrime.uk', 'Sky Crime', 'Documentary', 'UK1', 'Sky.Crime.HD.uk'),
    ('skydocumentaries.uk', 'Sky Documentaries', 'Documentary', 'UK1', 'Sky.Documentaries.HD.uk'),
    ('skynature.uk', 'Sky Nature', 'Documentary', 'UK1', 'Sky.Nature.HD.uk'),
    ('truecrime.uk', 'True Crime', 'Documentary', 'UK1', 'True.Crime.uk'),
    ('yesterday.uk', 'Yesterday', 'Documentary', 'UK1', 'U.and.YESTERDAY.uk'),
    ('4seven.uk', '4Seven', 'Entertainment', 'UK1', '4seven.uk'),
    ('5usa.uk', '5 USA', 'Entertainment', 'UK1', '5.USA.uk'),
    ('5actionie.ie', '5Action', 'Entertainment', 'UK1', '5ACTION.uk'),
    ('5star.uk', '5Star', 'Entertainment', 'UK1', '5STAR.uk'),
    ('a&e.us', 'A&E', 'Entertainment', 'US2', 'A.and.E.HD.East.us2'),
    ('u&alibi.ie', 'Alibi', 'Entertainment', 'UK1', 'U.and.alibi.HD.uk'),
    ('amc.us', 'AMC', 'Entertainment', 'US2', 'AMC.HD.us2'),
    ('amcplus.us', 'AMC +', 'Entertainment', 'US2', 'AMC+.us2'),
    ('antennatv.us', 'Antenna TV', 'Entertainment', 'US2', 'Antenna.TV.us2'),
    ('awe.us', 'AWE', 'Entertainment', 'US2', 'AWE.A.Wealth.of.Entertainment.HD.us2'),
    ('axstv.us', 'AXS TV', 'Entertainment', 'US2', 'AXS.TV.us2'),
    ('bbcamerica.us', 'BBC America', 'Entertainment', 'US2', 'BBC.America.HD.us2'),
    ('bbconeeast.uk', 'BBC One East', 'Entertainment', 'UK1', 'BBC.One.EastHD.uk'),
    ('blaze.uk', 'Blaze', 'Entertainment', 'UK1', 'BLAZE.uk'),
    ('bouncetv.us', 'Bounce TV', 'Entertainment', 'US2', 'Bounce.TV.us2'),
    ('bouncexl.us', 'Bounce XL', 'Entertainment', 'PLEX1', 'plex.tv.Bounce.XL.plex'),
    ('bravo.us', 'Bravo', 'Entertainment', 'US2', 'Bravo.HD.us2'),
    ('buzzr.us', 'Buzzr', 'Entertainment', 'US2', 'BUZZR.Stream.us2'),
    ('challenge.uk', 'Challenge', 'Entertainment', 'UK1', 'Challenge.uk'),
    ('charge!.us', 'Charge!', 'Entertainment', 'US2', 'CHARGE!.us2'),
    ('cleotv.us', 'Cleo TV', 'Entertainment', 'US2', 'Cleo.TV.HD.us2'),
    ('cmt.us', 'CMT', 'Entertainment', 'US2', 'CMT.HD.us2'),
    ('comedycentral.uk', 'Comedy Central', 'Entertainment', 'UK1', 'ComedyCentral.uk'),
    ('comedytv.us', 'Comedy TV', 'Entertainment', 'US2', 'Comedy.TV.HD.us2'),
    ('comet.us', 'Comet', 'Entertainment', 'US2', 'Comet.us2'),
    ('dave.uk', 'Dave', 'Entertainment', 'UK1', 'U.and.Dave.HD.uk'),
    ('daystar.uk', 'Daystar', 'Entertainment', 'UK1', 'DAYSTAR.HD.uk'),
    ('dmax.uk', 'DMAX', 'Entertainment', 'UK1', 'DMAX.uk'),
    ('drama.uk', 'Drama', 'Entertainment', 'UK1', 'U.and.Drama.uk'),
    ('e4.uk', 'E4', 'Entertainment', 'UK1', 'E4.HD.uk'),
    ('e4extra.uk', 'E4 Extra', 'Entertainment', 'UK1', 'E4.Extra.uk'),
    ('eden.uk', 'eden', 'Entertainment', 'UK1', 'U.and.Eden.uk'),
    ('freeform.us', 'Freeform', 'Entertainment', 'US2', 'Freeform.HD.us2'),
    ('fx.us', 'FX', 'Entertainment', 'US2', 'FX.HD.us2'),
    ('fxx.us', 'FXX', 'Entertainment', 'US2', 'FXX.HD.us2'),
    ('fyi.us', 'FYI', 'Entertainment', 'US2', 'FYI.Channel.HD.us2'),
    ('gold.uk', 'Gold', 'Entertainment', 'UK1', 'U.and.GOLD.HD.uk'),
    ('great!tv.uk', 'Great! TV', 'Entertainment', 'UK1', 'GREAT!.tv.uk'),
    ('gsn.us', 'GSN', 'Entertainment', 'US2', 'Game.Show.Network.HD.us2'),
    ('hgtv.uk', 'HGTV', 'Entertainment', 'UK1', 'HGTV.uk'),
    ('itv2.uk', 'ITV 2', 'Entertainment', 'UK1', 'ITV2.HD.uk'),
    ('itv3.uk', 'ITV 3', 'Entertainment', 'UK1', 'ITV3.HD.uk'),
    ('itvanglia.uk', 'ITV Anglia', 'Entertainment', 'UK1', 'ITV1.HD.uk'),
    ('legend.uk', 'Legend', 'Entertainment', 'UK1', 'Legend.uk'),
    ('legendxtra.uk', 'Legend Xtra', 'Entertainment', 'UK1', 'Legend.Xtra.uk'),
    ('lifetime.us', 'Lifetime', 'Entertainment', 'US2', 'Lifetime.HD.us2'),
    ('magnolianetwork.us', 'Magnolia Network', 'Entertainment', 'US2', 'Magnolia.Network.HD.us2'),
    ('more4.uk', 'More 4', 'Entertainment', 'UK1', 'More4.HD.uk'),
    ('oxygen.us', 'Oxygen', 'Entertainment', 'US2', 'Oxygen.True.Crime.HD.us2'),
    ('paramountnetwork.us', 'Paramount', 'Entertainment', 'US2', 'Paramount.Network.HD.us2'),
    ('quest.uk', 'Quest', 'Entertainment', 'UK1', 'QUEST.HD.uk'),
    ('questred.uk', 'Quest Red', 'Entertainment', 'UK1', 'Quest.Red.uk'),
    ('really.uk', 'Really', 'Entertainment', 'UK1', 'Really.uk'),
    ('retrotv.us', 'Retro TV', 'Entertainment', 'US2', 'RETRO.us2'),
    ('skyatlantic.uk', 'Sky Atlantic', 'Entertainment', 'UK1', 'Sky.Atlantic.HD.uk'),
    ('skyone.uk', 'Sky One', 'Entertainment', 'UK1', 'Sky.One.HD.uk'),
    ('skyscifi.uk', 'Sky Sci-fi', 'Entertainment', 'UK1', 'Sky.Sci-Fi.HD.uk'),
    ('skywitness.uk', 'Sky Witness', 'Entertainment', 'UK1', 'Sky.Witness.HD.uk'),
    ('sundancetv.us', 'Sundance', 'Entertainment', 'US2', 'SundanceTV.HD.us2'),
    ('syfy.us', 'SYFY', 'Entertainment', 'US2', 'Syfy.HD.us2'),
    ('talkingpictures.uk', 'Talking Pictures', 'Entertainment', 'UK1', 'TalkingPictures.uk'),
    ("that'stv.uk", "That's TV", 'Entertainment', 'UK1', 'Thats.TV.uk'),
    ('together.uk', 'Together', 'Entertainment', 'UK1', 'Together.uk'),
    ('u&w.uk', 'U&W', 'Entertainment', 'UK1', 'U.and.W.HD.uk'),
    ('vice.us', 'Vice', 'Entertainment', 'US2', 'Vice.HD.us2'),
    ('film4.uk', 'Film4', 'Movies', 'UK1', 'Film4.HD.uk'),
    ('fxm.us', 'FXM', 'Movies', 'US2', 'FX.Movie.Channel.HD.us2'),
    ('greatamericanfamily.us', 'Great American Family', 'Movies', 'US2', 'Great.American.Family.HD.us2'),
    ('great!action.uk', 'Great! Action', 'Movies', 'UK1', 'GREAT!.action.uk'),
    ('greatmovies.uk', 'Great! Movies', 'Movies', 'UK1', 'GREAT!.movies.uk'),
    ('hallmark.us', 'Hallmark', 'Movies', 'US2', 'Hallmark.Channel.HD.us2'),
    ('hallmarkfamily.us', 'Hallmark Family', 'Movies', 'US2', 'Hallmark.Family.us2'),
    ('hallmarkmystery.us', 'Hallmark Mystery', 'Movies', 'US2', 'Hallmark.Mystery.HD.us2'),
    ('skycinemacomedy.uk', 'Sky Cinema Comedy', 'Movies', 'UK1', 'Sky.Cinema.Comedy.uk'),
    ('skycinemahits.uk', 'Sky Cinema Hits', 'Movies', 'UK1', 'Sky.Cinema.Hits.HD.uk'),
    ('skycinemaselect.uk', 'Sky Cinema Select', 'Movies', 'UK1', 'Sky.Cinema.Select.uk'),
    ('tcm.us', 'TCM', 'Movies', 'US2', 'Turner.Classic.Movies.HD.us2'),
    ('dummy-104908', 'Box Hits', 'Music', 'UK1', 'Box.Hits.uk'),
    ('dummy-104912', 'Clubland TV', 'Music', 'UK1', 'Clubland.TV.uk'),
    ('dummy-53777', 'Fuse Music', 'Music', 'US2', 'Fuse.HD.us2'),
    ('mtv.us', 'MTV', 'Music', 'US2', 'MTV.-.Music.Television.HD.us2'),
    ('mtv90s.uk', "MTV 90's", 'Music', 'DK1', 'MTV.90s.dk'),
    ('mtvclassic.us', 'MTV Classic', 'Music', 'US2', 'MTV.Classic.us2'),
    ('MTV.Hits.dk', 'MTV Hits', 'Music', 'DK1', 'MTV.Hits.dk'),
    ('mtvlive.us', 'MTV Live', 'Music', 'US2', 'MTVLIVE.us2'),
    ("NOW.70's.es", "NOW 70's", 'Music', 'UK1', 'NOW.70s.uk'),
    ("NOW.80's.es", "NOW 80's", 'Music', 'UK1', 'NOW.80s.uk'),
    ('dummy-104971', "NOW 90's", 'Music', 'UK1', 'NOW.90s.uk'),
    ('stingrayclassicmasters.ca', 'Stingray: Classic Masters', 'Music', 'CA2', 'Stingray.Classic.Masters.ca2'),
    ('stingrayclassicrock.ca', 'Stingray: Classic Rock', 'Music', 'CA2', 'Stingray.Classic.Rock.ca2'),
    ('stingrayeasylistening.ca', 'Stingray: Easy Listening', 'Music', 'CA2', 'Stingray.Easy.Listening.ca2'),
    ('stingrayflashback70s.ca', "Stingray: Flashback 70's", 'Music', 'CA2', 'Stingray.Flashback.’70s.ca2'),
    ('stingrayfrancocountry.ca', 'Stingray: Franco Country', 'Music', 'CA2', 'Stingray.Franco.Country.ca2'),
    ('stingrayfrancoretro.ca', 'Stingray: Franco Retro', 'Music', 'CA2', 'Stingray.Franco.Retro.ca2'),
    ('stingrayhiphoprandb.ca', 'Stingray: Hip-Hop / R&B', 'Music', 'CA2', 'Stingray.Hip-Hop/R&B.ca2'),
    ('stingrayhitlist.ca', 'Stingray: Hit List', 'Music', 'CA2', 'Stingray.Hit.List.ca2'),
    ('stingrayhits.ca', 'Stingray: Hits', 'Music', 'CA2', 'Stingray.Hits!.ca2'),
    ('stingraylepalmarès.ca', 'Stingray: Le Palmarés', 'Music', 'CA2', 'Stingray.Le.Palmarès.ca2'),
    ('stingrayloud.ca', 'Stingray: Loud', 'Music', 'CA2', 'Stingray.LOUD.ca2'),
    ('stingraynature.ca', 'Stingray: Nature', 'Music', 'CA2', 'Stingray.Nature.ca2'),
    ('stingraynostalgie.ca', 'Stingray: Nostalgie', 'Music', 'CA2', 'Stingray.Nostalgie.ca2'),
    ('stingraynothinbut90s.ca', "Stingray: Nothin' but 90's", 'Music', 'CA2', 'Stingray.Nothin’.but.’90s.ca2'),
    ('qelloconcertsbystingray.ca', 'Stingray: Qello Concerts', 'Music', 'PLEX1', 'plex.tv.Qello.Concerts.plex'),
    ('stingrayrememberthe80s.ca', "Stingray: Remember the 80's", 'Music', 'CA2', 'Stingray.Remember.the.’80s.ca2'),
    ('stingrayretro.ca', 'Stingray: Retro', 'Music', 'CA2', 'Stingray.RETRO.HD.ca2'),
    ('stingraysmoothjazz.ca', 'Stingray: Smooth Jazz', 'Music', 'CA2', 'Stingray.Smooth.Jazz.ca2'),
    ('Stingray.The.Blues.ca2', 'Stingray: The Blues', 'Music', 'CA2', 'Stingray.The.Blues.ca2'),
    ('Stingray.The.Chill.Lounge.ca2', 'Stingray: The Chill Lounge', 'Music', 'CA2', 'Stingray.The.Chill.Lounge.ca2'),
    ('dummy-105013', 'VEVO 2K', 'Music', 'US2', 'Vevo.2K.us2'),
    ('dummy-105010', "VEVO 70's", 'Music', 'US2', 'Vevo.70s.us2'),
    ('dummy-105011', "VEVO 80's", 'Music', 'US2', 'Vevo.80s.us2'),
    ('dummy-105012', "VEVO 90's", 'Music', 'US2', 'Vevo.90s.us2'),
    ('dummy-105014', 'VEVO Country', 'Music', 'US2', 'Vevo.Country.us2'),
    ('dummy-105015', 'VEVO Hip-Hop', 'Music', 'US2', 'Vevo.Hip-Hop.us2'),
    ('dummy-105016', 'VEVO Latino', 'Music', 'US2', 'Vevo.Latino.us2'),
    ('dummy-105017', 'VEVO Pop', 'Music', 'US2', 'Vevo.Pop.us2'),
    ('vh1.us', 'VH1', 'Music', 'US2', 'VH1.HD.us2'),
    ('bbcnews.uk', 'BBC News', 'News', 'UK1', 'BBC.NEWS.HD.uk'),
    ('bbcparliament.uk', 'BBC Parliament', 'News', 'UK1', 'BBC.Parliament.HD.uk'),
    ('cnbc.us', 'CNBC', 'News', 'US2', 'CNBC.HD.us2'),
    ('cnn.uk', 'CNN', 'News', 'UK1', 'CNN.HD.uk'),
    ('euronews.uk', 'Euronews', 'News', 'UK1', 'Euronews.uk'),
    ('france24.uk', 'France 24', 'News', 'UK1', 'FRANCE.24.HD.uk'),
    ('news.uk', 'GB News', 'News', 'UK1', 'GB.News.HD.uk'),
    ('i24news.uk', 'I24News', 'News', 'US2', 'i24.News.English.us2'),
    ('nbcnewsnow.uk', 'NBC News Now', 'News', 'UK1', 'NBCNewsNowHD.uk'),
    ('skynews.uk', 'Sky News', 'News', 'UK1', 'Sky.News.HD.uk'),
    ('bestdirect.uk', 'Best Direct', 'Shopping', 'UK1', 'Best.Direct.uk'),
    ('gemstv.uk', 'Gems TV', 'Shopping', 'UK1', 'Gems.TV.uk'),
    ('highstreettv1.uk', 'High Street TV 1', 'Shopping', 'UK1', 'High.Street.TV.1.uk'),
    ('highstreettv2.uk', 'High Street TV 2', 'Shopping', 'UK1', 'High.Street.TV.2.uk'),
    ('idealworld.uk', 'Ideal World', 'Shopping', 'UK1', 'Ideal.World.HD.uk'),
    ('qvc.uk', 'QVC', 'Shopping', 'UK1', 'QVC.HD.uk'),
    ('qvcbeauty.uk', 'QVC Beauty', 'Shopping', 'UK1', 'QVC.Beauty.uk'),
    ('qvcextra.uk', 'QVC Extra', 'Shopping', 'UK1', 'QVC.Extra.uk'),
    ('qvcstyle.uk', 'QVC Style', 'Shopping', 'UK1', 'QVC.Style.HD.uk'),
]

# our id, playlist name, group - no source anywhere
PLACEHOLDERS = [
    ('cmtmusic.us', 'CMT Music', 'Entertainment'),
    ('dummy-104913', 'Dance TV', 'Music'),
    ('dummy-104928', 'Kiss', 'Music'),
    ('dummy-104931', 'Magic', 'Music'),
    ('dummy-104979', 'Retro 80', 'Music'),
    ('stingrayclassica.ca', 'Stingray: Classica', 'Music'),
    ('stingraydjazz.ca', 'Stingray: DJazz', 'Music'),
    ('stingrayfestival.ca', 'Stingray: Festival', 'Music'),
    ('stingraynaturescape.ca', 'Stingray: Naturescape', 'Music'),
    ('stingraynow.ca', 'Stingray: Now', 'Music'),
    ('stingrayrock.ca', 'Stingray: Romance Latino', 'Music'),
    ('bbcworldnews.uk', 'BBC World News', 'News'),
    ('talktv.uk', 'Talk TV', 'News'),
]


def canon(text):
    """epgshare ids can show &amp; (or &amp;amp;) - compare them unescaped."""
    return html.unescape(html.unescape(text or ""))


def download(name, local):
    if local:
        path = os.path.join(local, f"epg_ripper_{name}.xml.gz")
        return open(path, "rb").read() if os.path.exists(path) else None
    for scheme in ("https", "http"):                  # the site's own advice: try http if https fails
        for attempt in range(3):
            try:
                req = urllib.request.Request(EPGSHARE_URL.format(scheme=scheme, file=name), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=180) as r:
                    return r.read()
            except Exception as err:
                print(f"  {name}: {scheme} attempt {attempt + 1} failed ({type(err).__name__}: {err})", file=sys.stderr)
                time.sleep(5)
    return None


def stamp(text):
    """XMLTV time (20261031120000 +0000) -> aware datetime; no zone = UTC."""
    text = (text or "").strip()
    try:
        return datetime.strptime(text, "%Y%m%d%H%M%S %z")
    except ValueError:
        try:
            return datetime.strptime(text[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def text_of(el, tag):
    kids = el.findall(tag)
    best = next((k for k in kids if (k.get("lang") or "").lower().startswith("en")), kids[0] if kids else None)
    return re.sub(r"\s+", " ", (best.text or "") if best is not None else "").strip()


def read_file(raw, wanted, now):
    """{canon epgshare id: [(start, stop, title, sub, desc, category)]} for the wanted ids of one epgshare file."""
    try:
        data = gzip.decompress(raw)
    except OSError:
        data = raw
    out = {}
    first, last = now - KEEP_PAST, now + timedelta(days=DAYS_AHEAD)
    try:
        for _, el in ET.iterparse(io.BytesIO(data), events=("end",)):
            if el.tag != "programme":
                if el.tag == "channel":
                    el.clear()
                continue
            eid = canon(el.get("channel"))
            if eid in wanted:
                start, stop = stamp(el.get("start")), stamp(el.get("stop"))
                title = text_of(el, "title")
                if start and stop and stop > start and title and stop > first and start < last:
                    desc = text_of(el, "desc")
                    if len(desc) > MAX_DESC:
                        desc = desc[:MAX_DESC].rsplit(" ", 1)[0] + "..."
                    cat = text_of(el, "category")
                    sub = text_of(el, "sub-title")
                    out.setdefault(eid, {})[start] = (start, stop, title, sub if sub != title else "", desc, cat)
            el.clear()
    except ET.ParseError as err:
        print(f"  WARNING: file could not be read completely ({err})", file=sys.stderr)
    return {k: [v[s] for s in sorted(v)] for k, v in out.items()}


def previous_guide(path, now):
    """{our id: [programme elements not yet finished]} and {our id: name} from the last GENERAL_epg.xml.gz."""
    progs, names = {}, {}
    try:
        with gzip.open(path, "rb") as f:
            root = ET.parse(f).getroot()
    except (OSError, ET.ParseError, EOFError):
        return progs, names
    for c in root.iter("channel"):
        names[c.get("id")] = c.findtext("display-name") or c.get("id")
    for p in root.iter("programme"):
        stop = stamp(p.get("stop"))
        if stop and stop > now:
            progs.setdefault(p.get("channel"), []).append(p)
    return progs, names


def add_programme(tv, cid, start, stop, title, sub, desc, cat):
    fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S +0000")
    p = ET.SubElement(tv, "programme", {"start": fmt(start), "stop": fmt(stop), "channel": cid})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    if sub:
        ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    if desc:
        ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    if cat:
        ET.SubElement(p, "category", {"lang": "en"}).text = cat


def write_xml(tv, path):
    """Write the guide gzip-compressed with no time stamp (mtime=0), so the file only changes when the guide does."""
    ET.indent(tv, space=" ")
    text = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
            + ET.tostring(tv, encoding="unicode") + "\n").encode("utf-8")
    inner = os.path.basename(path)[:-3] if path.endswith(".gz") else path
    with open(path, "wb") as raw, gzip.GzipFile(filename=inner, mode="wb", fileobj=raw, mtime=0, compresslevel=9) as f:
        f.write(text)
    with gzip.open(path, "rb") as f:
        if ET.parse(f).getroot().tag != "tv":
            sys.exit(f"ERROR: {path} did not write correctly")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--local", help="folder with epg_ripper_<FILE>.xml.gz files to use instead of downloading")
    ap.add_argument("--out", default=OUTPUT)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    prev_progs, prev_names = previous_guide(args.out, now)

    tv = ET.Element("tv", {"generator-info-name": "GENERAL_epg.py", "source-info-name": "epgshare01.online (UK1/US2/CA2/PLEX1/DK1)"})
    chans, progs = [], {}                  # chans: (our id, name); progs: our id -> [(start, stop, title, sub, desc, cat)]
    carried = []
    files = sorted({c[3] for c in CHANNELS})
    for name in files:
        mine = [c for c in CHANNELS if c[3] == name]
        wanted = {canon(c[4]) for c in mine}
        raw = download(name, args.local)
        if not raw:
            print(f"{name}: NOT AVAILABLE this run - its {len(mine)} channels are kept from the previous guide")
            for c in mine:
                chans.append((c[0], c[1]))
                if prev_progs.get(c[0]):
                    carried.append(c[0])
            continue
        got = read_file(raw, wanted, now)
        n = sum(len(v) for v in got.values())
        empty = [c[1] for c in mine if canon(c[4]) not in got]
        print(f"{name}: {len(mine)} channels wanted, {len(mine) - len(empty)} with programmes, {n} programmes"
              + (f" - NO programmes for: {', '.join(empty)}" if empty else ""))
        for c in mine:
            chans.append((c[0], c[1]))
            if canon(c[4]) in got:
                progs[c[0]] = got[canon(c[4])]

    placeholders = [(c[0], c[1]) for c in PLACEHOLDERS]
    placeholders += [(cid, nm) for cid, nm in chans if not progs.get(cid) and cid not in carried]   # mapped but empty
    chans += [(cid, nm) for cid, nm in [(c[0], c[1]) for c in PLACEHOLDERS]]
    block_start = now.replace(minute=0, second=0, microsecond=0)
    for cid, nm in chans:
        c = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = nm
    count = 0
    for cid, nm in chans:
        if progs.get(cid):
            for s, e, title, sub, desc, cat in progs[cid]:
                add_programme(tv, cid, s, e, title, sub, desc, cat)
                count += 1
    for cid in carried:                                  # a source was down: previous listings
        for p in prev_progs[cid]:
            tv.append(p)
            count += 1
    for cid, nm in placeholders:
        if cid in carried:
            continue
        t = block_start
        while t < block_start + timedelta(hours=PLACEHOLDER_HOURS):
            nxt = t + timedelta(hours=2)
            add_programme(tv, cid, t, nxt, nm, PLACEHOLDER_SUB, PLACEHOLDER_DESC.format(name=nm), "")
            count += 1
            t = nxt
    if placeholders:
        print(f"Placeholders (no listings from any source): {len(placeholders)} - " + ", ".join(nm for _, nm in placeholders))
    write_xml(tv, args.out)
    print(f"\nWrote {args.out}: {len(chans)} channels, {count} programmes")


if __name__ == "__main__":
    main()
