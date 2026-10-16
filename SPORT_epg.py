#!/usr/bin/env python3
"""
SPORT_epg.py - XMLTV guide of sports TV in Israel (Sport 5, Charlton), Greece (Novasports),
the Netherlands (ESPN, Ziggo Sport), Romania (Digi Sport, Prima Sport)
Bulgaria (MAX Sport, Diema Sport, Nova Sport, Ring ...), the Balkans (Arena Sport,
Sport Klub), Belgium (Play Sports, DAZN), Spain (Movistar Plus+), Portugal (MEO), Brazil (Claro), Albania/Kosovo (SuperSport), Czechia (ČT sport, Nova Sport ...), Slovakia
(STVR Šport, JOJ Šport, Arena Sport), Poland (TVP Sport, Polsat Sport, Canal+ Sport,
Eleven Sports), Italy (Sky Sport, DAZN, Rai Sport), Germany (Sky Sport, SPORT1, Eurosport),
India (Star Sports, Sony Sports Ten, DD Sports), Switzerland (blue Sport,
MySports, SRF zwei, RTS 2, RSI LA 2), France (Canal+ Sport, beIN SPORTS, RMC Sport, L'Équipe)
the Nordics: Sweden (V Sport, TV4 Sport), Norway (TV 2 Sport, V Sport), Denmark
(TV 2 Sport, TV3 Sport) and Finland (MTV Urheilu, V Sport, Viaplay Urheilu), beIN SPORTS in Australia, Malaysia, Singapore, Hong Kong,
Thailand and Indonesia, and SuperSport (South Africa and the rest of Africa).

ISRAEL - Sport 5's public broadcast sheet, one day at a time:
    https://www.sport5.co.il/Ajax/GetBroadcastSheetData.aspx?Type=&Date=YYYY-MM-DD
  Type empty = the "live" view: every live broadcast, grouped by channel.
  Channels: IL.5Sport, IL.5Plus, IL.5Live, IL.5Stars, IL.5Max, IL.5Gold ...
  Only live events are listed, so FILLER fills the gaps (2-hour blocks).

ISRAEL (Charlton) - Sport 1's broadcast page (server-built HTML):
    https://sport1.maariv.co.il/broadcast-schedule/
  Charlton's channels Sport 1, 2, 3, 4 and 6, live broadcasts only, so FILLER fills
  the gaps, as for Sport 5. Later days: ?day_selected=YYYY-MM-DD&live=1
  "ישיר" marks a live event. Hebrew text is translated.
  Channels: IL.Sport1, IL.Sport2, IL.Sport3, IL.Sport4, IL.Sport6

NETHERLANDS - Ziggo GO's public guide (already in English):
    channels: https://spark-prod-nl.gnp.cloud.ziggogo.tv/eng/web/linear-service/v2/channels?...
    events:   https://staticqbr-prod-nl.gnp.cloud.ziggogo.tv/eng/web/epg-service-lite/nl/en/
              events/segments/YYYYMMDDHH0000   (6-hour blocks, UTC)
  Only channels whose name matches --nl-channels (default: ESPN or Ziggo Sport).
  Channels: NL.ESPN, NL.ESPN2, NL.ZiggoSport, NL.ZiggoSportTotaal ...

ROMANIA (Digi Sport) - Digi Sport's own TV page, one page per channel with 7 days:
    https://www.digisport.ro/program-tv/digisport-1   (... digisport-4)
  "LIVE" before a title marks a live event. Channels: RO.DigiSport1 ... RO.DigiSport4

ROMANIA (Prima Sport) - Prima Play's TV page, all channels and ~10 days in one page:
    https://www.primaplay.ro/programtv
  Prima Sport 1-5 and Prima Sport PPV1-4. Channels: RO.PrimaSport1 ... RO.PrimaSportPPV4

BALKANS - Arena Sport's own TV page (Serbian feed), all channels and 7 days in one page:
    https://tvarenasport.com/tv-scheme    (the data is the window.TV_SCHEMES object)
  Arena Sport 1-10, Arena Premium 1-5, Arena Tenis, Adrenalin, Arena 1X2.
  "uzivo" marks a live event. Serbian text is translated.
  Channels: RS.ArenaSport1 ... RS.ArenaPremium1 ... RS.ArenaTenis, RS.Adrenalin

BELGIUM - Telenet's Play Sports "sportkalender" page (one page, this week's big events):
    https://www2.telenet.be/residential/nl/producten/telenet-tv/play-sports/sportkalender.html
  Lines like "17/10 Everton - Chelsea 13u15 | Play Sports 1" become events on that
  channel, with the competition and round as the sub-title. It lists the main live
  events only (no full schedule), so FILLER fills the gaps, as for Israel.
  Events without a start time (multi-day golf, tennis weeks) are left out.
  Channels: BE.PlaySports1 ... BE.PlaySportsGolf, BE.DAZN1, BE.DAZN2, BE.DAZNJPL1 ...

SPAIN - Movistar Plus+ TV guide, one request per channel and day.
  Read from Movistar's JSON guide (as iptv-org does), with exact start/end times and
  Movistar's own live flag; a channel the JSON guide doesn't return falls back to the
  web pages (today + 5 days):
    https://ottcache.dof6.com/movistarplus/webplayer/OTT/epg?from=YYYY-MM-DDT00:00:00&span=1&channel=mliga...
    fallback: https://www.movistarplus.es/programacion-tv/chapio/2026-10-17
  Channels chosen with --es-channels (Movistar's channel codes;
  default: all M+ sports, LaLiga, Liga de Campeones, DAZN, Eurosport and Teledeporte
  channels). Spanish titles are translated. Channels: ES.MPlusLaLiga, ES.DAZN1 ...

PORTUGAL - MEO's public TV guide (JSON), one request per channel and day:
    https://meogouser.apps.meo.pt/Services/GridTv/GridTv.svc/GetLiveChannelProgramsByDate
        ?callLetter=SPT1HD&date=YYYY-MM-DD&userAgent=IPTV_OFR_GTV
  Start and end times are given (Lisbon time). Channels chosen with --pt-channels
  (MEO's channel codes; default: Sport TV 1-7, Sport TV+, DAZN 1-5, BTV, Sporting TV,
  Canal 11). Portuguese titles are translated. Channels: PT.SportTV1 ... PT.DAZN1 ...

BRAZIL - Claro's public TV guide (programacao.claro.com.br, JSON search service):
    channels:   .../gatekeeper/canal/select?q=id_cidade:1 ...
    programmes: .../gatekeeper/exibicao/select?q=id_revel:(1_471)+AND+id_cidade:1 ... one per channel and day
  Channels whose name matches --br-channels (default: SporTV, Premiere and ESPN);
  SD/HD copies are merged. Start and end times are
  given (Brasilia time). Portuguese titles are translated.
  Channels: BR.SporTV, BR.SporTV2, BR.SporTV3, BR.PremiereClubes, BR.Premiere2, BR.ESPN ...

ALBANIA / KOSOVO - IPKO's public web guide (Kosovo, JSON), one request per channel and day:
    POST https://stargate.ipko.tv/api/titan.tv.WebEpg/GetWebEpgData
         {"ch_ext_id": "supersport-1", "from": <unix>, "to": <unix>}
  SuperSport 1-7 (Digitalb's channels for Albania and Kosovo). Start and end times
  are given. Channels chosen with --al-channels (IPKO's channel names; default
  supersport-1 ... supersport-7). Albanian titles are translated.
  Channels: AL.SuperSport1 ... AL.SuperSport7

CZECHIA - mujtvprogram.cz's public service (XML), one request per channel and day:
    https://services.mujtvprogram.cz/tvprogram2services/services/tvprogrammelist_mobile.php
        ?channel_cid=18&day=0          (day = 0 today, 1 tomorrow ...)
  Start and end times are given. Channels chosen with --cz-channels (the site's channel
  numbers; default: ČT sport, Nova Sport 1-6, Sport 1, Sport 2, Canal+ Sport 1-2).
  Czech titles are translated. Channels: CZ.CTSport, CZ.NovaSport1 ... CZ.CanalPlusSport

SLOVAKIA - the same mujtvprogram.cz service as Czechia (Nova Sport, Sport 1/2 and
  Canal+ Sport are shared with Czechia and already come from there).
  Channels chosen with --slovakia-channels (default: STVR Šport, JOJ Šport 1-2,
  Arena Sport 1-2). Slovak titles are translated.
  Channels: SK.STVRSport, SK.JOJSport, SK.JOJSport2, SK.ArenaSport1, SK.ArenaSport2

ITALY - Sky Italia's public TV guide API (JSON), one request per channel and day:
    channels:   https://apid.sky.it/gtv/v1/channels?env=DTH
    programmes: https://apid.sky.it/gtv/v1/events?from=...T00:00:00Z&to=...&env=DTH&channels=11346
  Channels whose name matches --it-channels (default: Sky Sport incl. 251-259, DAZN 1-4,
  Rai Sport, SuperTennis). Start and end times are given. Italian titles are translated;
  "Live"/"Diretta" marks live. Channels: IT.SkySportUno, IT.SkySport251, IT.DAZN1, IT.RaiSport ...

GERMANY - MagentaTV's web guide (Deutsche Telekom, JSON). It first asks for an anonymous
  web-guest session, as Telekom's website does for every visitor (no account, password
  or CAPTCHA; dummy device details):
    POST https://api.prod.sngtv.magentatv.de/EPG/JSON/Authenticate  -> token + cookies
    POST https://api.prod.sngtv.magentatv.de/EPG/JSON/PlayBillList  one per channel and day
  Channels chosen with --de-channels (MagentaTV channel numbers; default: Sky Sport News,
  Top Event, Sky Sport 1-10, Bundesliga 1-10, F1, Tennis, Golf, Mix, Premier League,
  SPORT1, Eurosport 1-2, Sportdigital Fussball, MagentaSport). German text is translated.
  Channels: DE.SkySportNews, DE.SkySportBundesliga1, DE.SPORT1, DE.Eurosport1 ...

INDIA - Tata Play's public guide API (JSON), one request per channel and day:
    POST https://tm.tapi.videoready.tv/content-detail/pub/api/v2/channels/schedule?date=DD-MM-YYYY
         {"id": "600"}
  Channels chosen with --in-channels (Tata Play channel numbers; default: Star Sports 1-3,
  Select 1-2, 1-2 Hindi, Khel, Sony Sports Ten 1, 2, 3 Hindi, 5, DD Sports, Eurosport).
  Start and end times are given. Titles are mostly English; Hindi or regional-script
  titles are translated. Channels: IN.StarSports1, IN.SonySportsTen1, IN.DDSports ...

EPGSHARE01 - ready-made XMLTV files from https://epgshare01.online/epgshare01/ (free, no login),
  one file per country, read once per run (gzip):
    https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz   (also LV1, HK1, ID1, BEIN1)
  Groups chosen with --epgshare (default turkey,latvia,hk,id,mena); --no-epgshare for none.
  Each channel has a fixed ID and a list of the file's own IDs for it, best first; the one
  with most programmes is used. Turkish, Latvian and Indonesian titles are translated.
  Channels: TR.beINSPORTS1 ... TR.TRTSpor, LV.GO3Sport1 ... LV.SetantaSports, HK.beINSPORTS1,
  HK.NowSports1 ..., ID.beINSPORTS1, ID.SPOTV ..., MENA.beINSPORTS1 ..., MENA.Alkass1 ...

SWITZERLAND - Swisscom's public blue TV guide (JSON), one request per channel and day:
    https://services.sg101.prd.sctv.ch/catalog/tv/channels/list/(ids=483;start=YYYYMMDD0000;end=...;level=normal)
  Channels chosen with --ch-channels (blue TV channel numbers; default: blue Sport 1-2,
  blue Sport (FR), blue Sport Extra, MySports Eins/Un/2-9/EDGE, Swiss Sport TV, SRF zwei,
  RTS 2, RSI LA 2). The numbered blue Sport Live / MySports Event channels are left out.
  Start and end times are given. German/French/Italian titles are translated.
  Channels: CH.blueSport1, CH.MySportsEins, CH.SRFzwei ...

FRANCE - SFR's public TV guide: one static JSON file per day with every channel (~10 MB):
    https://static-cdn.tv.sfr.net/data/epg/gen8/guide_web_YYYYMMDD.json
  Channels chosen with --fr-channels (SFR channel numbers; default: Canal+ Sport, Sport 360,
  Foot, beIN SPORTS 1-3, RMC Sport 1, RMC Sport Access, Eurosport 1-2, L'Équipe, DAZN 1,
  Golf+, Automoto, Equidia). Start and end times and a live flag are given. French text is
  translated. Channels: FR.CanalPlusSport, FR.beINSPORTS1, FR.RMCSport1, FR.LEquipe ...

SWEDEN / NORWAY / DENMARK / FINLAND - Allente's public TV guides (Nordic satellite operator, JSON),
  one request per country and day with every channel (~3 MB each):
    https://www.allente.se/api/epg/refetch-epg-data?Start=YYYY-MM-DD   (.no, .dk, .fi the same)
  Channels chosen with --se-channels, --nor-channels, --dk-channels, --fi-channels (Allente
  channel numbers). V Sport Golf, V Sport Ultra and Eurosport 2 (shared Swedish/Finnish
  feed) are Nordic-wide and come under Sweden.
  Start and end times are given; off-air gaps are skipped. Allente has no live flag, so
  only titles saying "live"/"direkt(e)" are tagged live. Titles are translated.
  Channels: SE.VSport1, SE.TV4Sportkanalen, NO.TV2Sport1, NO.VSport1, DK.TV2Sport, DK.TV3Sport,
  FI.MTVUrheilu1, FI.VSport1, FI.Viaplay1Urheilu ...

beIN SPORTS ASIA-PACIFIC - beIN's own public API (JSON), as iptv-org uses:
    channels:   https://www.beinsports.com/api/opta/tv-channel?region=en-au
    programmes: https://www.beinsports.com/api/opta/tv-event?startBefore=...&endAfter=...&channelIds=...
  Each run asks beIN for each country's channel list (Australia en-au and Malaysia en-my
  are confirmed by iptv-org; Singapore, Hong Kong, Thailand and Indonesia are tried with
  their own codes). A country whose list comes back identical to one already used is
  skipped, so one country's schedule is never shown under another's name. Same-named
  feeds within a country are merged (fullest kept). Start and end times are given; the
  competition is the sub-title. Choose countries with --bein (default au,my,sg; hk,th,id have no programmes on beIN's site).
  Channels: AU.beINSPORTS1, MY.beINSPORTS1, SG.beINSPORTS1, HK..., TH..., ID...

SUPERSPORT AFRICA - DStv's public TV guide (JSON), every channel in one request per day:
    https://www.dstv.com/umbraco/api/TvGuide/GetProgrammes?d=YYYY-MM-DD&country=zaf
  Two line-ups: South Africa (country=zaf) and the rest of Africa (DStv's Nigeria guide,
  country=nga&package=DStv Premium, as iptv-org uses). DStv's sports block is channels
  200-249 (SuperSport, ESPN, WWE); --ss-numbers changes the range. DStv renames channels
  often ('BLITZ', 'SS Blitz Nigeria'), so names are tidied to 'SuperSport Blitz' etc. to
  keep IDs steady. Times are local to each country. Already in English.
  Channels: ZA.SuperSportPremierLeague, ZA.SuperSportRugby ... AF.SuperSportPremierLeague ...

POLAND - Onet's TV guide (server-built HTML), one page per channel and day:
    https://programtv.onet.pl/program-tv/tvp-sport-40?dzien=0     (dzien = 0 today, 1 tomorrow ...)
  Channels chosen with --pl-channels (the page names; default: TVP Sport, Polsat Sport,
  Extra, Fight, Premium 1-2, Canal+ Sport 1-5, Eleven Sports 1-4). Programmes run back to
  back; the programme type is the sub-title. Polish text is translated; "na żywo" marks live.
  Channels: PL.TVPSport, PL.PolsatSport, PL.CanalPlusSport, PL.ElevenSports1 ...

SPORT KLUB - Delo's TV guide (Slovenia), one page per channel and day:
    https://tvspored.delo.si/oddaje/sk1/vsi/vsi/20261016
  Channels chosen with --sk-channels (default SK 1-10; ones the site doesn't have are skipped).
  Slovenian text is translated. Channels: SI.SK1 ... SI.SK10

BULGARIA - тв-програма.bg (server-built HTML), one page per channel and day:
    https://www.xn----8sbafg9clhjcp.bg/tv/diema-sport/          (today)
    https://www.xn----8sbafg9clhjcp.bg/tv/diema-sport/Петък/    (next days, by weekday name)
  Channels chosen with --bg-channels (default: MAX Sport 1-4, MAX One, Diema Sport 1-3,
  Nova Sport, Ring, BNT 3, bTV Action, Eurosport 1-2). Bulgarian text is translated;
  "На живо" in the listing marks a live event.
  Channels: BG.MaxSport1 ... BG.DiemaSport, BG.NovaSport, BG.Ring ...

GREECE - Novasports' TV programme (novasports.gr/tv-program), one day at a time:
    https://www.novasports.gr/wp-admin/admin-ajax.php?action=nova_get_template
        &template=tv-program/broadcast&dt=YYYY-MM-DD
  The full schedule of every channel on the page (Novasports, Eurosport,
  Magenta Sport ...). Channels: GR.NovasportsPrime, GR.Novasports1HD ...
  Programmes run back to back, so no filler is needed.

Both:
  * Hebrew / Greek titles are translated to English (free Google endpoint,
    cached in SPORT_translations.json next to this script). --no-translate keeps them.
  * Times are converted to UK time; descriptions also give local time.
  * FIXED CHANNEL IDS and a fixed file name (SPORT_epg.xml.gz, gzip-compressed;
    --out SPORT_epg.xml writes a plain file instead). --run-ids gives fresh
    ids (IL.5Sport-Run3, GR.NovasportsPrime-Run3) when PlaylistLabs must replace
    programmes it already holds; --unique gives a new file name each run.

Usage:
    python3 SPORT_epg.py                  # all countries, next 7 days -> SPORT_epg.xml.gz
    python3 SPORT_epg.py --no-israel      # leave out Sport 5 (also --no-charlton, --no-greece, --no-netherlands, --no-romania, --no-bulgaria, --no-arena, --no-sportklub, --no-belgium, --no-spain, --no-portugal, --no-brazil, --no-albania, --no-czechia, --no-slovakia, --no-poland, --no-italy, --no-germany, --no-india, --no-switzerland, --no-france, --no-sweden,
                                          --no-norway, --no-denmark, --no-finland, --no-bein, --no-supersport)
    python3 SPORT_epg.py --days 10
    python3 SPORT_epg.py --debug          # print what was read for each day

Only the Python standard library is needed. On Windows: pip install tzdata
"""

import argparse
import gzip
import io
import json
import socket
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
SHEET_URL = "https://www.sport5.co.il/Ajax/GetBroadcastSheetData.aspx"
PAGE_URL = "https://www.sport5.co.il/html/pages/broadcastsheet.html"
ISRAEL = ZoneInfo("Asia/Jerusalem")
CHARLTON_PAGE = "https://sport1.maariv.co.il/broadcast-schedule/"
CHARLTON_NAMES = {"2": "Sport 1", "3": "Sport 2", "4": "Sport 3", "5": "Sport 4", "1": "Sport 6"}
ATHENS = ZoneInfo("Europe/Athens")
NOVA_URL = "https://www.novasports.gr/wp-admin/admin-ajax.php"
NOVA_PAGE = "https://www.novasports.gr/tv-program/"
AMSTERDAM = ZoneInfo("Europe/Amsterdam")
BUCHAREST = ZoneInfo("Europe/Bucharest")
DIGI_PAGE = "https://www.digisport.ro/program-tv/digisport-{n}"
PRIMA_PAGE = "https://www.primaplay.ro/programtv"
RO_MONTHS = {m: i for i, m in enumerate(["ianuarie", "februarie", "martie", "aprilie", "mai",
             "iunie", "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"], 1)}
SOFIA = ZoneInfo("Europe/Sofia")
BELGRADE = ZoneInfo("Europe/Belgrade")
LJUBLJANA = ZoneInfo("Europe/Ljubljana")
BRUSSELS = ZoneInfo("Europe/Brussels")
MADRID = ZoneInfo("Europe/Madrid")
MOVISTAR_PAGE = "https://www.movistarplus.es/programacion-tv/{code}/{day:%Y-%m-%d}"
MOVISTAR_EPG = ("https://ottcache.dof6.com/movistarplus/webplayer/OTT/epg?from={day:%Y-%m-%d}T00:00:00"
                "&span=1&channel={code}&version=8&mdrm=true&tlsstream=true&demarcation=18")
MOVISTAR_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*", "Accept-Language": "es-ES,es;q=0.9",
                    "Referer": "https://www.movistarplus.es/programacion-tv"}
ES_CHANNELS = {          # Movistar channel code -> channel name
    "vamosd": "M+ Vamos", "vam2sd": "M+ Vamos 2", "mellav": "M+ Ellas V",
    "mliga": "M+ LaLiga", "mlig1": "M+ LaLiga 2", "mlig2": "M+ LaLiga 3", "mlig3": "M+ LaLiga 4",
    "daznli": "DAZN LaLiga", "daznl2": "DAZN LaLiga 2",
    "mligs": "LaLiga TV Hypermotion", "mligs2": "LaLiga TV Hypermotion 2",
    "mligs3": "LaLiga TV Hypermotion 3",
    "chapio": "M+ Liga de Campeones",
    **{f"chap{i}": f"M+ Liga de Campeones {i + 1}" for i in range(1, 13)},
    "cpdep": "M+ Deportes", "arthur": "M+ Deportes 2", "usop2": "M+ Deportes 3",
    "usop3": "M+ Deportes 4", "usop11": "M+ Deportes 5", "multi8": "M+ Deportes 6",
    "mbalct": "M+ Baloncesto", **{f"mbalc{i}": f"M+ Baloncesto {i}" for i in range(2, 6)},
    "golf+": "M+ Golf", "golf2": "M+ Golf 2",
    "mvf1": "DAZN F1", "dazmot": "DAZN MotoGP", "m1sd": "DAZN 1", "m2sd": "DAZN 2",
    "dazn3": "DAZN 3", "dazn4": "DAZN 4",
    "dazba": "DAZN Baloncesto", "dazb2": "DAZN Baloncesto 2", "dazb3": "DAZN Baloncesto 3",
    "esp": "Eurosport 1", "esp2": "Eurosport 2", "tdep": "Teledeporte",
    "realm": "Real Madrid TV", "mcopa": "Primera Federacion",
}
LISBON = ZoneInfo("Europe/Lisbon")
MEO_GUIDE = ("https://meogouser.apps.meo.pt/Services/GridTv/GridTv.svc/GetLiveChannelProgramsByDate"
             "?callLetter={code}&date={day:%Y-%m-%d}&userAgent=IPTV_OFR_GTV")
MEO_HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36",
               "Origin": "https://www.meo.pt", "Referer": "https://www.meo.pt/",
               "Accept": "*/*", "Accept-Language": "pt-PT,pt;q=0.9"}
PT_CHANNELS = {          # MEO channel code -> channel name
    **{f"SPT{i}HD": f"Sport TV {i}" for i in range(1, 8)}, "SPTVHD": "Sport TV+",
    **{f"DAZN{i}": f"DAZN {i}" for i in range(1, 6)},
    "SLBHD": "BTV", "SCPHD": "Sporting TV", "C11": "Canal 11",
}
SAO_PAULO = ZoneInfo("America/Sao_Paulo")
TIRANE = ZoneInfo("Europe/Tirane")
PRAGUE = ZoneInfo("Europe/Prague")
WARSAW = ZoneInfo("Europe/Warsaw")
BRATISLAVA = ZoneInfo("Europe/Bratislava")
ROME = ZoneInfo("Europe/Rome")
BERLIN = ZoneInfo("Europe/Berlin")
# iptv-org's current, working browser identities (an older Chrome version gets 'HTTP 403')
IPTV_ORG_CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")
IPTV_ORG_EDGE = IPTV_ORG_CHROME + " Edg/143.0.0.0"
KOLKATA = ZoneInfo("Asia/Kolkata")
ZURICH = ZoneInfo("Europe/Zurich")
PARIS = ZoneInfo("Europe/Paris")
DSTV_GUIDE = "https://www.dstv.com/umbraco/api/TvGuide/GetProgrammes?d={day:%Y-%m-%d}{extra}&country={country}"
DSTV_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "application/json, */*", "Referer": "https://www.dstv.com/"}
SS_REGIONS = {           # prefix -> (DStv country, extra query, place, time zone, name suffix)
    "ZA": ("zaf", "", "South Africa", "Africa/Johannesburg", "SA"),
    "AF": ("nga", "&package=DStv%20Premium", "Africa", "Africa/Lagos", "Africa"),
}
BEIN_API = "https://www.beinsports.com/api/opta/"
BEIN_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "application/json, */*", "Referer": "https://www.beinsports.com/"}
BEIN_COUNTRIES = {       # code -> (place, time zone, region codes to try, fallback {channel id: name})
    "au": ("Australia", "Australia/Sydney", ["en-au"], {
        "164C0EDA-EBCE-4AA6-9DDA-D603E0948B9F": "beIN SPORTS 1", "63A30D9C-609D-4A30-8730-2CA391DF287A": "beIN SPORTS 2",
        "2E8A6222-8D90-4291-81E3-AF2F72557746": "beIN SPORTS 3", "C938A2D0-375A-4876-B05D-08EE29D33B07": "beIN SPORTS XTRA"}),
    "my": ("Malaysia", "Asia/Kuala_Lumpur", ["en-my"], {
        "0FA3DEF0-234B-4E25-934F-392DF2C3162C": "beIN SPORTS 1", "5F323488-6662-42DC-BE1C-B954ECDD5CD7": "beIN SPORTS 2",
        "07C1C284-D784-4AD2-9F7E-022DCD196D04": "beIN SPORTS 3"}),
    "sg": ("Singapore", "Asia/Singapore", ["en-sg"], {}),
    "hk": ("Hong Kong", "Asia/Hong_Kong", ["en-hk", "zh-hk"], {}),
    "th": ("Thailand", "Asia/Bangkok", ["en-th", "th-th"], {}),
    "id": ("Indonesia", "Asia/Jakarta", ["en-id", "id-id"], {}),
}
BEIN_DEFAULT = "au,my,sg"  # hk, th, id: beIN lists the channels but publishes no programmes (checked Oct 2026)
STOCKHOLM, OSLO, COPENHAGEN = ZoneInfo("Europe/Stockholm"), ZoneInfo("Europe/Oslo"), ZoneInfo("Europe/Copenhagen")
HELSINKI = ZoneInfo("Europe/Helsinki")
ALLENTE_GUIDE = "https://www.allente.{tld}/api/epg/refetch-epg-data?Start={day:%Y-%m-%d}"
SE_CHANNELS = {          # Allente channel number -> (id part, channel name)
    "50079": ("VSport1", "V Sport 1 SE"), "50078": ("VSportPremium", "V Sport Premium SE"),
    "50056": ("VSportFootball", "V Sport Football SE"), "20092": ("VSportExtra", "V Sport Extra"),
    "50048": ("VSportMotor", "V Sport Motor"), "50049": ("VSportVinter", "V Sport Vinter"),
    "50077": ("VSportGolf", "V Sport Golf"), "50105": ("VSportUltra", "V Sport Ultra"),
    "20083": ("TV4Sportkanalen", "TV4 Sportkanalen"), "50060": ("TV4Fotboll", "TV4 Fotboll"),
    "50053": ("TV4Hockey", "TV4 Hockey"), "50059": ("TV4Motor", "TV4 Motor"),
    "20063": ("TV4Tennis", "TV4 Tennis"),
    "20061": ("Eurosport1", "Eurosport 1 SE"), "50055": ("Eurosport2", "Eurosport 2 SE"),
}
NO_CHANNELS = {
    "10099": ("TV2Sport1", "TV 2 Sport 1"), "10021": ("TV2Sport2", "TV 2 Sport 2"),
    "10029": ("TV2SportPremium", "TV 2 Sport Premium"), "10030": ("TV2SportPremium2", "TV 2 Sport Premium 2"),
    "50047": ("VSport1", "V Sport 1 NO"), "50046": ("VSportPlus", "V Sport+ NO"),
    "50081": ("VSport3", "V Sport 3 NO"), "10106": ("VSportPremierLeague", "V Sport Premier League"),
    "10022": ("EurosportNorge", "Eurosport Norge"), "10091": ("Eurosport1", "Eurosport 1 NO"),
}
FI_CHANNELS = {
    "40051": ("VSport1", "V Sport 1 FI"), "40052": ("VSportPremium", "V Sport Premium FI"),
    "40049": ("VSportFootball", "V Sport Football FI"), "40050": ("VSportVinter", "V Sport Vinter FI"),
    "40032": ("Viaplay1Urheilu", "Viaplay 1 Urheilu"), "40031": ("Viaplay2Urheilu", "Viaplay 2 Urheilu"),
    "40030": ("Viaplay3Urheilu", "Viaplay 3 Urheilu"),
    "40015": ("MTVUrheilu1", "MTV Urheilu 1"), "40016": ("MTVUrheilu2", "MTV Urheilu 2"),
    "40054": ("MTVUrheilu3", "MTV Urheilu 3"), "40014": ("MTVMax", "MTV Max"),
    "20025": ("Eurosport1", "Eurosport 1 FI"),
}
DK_CHANNELS = {
    "30011": ("TV2Sport", "TV 2 Sport DK"), "30051": ("TV2SportX", "TV 2 Sport X"),
    "30027": ("TV3Sport", "TV3 Sport DK"), "30050": ("TV3MAX", "TV3 MAX"),
    "50022": ("Eurosport1", "Eurosport 1 DK"), "30010": ("Eurosport2", "Eurosport 2 DK"),
}
SFR_GUIDE = "https://static-cdn.tv.sfr.net/data/epg/gen8/guide_web_{day:%Y%m%d}.json"
FR_CHANNELS = {          # SFR channel number -> (id part, channel name)
    "35": ("CanalPlusSport", "Canal+ Sport"), "3504": ("CanalPlusSport360", "Canal+ Sport 360"),
    "3501": ("CanalPlusFoot", "Canal+ Foot"),
    "1290": ("beINSPORTS1", "beIN SPORTS 1 FR"), "1304": ("beINSPORTS2", "beIN SPORTS 2 FR"),
    "1335": ("beINSPORTS3", "beIN SPORTS 3 FR"),
    "2665": ("RMCSport1", "RMC Sport 1"), "2095": ("RMCSportAccess", "RMC Sport Access"),
    "76": ("Eurosport1", "Eurosport 1 FR"), "439": ("Eurosport2", "Eurosport 2 FR"),
    "1401": ("LEquipe", "L'Équipe"), "3795": ("DAZN1", "DAZN 1 FR"), "1295": ("GolfPlus", "Golf+"),
    "15": ("Automoto", "Automoto"), "64": ("Equidia", "Equidia"),
}
BLUE_GUIDE = ("https://services.sg101.prd.sctv.ch/catalog/tv/channels/list/"
              "(ids={cid};start={day:%Y%m%d}0000;end={nxt:%Y%m%d}0000;level=normal)")
CH_CHANNELS = {          # blue TV channel number -> (id part, channel name)
    "483": ("blueSport1", "blue Sport 1"), "494": ("blueSport2", "blue Sport 2"),
    "590": ("blueSportFR", "blue Sport (FR)"), "1240": ("blueSportExtra", "blue Sport Extra"),
    "1543": ("MySportsEins", "MySports Eins"), "1557": ("MySportsUn", "MySports Un"),
    **{str(1542 + i): (f"MySports{i}", f"MySports {i}") for i in range(2, 10)},
    "1722": ("MySportsEDGE", "MySports EDGE"), "1601": ("SwissSportTV", "Swiss Sport TV"),
    "401": ("SRFzwei", "SRF zwei"), "367": ("RTS2", "RTS 2"), "357": ("RSILA2", "RSI LA 2"),
}
TATAPLAY_GUIDE = "https://tm.tapi.videoready.tv/content-detail/pub/api/v2/channels/schedule?date={day:%d-%m-%Y}"
TATAPLAY_HEADERS = {"User-Agent": IPTV_ORG_EDGE,                      # exactly as iptv-org asks
                    "Accept": "*/*", "Content-Type": "application/json", "locale": "ENG",
                    "Origin": "https://watch.tataplay.com", "Referer": "https://watch.tataplay.com/"}
IN_CHANNELS = {          # Tata Play channel number -> (id part, channel name)
    "600": ("StarSports1", "Star Sports 1"), "609": ("StarSports2", "Star Sports 2"),
    "664": ("StarSports3", "Star Sports 3"),
    "141": ("StarSportsSelect1", "Star Sports Select 1"), "603": ("StarSportsSelect2", "Star Sports Select 2"),
    "601": ("StarSports1Hindi", "Star Sports 1 Hindi"), "980": ("StarSports2Hindi", "Star Sports 2 Hindi"),
    "1494": ("StarSportsKhel", "Star Sports Khel"),
    "150": ("SonySportsTen1", "Sony Sports Ten 1"), "170": ("SonySportsTen2", "Sony Sports Ten 2"),
    "171": ("SonySportsTen3Hindi", "Sony Sports Ten 3 Hindi"), "610": ("SonySportsTen5", "Sony Sports Ten 5"),
    "223": ("DDSports", "DD Sports"), "693": ("Eurosport", "Eurosport India"),
}
MAGENTA_API = "https://api.prod.sngtv.magentatv.de/EPG/JSON/"
MAGENTA_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DE_CHANNELS = {          # MagentaTV channel number -> channel name
    "190": "Sky Sport News", "31": "Sky Sport Top Event",
    "192": "Sky Sport 1", "212": "Sky Sport 2", "189": "Sky Sport 3", "111": "Sky Sport 4",
    "114": "Sky Sport 5", "113": "Sky Sport 6", "127": "Sky Sport 7", "261": "Sky Sport 8",
    "187": "Sky Sport 9", "5554": "Sky Sport 10",
    "42": "Sky Sport Bundesliga",
    "206": "Sky Sport Bundesliga 1", "211": "Sky Sport Bundesliga 2", "199": "Sky Sport Bundesliga 3",
    "232": "Sky Sport Bundesliga 4", "234": "Sky Sport Bundesliga 5", "231": "Sky Sport Bundesliga 6",
    "258": "Sky Sport Bundesliga 7", "219": "Sky Sport Bundesliga 8", "237": "Sky Sport Bundesliga 9",
    "5557": "Sky Sport Bundesliga 10",
    "4889": "Sky Sport F1", "198": "Sky Sport Tennis", "5558": "Sky Sport Golf",
    "5556": "Sky Sport Mix", "5555": "Sky Sport Premier League",
    "401": "SPORT1", "389": "Eurosport 1", "18": "Eurosport 2",
    "194": "Sportdigital Fussball", "5075": "MagentaSport",
}
SKYIT_API = "https://apid.sky.it/gtv/v1/"
SKYIT_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                 "Accept": "application/json, */*", "Origin": "https://guidatv.sky.it",
                 "Referer": "https://guidatv.sky.it/"}
IT_DEFAULT = r"^sky sport(?! 4k)|dazn|rai sport|supertennis"
IT_FALLBACK = {          # used only if Sky's channel list can't be read: id -> (number, name)
    9094: (200, "Sky Sport24"), 11346: (201, "Sky Sport Uno"), 9113: (202, "Sky Sport Calcio"),
    11237: (203, "Sky Sport Tennis"), 7507: (204, "Sky Sport Arena"), 9103: (205, "Sky Sport Max"),
    10254: (206, "Sky Sport Golf"), 9096: (207, "Sky Sport F1"), 9102: (208, "Sky Sport MotoGP"),
    9116: (209, "Sky Sport Basket"), 8753: (209, "Sky Sport NBA"), 11910: (210, "Sky Sport Legend"),
    11909: (211, "Sky Sport Mix"), 11402: (214, "DAZN 1"), 11401: (215, "DAZN 2"),
    11849: (216, "DAZN3"), 11850: (217, "DAZN4"), 807: (227, "RAI Sport"), 6000: (0, "SuperTennis HD"),
    11497: (251, "Sky Sport"), 11496: (252, "Sky Sport"), 11494: (253, "Sky Sport"),
    11490: (254, "Sky Sport"), 11491: (255, "Sky Sport"), 11492: (256, "Sky Sport"),
    11386: (257, "Sky Sport"), 9046: (258, "Sky Sport"), 8613: (259, "Sky Sport"),
}
SVK_CHANNELS = {         # mujtvprogram.cz channel number -> (id part, channel name)
    "928": ("STVRSport", "STVR Šport"),
    "1107": ("JOJSport", "JOJ Šport"), "1145": ("JOJSport2", "JOJ Šport 2"),
    "344": ("ArenaSport1", "Arena Sport 1 SK"), "379": ("ArenaSport2", "Arena Sport 2 SK"),
}
ONET_PAGE = "https://programtv.onet.pl/program-tv/{slug}?dzien={offset}"
PL_CHANNELS = {          # Onet page name -> (id part, channel name)
    "tvp-sport-40": ("TVPSport", "TVP Sport"),
    "polsat-sport-334": ("PolsatSport", "Polsat Sport"),
    "polsat-sport-extra-485": ("PolsatSportExtra", "Polsat Sport Extra"),
    "polsat-sport-fight-546": ("PolsatSportFight", "Polsat Sport Fight"),
    "polsat-sport-premium-1-643": ("PolsatSportPremium1", "Polsat Sport Premium 1"),
    "polsat-sport-premium-2-644": ("PolsatSportPremium2", "Polsat Sport Premium 2"),
    "canal-sport-14": ("CanalPlusSport", "Canal+ Sport"),
    "canal-sport-2-15": ("CanalPlusSport2", "Canal+ Sport 2"),
    "canal-sport-3-674": ("CanalPlusSport3", "Canal+ Sport 3"),
    "canal-sport-4-675": ("CanalPlusSport4", "Canal+ Sport 4"),
    "nsport-19": ("CanalPlusSport5", "Canal+ Sport 5"),
    "eleven-208": ("ElevenSports1", "Eleven Sports 1"),
    "eleven-sports-212": ("ElevenSports2", "Eleven Sports 2"),
    "eleven-extra-531": ("ElevenSports3", "Eleven Sports 3"),
    "eleven-sports-4-607": ("ElevenSports4", "Eleven Sports 4"),
}
MUJTV_LIST = ("https://services.mujtvprogram.cz/tvprogram2services/services/tvprogrammelist_mobile.php"
              "?channel_cid={cid}&day={offset}")
CZ_CHANNELS = {          # mujtvprogram.cz channel number -> (id part, channel name)
    "18": ("CTSport", "ČT sport"),
    "17": ("NovaSport1", "Nova Sport 1"), "466": ("NovaSport2", "Nova Sport 2"),
    "904": ("NovaSport3", "Nova Sport 3"), "905": ("NovaSport4", "Nova Sport 4"),
    "1073": ("NovaSport5", "Nova Sport 5"), "1074": ("NovaSport6", "Nova Sport 6"),
    "61": ("Sport1", "Sport 1 CZ"), "93": ("Sport2", "Sport 2 CZ"),
    "1040": ("CanalPlusSport", "Canal+ Sport"), "1071": ("CanalPlusSport2", "Canal+ Sport 2"),
}
IPKO_EPG = "https://stargate.ipko.tv/api/titan.tv.WebEpg/GetWebEpgData"
IPKO_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*", "Content-Type": "application/json",
                "X-AppLayout": "1", "x-language": "sq",
                "Origin": "https://ipko.tv", "Referer": "https://ipko.tv/"}
AL_DEFAULT = ",".join(f"supersport-{i}" for i in range(1, 8))
CLARO_BASE = "https://programacao.claro.com.br/gatekeeper/"
CLARO_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                 "Accept": "application/json, */*",
                 "Origin": "https://programacao.claro.com.br",
                 "Referer": "https://programacao.claro.com.br/", "Accept-Language": "pt-BR,pt;q=0.9"}
BR_DEFAULT = r"sportv|premiere|espn"
BR_FALLBACK = {          # used only if Claro's channel list can't be read
    "1_471": "SporTV", "1_470": "SporTV 2", "1_1023": "SporTV 3",
    "1_426": "ESPN", "1_427": "ESPN 2", "1_2251": "ESPN 3", "1_1034": "ESPN 4",
    "1_2239": "ESPN 5", "1_1091": "ESPN 6",
    "1_1360": "Premiere 2", "1_1361": "Premiere 3", "1_1362": "Premiere 4", "1_1363": "Premiere 5",
    "1_1364": "Premiere 6", "1_693": "Premiere 7", "1_1365": "Premiere Clubes",
}
TELENET_CAL = ("https://www2.telenet.be/residential/nl/producten/telenet-tv/play-sports/"
               "sportkalender.html")
DELO_PAGE = "https://tvspored.delo.si/oddaje/{slug}/vsi/vsi/{day:%Y%m%d}"
SK_DEFAULT = ",".join(f"sk{i}" for i in range(1, 11))
ARENA_PAGE = "https://www.tvarenasport.com/tv-scheme"
BG_SITE = "https://www.xn----8sbafg9clhjcp.bg/tv/{slug}/{day}"
BG_WEEKDAYS = ["Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък", "Събота", "Неделя"]
BG_CHANNELS = {          # page name on the site -> channel name
    "max-sport-1": "MAX Sport 1", "max-sport-2": "MAX Sport 2", "max-sport-3": "MAX Sport 3",
    "max-sport-4": "MAX Sport 4", "max-one": "MAX One",
    "diema-sport": "Diema Sport", "diema-sport-2": "Diema Sport 2", "diema-sport-3": "Diema Sport 3",
    "nova-sport": "Nova Sport", "ring-bg": "Ring", "bnt3": "BNT 3", "btv-action": "bTV Action",
    "eurosport": "Eurosport 1", "eurosport2": "Eurosport 2",
}
ZIGGO_CHANNELS = ("https://spark-prod-nl.gnp.cloud.ziggogo.tv/eng/web/linear-service/v2/channels"
                  "?cityId=65535&language=en&productClass=Orion-DASH&platform=web")
ZIGGO_SEGMENT = ("https://staticqbr-prod-nl.gnp.cloud.ziggogo.tv/eng/web/epg-service-lite/nl/en/"
                 "events/segments/{stamp}")
ZIGGO_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                 "Origin": "https://www.ziggogo.tv", "Referer": "https://www.ziggogo.tv/",
                 "Accept": "application/json"}
LONDON = ZoneInfo("Europe/London")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": PAGE_URL,
    "Accept": "text/html, */*; q=0.01",
}

OUTPUT_NAME = "SPORT_epg.xml.gz"         # a name ending in .xml gives a plain file
HERE = os.path.dirname(os.path.abspath(__file__))
RUN_STATE_FILE = os.path.join(HERE, "SPORT_epg_run.json")
CACHE_FILE = os.path.join(HERE, "SPORT_translations.json")
OLD_CACHE_FILE = os.path.join(HERE, "israel_translations.json")   # read once if the new one is missing

# Channel logo file on the site -> (channel id part, English name).
# Unknown logos still work: the id comes from the file name, the name from its alt text.
KNOWN_CHANNELS = {
    "SPORT5_CHANNEL": ("5Sport", "Sport 5"),
    "SPORT5_PLUS": ("5Plus", "Sport 5 Plus"),
    "SPORT5_LIVE": ("5Live", "Sport 5 Live"),
    "SPORT5_STARS": ("5Stars", "Sport 5 Stars"),
    "SPORT5_MAX": ("5Max", "Sport 5 Max"),
    "SPORT5_GOLD": ("5Gold", "Sport 5 Gold"),
    "SPORT5_MOBILE": ("5Mobile", "Sport 5 Mobile"),
    "SPORT5_4K": ("5Sport4K", "Sport 5 4K"),
}

DEFAULT_MINUTES = 120     # event length when the next event isn't sooner
FILLER_HOURS = 2          # longest filler block


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _ssl_context()
HOST_CTX = {}             # host -> SSL context that also trusts intermediates fetched for it


def _ca_issuers(pem):
    """The 'CA Issuers' addresses a certificate names for its issuer (where browsers fetch it)."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
        f.write(pem)
    try:
        return list(ssl._ssl._test_decode_cert(f.name).get("caIssuers") or [])
    except Exception:
        return []
    finally:
        os.unlink(f.name)


def _context_with_intermediates(host, port=443):
    """Like a browser: when a server leaves out an intermediate certificate, fetch it from the
    address its certificate names. The chain is still fully checked against trusted roots."""
    try:
        pem = ssl.get_server_certificate((host, port), timeout=FETCH_TIMEOUT)
    except Exception:
        return None
    found, todo = [], _ca_issuers(pem)
    for _ in range(3):                                  # at most 3 levels up
        if not todo:
            break
        url, todo = todo[0], []
        try:
            with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT, context=CTX) as resp:
                der = resp.read()
            inter = ssl.DER_cert_to_PEM_cert(der) if not der.lstrip().startswith(b"-----") else der.decode()
        except Exception:
            break
        found.append(inter)
        todo = _ca_issuers(inter)
    if not found:
        return None
    ctx = _ssl_context()
    ctx.load_verify_locations(cadata="".join(found))
    return ctx


LAST_STATUS = {"code": None}


HOST_FAILS = {}           # host -> failures in a row (reset on success)
HOST_GIVEN_UP = {}        # host -> reason, once a host has failed MAX_HOST_FAILS times in a row
MAX_HOST_FAILS = 3
FETCH_TIMEOUT = 60       # seconds to wait for an answer


def _reason(e):
    """A short, readable reason for a failed request."""
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code}" + (f" {e.reason}" if getattr(e, "reason", None) else "")
    r = getattr(e, "reason", e)
    if isinstance(r, (TimeoutError, socket.timeout)) or "timed out" in str(r).lower():
        return f"timed out (no answer in {FETCH_TIMEOUT} s)"
    if isinstance(r, ssl.SSLError):
        return f"SSL error: {r}"
    if isinstance(r, socket.gaierror):
        return f"address lookup failed: {r}"
    if isinstance(r, ConnectionRefusedError):
        return "connection refused"
    if isinstance(r, ConnectionResetError):
        return "connection reset by the server"
    return str(r)


def fetch(url, data=None, headers=None, method=None, parse="text", retries=3, quiet=False, label=None):
    """GET or POST url and return text or parsed JSON, or None.
    Failures name their reason (HTTP status, time-out, a web page instead of data ...).
    After MAX_HOST_FAILS failed requests in a row to one host (time-outs, refusals, blocks,
    server errors - not 'not found' answers), the rest of that host is skipped for this run,
    so an unreachable site can't hold the whole run up."""
    host = urllib.parse.urlsplit(url).hostname or url
    shown = label or url
    if host in HOST_GIVEN_UP:
        return None
    last, LAST_STATUS["code"] = None, None
    reachable = False                                  # a 400/404 answer: the site is there
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT, context=HOST_CTX.get(host, CTX)) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", "replace") if parse != "bytes" else ""
            if parse == "bytes":
                out = raw
            elif parse == "json":
                try:
                    out = json.loads(text)
                except ValueError:
                    head = re.sub(r"\s+", " ", text[:90]).strip()
                    kind = "a web page" if "<" in text[:200] else "something"
                    last = f"got {kind} instead of data ({ctype or 'no type'}): {head!r}"
                    break                               # a block page won't change on retry
            else:
                out = text
            HOST_FAILS[host] = 0
            return out
        except urllib.error.HTTPError as e:
            last, LAST_STATUS["code"] = _reason(e), e.code
            if e.code == 429:                          # 'too many requests': wait as asked, then retry
                reachable = True
                try:
                    wait = min(int(e.headers.get("Retry-After") or 0), 120)
                except (TypeError, ValueError):
                    wait = 0
                time.sleep(wait or 15 * (attempt + 1))
                continue
            if e.code in (400, 404, 410):
                reachable = True
                break
            if e.code in (401, 403, 451):
                break
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as e:
            last = _reason(e)
            r = getattr(e, "reason", None)
            if (isinstance(r, ssl.SSLCertVerificationError) and "local issuer" in str(r)
                    and host not in HOST_CTX):
                ctx = _context_with_intermediates(host)
                if ctx:
                    HOST_CTX[host] = ctx                # try again, now with the missing piece
                    continue
        server_error = (LAST_STATUS["code"] or 0) >= 500
        time.sleep((5 if server_error else 2) * (attempt + 1))  # a struggling server gets more time
    HOST_FAILS[host] = 0 if reachable else HOST_FAILS.get(host, 0) + 1
    if not quiet:
        print(f"  WARNING: could not fetch {shown}: {last}", file=sys.stderr)
    if HOST_FAILS[host] >= MAX_HOST_FAILS:
        HOST_GIVEN_UP[host] = last
        print(f"  WARNING: {host} failed {MAX_HOST_FAILS} times in a row ({last}) - "
              f"skipping the rest of it this run", file=sys.stderr)
    return None


def get_text(url, params, retries=3, headers=None, quiet=False):
    full = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    return fetch(full, headers=headers or HEADERS, retries=retries, quiet=quiet)


# --------------------------------------------------------------------------
# Parsing the broadcast sheet
# --------------------------------------------------------------------------
class SheetParser(HTMLParser):
    """Collects (channel_key, channel_alt, time_text, title, is_live) rows."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.channel_key = None
        self.channel_alt = None
        self._in_header = False
        self._td_class = None
        self._row = None
        self._date_text = []
        self._title_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "tr":
            self._in_header = "tr-header" in cls
            self._row = None if self._in_header else {"live": False}
            self._date_text, self._title_text = [], []
        elif tag == "img":
            src = a.get("src") or ""
            if self._in_header and "/channels/" in src.lower():
                name = os.path.basename(src)
                name = re.sub(r"\.(svg|png|jpe?g|gif|webp)$", "", name, flags=re.I)
                name = re.sub(r"_(white|black|color|colour|logo)$", "", name, flags=re.I)
                self.channel_key = name.upper()
                self.channel_alt = (a.get("alt") or a.get("title") or "").strip()
            elif self._row is not None and "img-live" in src.lower():
                self._row["live"] = True
        elif tag == "td" and self._row is not None:
            self._td_class = "date" if "date" in cls else "text" if "text" in cls else None

    def handle_endtag(self, tag):
        if tag == "td":
            self._td_class = None
        elif tag == "tr" and self._row is not None:
            when = re.search(r"\b(\d{1,2}):(\d{2})\b", " ".join(self._date_text))
            title = re.sub(r"\s+", " ", "".join(self._title_text)).strip()
            if when and title and self.channel_key:
                self.rows.append((self.channel_key, self.channel_alt,
                                  int(when.group(1)), int(when.group(2)),
                                  title, self._row["live"]))
            self._row = None

    def handle_data(self, data):
        if self._td_class == "date":
            self._date_text.append(data)
        elif self._td_class == "text":
            self._title_text.append(data)


def fetch_day(day, sheet_type, debug=False):
    html = get_text(SHEET_URL, {"Type": sheet_type, "Date": day.isoformat()})
    if not html:
        return []
    p = SheetParser()
    p.feed(html)
    if debug:
        print(f"  {day}: {len(p.rows)} rows")
        for r in p.rows[:5]:
            print("    ", r)
    return p.rows


# --------------------------------------------------------------------------
# Israel: Charlton (Sport 1 website broadcast page)
# --------------------------------------------------------------------------
def parse_charlton(page, default_date=None):
    """{channel_name: [(date_str, hh, mm, title, competition, live)]}
    default_date is used for a channel block that carries no date marker."""
    import html as _html
    clean = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
    names = {}                                   # data-channel-id -> "Sport N" (menu on the page)
    for cid, label in re.findall(r'<h2[^>]*data-channel-id="(\d+)"[^>]*>(.*?)</h2>', page, re.S):
        label = clean(label)
        num = re.search(r"\d+", label)
        names.setdefault(cid, f"Sport {num.group(0)}" if num and "ספורט" in label else label)
    end = page.find("</main>")
    body = page[:end] if end > 0 else page
    starts = list(re.finditer(r'id="channel-(\d+)-container"', body))
    out = {}
    for i, m in enumerate(starts):
        chunk = body[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(body)]
        name = (names.get(m.group(1)) or CHARLTON_NAMES.get(m.group(1))
                or f"Sport Channel {m.group(1)}")
        days = [(dm.group(1), dm.end()) for dm in
                re.finditer(r"shows-container-for-(\d{4}-\d{2}-\d{2})", chunk)]
        if not days and default_date:
            days = [(default_date, 0)]
        for j, (day_str, pos) in enumerate(days):
            block = chunk[pos: days[j + 1][1] if j + 1 < len(days) else len(chunk)]
            for show in block.split('class="col-12 show-container"')[1:]:
                t = re.search(r'class="show-starting-time"[^>]*>\s*(\d{1,2}):(\d{2})', show)
                n = re.search(r'class="show-name"[^>]*>(.*?)</p>', show, re.S)
                d = re.search(r'class="show-description"[^>]*>(.*?)</p>', show, re.S)
                st = re.search(r'class="show-second-status"[^>]*>(.*?)</p>', show, re.S)
                if not (t and n and clean(n.group(1))):
                    continue
                out.setdefault(name, []).append(
                    (day_str, int(t.group(1)), int(t.group(2)), clean(n.group(1)),
                     clean(d.group(1)) if d else "", bool(st and "ישיר" in clean(st.group(1)))))
    return out


def fetch_charlton(days, debug=False):
    """{channel_name: [{start, title, sub, live}]} from Sport 1's broadcast page.

    Today comes from the plain page. Later days come from the same page with
    ?day_selected=YYYY-MM-DD&live=1 (the address the site shows when a day tab is
    clicked); if that doesn't return that date, the day's own address
    broadcast-schedule/YYYY-MM-DD/?live=1 (the request the tab makes) is tried.
    Rows are only used for the date they are marked with, so a page that ignores
    the date can't put today's games on another day."""
    hdrs = {"User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "he-IL,he;q=0.9", "Referer": CHARLTON_PAGE}
    wanted = {d.isoformat() for d in [days[0] - timedelta(days=1)] + list(days)}
    rows = {}                                         # name -> {(date, hh, mm): row}

    def take(parsed, only=None):
        n = 0
        for name, items in parsed.items():
            for r in items:
                if r[0] in wanted and (only is None or r[0] == only):
                    rows.setdefault(name, {})[r[:3]] = r
                    n += 1
        return n

    page = get_text(CHARLTON_PAGE, {}, headers=hdrs)
    if page:
        n = take(parse_charlton(page))
        if debug:
            print(f"  Charlton today: {n} broadcasts")
    for day in days[1:]:
        d = day.isoformat()
        n = 0
        page = get_text(CHARLTON_PAGE, {"day_selected": d, "live": "1"}, headers=hdrs,
                        retries=2, quiet=True)
        if page:
            n = take(parse_charlton(page), only=d)
        how = "day_selected"
        if not n:
            page = get_text(f"{CHARLTON_PAGE}{d}/", {"live": "1"},
                            headers={**hdrs, "X-Requested-With": "XMLHttpRequest"},
                            retries=2, quiet=True)
            if page:
                n = take(parse_charlton(page, default_date=d), only=d)
            how = "day address"
        if debug:
            print(f"  Charlton {d}: {n} broadcasts ({how})")

    out = {}
    for name, items in rows.items():
        evs, last = {}, {}
        for day_str, hh, mm, title, comp, live in sorted(items.values(), key=lambda r: r[0]):
            y, mo, dd = map(int, day_str.split("-"))
            start = datetime(y, mo, dd, hh, mm, tzinfo=ISRAEL)
            if day_str in last and start < last[day_str]:
                start += timedelta(days=1)            # past midnight
            last[day_str] = start
            key = start.astimezone(timezone.utc)
            evs[key] = {"start": key, "title": title, "sub": comp, "live": live}
        if evs:
            out[name] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Greece: Novasports TV programme
# --------------------------------------------------------------------------
LOOKALIKE = str.maketrans("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧαβεικνορτυχ", "ABEZHIKMNOPTYXabeiknoptyx")
NOVA_HEADERS = {**HEADERS, "Referer": NOVA_PAGE, "X-Requested-With": "XMLHttpRequest"}
TOKEN = re.compile(
    r'class="channel-title[^"]*">\s*(?P<ch>[^<]+?)\s*</div>'
    r'|class="(?P<cls>tv-broadcast[^"]*)"')


def clean(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html_unescape(text)).strip()


def html_unescape(text):
    import html
    return html.unescape(text)


def parse_nova(page):
    """[(channel_name, hh, mm, title, subtitle, live)] from the channels view."""
    rows, channel = [], None
    marks = list(TOKEN.finditer(page))
    for i, m in enumerate(marks):
        if m.group("ch"):
            channel = clean(m.group("ch")).translate(LOOKALIKE)
            channel = re.sub(r"^Novasports(?=\S)", "Novasports ", channel)     # Novasports1HD
            channel = re.sub(r"(\d)(HD)$", r"\1 \2", channel)                  # -> Novasports 1 HD
            continue
        cls = m.group("cls").split()
        if channel is None or "column" in cls:      # "column" = the events view
            continue
        end = marks[i + 1].start() if i + 1 < len(marks) else len(page)
        block = page[m.end():end]
        t = re.search(r'class="time">\s*(\d{1,2}):(\d{2})', block)
        title = re.search(r'class="title">(.*?)</div>', block, re.S)
        sub = re.search(r'class="subtitle[^"]*">(.*?)</div>', block, re.S)
        if not (t and title):
            continue
        name = clean(title.group(1))
        live = "live-now" in block or bool(re.search(r"\((Ζ|Z)\)", name))
        name = re.sub(r"\s*\((Ζ|Z)\)\s*", " ", name).strip()     # (Ζ) = live
        rows.append((channel, int(t.group(1)), int(t.group(2)), name,
                     clean(sub.group(1)) if sub else "", live))
    return rows


def fetch_greece(days, debug=False):
    """{channel_name: [{start, title, sub, live}]}"""
    channels = {}
    for day in days:
        page = get_text(NOVA_URL, {"action": "nova_get_template",
                                   "template": "tv-program/broadcast",
                                   "dt": day.isoformat()}, headers=NOVA_HEADERS)
        rows = parse_nova(page) if page else []
        if debug:
            print(f"  Greece {day}: {len(rows)} rows")
            for r in rows[:5]:
                print("    ", r)
        last = {}
        for ch, hh, mm, title, sub, live in rows:
            start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=ATHENS)
            if ch in last and start < last[ch]:      # past midnight
                start += timedelta(days=1)
            last[ch] = start
            channels.setdefault(ch, []).append(
                {"start": start.astimezone(timezone.utc), "title": title, "sub": sub, "live": live})
    for ch, evs in channels.items():
        seen, uniq = set(), []
        for ev in sorted(evs, key=lambda e: e["start"]):
            if ev["start"] not in seen:
                seen.add(ev["start"])
                uniq.append(ev)
        channels[ch] = uniq
    return channels


# --------------------------------------------------------------------------
# Netherlands: Ziggo GO guide (ESPN, Ziggo Sport)
# --------------------------------------------------------------------------
def get_json_url(url, headers, quiet=False):
    return fetch(url, headers=headers, parse="json", quiet=quiet)


def ziggo_channels(pattern):
    """{channel_code: name} for channels whose name matches pattern."""
    data = get_json_url(ZIGGO_CHANNELS, ZIGGO_HEADERS)
    items = data if isinstance(data, list) else (data or {}).get("channels") or []
    wanted, rx = {}, re.compile(pattern, re.I)
    for ch in items:
        if not isinstance(ch, dict):
            continue
        code = ch.get("id") or ch.get("channelId") or ch.get("stationId")
        name = (ch.get("name") or ch.get("title") or ch.get("channelName")
                or ch.get("stationName") or "")
        if code and name and rx.search(name):
            wanted[code] = name.strip()
    return wanted


def fetch_netherlands(days, pattern, debug=False):
    """{channel_name: [{start, stop, title, sub, live}]}"""
    names = ziggo_channels(pattern)
    if debug:
        print(f"  Netherlands: {len(names)} matching channels: {sorted(set(names.values()))}")
    if not names:
        return {}
    events = {code: {} for code in names}
    for day in days:
        for hour in (0, 6, 12, 18):
            stamp = f"{day:%Y%m%d}{hour:02d}0000"
            data = get_json_url(ZIGGO_SEGMENT.format(stamp=stamp), ZIGGO_HEADERS) or {}
            for entry in data.get("entries") or []:
                code = entry.get("channelId")
                if code not in events:
                    continue
                for ev in entry.get("events") or []:
                    try:
                        start = datetime.fromtimestamp(int(ev["startTime"]), timezone.utc)
                        stop = datetime.fromtimestamp(int(ev["endTime"]), timezone.utc)
                    except (KeyError, TypeError, ValueError):
                        continue
                    title = (ev.get("title") or "").strip()
                    series = (ev.get("seriesName") or "").strip()
                    if title and stop > start:
                        events[code][start] = {
                            "start": start, "stop": stop, "title": title,
                            "sub": series if series and series != title else "",
                            "live": bool(ev.get("isLive")),
                            "desc": pick_desc(ev, "longDescription", "shortDescription", "description")}
            if debug:
                print(f"  Netherlands {stamp}: {len(data.get('entries') or [])} channels in block")
    out = {}
    for code, evs in events.items():
        if not evs:
            continue
        name = names[code]
        if name in out:                         # same name twice (e.g. SD and HD): keep the fuller one
            if len(evs) <= len(out[name]):
                continue
        out[name] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Romania: Digi Sport and Prima Play TV pages
# --------------------------------------------------------------------------
def fetch_digisport(days, debug=False):
    """{channel_name: [{start, title, sub, live}]} for Digi Sport 1-4."""
    import unicodedata
    plain = lambda x: unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()
    day_rx = re.compile(r"^(luni|marti|miercuri|joi|vineri|sambata|duminica)\s+(\d{1,2})\s+([a-z]+)$")
    row_rx = re.compile(r"^(\d{1,2}):(\d{2})\s*(.*)$")
    today = datetime.now(BUCHAREST).date()
    first, last_day = days[0], days[-1]
    out = {}
    for n in range(1, 5):
        page = get_text(DIGI_PAGE.format(n=n), {},
                        headers={"User-Agent": HEADERS["User-Agent"],
                                 "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                                 "Accept-Language": "ro-RO,ro;q=0.9"})
        if not page:
            continue
        evs, cur, last, pending = {}, None, None, None
        for line in html_lines(page):
            dm = day_rx.match(plain(line))
            if dm and dm.group(3) in RO_MONTHS:
                cands = []
                for y in (today.year - 1, today.year, today.year + 1):
                    try:
                        cands.append(date(y, RO_MONTHS[dm.group(3)], int(dm.group(2))))
                    except ValueError:
                        pass
                cur = min(cands, key=lambda c: abs((c - today).days)) if cands else None
                last, pending = None, None
                continue
            if cur is None or not (first <= cur <= last_day):
                continue
            rm = row_rx.match(line)
            if rm:
                pending = (int(rm.group(1)), int(rm.group(2)))
                text = rm.group(3).strip()
                if not text:
                    continue                      # title on the next line
            elif pending and len(line) < 150:
                text = line
            else:
                continue
            hh, mm = pending
            pending = None
            start = datetime(cur.year, cur.month, cur.day, hh, mm, tzinfo=BUCHAREST)
            if last and start < last:
                start += timedelta(days=1)
            last = start
            live = bool(re.match(r"live\b", text, re.I))
            title = re.sub(r"^(live|premiera)\s+", "", text, flags=re.I).strip()
            key = start.astimezone(timezone.utc)
            evs[key] = {"start": key, "title": title, "sub": "", "live": live}
        if debug:
            print(f"  Digi Sport {n}: {len(evs)} programmes")
        if evs:
            out[f"Digi Sport {n}"] = [evs[k] for k in sorted(evs)]
    return out


def fetch_primaplay(days, debug=False):
    """{channel_name: [{start, title, sub, live}]} for Prima Sport 1-5 and PPV1-4."""
    import html as _html
    page = get_text(PRIMA_PAGE, {}, headers={"User-Agent": HEADERS["User-Agent"],
                                             "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                                             "Accept-Language": "ro-RO,ro;q=0.9"})
    if not page:
        return {}
    names = {}
    for a in re.finditer(r'href="#channel\d{4}-\d{2}-\d{2}-(\d+)"(.*?)</a>', page, re.S):
        alt = re.search(r'alt="([^"]*)"', a.group(2))
        if alt:
            names.setdefault(a.group(1), _html.unescape(alt.group(1)).strip())
    sport = {n: (f"Prima Sport {nm}" if nm.upper().startswith("PPV") else nm)
             for n, nm in names.items() if re.search(r"sport|ppv", nm, re.I)}
    wanted = {d.isoformat() for d in days}
    clean = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
    out = {}
    starts = [m for m in re.finditer(r'id="channel(\d{4}-\d{2}-\d{2})-(\d+)" role="tabpanel"', page)]
    for i, m in enumerate(starts):
        day_str, n = m.group(1), m.group(2)
        if n not in sport or day_str not in wanted:
            continue
        block = page[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(page)]
        y, mo, d = map(int, day_str.split("-"))
        last = None
        evs = out.setdefault(sport[n], {})
        for t, body in re.findall(r'<tr>\s*<td>\s*(\d{1,2}:\d{2})\s*</td>\s*<td[^>]*>(.*?)</td>',
                                  block, re.S):
            body = re.sub(r'<span class="live">.*?</span>', " ", body, flags=re.S)  # "watch now" link
            title = clean(body)
            if not title:
                continue
            hh, mm = map(int, t.split(":"))
            start = datetime(y, mo, d, hh, mm, tzinfo=BUCHAREST)
            if last and start < last:
                start += timedelta(days=1)
            last = start
            key = start.astimezone(timezone.utc)
            evs[key] = {"start": key, "title": title, "sub": "", "live": False}
    if debug:
        print(f"  Prima Play: {', '.join(f'{k} {len(v)}' for k, v in out.items())}")
    return {k: [v[t] for t in sorted(v)] for k, v in out.items() if v}


# --------------------------------------------------------------------------
# Bulgaria: тв-програма.bg channel pages
# --------------------------------------------------------------------------
def parse_bg(page):
    """[(hh, mm, title, info, live)] from one channel page."""
    import html as _html
    rows = []
    for m in re.finditer(r'<div class="programTime">\s*(?:<span[^>]*>)?\s*(\d{1,2}):(\d{2}).*?'
                         r'<a href="/predavane/[^"]*">(.*?)</a>', page, re.S):
        body = m.group(3)
        strong = re.search(r"<strong>(.*?)</strong>(.*)", body, re.S)
        text = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
        if strong:
            title, rest = text(strong.group(1)), text(strong.group(2))
            extra = re.match(r"^(:[^:]*?)?\s*(?:-\s+(.*))?$", rest)
            if extra and extra.group(1):
                title = f"{title}: {extra.group(1)[1:].strip()}"
            info = (extra.group(2) if extra else rest) or ""
        else:
            title, info = text(body), ""
        live = bool(re.search(r"на живо|пряко", info, re.I))
        if title:
            rows.append((int(m.group(1)), int(m.group(2)), title, info, live))
    return rows


def fetch_bulgaria(days, slugs, debug=False):
    """{channel_name: [{start, title, sub, live}]}"""
    wanted = [x.strip() for x in slugs.split(",") if x.strip()]
    today = datetime.now(SOFIA).date()
    out = {}
    for slug in wanted:
        evs = {}
        for day in days:
            offset = (day - today).days
            if offset < 0 or offset > 6:
                continue
            day_part = "" if offset == 0 else urllib.parse.quote(BG_WEEKDAYS[day.weekday()]) + "/"
            page = get_text(BG_SITE.format(slug=slug, day=day_part), {},
                            headers={"User-Agent": HEADERS["User-Agent"],
                                     "Accept-Language": "bg-BG,bg;q=0.9"})
            rows = parse_bg(page) if page else []
            if debug:
                print(f"  Bulgaria {slug} {day}: {len(rows)} rows")
            last = None
            for hh, mm, title, info, live in rows:
                start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=SOFIA)
                if last and start < last:
                    start += timedelta(days=1)
                last = start
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title, "sub": info, "live": live}
        if evs:
            out[BG_CHANNELS.get(slug, slug.replace("-", " ").title())] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Balkans: Arena Sport TV page
# --------------------------------------------------------------------------
def arena_html_name(slug):
    """Logo file name -> the same channel name the page data uses ('a1p' -> 'Arena Premium 1')."""
    s = slug.lower()
    if re.fullmatch(r"0*\d+", s):
        return f"Arena Sport {int(s)}"
    m = re.fullmatch(r"a+(\d+)p", s)
    if m:
        return f"Arena Premium {m.group(1)}"
    if s == "1x2":
        return "Arena 1X2"
    if s == "a-adrenalin":
        return "Adrenalin"
    return "Arena " + s.replace("a-", "", 1).replace("-", " ").title()


def parse_arena_html(page, wanted, debug=False):
    """The page's HTML layout (used by iptv-org): {channel_name: [{start, title, sub, live}]}"""
    import html as _html
    txt = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x or ""))).strip()
    out = {}
    for block in page.split('class="tv-scheme-chanel"')[1:]:
        logo = re.search(r"chanel-([\w-]+?)\.png", block)
        if not logo:
            continue
        channel = arena_html_name(logo.group(1))
        dates = re.findall(r'tv-scheme-new-days-item[^>]*>\s*<span>[^<]*</span>\s*<span>[^<]*</span>\s*<span>\s*(\d{1,2})\.(\d{1,2})\.?', block)
        sliders = block.split("tv-scheme-new-slider-item")[1:]
        today = datetime.now(BELGRADE).date()
        evs = {}
        for idx, (dd, mo) in enumerate(dates):
            if idx >= len(sliders):
                break
            year = today.year + (1 if today.month == 12 and int(mo) == 1 else -1 if today.month == 1 and int(mo) == 12 else 0)
            try:
                day = date(year, int(mo), int(dd))
            except ValueError:
                continue
            if day.isoformat() not in wanted:
                continue
            last = None
            for item in sliders[idx].split('class="slider-content"')[1:]:
                tm = re.search(r'slider-content-top"[^>]*>\s*<span>\s*(\d{1,2}):(\d{2})', item)
                bottom = re.search(r'slider-content-bottom"[^>]*>(.*?)</div>', item, re.S)
                bottom = bottom.group(1) if bottom else ""
                title = txt((re.search(r"<p>(.*?)</p>", bottom, re.S) or [None, ""])[1])
                if not (tm and title):
                    continue
                sport = txt((re.search(r'slider-content-middle"[^>]*>\s*<span>(.*?)</span>', item, re.S) or [None, ""])[1])
                league = txt((re.search(r"</p>\s*<span>(.*?)</span>", bottom, re.S) or [None, ""])[1])
                live = "uživo" in txt((re.search(r'class="blob-text"[^>]*>(.*?)</span>', bottom, re.S) or [None, ""])[1]).lower()
                start = datetime(day.year, day.month, day.day, int(tm.group(1)), int(tm.group(2)), tzinfo=BELGRADE)
                if last and start < last:
                    start += timedelta(days=1)
                last = start
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title, "sub": " - ".join(x for x in (sport, league) if x),
                            "live": live}
        if debug:
            print(f"  Arena {channel}: {len(evs)} programmes (HTML layout)")
        if evs:
            out[channel] = [evs[k] for k in sorted(evs)]
    return out


def fetch_arena(days, debug=False):
    """{channel_name: [{start, title, sub, live}]} for the dates in days."""
    page = get_text(ARENA_PAGE, {}, headers={"User-Agent": HEADERS["User-Agent"],
                                             "Accept-Language": "sr-RS,sr;q=0.9"})
    if not page:
        return {}
    i = page.find("window.TV_SCHEMES")
    if i < 0:
        if 'class="tv-scheme-chanel"' in page:          # the HTML layout iptv-org reads
            return parse_arena_html(page, {d.isoformat() for d in days}, debug)
        print("  WARNING: Arena Sport page has no TV_SCHEMES data or schedule layout", file=sys.stderr)
        return {}
    try:
        data, _ = json.JSONDecoder().raw_decode(page[page.index("{", i):])
    except ValueError:
        print("  WARNING: could not read Arena Sport data", file=sys.stderr)
        return {}
    wanted = {d.isoformat() for d in days}
    out = {}
    for channel, info in data.items():
        evs = {}
        for day_str, day in sorted((info.get("days") or {}).items()):
            if day_str not in wanted:
                continue
            y, mo, d = map(int, day_str.split("-"))
            last = None
            for e in day.get("emisije") or []:
                tm = re.match(r"(\d{1,2}):(\d{2})", e.get("time") or "")
                title = (e.get("content") or "").strip()
                if not (tm and title):
                    continue
                start = datetime(y, mo, d, int(tm.group(1)), int(tm.group(2)), tzinfo=BELGRADE)
                if last and start < last:
                    start += timedelta(days=1)
                last = start
                sub = " - ".join(x for x in ((e.get("sport") or "").strip(),
                                             (e.get("category") or "").strip()) if x)
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title, "sub": sub,
                            "live": (e.get("description") or "").lower() == "uzivo"}
        if debug:
            print(f"  Arena {channel}: {len(evs)} programmes")
        if evs:
            out[channel.strip()] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Sport Klub: Delo TV guide (Slovenia)
# --------------------------------------------------------------------------
def parse_delo(page):
    """(channel_name, [(hh, mm, title, genre)])"""
    import html as _html
    name = re.search(r'itemtype="https://schema.org/TelevisionChannel".*?itemprop="name"[^>]*>(.*?)</h2>',
                     page, re.S)
    rows = []
    for block in re.findall(r'itemtype="https://schema.org/BroadcastEvent">(.*?)</a>', page, re.S):
        t = re.search(r'itemprop="startDate"[^>]*>\s*(\d{1,2}):(\d{2})', block)
        n = re.search(r'itemprop="name"[^>]*>(.*?)</div>', block, re.S)
        g = re.search(r'class="text-text text-sm[^"]*">(.*?)</div>', block, re.S)
        clean = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
        if t and n and clean(n.group(1)):
            rows.append((int(t.group(1)), int(t.group(2)), clean(n.group(1)),
                         clean(g.group(1)) if g else ""))
    return (clean(name.group(1)) if name else None), rows


def fetch_sportklub(days, slugs, debug=False):
    """{channel_name: [{start, title, sub, live}]}"""
    out = {}
    for slug in [x.strip() for x in slugs.split(",") if x.strip()]:
        evs, chname = {}, None
        for day in days:
            page = get_text(DELO_PAGE.format(slug=slug, day=day), {},
                            headers={"User-Agent": HEADERS["User-Agent"],
                                     "Accept-Language": "sl-SI,sl;q=0.9"}, retries=2,
                            quiet=True)
            name, rows = parse_delo(page) if page else (None, [])
            chname = chname or name
            if debug:
                print(f"  Sport Klub {slug} {day}: {len(rows)} rows")
            if not rows:
                if day == days[0]:
                    break                        # channel not on the site
                continue
            # The first row can be the end of the previous evening (e.g. 23:00 before 00:30)
            prev_day = len(rows) > 1 and (rows[0][0], rows[0][1]) > (rows[1][0], rows[1][1]) \
                and rows[0][0] >= 12
            last = None
            for i, (hh, mm, title, genre) in enumerate(rows):
                d = day - timedelta(days=1) if (i == 0 and prev_day) else day
                start = datetime(d.year, d.month, d.day, hh, mm, tzinfo=LJUBLJANA)
                if last and start < last:
                    start += timedelta(days=1)
                last = start
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title,
                            "sub": genre.replace("•", "-"), "live": False}
        if evs:
            out[chname or slug.upper()] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Belgium: Telenet Play Sports calendar
# --------------------------------------------------------------------------
BE_EVENT = re.compile(r"^(\d{1,2})/(\d{1,2})\s+(.+?)\s+(\d{1,2})u(\d{2})\s*\|\s*(.+?)\s*$")
BE_ROUND = re.compile(r"^(speeldag|ronde|round|kwartfinale|halve finale|finale|groep|"
                      r"play-?offs?|\d+/\d+e? finales?|\d+(e|ste|de)? (ronde|speeldag))", re.I)


def html_lines(page):
    import html as _html
    page = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|section)>", "\n", page)
    text = _html.unescape(re.sub(r"<[^>]+>", " ", page))
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]


def fetch_belgium(days, debug=False):
    """{channel_name: [{start, title, sub, live}]} from the Play Sports calendar."""
    page = get_text(TELENET_CAL, {}, headers={"User-Agent": HEADERS["User-Agent"],
                                              "Accept-Language": "nl-BE,nl;q=0.9"})
    if not page:
        return {}
    first, last_day = days[0] - timedelta(days=1), days[-1]
    out, headers, comp, rnd = {}, [], "", ""
    for line in html_lines(page):
        m = BE_EVENT.match(line)
        if not m:
            if len(line) <= 60 and "|" not in line:     # headings, not untimed events
                headers.append(line)
            continue
        if headers:                                   # headings since the last event
            rounds = [h for h in headers if BE_ROUND.search(h)]
            comps = [h for h in headers if not BE_ROUND.search(h)]
            if comps:
                comp, rnd = comps[-1], (rounds[-1] if rounds else "")
            elif rounds:
                rnd = rounds[-1]
            headers = []
        dd, mo, title, hh, mm, channel = m.groups()
        today = datetime.now(BRUSSELS).date()
        cands = []
        for y in (today.year - 1, today.year, today.year + 1):
            try:
                cands.append(date(y, int(mo), int(dd)))
            except ValueError:
                pass
        if not cands:
            continue
        d = min(cands, key=lambda c: abs((c - today).days))
        if not (first <= d <= last_day):
            continue                                  # old or far-off entries on the page
        start = datetime(d.year, d.month, d.day, int(hh), int(mm), tzinfo=BRUSSELS)
        channel = re.sub(r"\s+", " ", channel).strip()
        key = start.astimezone(timezone.utc)
        out.setdefault(channel, {})[key] = {
            "start": key, "title": title.strip(),
            "sub": " - ".join(x for x in (comp, rnd) if x), "live": True}
    if debug:
        print(f"  Belgium: {sum(len(v) for v in out.values())} events on {sorted(out)}")
    return {ch: [evs[k] for k in sorted(evs)] for ch, evs in out.items()}


# --------------------------------------------------------------------------
# Spain: Movistar Plus+ TV guide
# --------------------------------------------------------------------------
def parse_movistar(page):
    """[(hh, mm, title, genre)] - every programme is a link to its 'ficha' page."""
    import html as _html
    rows = []
    for inner in re.findall(r'<a [^>]*href="[^"]*/ficha\?[^"]*"[^>]*>(.*?)</a>', page, re.S):
        parts = [re.sub(r"\s+", " ", _html.unescape(x)).strip()
                 for x in re.split(r"<[^>]+>", inner)]
        parts = [x for x in parts if x and x not in ("*", "+")]
        times = [x for x in parts if re.fullmatch(r"\d{1,2}:\d{2}", x)]
        rest = [x for x in parts if x not in times]
        if not times or not rest:
            continue
        genre, title = (rest[0], " ".join(rest[1:])) if len(rest) > 1 else ("", rest[0])
        hh, mm = map(int, times[-1].split(":"))
        rows.append((hh, mm, title, genre))
    return rows


def spain_json(code, days, debug=False):
    """{start: event} from Movistar's JSON guide (exact times and a live flag)."""
    evs = {}
    for day in days:
        data = get_json_url(MOVISTAR_EPG.format(day=day, code=urllib.parse.quote(code, safe="")), MOVISTAR_HEADERS)
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) and data.get("Titulo") else []
        if debug:
            print(f"  Movistar JSON {code} {day}: {len(items)} programmes")
        if not items and day == days[0]:
            break                                      # channel not in the JSON guide
        for it in items:
            try:
                start = datetime.fromtimestamp(int(it["FechaHoraInicio"]) / 1000, timezone.utc)
                stop = datetime.fromtimestamp(int(it["FechaHoraFin"]) / 1000, timezone.utc)
            except (KeyError, TypeError, ValueError):
                continue
            title = re.sub(r"\s+", " ", it.get("Titulo") or "").strip()
            if not title or stop <= start:
                continue
            sub = re.sub(r"\s+", " ", it.get("TituloEpisodio") or "").strip()
            if re.match(r"(ep\.|episodio)\s*\d", sub, re.I) or sub == title:
                sub = ""                               # 'Ep. 1 ...' is a series episode, not a match
            live = bool(it.get("Directo")) or bool(re.search(r"\bdirecto\b", title, re.I))
            title = re.sub(r"\s*[(\-:]\s*\(?en directo\)?\s*$|\s*\(directo\)\s*$", "", title, flags=re.I).strip() or title
            evs[start] = {"start": start, "stop": stop, "title": title, "sub": sub, "live": live,
                          "desc": pick_desc(it, "Resena", "Descripcion", "Sinopsis")}
    return evs


def fetch_spain(days, codes, debug=False):
    """{channel_name: [{start, stop, title, sub, live}]} - Movistar's JSON guide, or its web pages."""
    today = datetime.now(MADRID).date()
    out = {}
    for code in [c.strip() for c in codes.split(",") if c.strip()]:
        name = ES_CHANNELS.get(code, code)
        evs = spain_json(code, days, debug)
        if evs:
            out[name] = [evs[k] for k in sorted(evs)]
            continue
        if debug:
            print(f"  Movistar {code}: nothing from the JSON guide, trying the web pages")
        for day in days:
            if not 0 <= (day - today).days <= 5:
                continue                               # the guide covers today + 5 days
            url = MOVISTAR_PAGE.format(code=urllib.parse.quote(code, safe=""), day=day)
            page = get_text(url, {}, headers={"User-Agent": HEADERS["User-Agent"],
                                              "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                                              "Accept-Language": "es-ES,es;q=0.9"},
                            retries=2, quiet=True)
            rows = parse_movistar(page) if page else []
            if debug:
                print(f"  Movistar {code} {day}: {len(rows)} rows")
            if not rows:
                if day == today:
                    break                              # channel not in the guide
                continue
            last = None
            for hh, mm, title, genre in rows:
                start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=MADRID)
                if last and start < last:
                    start += timedelta(days=1)         # past midnight
                last = start
                key = start.astimezone(timezone.utc)
                evs.setdefault(key, {"start": key, "title": title, "sub": "",
                                     "live": bool(re.search(r"\bdirecto\b", title, re.I))})
        if evs:
            out[name] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Portugal: MEO TV guide
# --------------------------------------------------------------------------
def fetch_portugal(days, codes, debug=False):
    """{channel_name: [{start, stop, title, sub, live}]}"""
    out = {}
    for code in [c.strip() for c in codes.split(",") if c.strip()]:
        name = PT_CHANNELS.get(code, code)
        evs = {}
        for day in days:
            data = get_json_url(MEO_GUIDE.format(code=urllib.parse.quote(code, safe=""), day=day),
                                MEO_HEADERS) or {}
            items = data.get("Result") if isinstance(data, dict) else None
            items = items if isinstance(items, list) else []
            if debug:
                print(f"  MEO {code} {day}: {len(items)} programmes")
            if not items and day == days[0]:
                break                                  # channel not in MEO's guide
            for it in items:
                try:
                    start = datetime.fromisoformat(it["StartDate"][:19]).replace(tzinfo=LISBON)
                    stop = datetime.fromisoformat(it["EndDate"][:19]).replace(tzinfo=LISBON)
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", it.get("Title") or "").strip()
                if not title or stop <= start:
                    continue
                live = bool(re.search(r"\b(direto|ao vivo)\b", title, re.I))
                title = re.sub(r"\s*[-(]?\s*\b(direto|ao vivo)\b\s*\)?\s*$", "", title,
                               flags=re.I).strip() or title
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "stop": stop.astimezone(timezone.utc),
                            "title": title, "sub": "", "live": live,
                            "desc": pick_desc(it, "Synopsis", "Description")}
        if evs:
            out[name] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Italy: Sky Italia TV guide
# --------------------------------------------------------------------------
def it_name(raw, number):
    """'Sky Sport' (251) -> 'Sky Sport 251', 'DAZN3' -> 'DAZN 3', 'RAI Sport ' -> 'Rai Sport'"""
    n = re.sub(r"\s+", " ", raw).strip()
    n = re.sub(r"\s*\bHD\b", "", n).strip()
    if n.lower() == "sky sport" and number:
        n = f"Sky Sport {number}"
    n = re.sub(r"\bDAZN(\d)", r"DAZN \1", n)
    n = re.sub(r"\bRAI\b", "Rai", n)
    return n


def sky_it_channels(pattern):
    """{channel id: clean name} for Sky Italia channels whose name matches pattern."""
    data = get_json_url(SKYIT_API + "channels?env=DTH", SKYIT_HEADERS) or {}
    chans = data.get("channels") if isinstance(data, dict) else None
    found = {c.get("id"): (c.get("number") or 0, c.get("name") or "")
             for c in (chans if isinstance(chans, list) else []) if c.get("id")}
    if not found:
        print("  WARNING: Sky Italia channel list not available, using the built-in list", file=sys.stderr)
        found = IT_FALLBACK
    rx = re.compile(pattern, re.I)
    return {cid: it_name(name, num) for cid, (num, name) in found.items() if name and rx.search(name.strip())}


def fetch_italy(days, pattern, debug=False):
    """{channel_name: [{start, stop, title, sub, live}]}"""
    names = sky_it_channels(pattern)
    if debug:
        print(f"  Italy: {len(names)} matching channels: {sorted(set(names.values()))}")
    events = {}
    for cid in names:
        evs = events.setdefault(cid, {})
        for day in days:
            nxt = day + timedelta(days=1)
            url = (f"{SKYIT_API}events?from={day:%Y-%m-%d}T00:00:00Z&to={nxt:%Y-%m-%d}T00:00:00Z"
                   f"&pageSize=999&pageNum=0&env=DTH&channels={cid}")
            data = get_json_url(url, SKYIT_HEADERS) or {}
            items = data.get("events") if isinstance(data, dict) else None
            items = items if isinstance(items, list) else []
            if debug:
                print(f"  Sky IT {names[cid]} {day}: {len(items)} programmes")
            if not items and day == days[0]:
                break
            for it in items:
                try:
                    start = datetime.fromisoformat(it["starttime"].replace("Z", "+00:00")).astimezone(timezone.utc)
                    stop = datetime.fromisoformat(it["endtime"].replace("Z", "+00:00")).astimezone(timezone.utc)
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
                title = re.sub(r"\s+", " ", it.get("eventTitle") or "").strip()
                if not title or stop <= start:
                    continue
                rx = r"\b(live|diretta)\b"
                live = bool(re.match(r"\s*" + rx, title, re.I) or re.search(r"[(-]\s*" + rx + r"\s*\)?\s*$", title, re.I))
                title = re.sub(r"^\s*" + rx + r"\s*[:\-]?\s*|\s*[(-]\s*" + rx + r"\s*\)?\s*$", "", title,
                               flags=re.I).strip() or title
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": pick_desc(it, "eventSynopsis", "epgEventSynopsis")}
    out = {}
    for cid, evs in events.items():
        if not evs:
            continue
        name = names[cid]
        if name in out and len(evs) <= len(out[name]):
            continue                                  # same channel listed twice: keep the fuller one
        out[name] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Germany: MagentaTV web guide (anonymous web-guest session)
# --------------------------------------------------------------------------
def magenta_session():
    """Anonymous web-guest session: {'X_CSRFTOKEN': ..., 'Cookie': ...} or None."""
    body = json.dumps({"terminalid": "00:00:00:00:00:00", "mac": "00:00:00:00:00:00",
                       "terminaltype": "WEBTV", "utcEnable": 1, "timezone": "Etc/GMT0",
                       "userType": 3, "terminalvendor": "Unknown"}).encode("utf-8")
    url = MAGENTA_API + "Authenticate?SID=firstup&T=Windows_chrome_118"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=body, method="POST", headers={
                "User-Agent": MAGENTA_UA, "Content-Type": "application/json",
                "Accept": "application/json", "Origin": "https://web.magentatv.de",
                "Referer": "https://web.magentatv.de/"})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                cookies = {}
                for line in resp.headers.get_all("Set-Cookie") or []:
                    m = re.match(r"\s*(JSESSIONID|CSESSIONID|CSRFSESSION)=([^;]+)", line)
                    if m:
                        cookies.setdefault(m.group(1), m.group(2))
                token = (json.load(resp) or {}).get("csrfToken")
            if token:
                return {"X_CSRFTOKEN": token, "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())}
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(2 * (attempt + 1))
    print("  WARNING: MagentaTV guest session could not be started - Germany skipped", file=sys.stderr)
    return None


def magenta_time(text):
    """'2024-11-05 15:37:03 UTC+01:00' -> aware UTC datetime"""
    m = re.match(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(?:\s*UTC([+-]\d{2}:?\d{2}))?", text or "")
    if not m:
        raise ValueError(text)
    off = (m.group(3) or "+00:00")
    off = off if ":" in off else off[:3] + ":" + off[3:]
    return datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}{off}").astimezone(timezone.utc)


def fetch_germany(days, ids, debug=False):
    """{channel number: [{start, stop, title, sub, live}]}"""
    sess = magenta_session()
    if not sess:
        return {}
    headers = {"User-Agent": MAGENTA_UA, "Content-Type": "application/json", "Accept": "application/json",
               "Origin": "https://web.magentatv.de", "Referer": "https://web.magentatv.de/", **sess}
    out = {}
    for cid in [c.strip() for c in ids.split(",") if c.strip()]:
        evs = {}
        for day in days:
            nxt = day + timedelta(days=1)
            body = {"count": -1, "isFillProgram": 1, "offset": 0,
                    "properties": [{"include": "endtime,genres,id,name,starttime,channelid,subName,introduce",
                                    "name": "playbill"}],
                    "type": 2, "begintime": f"{day:%Y%m%d}000000", "channelid": cid,
                    "endtime": f"{nxt:%Y%m%d}000000"}
            data = post_json(MAGENTA_API + "PlayBillList", body, headers) or {}
            items = data.get("playbilllist") if isinstance(data, dict) else None
            items = items if isinstance(items, list) else []
            if debug:
                print(f"  MagentaTV {DE_CHANNELS.get(cid, cid)} {day}: {len(items)} programmes")
            if not items and day == days[0]:
                break
            for it in items:
                try:
                    start, stop = magenta_time(it.get("starttime")), magenta_time(it.get("endtime"))
                except ValueError:
                    continue
                title = re.sub(r"\s+", " ", it.get("name") or "").strip()
                sub = re.sub(r"\s+", " ", it.get("subName") or "").strip()
                if not title or stop <= start:
                    continue
                rx = r"\b(live|live-übertragung|live übertragung)\b"
                live = bool(re.search(r"^\s*" + rx + r"|[(\-:]\s*" + rx + r"\s*\)?\s*$", title, re.I)
                            or re.search(r"^\s*" + rx, sub, re.I))
                title = re.sub(r"^\s*" + rx + r"\s*[:\-]?\s*|\s*[(\-:]\s*" + rx + r"\s*\)?\s*$", "", title,
                               flags=re.I).strip() or title
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": sub, "live": live,
                              "desc": pick_desc(it, "introduce")}
        if evs:
            out[cid] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Sweden / Norway / Denmark: Allente TV guides
# --------------------------------------------------------------------------
NORDIC_OFFAIR = (r"^(sändningsuppehåll|airing break|sendepause|sendingspause|udsendelsespause|pause|slutt|ophold"
                 r"|ei lähetystä|lähetystauko)$")
NORDIC_LIVE = r"\b(live|direkt|direkte|direktesendt|direkte sendt|suora|suorana|suora lähetys)\b"


def fetch_allente(tld, days, ids, debug=False):
    """{channel number: [{start, stop, title, sub, live}]} from allente.<tld>"""
    wanted = [c.strip() for c in ids.split(",") if c.strip()]
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json, */*",
            "Referer": f"https://www.allente.{tld}/tv-guide/"}
    per = {c: {} for c in wanted}
    for day in days:
        data = get_json_url(ALLENTE_GUIDE.format(tld=tld, day=day), hdrs) or {}
        chans = data.get("channels") if isinstance(data, dict) else None
        chans = {str(c.get("id")): c for c in chans if isinstance(c, dict)} if isinstance(chans, list) else {}
        if debug:
            print(f"  Allente .{tld} {day}: {len(chans)} channels, "
                  f"{sum(len((chans.get(c) or {}).get('programs') or []) for c in wanted)} programmes on the chosen ones")
        for cid in wanted:
            for pr in (chans.get(cid) or {}).get("programs") or []:
                try:
                    start = datetime.fromisoformat(pr["eventStart"].replace("Z", "+00:00")).astimezone(timezone.utc)
                    stop = datetime.fromisoformat(pr["eventEnd"].replace("Z", "+00:00")).astimezone(timezone.utc)
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
                title = re.sub(r"\s+", " ", pr.get("title") or "").strip()
                if not title or re.match(NORDIC_OFFAIR, title, re.I) or stop <= start:
                    continue
                live = bool(re.match(r"\s*" + NORDIC_LIVE, title, re.I)
                            or re.search(r"[(\-:]\s*" + NORDIC_LIVE + r"\s*\)?\s*$", title, re.I)
                            or any(re.search(NORDIC_LIVE, str(t), re.I) for t in pr.get("tags") or []))
                title = re.sub(r"^\s*" + NORDIC_LIVE + r"\s*[:\-]?\s*|\s*[(\-:]\s*" + NORDIC_LIVE + r"\s*\)?\s*$",
                               "", title, flags=re.I).strip() or title
                per[cid][start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                                   "desc": pick_desc(pr, "shortDescription", "description", "details.description")}
    return {cid: [evs[k] for k in sorted(evs)] for cid, evs in per.items() if evs}


# --------------------------------------------------------------------------
# SuperSport Africa: DStv TV guide
# --------------------------------------------------------------------------
def ss_name(raw):
    """'BLITZ' / 'SS Blitz Nigeria' -> 'SuperSport Blitz'; 'ESPN 2 HD' -> 'ESPN 2'; 'WWE Channel' -> 'WWE'"""
    n = re.sub(r"\s+", " ", raw or "").strip()
    n = re.sub(r"\s*\((P|HD)\)$|\s+HD$|\s+Nigeria$|\s+SA$", "", n, flags=re.I).strip()
    if re.match(r"(ESPN|WWE)\b", n, re.I):
        return re.sub(r"(?i)^wwe channel$", "WWE", n).replace("Espn", "ESPN")
    n = re.sub(r"^(SS|SuperSport)\s+", "", n, flags=re.I)
    words = [w.upper() if w.upper() in ("PSL", "OTT", "UFC", "NBA", "TV") else
             (w.capitalize() if (w.isupper() or w.islower() or w.lower() == "motorsport") else w) for w in n.split()]
    return "SuperSport " + " ".join(words) if words else raw


def fetch_dstv(country, extra, zone, days, lo, hi, debug=False):
    """{tidy channel name: [{start, stop, title, sub, live}]} for DStv channel numbers lo..hi"""
    tz, events, names = ZoneInfo(zone), {}, {}
    for day in days:
        data = get_json_url(DSTV_GUIDE.format(day=day, extra=extra, country=country), DSTV_HEADERS) or {}
        chans = data.get("Channels") if isinstance(data, dict) else None
        chans = chans if isinstance(chans, list) else []
        picked = 0
        for ch in chans:
            num = str(ch.get("Number") or "")
            if not (num.isdigit() and lo <= int(num) <= hi) or not ch.get("Name"):
                continue
            picked += 1
            names[num] = ss_name(ch["Name"])
            evs = events.setdefault(num, {})
            for pr in ch.get("Programmes") or []:
                try:
                    start = datetime.fromisoformat(pr["StartTime"][:19]).replace(tzinfo=tz).astimezone(timezone.utc)
                    stop = datetime.fromisoformat(pr["EndTime"][:19]).replace(tzinfo=tz).astimezone(timezone.utc)
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", pr.get("Title") or "").strip()
                if not title or stop <= start:
                    continue
                live = bool(re.match(r"(live|l)\s*[:/]\s*", title, re.I) or re.search(r"\(live\)\s*$", title, re.I))
                title = re.sub(r"^(live|l)\s*[:/]\s*|\s*\(live\)\s*$", "", title, flags=re.I).strip() or title
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": pick_desc(pr, "Synopsis", "ShortSynopsis", "Description")}
        if debug:
            print(f"  DStv {country} {day}: {len(chans)} channels, {picked} in {lo}-{hi}")
    out = {}
    for num, evs in events.items():
        name = names[num]
        if evs and (name not in out or len(evs) > len(out[name])):
            out[name] = [evs[k] for k in sorted(evs)]   # same tidy name twice (e.g. HD copy): keep the fuller
    return out


# --------------------------------------------------------------------------
# beIN SPORTS Asia-Pacific: beIN's own API
# --------------------------------------------------------------------------
def bein_region_channels(codes, debug=False):
    """(region code used, {channel id: name}) - the first of codes that beIN answers."""
    for code in codes:
        data = get_json_url(f"{BEIN_API}tv-channel?region={code}", BEIN_HEADERS)
        rows = (data.get("rows") if isinstance(data, dict) else None) or []
        found = {str(r.get("id")): re.sub(r"\s+", " ", r.get("name") or "").strip()
                 for r in rows if isinstance(r, dict) and r.get("id") and r.get("name")}
        if debug:
            print(f"  beIN region {code}: {len(found)} channel(s)")
        if found:
            return code, found
    return None, {}


def bein_events(ids, days, debug=False):
    """{channel id: {start: event}} - all ids in one request per day, else one by one."""
    per = {i: {} for i in ids}
    by_upper = {i.upper(): i for i in ids}            # beIN may change the letters' case
    why = {}                                          # --debug: reasons programmes were dropped
    seen_ids = set()
    saved = [False]

    def take(rows, asked=None):
        """asked: the one channel this request was for - its programmes count even if
        beIN labels them differently (as iptv-org does)."""
        n = 0
        for it in rows:
            if not isinstance(it, dict):
                why["not a programme"] = why.get("not a programme", 0) + 1
                continue
            raw = str(it.get("channelId") or "")
            seen_ids.add(raw or "(none)")
            cid = by_upper.get(raw.upper()) or asked
            if cid not in per:
                why["unknown channel"] = why.get("unknown channel", 0) + 1
                continue
            try:
                start = datetime.fromisoformat(it["startDate"].replace("Z", "+00:00")).astimezone(timezone.utc)
                stop = datetime.fromisoformat(it["endDate"].replace("Z", "+00:00")).astimezone(timezone.utc)
            except (KeyError, TypeError, ValueError, AttributeError):
                why["unreadable times"] = why.get("unreadable times", 0) + 1
                continue
            title = re.sub(r"\s+", " ", it.get("title") or "").strip()
            if not title or stop <= start:
                why["no title or bad times"] = why.get("no title or bad times", 0) + 1
                continue
            comp = re.sub(r"\s+", " ", ((it.get("data") or {}).get("title") or "")).strip()
            rx = r"\b(live)\b"
            live = bool(re.match(r"\s*\(?" + rx, title, re.I) or re.search(r"[(\-:]\s*" + rx + r"\s*\)?\s*$", title, re.I))
            title = re.sub(r"^\s*\(?" + rx + r"\)?\s*[:\-]?\s*|\s*[(\-:]\s*" + rx + r"\s*\)?\s*$", "", title,
                           flags=re.I).strip() or title
            per[cid][start] = {"start": start, "stop": stop, "title": title,
                               "sub": comp if comp and comp.lower() != title.lower() else "", "live": live,
                               "desc": pick_desc(it, "description", "synopsis")}
            n += 1
        return n

    def rows_of(data, label):
        rows = (data.get("rows") if isinstance(data, dict) else data if isinstance(data, list) else None) or []
        if debug and rows and not saved[0]:          # keep one real answer for a closer look
            saved[0] = True
            name = f"bein_debug_{label}.json"
            try:
                with open(name, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
                print(f"    saved one beIN answer to {name}")
            except OSError:
                pass
        return rows

    for day in days:
        nxt = day + timedelta(days=1)
        window = f"startBefore={nxt:%Y-%m-%d}T00:00:00.000Z&endAfter={day:%Y-%m-%d}T00:00:00.000Z"
        data = get_json_url(f"{BEIN_API}tv-event?&{window}&channelIds={','.join(ids)}", BEIN_HEADERS,
                            quiet=len(ids) > 1)            # one-by-one requests follow if it fails
        rows = rows_of(data, "all")
        n = take(rows, ids[0] if len(ids) == 1 else None)
        if debug:
            print(f"    combined request: {'no answer' if data is None else f'{len(rows)} row(s)'}")
        if not n and len(ids) > 1:                      # the combined request didn't work: one by one
            for cid in ids:
                data = get_json_url(f"{BEIN_API}tv-event?&{window}&channelIds={cid}", BEIN_HEADERS)
                rows = rows_of(data, cid[:8])
                got = take(rows, cid)
                n += got
                if debug:
                    print(f"    channel {cid[:8]}…: {'no answer' if data is None else f'{len(rows)} row(s)'}, {got} kept")
        if debug:
            print(f"  beIN {day}: {n} programme(s) on {len(ids)} channel(s)")
            if why:
                print(f"    dropped: {why}; channel labels seen: {sorted(seen_ids)[:6]}")
                why.clear()
    return per


def fetch_bein(days, countries, debug=False):
    """{country code: {channel name: [{start, stop, title, sub, live}]}}"""
    out, used = {}, []
    for cc in [c.strip().lower() for c in countries.split(",") if c.strip()]:
        if cc not in BEIN_COUNTRIES:
            print(f"  WARNING: unknown beIN country '{cc}' (use {','.join(BEIN_COUNTRIES)})", file=sys.stderr)
            continue
        place, _, codes, fallback = BEIN_COUNTRIES[cc]
        code, chans = bein_region_channels(codes, debug)
        if not chans and fallback:
            code, chans = "built-in list", dict(fallback)
        if not chans:
            print(f"  beIN {place}: no channel list from beIN - skipped")
            continue
        if any(set(chans) == u for u in used):
            print(f"  beIN {place}: beIN returned the same channels as another country - skipped")
            continue
        used.append(set(chans))
        if debug:
            print(f"  beIN {place} ({code}): {sorted(set(chans.values()))}")
        per = bein_events(sorted(chans), days, debug)
        got = {}
        for cid, evs in per.items():
            name = chans[cid]
            if evs and (name not in got or len(evs) > len(got[name])):
                got[name] = [evs[k] for k in sorted(evs)]   # same-named feeds: keep the fullest
        if got:
            out[cc] = got
    return out


# --------------------------------------------------------------------------
# France: SFR TV guide
# --------------------------------------------------------------------------
def short_desc(text, limit=300):
    """A description cut to about limit characters, at the end of a sentence where possible."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[:end + 1] if end > limit // 3 else cut.rsplit(" ", 1)[0] + " …"


def pick_desc(item, *keys):
    """The first non-empty description among keys ('a.b' looks inside a nested dict), shortened."""
    for key in keys:
        v = item
        for part in key.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        if isinstance(v, str) and v.strip():
            return short_desc(v)
    return ""


def fetch_france(days, ids, debug=False):
    """{channel number: [{start, stop, title, sub, live}]}"""
    wanted = [c.strip() for c in ids.split(",") if c.strip()]
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json, */*",
            "Origin": "https://tv.sfr.fr", "Referer": "https://tv.sfr.fr/"}
    per = {c: {} for c in wanted}
    for day in days:
        data = get_json_url(SFR_GUIDE.format(day=day), hdrs) or {}
        epg = data.get("epg") if isinstance(data, dict) else None
        epg = epg if isinstance(epg, dict) else {}
        if debug:
            print(f"  SFR {day}: {len(epg)} channels in file, "
                  f"{sum(len(epg.get(c) or []) for c in wanted)} programmes on the chosen ones")
            sample = next((it for c in wanted for it in epg.get(c) or []
                           if isinstance(it, dict) and re.search(r"football|ligue", str(it.get("title")), re.I)), None)
            if sample and day == days[0]:
                print(f"    SFR programme fields: {sorted(sample)}")
                for k in ("title", "subTitle", "genre", "longSynopsis", "shortSynopsis", "synopsis", "description"):
                    if sample.get(k):
                        print(f"    {k}: {str(sample[k])[:160]!r}")
        for cid in wanted:
            for it in epg.get(cid) or []:
                try:
                    start = datetime.fromtimestamp(int(it["startDate"]) / 1000, timezone.utc)
                    stop = datetime.fromtimestamp(int(it["endDate"]) / 1000, timezone.utc)
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", it.get("title") or "").strip()
                sub = re.sub(r"\s+", " ", it.get("subTitle") or "").strip()
                desc = pick_desc(it, "longSynopsis", "shortSynopsis", "synopsis", "description")
                if not title or stop <= start:
                    continue
                rx = r"\b(en direct|direct|live)\b"
                live = bool(it.get("isLive")) or bool(re.search(r"[(\-:]\s*" + rx + r"\s*\)?\s*$", title, re.I))
                title = re.sub(r"\s*[(\-:]\s*" + rx + r"\s*\)?\s*$", "", title, flags=re.I).strip() or title
                per[cid][start] = {"start": start, "stop": stop, "title": title,
                                   "sub": sub if sub != title else "", "live": live,
                                   "desc": desc if desc not in (title, sub) else ""}
    return {cid: [evs[k] for k in sorted(evs)] for cid, evs in per.items() if evs}


# --------------------------------------------------------------------------
# Switzerland: Swisscom blue TV guide
# --------------------------------------------------------------------------
CH_LIVE = r"\b(live|en direct|direct|diretta|in diretta)\b"


def fetch_switzerland(days, ids, debug=False):
    """{channel number: [{start, stop, title, sub, live}]}"""
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json, */*",
            "Origin": "https://tv.blue.ch", "Referer": "https://tv.blue.ch/"}
    out = {}
    for cid in [c.strip() for c in ids.split(",") if c.strip()]:
        evs = {}
        for day in days:
            data = get_json_url(BLUE_GUIDE.format(cid=urllib.parse.quote(cid, safe=""), day=day,
                                                  nxt=day + timedelta(days=1)), hdrs) or {}
            nodes = ((data.get("Nodes") or {}).get("Items") or []) if isinstance(data, dict) else []
            items = []
            for n in nodes:
                if isinstance(n, dict) and n.get("Kind") == "Channel":
                    items = [b for b in (((n.get("Content") or {}).get("Nodes") or {}).get("Items") or [])
                             if isinstance(b, dict) and b.get("Kind") == "Broadcast"]
                    break
            if debug:
                print(f"  blue TV {CH_CHANNELS.get(cid, (0, cid))[1]} {day}: {len(items)} programmes")
            if not items and day == days[0]:
                break
            for b in items:
                av = (b.get("Availabilities") or [{}])[0]
                desc = ((b.get("Content") or {}).get("Description") or {})
                try:
                    start = datetime.fromisoformat(av["AvailabilityStart"].replace("Z", "+00:00")).astimezone(timezone.utc)
                    stop = datetime.fromisoformat(av["AvailabilityEnd"].replace("Z", "+00:00")).astimezone(timezone.utc)
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
                title = re.sub(r"\s+", " ", desc.get("Title") or "").strip()
                if not title or title == "Sendepause" or stop <= start:
                    continue
                live = bool(re.match(r"\s*" + CH_LIVE, title, re.I)
                            or re.search(r"[(\-:]\s*" + CH_LIVE + r"\s*\)?\s*$", title, re.I))
                title = re.sub(r"^\s*" + CH_LIVE + r"\s*[:\-]?\s*|\s*[(\-:]\s*" + CH_LIVE + r"\s*\)?\s*$", "",
                               title, flags=re.I).strip() or title
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": pick_desc(desc, "Summary", "ShortSummary")}
        if evs:
            out[cid] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# India: Tata Play guide
# --------------------------------------------------------------------------
def tataplay_time(value):
    """ISO text ('2025-06-09T18:00:00.000Z') or epoch milliseconds -> aware UTC datetime"""
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        v = int(value)
        return datetime.fromtimestamp(v / 1000 if v > 10**11 else v, timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def fetch_india(days, ids, debug=False):
    """{channel number: [{start, stop, title, sub, live}]}"""
    out = {}
    for cid in [c.strip() for c in ids.split(",") if c.strip()]:
        evs = {}
        for day in days:
            data = post_json(TATAPLAY_GUIDE.format(day=day), {"id": cid}, TATAPLAY_HEADERS) or {}
            time.sleep(1)                              # Tata Play says '429 Too Many Requests' if rushed
            epg = ((data.get("data") or {}).get("epg") if isinstance(data, dict) else None) or []
            epg = epg if isinstance(epg, list) else []
            if debug:
                print(f"  Tata Play {IN_CHANNELS.get(cid, (0, cid))[1]} {day}: {len(epg)} programmes")
            if not epg and day == days[0]:
                break
            for pr in epg:
                try:
                    start, stop = tataplay_time(pr["startTime"]), tataplay_time(pr["endTime"])
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", pr.get("title") or "").strip()
                if not title or stop <= start:
                    continue
                rx = r"\b(live)\b"
                live = bool(re.match(r"\s*" + rx, title, re.I) or re.search(r"[(\-:]\s*" + rx + r"\s*\)?\s*$", title, re.I))
                title = re.sub(r"^\s*" + rx + r"\s*[:\-]?\s*|\s*[(\-:]\s*" + rx + r"\s*\)?\s*$", "", title,
                               flags=re.I).strip() or title
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": pick_desc(pr, "desc", "description", "synopsis")}
        if evs:
            out[cid] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Poland: Onet TV guide
# --------------------------------------------------------------------------
def parse_onet(page):
    """[(hh, mm, title, type, live, description)] in page order."""
    import html as _html
    clean = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
    i = page.find('class="emissions"')
    if i < 0:
        return []
    rows = []
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", page[i:], re.S):
        t = re.search(r'class="hour"[^>]*>\s*(\d{1,2}):(\d{2})', li)
        a = re.search(r'class="titles"[^>]*>\s*<a\b[^>]*>(.*?)</a\s*>', li, re.S)
        if not (t and a and clean(a.group(1))):
            continue
        typ = re.search(r'class="type"[^>]*>(.*?)</span>', li, re.S)
        desc = re.search(r"<p>(.*?)</p>", li, re.S)
        title, typ = clean(a.group(1)), clean(typ.group(1)) if typ else ""
        rx = r"\b(na żywo|transmisja na żywo|live)\b"
        live = bool(re.search(rx, title, re.I) or re.search(rx, typ, re.I)
                    or (desc and re.search(rx, clean(desc.group(1))[:80], re.I)))
        title = re.sub(r"\s*[-(:]?\s*" + rx + r"\s*\)?\s*$", "", title, flags=re.I).strip() or title
        rows.append((int(t.group(1)), int(t.group(2)), title, typ, live,
                     short_desc(clean(desc.group(1))) if desc else ""))
    return rows


def fetch_poland(days, slugs, debug=False):
    """{slug: [{start, title, sub, live}]}"""
    today = datetime.now(WARSAW).date()
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9"}
    out = {}
    for slug in [x.strip() for x in slugs.split(",") if x.strip()]:
        evs = {}
        for day in days:
            offset = (day - today).days
            if offset < 0:
                continue
            page = get_text(ONET_PAGE.format(slug=urllib.parse.quote(slug, safe="-"), offset=offset), {},
                            headers=hdrs, retries=2, quiet=True)
            rows = parse_onet(page) if page else []
            if debug:
                print(f"  Onet {slug} {day}: {len(rows)} programmes")
            time.sleep(1)                              # be gentle with the site
            if not rows:
                if day == days[0]:
                    break                              # channel not on the site
                continue
            last = None
            for hh, mm, title, typ, live, desc in rows:
                start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=WARSAW)
                if last and start < last:
                    start += timedelta(days=1)         # past midnight
                last = start
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title, "sub": typ, "live": live,
                            "desc": desc if desc not in (title, typ) else ""}
        if evs:
            out[slug] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Czechia: mujtvprogram.cz service
# --------------------------------------------------------------------------
def fetch_czechia(days, cids, debug=False, tz=PRAGUE):
    """{channel number: [{start, stop, title, sub, live}]} (also used for Slovakia)"""
    today = datetime.now(tz).date()
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/xml, text/xml, */*",
            "Accept-Language": "cs-CZ,cs;q=0.9"}
    out = {}
    for cid in [c.strip() for c in cids.split(",") if c.strip()]:
        evs = {}
        for day in days:
            offset = (day - today).days
            if offset < 0:
                continue
            page = get_text(MUJTV_LIST.format(cid=urllib.parse.quote(cid, safe=""), offset=offset), {},
                            headers=hdrs, retries=2, quiet=True)
            try:
                root = ET.fromstring(page.encode("utf-8")) if page else None
            except ET.ParseError:
                root = None
            items = root.findall("programme") if root is not None else []
            if debug:
                print(f"  mujtvprogram {cid} {day}: {len(items)} programmes")
            if not items and day == days[0]:
                break                                  # channel not on the site
            for it in items:
                get = lambda tag: (it.findtext(tag) or "").strip()
                try:
                    start = datetime.fromtimestamp(int(get("startDateTimeInSec")), timezone.utc)
                    stop = datetime.fromtimestamp(int(get("endDateTimeInSec")), timezone.utc)
                except ValueError:
                    continue
                title = re.sub(r"\s+", " ", get("name"))
                if not title or stop <= start:
                    continue
                rx = r"\b(živě|naživo|přímý přenos|priamy prenos|live)\b"
                live = bool(re.search(rx, title, re.I) or re.search(rx, get("shortDescription"), re.I))
                title = re.sub(r"\s*[-(]?\s*" + rx + r"\s*\)?\s*$", "", title, flags=re.I).strip() or title
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": short_desc(get("longDescription") or get("shortDescription"))}
        if evs:
            out[cid] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Albania / Kosovo: SuperSport from IPKO's web guide
# --------------------------------------------------------------------------
def post_json(url, body, headers, retries=3, quiet=False):
    return fetch(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST",
                 parse="json", retries=retries, quiet=quiet, label=f"{url} {body}")


def al_name(slug):
    """'supersport-3' -> 'SuperSport 3', 'tring-sport-1' -> 'Tring Sport 1'"""
    name = " ".join(w.capitalize() for w in slug.split("-"))
    return re.sub(r"\bSupersport\b", "SuperSport", name)


def fetch_albania(days, slugs, debug=False):
    """{channel_name: [{start, stop, title, sub, live}]}"""
    out = {}
    for slug in [x.strip() for x in slugs.split(",") if x.strip()]:
        evs = {}
        for day in days:
            frm = int(datetime(day.year, day.month, day.day, tzinfo=TIRANE).timestamp())
            nxt = day + timedelta(days=1)
            to = int(datetime(nxt.year, nxt.month, nxt.day, tzinfo=TIRANE).timestamp())
            data = post_json(IPKO_EPG, {"ch_ext_id": slug, "from": frm, "to": to}, IPKO_HEADERS) or {}
            shows = data.get("shows") if isinstance(data, dict) else None
            shows = shows if isinstance(shows, list) else []
            if debug:
                print(f"  IPKO {slug} {day}: {len(shows)} programmes")
            if not shows and day == days[0]:
                break                                  # channel not in IPKO's guide
            for sh in shows:
                try:
                    start = datetime.fromtimestamp(int(sh["show_start"]), timezone.utc)
                    stop = datetime.fromtimestamp(int(sh["show_end"]), timezone.utc)
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", sh.get("title") or "").strip()
                if not title or stop <= start:
                    continue
                rx = r"\b(live|drejtp[eë]rdrejt)\b"
                live = bool(sh.get("is_live")) or bool(re.search(rx, title, re.I))
                title = re.sub(r"\s*[-(]?\s*" + rx + r"\s*\)?\s*$", "", title, flags=re.I).strip() or title
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": pick_desc(sh, "description", "desc", "synopsis", "show_desc")}
        if evs:
            out[al_name(slug)] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Brazil: Claro TV guide
# --------------------------------------------------------------------------
def br_name(raw):
    """'SporTV 2 HD ³' -> 'SporTV 2', 'PREMIERE HD 3 ³' -> 'Premiere 3', 'Espn 4' -> 'ESPN 4'"""
    n = re.sub(r"[\u00b2\u00b3\u00b9*]+", " ", raw)
    n = re.sub(r"\b(hd|sd|fhd|uhd|4k)\b", " ", n, flags=re.I)
    n = re.sub(r"\s+", " ", n).strip()
    fixes = [(r"\bsportv\b", "SporTV"), (r"\bespn\b", "ESPN"), (r"\bpremiere\b", "Premiere"),
             (r"\bband ?sports\b", "BandSports"), (r"\bcombate\b", "Combate"),
             (r"\btnt sports\b", "TNT Sports"), (r"\bxsports\b", "Xsports"),
             (r"\bclubes\b", "Clubes")]
    for rx, good in fixes:
        n = re.sub(rx, good, n, flags=re.I)
    return n or raw.strip()


def claro_channels(pattern):
    """{site_id: clean name} for Claro channels whose name matches pattern."""
    url = (CLARO_BASE + "canal/select?q=id_cidade:1&rows=1000&wt=json&sort=cn_canal+asc"
           "&fl=id_canal+st_canal+cn_canal+nome+id_cidade&fq=nome:*")
    data = get_json_url(url, CLARO_HEADERS) or {}
    docs = ((data.get("response") or {}).get("docs") or []) if isinstance(data, dict) else []
    rx, out = re.compile(pattern, re.I), {}
    for d in docs:
        name, cid = (d.get("nome") or "").strip(), d.get("id_canal")
        if name and cid and rx.search(name) and not re.search(r"novelas|s[ée]ries", name, re.I):
            out[f"{d.get('id_cidade') or 1}_{cid}"] = br_name(name)
    if not out:
        print("  WARNING: Claro channel list not available, using the built-in list", file=sys.stderr)
        out = {k: v for k, v in BR_FALLBACK.items() if rx.search(v)}
    return out


def fetch_brazil(days, pattern, debug=False):
    """{channel_name: [{start, stop, title, sub, live}]}"""
    names = claro_channels(pattern)
    if debug:
        print(f"  Brazil: {len(names)} matching channels: {sorted(set(names.values()))}")
    if not names:
        return {}
    events = {sid: {} for sid in names}
    for day in days:
        # Exactly iptv-org's request: one channel per request, spaces written as '+'
        # (a single request for all channels was refused by Claro's server).
        d0 = f"{day.year}-{day.month}-{day.day}"
        docs = []
        for sid in sorted(names):
            url = (f"{CLARO_BASE}exibicao/select?q=id_revel:({urllib.parse.quote(sid, safe='_')})+AND+id_cidade:1"
                   f"&wt=json&rows=100000&start=0&sort=id_canal+asc,dh_inicio+asc"
                   f"&fl=dh_fim+dh_inicio+st_titulo+titulo+id_programa+id_canal+id_cidade"
                   f"&fq=dh_inicio:[{d0}T00:00:00Z+TO+{d0}T23:59:00Z]")
            data = get_json_url(url, CLARO_HEADERS) or {}
            docs += ((data.get("response") or {}).get("docs") or []) if isinstance(data, dict) else []
            time.sleep(1)                              # Claro's server errors when pressed
        if debug:
            print(f"  Claro {day}: {len(docs)} programmes on {len(names)} channel(s)")
        for d in docs:
            sid = f"{d.get('id_cidade') or 1}_{d.get('id_canal')}"
            if sid not in events:
                continue
            try:                                  # local Brasilia time, despite the "Z"
                start = datetime.fromisoformat(d["dh_inicio"].rstrip("Z")[:16]).replace(tzinfo=SAO_PAULO)
                stop = datetime.fromisoformat(d["dh_fim"].rstrip("Z")[:16]).replace(tzinfo=SAO_PAULO)
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
            title = re.sub(r"\s+", " ", d.get("titulo") or "").strip()
            if not title or stop <= start:
                continue
            live = bool(re.search(r"\bao vivo\b", title, re.I))
            title = re.sub(r"\s*[-(]?\s*\bao vivo\b\s*\)?\s*$", "", title, flags=re.I).strip() or title
            key = start.astimezone(timezone.utc)
            events[sid][key] = {"start": key, "stop": stop.astimezone(timezone.utc),
                                "title": title, "sub": "", "live": live}
    out = {}
    for sid, evs in events.items():
        if not evs:
            continue
        name = names[sid]
        if name in out and len(evs) <= len(out[name]):
            continue                              # SD and HD copies: keep the fuller one
        out[name] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# epgshare01.online: ready-made XMLTV files, one per country (free, no login)
# --------------------------------------------------------------------------
EPGSHARE_URL = "{scheme}://epgshare01.online/epgshare01/epg_ripper_{file}.xml.gz"
EPGSHARE = {   # group -> file, id prefix, place, time zone, English?, {id part: (name, [epgshare ids, best first])}
    "turkey": {"file": "TR1", "prefix": "TR", "place": "Turkey", "tz": "Europe/Istanbul", "english": False,
               "channels": {
                   "beINSPORTS1": ("beIN SPORTS 1", ["beIN.SPORTS.1.tr", "Beinsports.tr"]),
                   "beINSPORTS2": ("beIN SPORTS 2", ["beIN.SPORTS.2.tr", "Beinsports.2.tr"]),
                   "beINSPORTS3": ("beIN SPORTS 3", ["beIN.SPORTS.3.tr", "Beinsports.3.tr"]),
                   "beINSPORTS4": ("beIN SPORTS 4", ["beIN.SPORTS.4.tr", "Beinsports.4.tr"]),
                   "beINSPORTSMAX1": ("beIN SPORTS MAX 1", ["beIN.SPORTS.MAX.1.tr"]),
                   "beINSPORTSMAX2": ("beIN SPORTS MAX 2", ["beIN.SPORTS.MAX.2.tr"]),
                   "beINSPORTSHABER": ("beIN SPORTS HABER", ["beIN.SPORTS.HABER.HD.tr", "Bein.Sports.Haber.tr"]),
                   "SSport": ("S Sport", ["SSport.tr"]),
                   "SSport2": ("S Sport 2", ["SSport.2.tr"]),
                   "TRTSpor": ("TRT Spor", ["TRT.SPOR.HD.tr", "TRT.SPOR.tr"]),
                   "ASpor": ("A Spor", ["A.SPOR.HD.tr", "A.SPOR.tr"]),
               }},
    "latvia": {"file": "LV1", "prefix": "LV", "place": "Latvia", "tz": "Europe/Riga", "english": False,
               "channels": {
                   "GO3Sport1": ("GO3 Sport 1", ["Go3.Sport.1.HD.lv"]),
                   "GO3Sport2": ("GO3 Sport 2", ["Go3.Sport.2.HD.lv"]),
                   "GO3Sport3": ("GO3 Sport 3", ["Go3.Sport.3.HD.lv"]),
                   "GO3SportOpen": ("GO3 Sport Open", ["Go3.Sport.Open.HD.lv"]),
                   "Best4Sport": ("Best4Sport", ["Best4Sport.TV.HD.lv"]),
                   "Best4Sport2": ("Best4Sport 2", ["Best4Sport.TV-2.HD.lv"]),
                   "SetantaSports": ("Setanta Sports", ["Setanta.Sports.1.HD.lv"]),
                   "SetantaSports2": ("Setanta Sports 2", ["Setanta.Sports.2.HD.lv"]),
               }},
    "hk": {"file": "HK1", "prefix": "HK", "place": "Hong Kong", "tz": "Asia/Hong_Kong", "english": True,
           "channels": {
               **{f"beINSPORTS{n}": (f"beIN SPORTS {n} HK", [f"beIN.SPORTS.{n}.hk"]) for n in range(1, 7)},
               **{f"NowSports{n}": (f"Now Sports {n}", [f"Now.Sports.{n}.hk"]) for n in range(1, 8)},
               "NowSportsPrime": ("Now Sports Prime", ["Now.Sports.Prime.hk"]),
               "NowSportsPlus": ("Now Sports Plus", ["Now.Sports.Plus.hk"]),
               **{f"NowSportsPL{n}": (f"Now Sports Premier League {n}", [f"Now.Sports.Premier.League.{n}.hk"])
                  for n in range(1, 8)},
               "NowSportsPLTV": ("Now Sports Premier League TV", ["Now.Sports.Premier.League.TV.hk"]),
           }},
    "id": {"file": "ID1", "prefix": "ID", "place": "Indonesia", "tz": "Asia/Jakarta", "english": False,
           "channels": {
               "beINSPORTS1": ("beIN SPORTS 1 ID", ["beIN.Sports.1.HD.id", "beIN.Sports.1.id", "Bein.1.id"]),
               "beINSPORTS2": ("beIN SPORTS 2 ID", ["beIN.Sports.2.HD.id", "beIN.Sports.2.id", "Bein.2.id"]),
               "beINSPORTS3": ("beIN SPORTS 3 ID", ["beIN.Sports.3.HD.id", "beIN.Sports.3.id", "Bein.3.id"]),
               "beINSPORTS4": ("beIN SPORTS 4 ID", ["beIN.SPORTS.4.id"]),
               "beINSPORTS5": ("beIN SPORTS 5 ID", ["beIN.SPORTS.5.id"]),
               "SPOTV": ("SPOTV ID", ["SPOTV.HD.id", "SPOTV.id"]),
               "SPOTV2": ("SPOTV 2 ID", ["SPOTV.2.HD.id", "SPOTV.2.id"]),
               **{f"ChampionsTV{n}": (f"Champions TV {n}", [f"Champions.TV.{n}.id"]) for n in (1, 2, 3, 5, 6)},
               "Sportstars": ("Sportstars", ["Sportstars.HD.id", "Sportstars.id"]),
               "Sportstars2": ("Sportstars 2", ["Sportstars.2.HD.id", "Sportstars.2.id"]),
               "Sportstars3": ("Sportstars 3", ["sportstars.3.HD.id", "Sportstars.3.id"]),
               "Sportstars4": ("Sportstars 4", ["Sportstars.4.HD.id", "Sportstars.4.id"]),
               "SoccerChannel": ("Soccer Channel", ["Soccer.Channel.HD.id", "Soccer.Channel.id"]),
           }},
    "mena": {"file": "BEIN1", "prefix": "MENA", "place": "Qatar", "tz": "Asia/Qatar", "english": True,
             "channels": {
                 **{f"beINSPORTS{n}": (f"beIN SPORTS {n} MENA", [f"beIN_SPORTS{n}_DIGITAL_Mono_EN.bein",
                                                                f"beIN_SPORTS{n}_DIGITAL_Mono_AR.bein"])
                    for n in range(1, 8) if n != 6},
                 "beINSPORTS6": ("beIN SPORTS 6 MENA", ["beIN_SPORTS66_DIGITAL_Mono-01_EN.bein",
                                                         "beIN_SPORTS6_DIGITAL_Mono-d-1_AR.bein"]),
                 "beINSPORTS8": ("beIN SPORTS 8 MENA", ["logos-_beINSPORTS8_EN.bein", "logos-_beINSPORTS8_AR.bein"]),
                 "beINSPORTS9": ("beIN SPORTS 9 MENA", ["logos-_beINSPORTS9_EN.bein", "logos-_beINSPORTS9_AR.bein"]),
                 "beINSPORTSEnglish1": ("beIN SPORTS English 1 MENA", ["beIN_SPORTS1_ENGLISH_Digital_Mono_EN.bein"]),
                 "beINSPORTSEnglish2": ("beIN SPORTS English 2 MENA", ["beIN_SPORTS2_ENGLISH_Digital_Mono_EN.bein"]),
                 "beINSPORTSFrench1": ("beIN SPORTS French 1 MENA", ["beIN_SPORTS1_FRENCH_Digital_Mono_EN.bein"]),
                 "beINSPORTSFrench2": ("beIN SPORTS French 2 MENA", ["beIN_SPORTS2_FRENCH_Digital_Mono_EN.bein"]),
                 **{f"beINSPORTSMAX{n}": (f"beIN SPORTS MAX {n} MENA", [f"beIN_SPORTS_MAX{n}_DIGITAL_Mono_EN.bein",
                                                                       f"beIN_SPORTS_MAX{n}_DIGITAL_Mono_AR.bein"])
                    for n in range(1, 7)},
                 "beINSPORTSXTRA1": ("beIN SPORTS XTRA 1 MENA", ["beIN_SPORTS_XTRA1_Digital_Mono_EN.bein"]),
                 "beINSPORTSXTRA2": ("beIN SPORTS XTRA 2 MENA", ["beIN_SPORTS_XTRA2_Digital_Mono_EN.bein"]),
                 "beINSPORTSXTRA3": ("beIN SPORTS XTRA 3 MENA", ["logos-_beINSPORTSXTRA3_EN.bein"]),
                 **{f"beINSPORTSXTRA{n}": (f"beIN SPORTS XTRA {n} MENA",
                                           [f"beIN_SPORTS_XTRA_0{n}_bein.com_EN.bein", f"beIN_SPORTS_XTRA_0{n}_Bein.com_EN.bein"])
                    for n in range(4, 9)},
                 "beINSPORTSXTRA9": ("beIN SPORTS XTRA 9 MENA", ["beIN_SPORTS_XTRA_Digital_09_Bein.com_EN.bein"]),
                 "beINSPORTSNews": ("beIN SPORTS News MENA", ["NEWS_DIGITAL_Mono_EN.bein", "NEWS_DIGITAL_Mono_AR.bein"]),
                 "beINSPORTSFTA": ("beIN SPORTS FTA MENA", ["bein_SPORTS_FTA_DIGITAL_Mono_EN.bein"]),
                 **{f"Alkass{n}": (f"Alkass {n}", [f"Alkass_{n}_EN.bein", f"Alkass_{n}_AR.bein"]) for n in range(1, 9)},
             }},
}
EPGSHARE_LIVE = (r"\b(live|canlı|canli|tiešraide|tiesraide|langsung|siaran langsung|"
                 r"直播|現場直播|مباشر)\b|\(c\)\s*$|\bL\s*$")


def xmltv_stamp(text):
    """'20261016180000 +0300' -> aware UTC datetime"""
    text = (text or "").strip()
    try:
        return datetime.strptime(text[:20], "%Y%m%d%H%M%S %z").astimezone(timezone.utc)
    except ValueError:
        return datetime.strptime(text[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def fetch_epgshare(group, days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for one EPGSHARE group."""
    import gzip as _gzip
    cfg = EPGSHARE[group]
    raw = None
    for scheme in ("https", "http"):                   # the site's own advice: try http if https fails
        raw = fetch(EPGSHARE_URL.format(scheme=scheme, file=cfg["file"]), headers={"User-Agent": HEADERS["User-Agent"]},
                    parse="bytes", retries=2, quiet=(scheme == "https"))
        if raw:
            break
    if not raw:
        return {}
    try:
        data = _gzip.decompress(raw)
    except OSError:
        data = raw                                     # already plain XML
    wanted = {eid for _, alts in cfg["channels"].values() for eid in alts}
    tz = ZoneInfo(cfg["tz"])
    first = datetime(days[0].year, days[0].month, days[0].day, tzinfo=tz).astimezone(timezone.utc)
    last_day = days[-1] + timedelta(days=1)
    end = datetime(last_day.year, last_day.month, last_day.day, tzinfo=tz).astimezone(timezone.utc)
    per = {}                                           # epgshare id -> {start: event}
    seen_ids = set()

    def pick(el, tag):
        """Text of the English child if there is one, else the first."""
        kids = el.findall(tag)
        best = next((k for k in kids if (k.get("lang") or "").lower().startswith("en")), kids[0] if kids else None)
        return re.sub(r"\s+", " ", (best.text or "") if best is not None else "").strip()

    try:
        for _, el in ET.iterparse(io.BytesIO(data), events=("end",)):
            if el.tag == "channel":
                seen_ids.add(el.get("id"))
                el.clear()
                continue
            if el.tag != "programme":
                continue
            eid = el.get("channel")
            if eid in wanted:
                try:
                    start, stop = xmltv_stamp(el.get("start")), xmltv_stamp(el.get("stop"))
                except ValueError:
                    start = stop = None
                title = pick(el, "title")
                if start and stop and stop > start and title and start < end and stop > first:
                    sub, desc = pick(el, "sub-title"), pick(el, "desc")
                    live = bool(re.search(EPGSHARE_LIVE, title, re.I) or el.find("live") is not None)
                    title = re.sub(r"^\s*(live|canlı|canli)\s*[:\-]\s*|\s*[-(:]?\s*\(?\b(live|canlı|canli|"
                                   r"tiešraide|langsung)\b\)?\s*$|\s*\(c\)\s*$", "", title, flags=re.I).strip() or title
                    per.setdefault(eid, {})[start] = {
                        "start": start, "stop": stop, "title": title, "sub": sub if sub != title else "",
                        "live": live, "desc": short_desc(desc) if desc not in (title, sub) else ""}
            el.clear()
    except ET.ParseError as e:
        print(f"  WARNING: epgshare01 {cfg['file']} could not be read completely ({e})", file=sys.stderr)
    out = {}
    for part, (name, alts) in cfg["channels"].items():
        best = max(alts, key=lambda a: len(per.get(a) or {}))
        evs = per.get(best) or {}
        if debug:
            print(f"    {name}: {len(evs)} programmes from {best}"
                  + ("" if any(a in seen_ids for a in alts) else " (channel not in the file)"))
        if evs:
            out[part] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Translation (Hebrew / Greek -> English), cached
# --------------------------------------------------------------------------
FOREIGN = re.compile(r"[\u0590-\u05FF\u0600-\u06FF\u0370-\u03FF\u1F00-\u1FFF\u0400-\u04FF\u0900-\u0DFF\u0E00-\u0E7F"
                     r"\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]")
# Hebrew, Greek, Cyrillic, Indian scripts (Devanagari, Tamil ...), Thai, Japanese, Chinese, Korean
TRANSLATIONS = {}
DESC_USED = {}            # translated description -> last day it was in the guide (old ones are dropped)
DESC_KEEP_DAYS = 14
DESC_PENDING = set()      # descriptions not translated yet: left out of the guide this run
ENGLISH_PLACES = {"Australia", "Malaysia", "Singapore", "Hong Kong", "Thailand",
                  "South Africa", "Africa", "India", "Qatar"}   # their guides are already in English
GOOGLE_LIMITED = [False]  # Google said 'too many requests': stop translating for the rest of this run
GOOGLE_WHY = [""]         # the reason the last translation failed, for the summary line


def load_cache():
    path = CACHE_FILE if os.path.exists(CACHE_FILE) else OLD_CACHE_FILE
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        TRANSLATIONS.update({k: v for k, v in data.items() if isinstance(v, str)})
        used = data.get("__desc_used__")
        DESC_USED.update({k: v for k, v in (used if isinstance(used, dict) else {}).items()
                          if isinstance(v, str)})
    except (OSError, ValueError, AttributeError):
        pass


def save_cache():
    oldest = (date.today() - timedelta(days=DESC_KEEP_DAYS)).isoformat()
    for text, day in list(DESC_USED.items()):
        if day < oldest:                               # a description not seen for a while
            DESC_USED.pop(text, None)
            TRANSLATIONS.pop(text, None)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({**TRANSLATIONS, "__desc_used__": DESC_USED}, f, ensure_ascii=False, indent=1,
                      sort_keys=True)
    except OSError as e:
        print(f"WARNING: could not save translations: {e}", file=sys.stderr)


def google_translate(text):
    if GOOGLE_LIMITED[0]:
        return None
    params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text}
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
    for attempt in range(2):
        try:
            time.sleep(1.0)
            req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as resp:
                data = json.load(resp)
            out = "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
            if out:
                return out
        except urllib.error.HTTPError as e:
            GOOGLE_WHY[0] = f"HTTP {e.code} {e.reason}"
            if e.code == 429:
                GOOGLE_LIMITED[0] = True     # rate limited: keep the original text this run
                return None
        except (urllib.error.URLError, TimeoutError, ValueError, IndexError, TypeError) as e:
            GOOGLE_WHY[0] = f"{type(e).__name__}: {e}"[:120]
        time.sleep(3 * (attempt + 1))
    return None


def translate_all(texts, force=()):
    """Translate texts in Hebrew/Greek/Cyrillic/Indian scripts, plus everything in force."""
    todo = sorted({t for t in texts if t and FOREIGN.search(t) and t not in TRANSLATIONS} |
                  {t for t in force if t and t not in TRANSLATIONS})
    if todo:
        print(f"Translating {len(todo)} new text(s) (about {int(len(todo) * 1.5)}s)...")
    done = 0
    for t in todo:
        if GOOGLE_LIMITED[0]:
            break
        out = google_translate(t)
        if out:
            TRANSLATIONS[t] = out
            done += 1
    if todo:
        why = f" - Google: {GOOGLE_WHY[0]}" if done < len(todo) and GOOGLE_WHY[0] else ""
        stop = "; stopped, the rest will be tried next run" if GOOGLE_LIMITED[0] else ""
        print(f"  translated {done}/{len(todo)}{why}{stop}")
        save_cache()


def en(text):
    return TRANSLATIONS.get(text, text)


def google_translate_batch(texts):
    """Several one-line texts in one request (joined by new lines); None if that didn't work."""
    params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": "\n".join(texts)}
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
    try:
        time.sleep(1.0)
        req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as resp:
            data = json.load(resp)
        lines = "".join(seg[0] for seg in data[0] if seg and seg[0]).split("\n")
        lines = [ln.strip() for ln in lines]
        return lines if len(lines) == len(texts) and all(lines) else None
    except urllib.error.HTTPError as e:
        GOOGLE_WHY[0] = f"HTTP {e.code} {e.reason}"
        if e.code == 429:
            GOOGLE_LIMITED[0] = True
    except (urllib.error.URLError, TimeoutError, ValueError, IndexError, TypeError) as e:
        GOOGLE_WHY[0] = type(e).__name__
    return None


def translate_descriptions(records, limit):
    """Translate the guide's descriptions (nearest programmes first, at most limit new ones),
    about ten per request. Ones not translated yet go into DESC_PENDING and are left out."""
    today = date.today().isoformat()
    need = {}                                          # text -> earliest start
    for rec in records:
        english = rec["place"] in ENGLISH_PLACES
        for ev in rec["events"]:
            d = ev.get("desc")
            if d and not (english and not FOREIGN.search(d)):
                need[d] = min(need.get(d, ev["start"]), ev["start"])
    for d in need:
        if d in TRANSLATIONS:
            DESC_USED[d] = today
    todo = sorted((d for d in need if d not in TRANSLATIONS), key=lambda d: need[d])[:max(limit, 0)]
    if todo:
        print(f"Translating {len(todo)} new description(s), about ten at a time ...")
    done, i = 0, 0
    while i < len(todo) and not GOOGLE_LIMITED[0]:
        batch = []
        while i < len(todo) and len(batch) < 10 and \
                len(urllib.parse.quote("\n".join(batch + [todo[i]]))) <= 6000:
            batch.append(todo[i])
            i += 1
        if not batch:                                  # one very long text: on its own
            batch, i = [todo[i]], i + 1
        out = google_translate_batch(batch) if len(batch) > 1 else None
        if out is None:                                # the batch didn't split cleanly: one by one
            out = [google_translate(t) for t in batch]  # (returns None at once if Google refused)
        for t, tr_ in zip(batch, out):
            if tr_:
                TRANSLATIONS[t] = tr_
                DESC_USED[t] = today
                done += 1
    if todo:
        why = f" - Google: {GOOGLE_WHY[0]}" if done < len(todo) and GOOGLE_WHY[0] else ""
        stop = "; stopped, the rest will be tried next run" if GOOGLE_LIMITED[0] else ""
        print(f"  translated {done}/{len(todo)}{why}{stop}")
    DESC_PENDING.update(d for d in need if d not in TRANSLATIONS)
    if DESC_PENDING:
        print(f"  {len(DESC_PENDING)} description(s) left out until translated on a later run")
    save_cache()


# --------------------------------------------------------------------------
# Building programmes
# --------------------------------------------------------------------------
def collect(days, sheet_type, debug):
    """{channel_key: {"alt":..., "events":[{start, title, live}]}}"""
    channels = {}
    for day in days:
        rows = fetch_day(day, sheet_type, debug)
        last = {}
        for key, alt, hh, mm, title, live in rows:
            start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=ISRAEL)
            # a time earlier than the previous one on the same channel is after midnight
            if key in last and start < last[key]:
                start += timedelta(days=1)
            last[key] = start
            ch = channels.setdefault(key, {"alt": alt, "events": []})
            ch["events"].append({"start": start.astimezone(timezone.utc),
                                 "title": title, "live": live})
    for ch in channels.values():
        seen, uniq = set(), []
        for ev in sorted(ch["events"], key=lambda e: e["start"]):
            k = (ev["start"], ev["title"])
            if k not in seen:
                seen.add(k)
                uniq.append(ev)
        ch["events"] = uniq
    return channels


# Tidy ids and English names for the logos seen on the site (by id part).
NICE_NAMES = {
    "5Sport": "Sport 5", "5Plus": "Sport 5 Plus", "5Live": "Sport 5 Live",
    "5Stars": "Sport 5 Stars", "5Max": "Sport 5 Max", "5Gold": "Sport 5 Gold",
    "5Mobile": "Sport 5 Mobile", "5Radio": "Sport 5 Radio", "5Site": "Sport 5 Website",
    "5Sport4K": "Sport 5 4K", "54K": "Sport 5 4K",
}


def channel_ident(key, alt):
    if key in KNOWN_CHANNELS:
        part, name = KNOWN_CHANNELS[key]
    else:
        part = re.sub(r"[^A-Za-z0-9]+", "", key.title()) or "Channel"
        name = en(alt) if alt else key.replace("_", " ").title()
    part = re.sub(r"Channel$", "", part) or part      # 5MaxChannel -> 5Max
    return part, NICE_NAMES.get(part, name)


def xmltv_time(dt):
    return dt.astimezone(LONDON).strftime("%Y%m%d%H%M%S %z")


def add_programme(tv, cid, start, stop, title, sub, desc, live):
    p = ET.SubElement(tv, "programme", {
        "start": xmltv_time(start), "stop": xmltv_time(stop), "channel": cid})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    if sub:
        ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    ET.SubElement(p, "category", {"lang": "en"}).text = "Sports"
    if live:
        ET.SubElement(p, "category", {"lang": "en"}).text = "Live"


def filler_blocks(start, stop):
    cur = start
    while cur < stop:
        local = cur.astimezone(LONDON).replace(minute=0, second=0, microsecond=0)
        boundary = local + timedelta(hours=FILLER_HOURS - local.hour % FILLER_HOURS)
        nxt = min(boundary.astimezone(timezone.utc), stop)
        if nxt <= cur:
            nxt = min(cur + timedelta(hours=1), stop)
        yield cur, nxt
        cur = nxt


def build_xmltv(records, suffix, minutes):
    """records: [{id, name, tz, place, filler, back_to_back, events:[{start,title,sub,live}]}]"""
    tv = ET.Element("tv", {"generator-info-name": "SPORT_epg.py",
                           "source-info-name": "Sport 5 + Charlton (IL), Novasports (GR), Ziggo GO (NL), Digi Sport + Prima Play (RO), tv-programa.bg (BG), Arena Sport (RS), Delo (SI), Telenet (BE), Movistar Plus+ (ES), MEO (PT), Claro (BR), IPKO (AL/XK), mujtvprogram.cz (CZ/SK), Onet (PL), Sky Italia (IT), MagentaTV (DE), Tata Play (IN), blue TV (CH), SFR (FR), Allente (SE/NO/DK), epgshare01.online (TR/LV/HK/ID/MENA), beIN SPORTS (AU/MY/SG/HK/TH/ID), DStv (ZA/Africa)"})
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    count, listed = 0, []
    for rec in records:
        cid, name = f"{rec['id']}{suffix}", rec["name"]
        listed.append((cid, name))
        c = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = name

        evs = rec["events"]
        last_stop = None
        for i, ev in enumerate(evs):
            start = ev["start"]
            if last_stop and start < last_stop:
                start = last_stop
            nxt = evs[i + 1]["start"] if i + 1 < len(evs) else None
            if ev.get("stop"):
                stop = ev["stop"]
            elif rec["back_to_back"] and nxt and nxt - ev["start"] <= timedelta(hours=6):
                stop = nxt
            else:
                stop = ev["start"] + timedelta(minutes=minutes)
                if nxt and nxt < stop:
                    stop = nxt
            if stop <= start:
                continue
            title = en(ev["title"])
            sub = en(ev.get("sub") or "") or None
            loc = ev["start"].astimezone(rec["tz"])
            uk = ev["start"].astimezone(LONDON)
            when = f"{uk:%a %d %b, %H:%M}"
            orig = f" Original title: {ev['title']}." if title != ev["title"] else ""
            about = "" if ev.get("desc") in DESC_PENDING else en(ev.get("desc") or "")
            about = about + ("" if about[-1:] in ".!?…" else ".") + " " if about else ""
            desc = (f"{'LIVE. ' if ev['live'] else ''}{sub + '. ' if sub else ''}{about}{name}, "
                    f"{when} UK ({loc:%H:%M} {rec['place']}).{orig}")
            if rec["filler"]:
                for a, b in filler_blocks(last_stop or now, start):
                    add_programme(tv, cid, a, b, f"{title} ({when})", "Coming up",
                                  f"Upcoming on {name}: {title}, {when} UK "
                                  f"({loc:%H:%M} {rec['place']}).", False)
                    count += 1
            add_programme(tv, cid, start, stop, title,
                          sub or ("Live" if ev["live"] else None), desc, ev["live"])
            count += 1
            last_stop = stop
    return tv, count, listed


def write_xml(tv, path):
    """Write the guide; a path ending in .gz is gzip-compressed. The gzip header carries no
    time stamp (mtime=0), so the file only changes when the guide does (no empty commits)."""
    ET.indent(tv, space="  ")
    text = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
            + ET.tostring(tv, encoding="unicode") + "\n").encode("utf-8")
    if path.endswith(".gz"):
        inner = os.path.basename(path)[:-3]
        with open(path, "wb") as raw, gzip.GzipFile(filename=inner, mode="wb", fileobj=raw,
                                                    mtime=0, compresslevel=9) as f:
            f.write(text)
        with gzip.open(path, "rb") as f:
            ok = ET.parse(f).getroot().tag == "tv"
    else:
        with open(path, "wb") as f:
            f.write(text)
        ok = ET.parse(path).getroot().tag == "tv"
    if not ok:
        sys.exit(f"ERROR: {path} did not write correctly")


def load_last_run():
    try:
        with open(RUN_STATE_FILE, encoding="utf-8") as f:
            return int(json.load(f)["last_run"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_last_run(n):
    try:
        with open(RUN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_run": n}, f)
    except OSError as e:
        print(f"WARNING: could not save run number: {e}", file=sys.stderr)


def unique_path(path):
    stem, ext = os.path.splitext(path)
    if ext == ".gz":                                   # keep .xml.gz together
        stem, inner = os.path.splitext(stem)
        ext = inner + ext
    while True:
        cand = f"{stem}_{datetime.now(LONDON):%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:6]}{ext}"
        if not os.path.exists(cand):
            return cand


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="XMLTV guide of sports TV channels in several countries.")
    ap.add_argument("--out", default=OUTPUT_NAME, help=f"output file (default {OUTPUT_NAME})")
    ap.add_argument("--unique", action="store_true", help="new file name each run")
    ap.add_argument("--days", type=int, default=7, help="days to cover from today (default 7)")
    ap.add_argument("--minutes", type=int, default=DEFAULT_MINUTES,
                    help=f"event length if the next event isn't sooner (default {DEFAULT_MINUTES})")
    ap.add_argument("--type", default="", help="Sport 5 sheet Type value (default empty = live view)")
    ap.add_argument("--no-israel", action="store_true", help="leave out the Sport 5 channels")
    ap.add_argument("--no-charlton", action="store_true", help="leave out Charlton's Sport 1-6")
    ap.add_argument("--no-greece", action="store_true", help="leave out the Novasports page channels")
    ap.add_argument("--no-netherlands", action="store_true", help="leave out the Ziggo GO channels")
    ap.add_argument("--no-romania", action="store_true", help="leave out the Romanian channels")
    ap.add_argument("--no-bulgaria", action="store_true", help="leave out the Bulgarian channels")
    ap.add_argument("--no-arena", action="store_true", help="leave out the Arena Sport channels")
    ap.add_argument("--no-sportklub", action="store_true", help="leave out the Sport Klub channels")
    ap.add_argument("--no-belgium", action="store_true", help="leave out the Belgian channels")
    ap.add_argument("--no-spain", action="store_true", help="leave out the Spanish channels")
    for cc, name, table in (("se", "sweden", "SE_CHANNELS"), ("nor", "norway", "NO_CHANNELS"),
                            ("dk", "denmark", "DK_CHANNELS"), ("fi", "finland", "FI_CHANNELS")):
        ap.add_argument(f"--no-{name}", action="store_true", help=f"leave out the {name.title()} channels")
        ap.add_argument(f"--{cc}-channels", default=",".join(globals()[table]),
                        help=f"Allente channel numbers for {name.title()}, comma separated")
    ap.add_argument("--no-supersport", action="store_true", help="leave out SuperSport Africa")
    ap.add_argument("--ss-regions", default="ZA,AF", help="ZA (South Africa), AF (rest of Africa), or both")
    ap.add_argument("--ss-numbers", default="200-249", help="DStv channel numbers to take (default 200-249)")
    ap.add_argument("--no-bein", action="store_true", help="leave out the beIN SPORTS Asia-Pacific channels")
    ap.add_argument("--bein", default=BEIN_DEFAULT,
                    help=f"beIN countries, comma separated (default {BEIN_DEFAULT}; also {','.join(c for c in BEIN_COUNTRIES if c not in BEIN_DEFAULT)})")
    ap.add_argument("--no-france", action="store_true", help="leave out the French channels")
    ap.add_argument("--fr-channels", default=",".join(FR_CHANNELS),
                    help="SFR channel numbers, comma separated (e.g. 35,1290,2665)")
    ap.add_argument("--no-switzerland", action="store_true", help="leave out the Swiss channels")
    ap.add_argument("--ch-channels", default=",".join(CH_CHANNELS),
                    help="blue TV channel numbers, comma separated (e.g. 483,1543,401)")
    ap.add_argument("--no-india", action="store_true", help="leave out the Indian channels")
    ap.add_argument("--in-channels", default=",".join(IN_CHANNELS),
                    help="Tata Play channel numbers, comma separated (e.g. 600,150)")
    ap.add_argument("--no-germany", action="store_true", help="leave out the German channels")
    ap.add_argument("--de-channels", default=",".join(DE_CHANNELS),
                    help="MagentaTV channel numbers, comma separated (e.g. 190,206,401)")
    ap.add_argument("--no-italy", action="store_true", help="leave out the Italian channels")
    ap.add_argument("--it-channels", default=IT_DEFAULT,
                    help=f"which Sky Italia channels to include, by name (default: '{IT_DEFAULT}')")
    ap.add_argument("--no-poland", action="store_true", help="leave out the Polish channels")
    ap.add_argument("--pl-channels", default=",".join(PL_CHANNELS),
                    help="Onet channel page names, comma separated (e.g. tvp-sport-40,eleven-208)")
    ap.add_argument("--no-slovakia", action="store_true", help="leave out the Slovak channels")
    ap.add_argument("--slovakia-channels", default=",".join(SVK_CHANNELS),
                    help="mujtvprogram.cz channel numbers for Slovakia, comma separated")
    ap.add_argument("--no-czechia", action="store_true", help="leave out the Czech channels")
    ap.add_argument("--cz-channels", default=",".join(CZ_CHANNELS),
                    help="mujtvprogram.cz channel numbers, comma separated (e.g. 18,17,466)")
    ap.add_argument("--no-albania", action="store_true", help="leave out the SuperSport channels")
    ap.add_argument("--al-channels", default=AL_DEFAULT,
                    help="IPKO channel names, comma separated (default supersport-1 ... supersport-7)")
    ap.add_argument("--no-brazil", action="store_true", help="leave out the Brazilian channels")
    ap.add_argument("--br-channels", default=BR_DEFAULT,
                    help=f"which Claro channels to include, by name (default: '{BR_DEFAULT}')")
    ap.add_argument("--no-portugal", action="store_true", help="leave out the Portuguese channels")
    ap.add_argument("--pt-channels", default=",".join(PT_CHANNELS),
                    help="MEO channel codes, comma separated (e.g. SPT1HD,DAZN1,SLBHD)")
    ap.add_argument("--es-channels", default=",".join(ES_CHANNELS),
                    help="Movistar channel codes from the guide address, comma separated")
    ap.add_argument("--sk-channels", default=SK_DEFAULT,
                    help="Delo channel names from the page address, comma separated (default sk1-sk10)")
    ap.add_argument("--bg-channels", default=",".join(BG_CHANNELS),
                    help="тв-програма.bg channel names from the page address, comma separated")
    ap.add_argument("--nl-channels", default=r"ESPN|Ziggo Sport",
                    help="which Ziggo channels to include, by name (default: 'ESPN|Ziggo Sport')")
    ap.add_argument("--no-filler", action="store_true", help="no programmes between Israeli events")
    ap.add_argument("--no-translate", action="store_true", help="keep Hebrew / Greek titles")
    ap.add_argument("--no-epgshare", action="store_true", help="leave out everything from epgshare01.online")
    ap.add_argument("--epgshare", default=",".join(EPGSHARE),
                    help=f"epgshare01 groups, comma separated (default {','.join(EPGSHARE)})")
    ap.add_argument("--no-desc", action="store_true", help="leave out the sources' own programme descriptions")
    ap.add_argument("--desc-translations", type=int, default=3000,
                    help="most new descriptions to translate in one run (default 3000; the rest follow next run)")
    ap.add_argument("--run-ids", action="store_true", help="fresh ids with a run number")
    ap.add_argument("--suffix", type=int, default=None, help="run ids with this run number")
    ap.add_argument("--debug", action="store_true", help="print rows read for each day")
    args = ap.parse_args()

    il_days = [datetime.now(ISRAEL).date() + timedelta(days=i) for i in range(max(args.days, 1))]
    gr_days = [datetime.now(ATHENS).date() + timedelta(days=i) for i in range(max(args.days, 1))]

    il = {}
    if not args.no_israel:
        print(f"Israel: reading Sport 5 broadcast sheet {il_days[0]} to {il_days[-1]} ...")
        il = collect(il_days, args.type, args.debug)
        print(f"  {sum(len(c['events']) for c in il.values())} broadcasts on {len(il)} channel(s)")
    ch1 = {}
    if not args.no_charlton:
        print("Israel: reading Charlton (Sport 1) broadcast page ...")
        ch1 = fetch_charlton(il_days, args.debug)
        print(f"  {sum(len(v) for v in ch1.values())} broadcasts on {len(ch1)} channel(s)")
    gr = {}
    if not args.no_greece:
        print(f"Greece: reading Novasports TV programme {gr_days[0]} to {gr_days[-1]} ...")
        gr = fetch_greece(gr_days, args.debug)
        print(f"  {sum(len(v) for v in gr.values())} programmes on {len(gr)} channel(s)")
    nl = {}
    if not args.no_netherlands:
        nl_days = [datetime.now(timezone.utc).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Netherlands: reading Ziggo GO guide {nl_days[0]} to {nl_days[-1]} ...")
        nl = fetch_netherlands(nl_days, args.nl_channels, args.debug)
        print(f"  {sum(len(v) for v in nl.values())} programmes on {len(nl)} channel(s)")
    ro = {}
    if not args.no_romania:
        ro_days = [datetime.now(BUCHAREST).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Romania: reading Digi Sport and Prima Play {ro_days[0]} to {ro_days[-1]} ...")
        ro = fetch_digisport(ro_days, args.debug)
        ro.update(fetch_primaplay(ro_days, args.debug))
        print(f"  {sum(len(v) for v in ro.values())} programmes on {len(ro)} channel(s)")
    bg = {}
    if not args.no_bulgaria:
        bg_days = [datetime.now(SOFIA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Bulgaria: reading тв-програма.bg {bg_days[0]} to {bg_days[-1]} ...")
        bg = fetch_bulgaria(bg_days, args.bg_channels, args.debug)
        print(f"  {sum(len(v) for v in bg.values())} programmes on {len(bg)} channel(s)")
    arena = {}
    if not args.no_arena:
        ar_days = [datetime.now(BELGRADE).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Balkans: reading Arena Sport TV page {ar_days[0]} to {ar_days[-1]} ...")
        arena = fetch_arena(ar_days, args.debug)
        print(f"  {sum(len(v) for v in arena.values())} programmes on {len(arena)} channel(s)")
    sk = {}
    if not args.no_sportklub:
        sk_days = [datetime.now(LJUBLJANA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Sport Klub: reading Delo TV guide {sk_days[0]} to {sk_days[-1]} ...")
        sk = fetch_sportklub(sk_days, args.sk_channels, args.debug)
        print(f"  {sum(len(v) for v in sk.values())} programmes on {len(sk)} channel(s)")
    be = {}
    if not args.no_belgium:
        be_days = [datetime.now(BRUSSELS).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print("Belgium: reading Telenet Play Sports calendar ...")
        be = fetch_belgium(be_days, args.debug)
        print(f"  {sum(len(v) for v in be.values())} events on {len(be)} channel(s)")
    es = {}
    if not args.no_spain:
        es_days = [datetime.now(MADRID).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Spain: reading Movistar Plus+ guide {es_days[0]} to {es_days[min(5, len(es_days) - 1)]} ...")
        es = fetch_spain(es_days, args.es_channels, args.debug)
        print(f"  {sum(len(v) for v in es.values())} programmes on {len(es)} channel(s)")
    pt = {}
    if not args.no_portugal:
        pt_days = [datetime.now(LISBON).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Portugal: reading MEO TV guide {pt_days[0]} to {pt_days[-1]} ...")
        pt = fetch_portugal(pt_days, args.pt_channels, args.debug)
        print(f"  {sum(len(v) for v in pt.values())} programmes on {len(pt)} channel(s)")
    br = {}
    if not args.no_brazil:
        br_days = [datetime.now(SAO_PAULO).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Brazil: reading Claro TV guide {br_days[0]} to {br_days[-1]} ...")
        br = fetch_brazil(br_days, args.br_channels, args.debug)
        print(f"  {sum(len(v) for v in br.values())} programmes on {len(br)} channel(s)")
    al = {}
    if not args.no_albania:
        al_days = [datetime.now(TIRANE).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Albania/Kosovo: reading IPKO guide {al_days[0]} to {al_days[-1]} ...")
        al = fetch_albania(al_days, args.al_channels, args.debug)
        print(f"  {sum(len(v) for v in al.values())} programmes on {len(al)} channel(s)")
    cz = {}
    if not args.no_czechia:
        cz_days = [datetime.now(PRAGUE).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Czechia: reading mujtvprogram.cz {cz_days[0]} to {cz_days[-1]} ...")
        cz = fetch_czechia(cz_days, args.cz_channels, args.debug)
        print(f"  {sum(len(v) for v in cz.values())} programmes on {len(cz)} channel(s)")
    svk = {}
    if not args.no_slovakia:
        svk_days = [datetime.now(BRATISLAVA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Slovakia: reading mujtvprogram.cz {svk_days[0]} to {svk_days[-1]} ...")
        svk = fetch_czechia(svk_days, args.slovakia_channels, args.debug, tz=BRATISLAVA)
        print(f"  {sum(len(v) for v in svk.values())} programmes on {len(svk)} channel(s)")
    pl = {}
    if not args.no_poland:
        pl_days = [datetime.now(WARSAW).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Poland: reading Onet TV guide {pl_days[0]} to {pl_days[-1]} ...")
        pl = fetch_poland(pl_days, args.pl_channels, args.debug)
        print(f"  {sum(len(v) for v in pl.values())} programmes on {len(pl)} channel(s)")
    it = {}
    if not args.no_italy:
        it_days = [datetime.now(ROME).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Italy: reading Sky Italia TV guide {it_days[0]} to {it_days[-1]} ...")
        it = fetch_italy(it_days, args.it_channels, args.debug)
        print(f"  {sum(len(v) for v in it.values())} programmes on {len(it)} channel(s)")
    de = {}
    if not args.no_germany:
        de_days = [datetime.now(BERLIN).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Germany: reading MagentaTV guide {de_days[0]} to {de_days[-1]} ...")
        de = fetch_germany(de_days, args.de_channels, args.debug)
        print(f"  {sum(len(v) for v in de.values())} programmes on {len(de)} channel(s)")
    ind = {}
    if not args.no_india:
        in_days = [datetime.now(KOLKATA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"India: reading Tata Play guide {in_days[0]} to {in_days[-1]} ...")
        ind = fetch_india(in_days, args.in_channels, args.debug)
        print(f"  {sum(len(v) for v in ind.values())} programmes on {len(ind)} channel(s)")
    swi = {}
    if not args.no_switzerland:
        ch_days = [datetime.now(ZURICH).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Switzerland: reading blue TV guide {ch_days[0]} to {ch_days[-1]} ...")
        swi = fetch_switzerland(ch_days, args.ch_channels, args.debug)
        print(f"  {sum(len(v) for v in swi.values())} programmes on {len(swi)} channel(s)")
    fra = {}
    if not args.no_france:
        fr_days = [datetime.now(PARIS).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"France: reading SFR TV guide {fr_days[0]} to {fr_days[-1]} ...")
        fra = fetch_france(fr_days, args.fr_channels, args.debug)
        print(f"  {sum(len(v) for v in fra.values())} programmes on {len(fra)} channel(s)")
    nordic = {}                                       # (prefix, tz, place, table) -> events
    for flag, tld, chans, prefix, zone, place, table in (
            ("no_sweden", "se", args.se_channels, "SE", STOCKHOLM, "Sweden", SE_CHANNELS),
            ("no_norway", "no", args.nor_channels, "NO", OSLO, "Norway", NO_CHANNELS),
            ("no_denmark", "dk", args.dk_channels, "DK", COPENHAGEN, "Denmark", DK_CHANNELS),
            ("no_finland", "fi", args.fi_channels, "FI", HELSINKI, "Finland", FI_CHANNELS)):
        if getattr(args, flag):
            continue
        nd_days = [datetime.now(zone).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"{place}: reading Allente guide {nd_days[0]} to {nd_days[-1]} ...")
        got = fetch_allente(tld, nd_days, chans, args.debug)
        print(f"  {sum(len(v) for v in got.values())} programmes on {len(got)} channel(s)")
        if got:
            nordic[(prefix, zone, place, id(table))] = (table, got)
    ss = {}
    if not args.no_supersport:
        lo, _, hi = args.ss_numbers.partition("-")
        lo, hi = int(lo), int(hi or lo)
        for prefix in [r.strip().upper() for r in args.ss_regions.split(",") if r.strip()]:
            if prefix not in SS_REGIONS:
                print(f"  WARNING: unknown SuperSport region '{prefix}' (use ZA, AF)", file=sys.stderr)
                continue
            country, extra, place, zone, _ = SS_REGIONS[prefix]
            ss_days = [datetime.now(ZoneInfo(zone)).date() + timedelta(days=i) for i in range(max(args.days, 1))]
            print(f"SuperSport {place}: reading DStv guide {ss_days[0]} to {ss_days[-1]} ...")
            got = fetch_dstv(country, extra, zone, ss_days, lo, hi, args.debug)
            print(f"  {sum(len(v) for v in got.values())} programmes on {len(got)} channel(s)")
            if got:
                ss[prefix] = got
    eps = {}
    if not args.no_epgshare:
        for group in [g.strip().lower() for g in args.epgshare.split(",") if g.strip()]:
            if group not in EPGSHARE:
                print(f"  WARNING: unknown epgshare group {group!r} (known: {', '.join(EPGSHARE)})", file=sys.stderr)
                continue
            cfg = EPGSHARE[group]
            tz = ZoneInfo(cfg["tz"])
            g_days = [datetime.now(tz).date() + timedelta(days=i) for i in range(max(args.days, 1))]
            print(f"{cfg['place']} (epgshare01 {cfg['file']}): reading {g_days[0]} to {g_days[-1]} ...")
            got = fetch_epgshare(group, g_days, args.debug)
            print(f"  {sum(len(v) for v in got.values())} programmes on {len(got)} channel(s)")
            if got:
                eps[group] = got
    bein = {}
    if not args.no_bein:
        bn_days = [datetime.now(ZoneInfo("Asia/Singapore")).date() + timedelta(days=i - 1)
                   for i in range(max(args.days, 1) + 1)]      # from yesterday (UTC days, Asia is ahead)
        print(f"beIN SPORTS: reading beIN's guide {bn_days[0]} to {bn_days[-1]} ...")
        bein = fetch_bein(bn_days, args.bein, args.debug)
        print(f"  {sum(len(v) for g in bein.values() for v in g.values())} programmes on "
              f"{sum(len(g) for g in bein.values())} channel(s)")
    if not il and not ch1 and not gr and not nl and not ro and not bg and not arena and not sk and not be \
            and not es and not pt and not br and not al and not cz and not svk and not pl and not it and not de and not ind and not swi and not fra and not nordic and not bein and not ss and not eps:
        sys.exit("Nothing found - the sites may be unreachable from here, or changed.")

    if not args.no_translate:
        load_cache()
        texts = [e["title"] for c in il.values() for e in c["events"]]
        texts += [c["alt"] for c in il.values()]
        texts += [t for evs in ch1.values() for e in evs for t in (e["title"], e["sub"])]
        texts += [t for evs in gr.values() for e in evs for t in (e["title"], e["sub"])]
        texts += [t for evs in bg.values() for e in evs for t in (e["title"], e["sub"])]
        texts += [e["title"] for evs in ind.values() for e in evs]   # only Indian-script titles
        force = [e["title"] for evs in ro.values() for e in evs]
        force += [t for evs in arena.values() for e in evs for t in (e["title"], e["sub"])]
        force += [t for evs in sk.values() for e in evs for t in (e["title"], e["sub"])]
        force += [e["sub"] for evs in be.values() for e in evs]
        force += [e["title"] for evs in es.values() for e in evs]
        force += [e["title"] for evs in pt.values() for e in evs]
        force += [e["title"] for evs in br.values() for e in evs]
        force += [e["title"] for evs in al.values() for e in evs]
        force += [e["title"] for evs in cz.values() for e in evs]
        force += [e["title"] for evs in svk.values() for e in evs]
        force += [e["title"] for evs in it.values() for e in evs]
        force += [t for evs in de.values() for e in evs for t in (e["title"], e["sub"])]
        force += [e["title"] for evs in swi.values() for e in evs]
        force += [t for evs in fra.values() for e in evs for t in (e["title"], e["sub"])]
        force += [e["title"] for _, got in nordic.values() for evs in got.values() for e in evs]
        texts += [t for g in bein.values() for evs in g.values() for e in evs for t in (e["title"], e["sub"])]
        force += [t for evs in pl.values() for e in evs for t in (e["title"], e["sub"])]
        for group, got in eps.items():
            words = [t for evs in got.values() for e in evs for t in (e["title"], e["sub"])]
            if EPGSHARE[group]["english"]:
                texts += words                          # only Arabic / Chinese ... text
            else:
                force += words
        translate_all(texts, force=force)

    records = []
    for key, ch in il.items():
        part, name = channel_ident(key, ch["alt"])
        records.append({"id": f"IL.{part}", "name": name, "tz": ISRAEL, "place": "Israel",
                        "filler": not args.no_filler, "back_to_back": False,
                        "events": [dict(e, sub="") for e in ch["events"]]})
    for chname, evs in ch1.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"IL.{part}", "name": chname, "tz": ISRAEL, "place": "Israel",
                        "filler": not args.no_filler, "back_to_back": False, "events": evs})
    for chname, evs in gr.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"GR.{part}", "name": chname, "tz": ATHENS, "place": "Greece",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in es.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname.replace("+", "Plus")) or "Channel"
        records.append({"id": f"ES.{part}", "name": chname, "tz": MADRID, "place": "Spain",
                        "filler": False, "back_to_back": True, "events": evs})
    for prefix, got in ss.items():
        _, _, place, zone, suffix = SS_REGIONS[prefix]
        for name, evs in got.items():
            part = re.sub(r"[^A-Za-z0-9]+", "", name) or "Channel"
            shown = name if re.search(rf"\b{suffix}\b", name) else f"{name} {suffix}"   # no 'Africa Africa'
            records.append({"id": f"{prefix}.{part}", "name": shown, "tz": ZoneInfo(zone),
                            "place": place, "filler": False, "back_to_back": True, "events": evs})
    for group, got in eps.items():
        cfg = EPGSHARE[group]
        for part, evs in got.items():
            records.append({"id": f"{cfg['prefix']}.{part}", "name": cfg["channels"][part][0],
                            "tz": ZoneInfo(cfg["tz"]), "place": cfg["place"],
                            "filler": False, "back_to_back": True, "events": evs})
    for cc, got in bein.items():
        place, zone = BEIN_COUNTRIES[cc][0], ZoneInfo(BEIN_COUNTRIES[cc][1])
        for name, evs in got.items():
            chname = f"{name} {cc.upper()}"
            part = re.sub(r"[^A-Za-z0-9]+", "", name) or "Channel"
            records.append({"id": f"{cc.upper()}.{part}", "name": chname, "tz": zone, "place": place,
                            "filler": False, "back_to_back": True, "events": evs})
    for (prefix, zone, place, _), (table, got) in nordic.items():
        for cid, evs in got.items():
            part, chname = table.get(cid, (f"Channel{re.sub(r'[^A-Za-z0-9]+', '', cid)}",
                                           f"{place} channel {cid}"))
            records.append({"id": f"{prefix}.{part}", "name": chname, "tz": zone, "place": place,
                            "filler": False, "back_to_back": True, "events": evs})
    for cid, evs in fra.items():
        part, chname = FR_CHANNELS.get(cid, (f"Channel{re.sub(r'[^A-Za-z0-9]+', '', cid)}",
                                             f"French channel {cid}"))
        records.append({"id": f"FR.{part}", "name": chname, "tz": PARIS, "place": "France",
                        "filler": False, "back_to_back": True, "events": evs})
    for cid, evs in swi.items():
        part, chname = CH_CHANNELS.get(cid, (f"Channel{re.sub(r'[^A-Za-z0-9]+', '', cid)}",
                                             f"Swiss channel {cid}"))
        records.append({"id": f"CH.{part}", "name": chname, "tz": ZURICH, "place": "Switzerland",
                        "filler": False, "back_to_back": True, "events": evs})
    for cid, evs in ind.items():
        part, chname = IN_CHANNELS.get(cid, (f"Channel{re.sub(r'[^A-Za-z0-9]+', '', cid)}",
                                             f"Indian channel {cid}"))
        records.append({"id": f"IN.{part}", "name": chname, "tz": KOLKATA, "place": "India",
                        "filler": False, "back_to_back": True, "events": evs})
    for cid, evs in de.items():
        chname = DE_CHANNELS.get(cid, f"German channel {cid}")
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"DE.{part}", "name": chname, "tz": BERLIN, "place": "Germany",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in it.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"IT.{part}", "name": chname, "tz": ROME, "place": "Italy",
                        "filler": False, "back_to_back": True, "events": evs})
    for slug, evs in pl.items():
        part, chname = PL_CHANNELS.get(slug, (re.sub(r"[^A-Za-z0-9]+", "", slug.title()) or "Channel",
                                              slug.replace("-", " ").title()))
        records.append({"id": f"PL.{part}", "name": chname, "tz": WARSAW, "place": "Poland",
                        "filler": False, "back_to_back": True, "events": evs})
    for cid, evs in svk.items():
        part, chname = SVK_CHANNELS.get(cid, (f"Channel{re.sub(r'[^A-Za-z0-9]+', '', cid)}",
                                              f"Slovak channel {cid}"))
        records.append({"id": f"SK.{part}", "name": chname, "tz": BRATISLAVA, "place": "Slovakia",
                        "filler": False, "back_to_back": True, "events": evs})
    for cid, evs in cz.items():
        part, chname = CZ_CHANNELS.get(cid, (f"Channel{re.sub(r'[^A-Za-z0-9]+', '', cid)}",
                                             f"Czech channel {cid}"))
        records.append({"id": f"CZ.{part}", "name": chname, "tz": PRAGUE, "place": "Czechia",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in al.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"AL.{part}", "name": chname, "tz": TIRANE, "place": "Albania",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in br.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"BR.{part}", "name": chname, "tz": SAO_PAULO, "place": "Brasilia",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in pt.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname.replace("+", "Plus")) or "Channel"
        records.append({"id": f"PT.{part}", "name": chname, "tz": LISBON, "place": "Portugal",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in be.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"BE.{part}", "name": chname, "tz": BRUSSELS, "place": "Belgium",
                        "filler": not args.no_filler, "back_to_back": False, "events": evs})
    for chname, evs in sk.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"SI.{part}", "name": chname.replace("SK ", "Sport Klub "),
                        "tz": LJUBLJANA, "place": "Slovenia",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in arena.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"RS.{part}", "name": chname, "tz": BELGRADE, "place": "Serbia",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in bg.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"BG.{part}", "name": chname, "tz": SOFIA, "place": "Bulgaria",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in ro.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"RO.{part}", "name": chname, "tz": BUCHAREST, "place": "Romania",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in nl.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"NL.{part}", "name": chname, "tz": AMSTERDAM, "place": "NL",
                        "filler": False, "back_to_back": True, "events": evs})
    records.sort(key=lambda r: r["id"])

    run_no, suffix = None, ""
    if args.run_ids or args.suffix is not None:
        run_no = args.suffix if args.suffix is not None else load_last_run() + 1
        suffix = f"-Run{run_no}"

    if args.no_desc:
        for rec in records:
            rec["events"] = [dict(e, desc="") for e in rec["events"]]
    elif not args.no_translate:
        try:
            translate_descriptions(records, args.desc_translations)
        except Exception as e:                         # never lose the guide over a description
            print(f"WARNING: description translation stopped ({type(e).__name__}: {e}) - "
                  f"untranslated descriptions left out this run", file=sys.stderr)
            DESC_PENDING.update(ev.get("desc") for rec in records for ev in rec["events"]
                                if ev.get("desc") and ev["desc"] not in TRANSLATIONS
                                and rec["place"] not in ENGLISH_PLACES)
    tv, count, listed = build_xmltv(records, suffix, args.minutes)
    out_path = unique_path(args.out) if args.unique else args.out
    write_xml(tv, out_path)
    if run_no is not None:
        save_last_run(run_no)

    print(f"\nWrote {out_path}: {len(listed)} channels, {count} programmes")
    for cid, name in listed:
        print(f"  {cid:<32} {name}")


if __name__ == "__main__":
    main()
