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

ROMANIA (Sport Extra) - programetv.ro, one page per channel and weekday (luni ... duminica):
    https://www.programetv.ro/program-tv/sport-extra/joi/
  Channel: RO.SportExtra (29 Oct 2026). Add more in PROGRAMETV_CHANNELS.

BALKANS - Arena Sport's own TV page (Serbian feed), all channels and 7 days in one page:
    https://tvarenasport.com/tv-scheme    (the data is the window.TV_SCHEMES object)
  Arena Sport 1-10, Arena Premium 1-5, Arena Tenis, Adrenalin, Arena 1X2.
  "uzivo" marks a live event. Serbian text is translated.
  Serbian Eurosport 1-2 and Arena Fight from mts's TV guide (mts.rs, one JSON request per day):
  RS.Eurosport1, RS.Eurosport2, RS.ArenaFight (29 Oct 2026).
  SLOVENIA - Telekom Slovenije's NEO guide (stargate.telekom.si, same API as IPKO; one request per channel
  and day): Arena Sport 1-4 SI, Arena Sport 1 Premium SI, Arena Fight SI, Šport TV 1-3 -> SI.ArenaSport1 ...,
  SI.ArenaPremium1, SI.ArenaFight, SI.SportTV1 ... (29 Oct 2026). --no-slovenia to leave out.
  (Sport Klub Slovenia already comes from Delo: SI.SK1 ...)
  CROATIA - MAXtv's (Hrvatski Telekom) guide API (tv-hr-prod.yo-digital.com, 8 requests a day, all
  channels): Arena Sport 1-10 HR, Arena Fight HR, MAX Sport 1-2, Sportska Televizija, Sport Klub 1-12 HR,
  Sport Klub Golf HR -> HR.ArenaSport1 ..., HR.ArenaFight, HR.MAXSport1/2, HR.SportskaTV, HR.SportKlub1 ...,
  HR.SportKlubGolf (29 Oct 2026). --no-croatia to leave out.
  Bosnia and Herzegovina feed (own schedule) from tvarenasport.com/ba/tv-scheme: BA.ArenaSport1 ...,
  BA.ArenaPremium1 ... (29 Oct 2026; "BH" dropped from the IDs).
  Channels: RS.ArenaSport1 ... RS.ArenaPremium1 ... RS.ArenaTenis, RS.Adrenalin

BELGIUM - Telenet's Play Sports "sportkalender" page (one page, this week's big events):
    https://www2.telenet.be/residential/nl/producten/telenet-tv/play-sports/sportkalender.html
  Lines like "17/10 Everton - Chelsea 13u15 | Play Sports 1" become events on that
  channel, with the competition and round as the sub-title. It lists the main live
  events only (no full schedule), so FILLER fills the gaps, as for Israel.
  Events without a start time (multi-day golf, tennis weeks) are left out.
  Channels: BE.PlaySports1 ... BE.PlaySportsGolf, BE.DAZN1, BE.DAZN2, BE.DAZNJPL1 ...
  Since 29 Oct 2026 Telenet's FULL guide (staticqbr-prod-be.gnp.cloud.telenet.tv, same platform as Ziggo)
  replaces the calendar for Play Sports 1-4, Play Sports Golf, DAZN 1-2 and DAZN JPL 1-2 (= DAZN Pro
  League 1-2); calendar events keep their LIVE and competition. See TELENET_CHANNELS.

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
  Channels whose name matches --br-channels (default: SporTV, Premiere, ESPN, BandSports, Combate);
  SD/HD copies are merged. Start and end times are
  given (Brasilia time). Portuguese titles are translated.
  Channels: BR.SporTV, BR.SporTV2, BR.SporTV3, BR.PremiereClubes, BR.Premiere2, BR.ESPN ...

ALBANIA / KOSOVO - IPKO's public web guide (Kosovo, JSON), one request per channel and day:
    POST https://stargate.ipko.tv/api/titan.tv.WebEpg/GetWebEpgData
         {"ch_ext_id": "supersport-1", "from": <unix>, "to": <unix>}
  SuperSport 1-7 (Digitalb's channels for Albania and Kosovo) and Tring Sport 1-7 (added 4 Nov 2026; IPKO carries
  them as tring-sport-1 ... - one IPKO doesn't list is skipped and named in the log). Start and end times
  are given. Channels chosen with --al-channels (IPKO's channel names; default
  supersport-1 ... supersport-7, tring-sport-1 ... tring-sport-7). Albanian titles are translated.
  Channels: AL.SuperSport1 ... AL.SuperSport7, AL.TringSport1 ... AL.TringSport7

CZECHIA - mujtvprogram.cz's public service (XML), one request per channel and day:
    https://services.mujtvprogram.cz/tvprogram2services/services/tvprogrammelist_mobile.php
        ?channel_cid=18&day=0          (day = 0 today, 1 tomorrow ...)
  Start and end times are given. Channels chosen with --cz-channels (the site's channel
  numbers; default: ČT sport, Nova Sport 1-6, Sport 1, Sport 2, Canal+ Sport 1-2,
  FightBox - CZ.FightBox).
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

UK / IRELAND - Sky's public TV guide (behind sky.com's TV guide; JSON, no login or key):
    https://awk.epgsky.com/hawk/linear/schedule/20261021/4002,1120   (header X-SkyOTT-Territory: GB)
    https://atlantis.epgsky.com/as/schedule/20261021/7201            (4K channels)
  Sky Sports (Main Event, Premier League, Football, ... , Main Event 4K, F1 4K), TNT Sports 1-10,
  Ultimate, Box Office 1-2, Premier Sports 1-2, Racing TV, MUTV, LFCTV, RTÉ One, RTÉ2, Virgin Media One-Four, BBC One,
  BBC Two, ITV1, ITV4, Channel 4, Channel 5 (general channels: only live sport events are LIVE - see GENERAL_CHANNELS).
  --no-sky to leave out; epgshare01's UK1/IE1 files are the backup (and give Sky Sports NFL;
  none for RTÉ, Virgin Media, BBC or ITV). Channels: UK.SkySportsMainEvent, UK.TNTSports1,
  UK.BBCOne, UK.BBCTwo, UK.ITV1, UK.ITV4, UK.Channel4, UK.Channel5,
  IE.PremierSports1 (Irish feed; UK.PremierSports1/2 = UK feeds, split by SKY_SPLIT), IE.RTEOne, IE.RTE2, IE.VirginMediaOne ... IE.VirginMediaFour

CYPRUS - Cyta's own TV guide (epg.cyta.com.cy, JSON), as in cyta_epg.py:
    channels:     https://epg.cyta.com.cy/api/mediacatalog/fetchChannels?language=0
    programmes:   .../fetchEpg?startTimeEpoch=..&endTimeEpoch=..&language=0&channelIds=..  (8 channels per request, per day)
    descriptions: .../fetchEpgDetails?language=0&id=..   (one per programme; skipped with --no-desc)
  Channels whose name has every word of one --cy-keywords entry (default 'cyta sport': Cytavision
  Sports 1-8, Premier League ...). Start and end times are given. Greek text is translated and ALL CAPS
  titles are put in normal case. --no-cyprus to leave out.
  Channels: CY.CytavisionSports1 ... CY.CytavisionSportsPremierLeague

HONG KONG - Now TV's public guide (JSON), one request per day for all channels (cookie LANG=en):
    https://nowplayer.now.com/tvguide/epglist?channelIdList[]=631&channelIdList[]=638&day=1
  Channels chosen with --now-channels (Now TV channel numbers; default: its 36 sports
  channels - Now Sports, Premier League 1-9, beIN SPORTS 1-6, NBA TV, MUTV, golf ...);
  --no-nowtv to leave out. Start and end times are given. epgshare01's HK file is the backup.
  Channels: HK.NowSports1, HK.NowSportsPL1, HK.beINSPORTS1, HK.MUTV ...

AUSTRALIA - Fox Sports and ESPN AU come from YourTV's Foxtel guide (4 Nov 2026; Nine's public TV guide, pay region
  168 = Foxtel, no login): today + the next six days, with descriptions for the next 72 hours. epgshare01's AU1 file
  (group "au") is the fallback per channel and fills the part of today before YourTV's first programme. (Foxtel's own
  pages refuse GitHub's servers with HTTP 403, 29 Oct 2026; AU1 had stalled at about one day ahead.)
  --no-yourtv turns it off. Channels: AU.FoxCricket, AU.FoxLeague, AU.FoxSports503, AU.FoxFooty, AU.FoxSports505,
  AU.FoxSports506, AU.FoxSports507, AU.FoxSportsNews, AU.ESPN, AU.ESPN2.

MALAYSIA - Astro Premier League 1-5, Football, Grandstand, Cricket, Arena 1 + 2, Sports UHD and Sports Plus: epgshare01's
  MY1 file is the main source (with descriptions, about 1-2 days ahead); since 5 Nov 2026 Astro's own TV guide (the call
  astro.com.my makes, no login, 7 days, titles and times only, live programmes start \"(L) \") adds the programmes after
  epgshare's last one, and is the only source for a channel epgshare has nothing for (Premier League 3 / 4). A channel whose
  Astro times don't match epgshare stays on epgshare. --no-astro turns it off.

SINGAPORE - StarHub TV+'s guide API (JSON, no login; added 29 Oct 2026), per channel and day:
    https://waf-starhub-metadata-api-p001.sh-ifs.com/v3.1/epg/schedules?...&in_channel_id=<id>
  Hub Sports 1-8, found by name in StarHub's channel list (known ids as fallback). Live =
  StarHub's schedule_type "live" (or "LIVE" in the title). --no-starhub to leave out;
  epgshare01's SG file is tried as the backup. Channels: SG.HubSports1 ... SG.HubSports8.
  beIN SPORTS 4 and 5 SG come from mewatch (cdn.mewatch.sg/api/schedules, with a live flag):
  SG.beINSPORTS4, SG.beINSPORTS5 (beIN's own API lists only 1-3 for Singapore).

EPGSHARE01 - ready-made XMLTV files from https://epgshare01.online/epgshare01/ (free, no login),
  one file per country, read once per run (gzip):
    https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz   (also LV1, HK1, ID1, BEIN1)
  Groups chosen with --epgshare (default turkey,latvia,hk,id,mena,france,golfplus,sg,my,au,italy);
  --no-epgshare for none. france/golfplus/italy are backups for channels SFR and Sky Italia
  list but send nothing for (Eurosport 1-2 FR, DAZN 1 FR, Golf+, Sky Sport 253-258,
  Sky Sport NBA, DAZN 4): same IDs, used only when your own source has nothing. france also
  adds beIN SPORTS MAX 4-10 FR. sg/my/au back up beIN's own site under the same IDs
  (SG.beINSPORTS1 ...), and sg adds beIN SPORTS 4-5 and RUGBY SG. brazil backs up Claro
  (SporTV, ESPN, Premiere) under the same IDs when Claro sends nothing. sg also gives Hub Premier
  1-6 and my Astro's sports channels; uk/ireland back up Sky's guide (and give Sky Sports NFL);
  nz (Sky Sport NZ), usa (USA Network, NBC), canada (Sportsnet).
  Each channel has a fixed ID and a list of the file's own IDs for it, best first; the one
  with most programmes is used. Turkish, Latvian and Indonesian titles are translated.
  Channels: TR.beINSPORTS1 ... TR.TRTSpor, LV.GO3Sport1 ... LV.SetantaSports, HK.beINSPORTS1,
  HK.NowSports1 ..., ID.beINSPORTS1, ID.SPOTV ..., MENA.beINSPORTS1 ...

SWITZERLAND - Swisscom's public blue TV guide (JSON), one request per channel and day:
    https://services.sg101.prd.sctv.ch/catalog/tv/channels/list/(ids=483;start=YYYYMMDD0000;end=...;level=normal)
  Channels chosen with --ch-channels (blue TV channel numbers; default: blue Sport 1-2,
  blue Sport (FR), blue Sport Extra, MySports Eins/Un/2-9/EDGE, Swiss Sport TV, SRF zwei,
  RTS 2, RSI LA 2, blue Sport 3-4, blue Zoom F - CH.blueZoomF). The other numbered blue Sport Live / MySports Event channels are
  left out. blue Sport 3/4 (CH.blueSport3/4) = blue TV's "blue Sport 3/4 Live D" pop-up channels
  (1250, 1440), or the older "Live" numbers (512, 513) if those are empty.
  Start and end times are given. German/French/Italian titles are translated.
  Channels: CH.blueSport1, CH.MySportsEins, CH.SRFzwei ...

FRANCE - SFR's public TV guide: one static JSON file per day with every channel (~10 MB):
    https://static-cdn.tv.sfr.net/data/epg/gen8/guide_web_YYYYMMDD.json
  Channels chosen with --fr-channels (SFR channel numbers; default: Canal+ Sport, Sport 360,
  Foot, beIN SPORTS 1-3, RMC Sport 1, RMC Sport Access, Eurosport 1-2, L'Équipe, DAZN 1,
  Golf+, Automoto, Equidia, Sport en France). Infosport+ (FR.InfosportPlus) comes from epgshare01's FR1 file
  (Canal+'s guide API refuses GitHub; Eurosport 360 1-8 and Canal+ Premier League were removed 29 Oct 2026, late). Start and end times and a live flag are given. French text is
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
  competition is the sub-title. Choose countries with --bein (default my,sg; hk,th,id have no programmes on beIN's site).
  Channels: MY.beINSPORTS1, SG.beINSPORTS1, HK..., TH..., ID...

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
  Extra, Fight, Premium 1-2, Canal+ Sport 1-5, Eleven Sports 1-4, Eurosport 1-2). Programmes run back to
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
  * Times are converted to UK time.
  * FIXED CHANNEL IDS and a fixed file name (SPORT_epg.xml.gz, gzip-compressed;
    --out SPORT_epg.xml writes a plain file instead). --run-ids gives fresh
    ids (IL.5Sport-Run3, GR.NovasportsPrime-Run3) when PlaylistLabs must replace
    programmes it already holds; --unique gives a new file name each run.

Usage:
    python3 SPORT_epg.py                  # all countries, next 7 days -> SPORT_epg.xml.gz
    python3 SPORT_epg.py --no-israel      # leave out Sport 5 (also --no-cyprus, --no-charlton, --no-greece, --no-netherlands, --no-romania, --no-bulgaria, --no-arena, --no-sportklub, --no-belgium, --no-spain, --no-portugal, --no-brazil, --no-albania, --no-czechia, --no-slovakia, --no-poland, --no-italy, --no-germany, --no-india, --no-switzerland, --no-france, --no-sweden,
                                          --no-norway, --no-denmark, --no-finland, --no-bein, --no-supersport)
    python3 SPORT_epg.py --days 10
    python3 SPORT_epg.py --debug          # print what was read for each day

Only the Python standard library is needed. On Windows: pip install tzdata
"""

import argparse
import gzip
import html
import unicodedata
import http.client
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
# yes (Israel) guide API (29 Oct 2026, as iptv-org's yes.co.il reader): one request per channel and day.
# yes channel id -> (id part, name); IDs IL.<part>. Hebrew titles are translated.
YES_EPG = "https://svc.yes.co.il/api/content/broadcast-schedule/channels/{cid}?date={day.year}-{day.month}-{day.day}"
YES_CHANNELS = {}   # 29 Oct 2026: yes refused GitHub (HTTP 403) - were PT39 Eurosport 1 IL, CH33 Eurosport 2 IL
CHARLTON_PAGE = "https://sport1.maariv.co.il/broadcast-schedule/"
CHARLTON_NAMES = {"2": "Sport 1", "3": "Sport 2", "4": "Sport 3", "5": "Sport 4", "1": "Sport 6"}
ATHENS = ZoneInfo("Europe/Athens")
NOVA_URL = "https://www.novasports.gr/wp-admin/admin-ajax.php"
NOVA_PAGE = "https://www.novasports.gr/tv-program/"
AMSTERDAM = ZoneInfo("Europe/Amsterdam")
BUCHAREST = ZoneInfo("Europe/Bucharest")
SARAJEVO = ZoneInfo("Europe/Sarajevo")
DIGI_PAGE = "https://www.digisport.ro/program-tv/digisport-{n}"
PRIMA_PAGE = "https://www.primaplay.ro/programtv"
# programetv.ro (29 Oct 2026, as iptv-org's reader): one page per channel and WEEKDAY name, with the
# programmes as JSON in "var pageData = {...};". For Romanian channels the other two pages don't have.
PROGRAMETV_PAGE = "https://www.programetv.ro/program-tv/{slug}/{weekday}/"
PROGRAMETV_DAYS = ("luni", "marti", "miercuri", "joi", "vineri", "sambata", "duminica")   # Monday first
PROGRAMETV_CHANNELS = {"sport-extra": "Sport Extra"}      # page name -> channel name (ID RO.SportExtra)
RO_MONTHS = {m: i for i, m in enumerate(["ianuarie", "februarie", "martie", "aprilie", "mai",
             "iunie", "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"], 1)}
SOFIA = ZoneInfo("Europe/Sofia")
BELGRADE = ZoneInfo("Europe/Belgrade")
ZAGREB = ZoneInfo("Europe/Zagreb")
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
# 11 Nov 2026 (user): the SuperSport / ESPN rows (ZA and AF) were DELETED from both playlists ("they rarely play"), and DStv's Nigeria
# feed (AF) has been returning HTTP 404 for every day (the retries add minutes to a ~45 min run). Both DStv feeds are OFF: no requests,
# no ZA. / AF. channels (CARRY_SKIP below stops the previous guide's copies being carried over). Set True to bring them back.
SUPERSPORT = False
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
BEIN_DEFAULT = "my,sg"  # hk, th, id: beIN lists the channels but publishes no programmes (checked Oct 2026)
BARE_WEEKDAY = re.compile(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?", re.I)
WEEKDAY_FULL = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
                "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}


def bein_show_fix(title, show, desc):
    """beIN sometimes sends only the episode name as the title ("Tue", "Wed") and puts the programme's real name in
    its 'category' field ("The UCL Preview Show 2026/27"), with a round code like "MD4" as the description.
    Returns (title, sub-title, description) with the show name as the title, or None when this does not apply."""
    show = re.sub(r"\s+", " ", str(show or "")).strip()
    m = BARE_WEEKDAY.fullmatch((title or "").strip())
    if not m or not show or BARE_WEEKDAY.fullmatch(show):
        return None
    day = WEEKDAY_FULL[m.group(1).lower()]
    r = re.fullmatch(r"\s*(?:MD|Match\s*Day)\s*\.?\s*(\d+)\s*\.?\s*", desc or "", re.I)
    if r:
        rnd = f"Match Day {r.group(1)}"
        return show, f"{day} - {rnd}", f"{show}: {rnd} ({day})."
    return show, day, f"{show}: {day}."
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
    # 29 Oct 2026: found by NAME in Allente's Swedish guide ("re:" = pattern tried against the channel's text;
    # their numbers aren't known - see FI_CHANNELS)
    # (ATG Live: not in Allente's Swedish guide - removed 30 Oct 2026)
    # (Motorvision TV: not in Allente's guides - it comes from blue TV, CH.MotorvisionTV, see CH_CHANNELS)
    **{rf"re:TV4\s*Sport\s*Live\s*{n}\b": (f"TV4SportLive{n}", f"TV4 Sport Live {n}") for n in range(1, 5)},
}
NO_CHANNELS = {
    "10099": ("TV2Sport1", "TV 2 Sport 1"), "10021": ("TV2Sport2", "TV 2 Sport 2"),
    "10029": ("TV2SportPremium", "TV 2 Sport Premium"), "10030": ("TV2SportPremium2", "TV 2 Sport Premium 2"),
    "50047": ("VSport1", "V Sport 1 NO"), "50046": ("VSportPlus", "V Sport+ NO"),
    "50081": ("VSport3", "V Sport 3 NO"), "10106": ("VSportPremierLeague", "V Sport Premier League"),
    # 29 Oct 2026: the extra Premier League match channels (Allente NO numbers from iptv-org's list)
    "10107": ("VSportPremierLeague1", "V Sport Premier League 1"),
    "10108": ("VSportPremierLeague2", "V Sport Premier League 2"),
    "10109": ("VSportPremierLeague3", "V Sport Premier League 3"),
    "10110": ("VSportPremierLeague4", "V Sport Premier League 4"),
    "10022": ("EurosportNorge", "Eurosport Norge"), "10091": ("Eurosport1", "Eurosport 1 NO"),
    # (V Sport 2 NO: not in Allente's Norwegian guide - it comes from RiksTV, see RIKSTV_CHANNELS)
}
# RiksTV (Norway) guide API (29 Oct 2026, as iptv-org's rikstv.no reader): one request per channel and day.
# For Norwegian channels Allente doesn't carry. RiksTV channel id -> (id part, name); IDs NO.<part>
RIKSTV_EPG = "https://play.rikstv.no/api/content-search/1/channel/{cid}/epg/{day:%Y-%m-%d}"
RIKSTV_CHANNELS = {"363": ("VSport2", "V Sport 2 NO")}
FI_CHANNELS = {
    "40051": ("VSport1", "V Sport 1 FI"), "40052": ("VSportPremium", "V Sport Premium FI"),
    "40049": ("VSportFootball", "V Sport Football FI"), "40050": ("VSportVinter", "V Sport Vinter FI"),
    "40032": ("Viaplay1Urheilu", "Viaplay 1 Urheilu"), "40031": ("Viaplay2Urheilu", "Viaplay 2 Urheilu"),
    "40030": ("Viaplay3Urheilu", "Viaplay 3 Urheilu"),
    "40015": ("MTVUrheilu1", "MTV Urheilu 1"), "40016": ("MTVUrheilu2", "MTV Urheilu 2"),
    "40054": ("MTVUrheilu3", "MTV Urheilu 3"), "40014": ("MTVMax", "MTV Max"),
    "20025": ("Eurosport1", "Eurosport 1 FI"),
    # (29 Oct 2026, evening) "V Sport+ Suomi" and a Finnish "V Sport Motor" were tried here by name and removed:
    # V Sport+ Suomi was renamed Viaplay 3 Urheilu in Aug 2025 (the user's stream shows Viaplay 1 Urheilu ->
    # linked to FI.Viaplay1Urheilu), and V Sport Motor is one Nordic channel, only in Allente's Swedish list
    # (SE.VSportMotor). The "re:" mechanism stays for the SE/NO/DK entries.
}
DK_CHANNELS = {
    "30011": ("TV2Sport", "TV 2 Sport DK"), "30051": ("TV2SportX", "TV 2 Sport X"),
    "30027": ("TV3Sport", "TV3 Sport DK"), "30050": ("TV3MAX", "TV3 MAX"),
    "50022": ("Eurosport1", "Eurosport 1 DK"), "30010": ("Eurosport2", "Eurosport 2 DK"),
    # 29 Oct 2026: found by NAME in Allente's Danish guide ("re:" = pattern, see FI_CHANNELS); the Nordic-wide
    # V Sport Ultra stays under Sweden (SE.VSportUltra)
    # (Viasat Sport Ultra DK: not in Allente's Danish guide - use SE.VSportUltra; removed 30 Oct 2026)
    # Sport Live (F3 Mediagroup's small-sports channel, ex Dantoto Racing Live): Allente DK channel 30026
    # "Sport Live HD" (iptv-org's allente.dk list; the earlier "re:" name pattern found nothing)
    "30026": ("SportLive", "Sport Live DK"),
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
    "2837": ("SportEnFrance", "Sport en France"),     # 29 Oct 2026 (SFR number from iptv-org's tv.sfr.fr list)
}
# Canal+ (myCANAL) guide API (29 Oct 2026; as iptv-org's canalplus.com reader): a token from
# authenticate.json, then one request per channel and day (day 0 = today UTC). Start times only.
# For channels SFR doesn't carry: Eurosport 360 1-8 (pop-up event channels), Canal+ Premier League,
# Infosport+. Channel ids from iptv-org's canalplus.com_fr list.
CANAL_AUTH = ("https://hodor.canalplus.pro/api/v2/mycanal/authenticate.json/webapp/6.0"
              "?experiments=beta-test-one-tv-guide:control")
CANAL_DAY = "https://hodor.canalplus.pro/api/v2/mycanal/channels/{token}/{cid}/broadcasts/day/{n}"
CANAL_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/145.0.0.0 Safari/537.36",
                 "Accept": "application/json, text/plain, */*", "Accept-Language": "fr-FR,fr;q=0.6",
                 "Origin": "https://www.canalplus.com", "Referer": "https://www.canalplus.com/"}
CANAL_CHANNELS = {       # Canal+ channel id -> (id part, name)
    # 29 Oct 2026 (late): Eurosport 360 1-8 and Canal+ Premier League removed - Canal+ refuses GitHub's servers and the
    # user deleted the channels. Infosport+ (551) also left out: it comes from the epgshare FR1 backup, so the
    # reader is skipped altogether (main() only runs it when this table isn't empty).
}
CANAL_LIVE = re.compile(r"(?i)\b(en direct|direct|live)\b")
BLUE_GUIDE = ("https://services.sg101.prd.sctv.ch/catalog/tv/channels/list/"
              "(ids={cid};start={day:%Y%m%d}0000;end={nxt:%Y%m%d}0000;level=normal)")
CH_CHANNELS = {          # blue TV channel number -> (id part, channel name)
    "483": ("blueSport1", "blue Sport 1"), "494": ("blueSport2", "blue Sport 2"),
    "590": ("blueSportFR", "blue Sport (FR)"), "1240": ("blueSportExtra", "blue Sport Extra"),
    "1543": ("MySportsEins", "MySports Eins"), "1557": ("MySportsUn", "MySports Un"),
    **{str(1542 + i): (f"MySports{i}", f"MySports {i}") for i in range(2, 10)},
    "1722": ("MySportsEDGE", "MySports EDGE"), "1601": ("SwissSportTV", "Swiss Sport TV"),
    "401": ("SRFzwei", "SRF zwei"), "367": ("RTS2", "RTS 2"), "357": ("RSILA2", "RSI LA 2"),
    # blue Sport 3 and 4 (29 Oct 2026): blue TV has no plain "blue Sport 3/4", only live pop-up channels.
    # "blue Sport 3/4 Live D" (newest numbers) first; if empty, the older "blue Sport 3/4 Live" (CH_FALLBACK).
    "1250": ("blueSport3", "blue Sport 3"), "1440": ("blueSport4", "blue Sport 4"),
    "420": ("blueZoomF", "blue Zoom (FR)"),
    "264": ("MotorvisionTV", "Motorvision TV"),   # 29 Oct 2026: for the Nordic stream - no Nordic guide lists it      # 29 Oct 2026: French version (German = 1221 "blue Zoom D")
}
CH_FALLBACK = {"1250": ["512"], "1440": ["513"]}     # channel number -> numbers to try if it comes back empty
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
    "150": ("SonySportsTen1", "Sony Sports 1"), "170": ("SonySportsTen2", "Sony Sports 2"),
    "171": ("SonySportsTen3Hindi", "Sony Sports 3 Hindi"), "610": ("SonySportsTen5", "Sony Sports 5"),
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
    "canal-246": ("CanalPlusPremium", "Canal+ Premium"),   # 30 Oct 2026: films + sport - general channel
    "canal-sport-14": ("CanalPlusSport", "Canal+ Sport"),
    "canal-sport-2-15": ("CanalPlusSport2", "Canal+ Sport 2"),
    "canal-sport-3-674": ("CanalPlusSport3", "Canal+ Sport 3"),
    "canal-sport-4-675": ("CanalPlusSport4", "Canal+ Sport 4"),
    "nsport-19": ("CanalPlusSport5", "Canal+ Sport 5"),
    "eleven-208": ("ElevenSports1", "Eleven Sports 1"),
    "eleven-sports-212": ("ElevenSports2", "Eleven Sports 2"),
    "eleven-extra-531": ("ElevenSports3", "Eleven Sports 3"),
    "eleven-sports-4-607": ("ElevenSports4", "Eleven Sports 4"),
    "eurosport-1-93": ("Eurosport1", "Eurosport 1 PL"),      # 29 Oct 2026 (Onet page names from iptv-org)
    "eurosport-2-76": ("Eurosport2", "Eurosport 2 PL"),
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
    "301": ("FightBox", "FightBox"),     # 29 Oct 2026: one pan-European schedule (FR/NL/BE/CZ feeds differ only in audio)
    # 29 Oct 2026 (numbers from iptv-org's mujtvprogram.cz list)
    "16": ("Eurosport1", "Eurosport 1 CZ"), "25": ("Eurosport2", "Eurosport 2 CZ"),
    "902": ("PremierSport2", "Premier Sport 2 CZ"),
    "344": ("ArenaSport1", "Arena Sport 1 CZ/SK"), "379": ("ArenaSport2", "Arena Sport 2 CZ/SK"),
}
# m.tv.sms.cz (29 Oct 2026, as iptv-org's reader): one cp1250 HTML page per channel and day, for Czech channels
# mujtvprogram.cz doesn't have. Page name -> (id part, name); IDs CZ.<part>. Start times only.
SMS_PAGE = "https://m.tv.sms.cz/index.php?stanice={slug}&cas=0&den={day:%Y-%m-%d}"
SMS_CHANNELS = {"Premier+Sport+1": ("PremierSport1", "Premier Sport 1 CZ"),
                "Premier+Sport+3": ("PremierSport3", "Premier Sport 3 CZ")}
IPKO_EPG = "https://stargate.ipko.tv/api/titan.tv.WebEpg/GetWebEpgData"
IPKO_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*", "Content-Type": "application/json",
                "X-AppLayout": "1", "x-language": "sq",
                "Origin": "https://ipko.tv", "Referer": "https://ipko.tv/"}
# Slovenia (29 Oct 2026): Telekom Slovenije's NEO guide - the same "stargate" API as IPKO above
# (iptv-org's neo.io reader). Slovenian feeds of Arena Sport / Arena Premium / Arena Fight and Šport TV.
NEO_EPG = "https://stargate.telekom.si/api/titan.tv.WebEpg/GetWebEpgData"
NEO_HEADERS = dict(IPKO_HEADERS, **{"x-language": "sl", "Origin": "https://neo.io", "Referer": "https://neo.io/"})
NEO_CHANNELS = {         # NEO channel slug -> (id part, channel name); IDs SI.<part>
    "arena-sport-1": ("ArenaSport1", "Arena Sport 1 SI"), "arena-sport-2": ("ArenaSport2", "Arena Sport 2 SI"),
    "arena-sport-3": ("ArenaSport3", "Arena Sport 3 SI"), "arena-sport-4": ("ArenaSport4", "Arena Sport 4 SI"),
    "arena-sport-1-premium": ("ArenaPremium1", "Arena Sport 1 Premium SI"),
    "arena-fight": ("ArenaFight", "Arena Fight SI"),
    "sport-tv-1": ("SportTV1", "Šport TV 1"), "sport-tv-2": ("SportTV2", "Šport TV 2"),
    "sport-tv-3": ("SportTV3", "Šport TV 3"),
}
AL_DEFAULT = ",".join([f"supersport-{i}" for i in range(1, 8)] + [f"tring-sport-{i}" for i in range(1, 8)])   # Tring Sport added 4 Nov 2026
CLARO_BASE = "https://programacao.claro.com.br/gatekeeper/"
CLARO_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                 "Accept": "application/json, */*",
                 "Origin": "https://programacao.claro.com.br",
                 "Referer": "https://programacao.claro.com.br/", "Accept-Language": "pt-BR,pt;q=0.9"}
BR_DEFAULT = r"sportv|premiere|espn|band ?sports|combate"     # BandSports, Combate added 29 Oct 2026
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
# Bosnia and Herzegovina feed (29 Oct 2026): own schedule (Arena Sport 1-5 BH, Premium 1-3 BH ...) on the
# same site; tried in order until one gives data. IDs BA.<name>, e.g. BA.ArenaSport1, BA.ArenaPremium1.
# mts (Telekom Srbija) TV guide (29 Oct 2026, as iptv-org's mts.rs reader): one JSON request per day with
# every channel. For Serbian channels Arena's own page doesn't list. mts code -> channel name (ID RS.<name>)
MTS_SEARCH = ("https://mts.rs/hybris/ecommerce/b2c/v1/products/search?sort=pozicija-rastuce"
              "&searchQueryContext=CHANNEL_PROGRAM&query=:pozicija-rastuce:tip-kanala-radio:TV%20kanali"
              ":channelProgramDates:{day:%Y-%m-%d}&pageSize=10000")
MTS_CHANNELS = {}        # 29 Oct 2026 (late): Eurosport 1-2 / Arena Fight Serbia removed (no data from GitHub; user deleted them)
# Croatia (29 Oct 2026): MAXtv (Hrvatski Telekom) guide API, as iptv-org's mojmaxtv.hrvatskitelekom.hr reader.
# One request per 3-hour slice (8 per day) with every channel; guest headers incl. a sha256 x-txn-id.
MAXTV_API = "https://tv-hr-prod.yo-digital.com/hr-bifrost"
MAXTV_APP_KEY, MAXTV_APP_VERSION = "GWaBW4RTloLwpUgYVzOiW5zUxFLmoMj5", "02.0.1470"
MAXTV_CHANNELS = {       # MAXtv station id -> (id part, channel name); IDs HR.<part>
    "274914856088": ("ArenaSport1", "Arena Sport 1 HR"), "282238503965": ("ArenaSport2", "Arena Sport 2 HR"),
    "282238503966": ("ArenaSport3", "Arena Sport 3 HR"), "282238503968": ("ArenaSport4", "Arena Sport 4 HR"),
    "282235944358": ("ArenaSport5", "Arena Sport 5 HR"), "282238503971": ("ArenaSport6", "Arena Sport 6 HR"),
    "282235944384": ("ArenaSport7", "Arena Sport 7 HR"), "282235944385": ("ArenaSport8", "Arena Sport 8 HR"),
    "282237992142": ("ArenaSport9", "Arena Sport 9 HR"), "282237992144": ("ArenaSport10", "Arena Sport 10 HR"),
    "346589736202": ("ArenaFight", "Arena Fight HR"),
    "311616552052": ("MAXSport1", "MAX Sport 1"), "311620648169": ("MAXSport2", "MAX Sport 2"),
    "276770856251": ("SportskaTV", "Sportska Televizija"),
    "696524328080": ("SportKlub1", "Sport Klub 1 HR"), "696528936296": ("SportKlub2", "Sport Klub 2 HR"),
    "696530472226": ("SportKlub3", "Sport Klub 3 HR"), "696530983951": ("SportKlub4", "Sport Klub 4 HR"),
    "696521768448": ("SportKlub5", "Sport Klub 5 HR"), "696524328149": ("SportKlub6", "Sport Klub 6 HR"),
    "696529959967": ("SportKlub7", "Sport Klub 7 HR"), "696523816253": ("SportKlub8", "Sport Klub 8 HR"),
    "696529447952": ("SportKlub9", "Sport Klub 9 HR"), "696529448021": ("SportKlub10", "Sport Klub 10 HR"),
    "704057896278": ("SportKlub11", "Sport Klub 11 HR"), "708158504296": ("SportKlub12", "Sport Klub 12 HR"),
    "704057896326": ("SportKlubGolf", "Sport Klub Golf HR"),
}
ARENA_PAGES_BA = ("https://tvarenaprogram.com/live/v2/ba", "https://www.tvarenasport.com/ba/tv-scheme", "https://www.tvarenasport.ba/tv-scheme",
                  "https://tvarenasport.ba/tv-scheme")
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
# Belgium (29 Oct 2026): Telenet's full TV guide - the same Liberty Global platform as Ziggo (iptv-org's
# telenet.tv reader): 4 six-hour segments a day, every channel. Telenet channel code -> our channel name
# (the names the Play Sports calendar already uses, so the IDs BE.PlaySports1, BE.DAZNJPL1 ... stay).
TELENET_SEGMENT = ("https://staticqbr-prod-be.gnp.cloud.telenet.tv/eng/web/epg-service-lite/be/nl/"
                   "events/segments/{stamp}")
TELENET_HEADERS = dict(ZIGGO_HEADERS, Origin="https://www.telenet.tv", Referer="https://www.telenet.tv/")
TELENET_CHANNELS = {
    "primesporthd": "Play Sports 1", "sportinghd2": "Play Sports 2", "sporting3": "Play Sports 3",
    "sporting4": "Play Sports 4", "primegolf": "Play Sports Golf",
    "sporting5": "Play Sports Premier League",                   # 30 Oct 2026 (BE.PlaySportsPremierLeague)
    "jplnl01": "DAZN JPL 1", "jplnl02": "DAZN JPL 2",            # = DAZN (Eleven) Pro League 1 / 2
    "11football": "DAZN 1", "11sports": "DAZN 2",                # = DAZN Eleven Sports 1 / 2
}
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


def _weak_dh_context():
    """For old servers whose handshake uses a small DH key (OpenSSL refuses it by default:
    'DH_KEY_TOO_SMALL'). Certificates are still checked; only the key-size rule is relaxed."""
    ctx = _ssl_context()
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    except ssl.SSLError:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    return ctx


HOST_CTX["m.tv.sms.cz"] = _weak_dh_context()   # 29 Oct 2026: the run failed with DH_KEY_TOO_SMALL


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
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError,
                http.client.HTTPException, OSError) as e:      # incl. a download cut short
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


def fetch_netherlands(days, pattern, debug=False, names=None, segment_url=ZIGGO_SEGMENT, headers=ZIGGO_HEADERS):
    """{channel_name: [{start, stop, title, sub, live}]} (also Telenet, Belgium: names + segment_url given)"""
    names = names if names is not None else ziggo_channels(pattern)
    if debug:
        print(f"  Netherlands: {len(names)} matching channels: {sorted(set(names.values()))}")
    if not names:
        return {}
    events = {code: {} for code in names}
    for day in days:
        for hour in (0, 6, 12, 18):
            stamp = f"{day:%Y%m%d}{hour:02d}0000"
            data = get_json_url(segment_url.format(stamp=stamp), headers) or {}
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


def fetch_programetv(days, debug=False):
    """{channel_name: [{start, stop, title, sub, live, desc}]} for PROGRAMETV_CHANNELS."""
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9"}
    out = {}
    for slug, name in PROGRAMETV_CHANNELS.items():
        rows = {}
        for day in days:
            page = get_text(PROGRAMETV_PAGE.format(slug=slug, weekday=PROGRAMETV_DAYS[day.weekday()]), {},
                            headers=hdrs, retries=2, quiet=True)
            m = re.search(r"var pageData = ({.+?});", page or "", re.S)
            try:
                data = json.loads(m.group(1)) if m else {}
            except ValueError:
                data = {}
            for it in (data.get("shows") or []) if isinstance(data, dict) else []:
                if not isinstance(it, dict):
                    continue
                try:
                    times = []
                    for k in ("start", "stop"):
                        t = datetime.fromisoformat(str(it.get(k)).replace("Z", "+00:00").replace(" ", "T"))
                        times.append((t if t.tzinfo else t.replace(tzinfo=BUCHAREST)).astimezone(timezone.utc))
                except (TypeError, ValueError):
                    continue
                start, stop = times
                if stop <= start or start.astimezone(BUCHAREST).date() != day:
                    continue                             # a weekday page can hold another week's day
                title = re.sub(r"\s+", " ", str(it.get("title") or "")).strip()
                if not title:
                    continue
                sub = re.sub(r"\s+", " ", str(it.get("titleOriginal") or "")).strip()
                desc = re.sub(r"\s+", " ", str(it.get("desc") or it.get("obs") or "")).strip()
                rx = r"\b(live|în direct|in direct|direct)\b"
                live = bool(it.get("live") is True or re.search(rx, title, re.I))
                title = re.sub(r"(?i)^\s*live\s*[:\-]?\s*|\s*[(\-:]?\s*\(?\b(live|în direct|in direct|direct)\b\)?\s*$",
                               "", title).strip() or title
                rows[start] = {"start": start, "stop": stop, "title": title, "sub": sub if sub != title else "",
                               "live": live, "desc": short_desc(desc) if desc not in (title, sub) else ""}
        evs = [rows[k] for k in sorted(rows)]
        if evs:
            out[name] = evs
        print(f"  programetv.ro {name}: {len(evs)} programmes, {sum(e['live'] for e in evs)} live")
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


def fetch_mts(days, debug=False):
    """{channel_name: [{start, stop, title, sub, live, desc}]} for MTS_CHANNELS from mts.rs."""
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json, */*",
            "Accept-Language": "sr-RS,sr;q=0.9"}
    rows = {name: {} for name in MTS_CHANNELS.values()}
    shown = False
    for day in days:
        data = get_json_url(MTS_SEARCH.format(day=day), hdrs, quiet=True)
        products = data.get("products") if isinstance(data, dict) else None
        if not isinstance(products, list):
            continue
        for ch in products:
            name = MTS_CHANNELS.get((ch or {}).get("code")) if isinstance(ch, dict) else None
            if not name:
                continue
            for it in ch.get("programs") or []:
                if not isinstance(it, dict):
                    continue
                if not shown:
                    print(f"    mts programme fields: {sorted(it)}")
                    shown = True
                try:
                    times = []
                    for k in ("start", "end"):
                        v = it.get(k)
                        if isinstance(v, (int, float)) or str(v).isdigit():
                            v = int(v)
                            t = datetime.fromtimestamp(v / 1000 if v > 10**11 else v, timezone.utc)
                        else:
                            t = datetime.fromisoformat(str(v).replace("Z", "+00:00").replace(" ", "T"))
                            t = t if t.tzinfo else t.replace(tzinfo=BELGRADE)
                        times.append(t.astimezone(timezone.utc))
                except (TypeError, ValueError):
                    continue
                start, stop = times
                title = re.sub(r"\s+", " ", str(it.get("title") or "")).strip()
                if not title or stop <= start:
                    continue
                cat = it.get("category")
                sub = ", ".join(map(str, cat)) if isinstance(cat, list) else str(cat or "").strip()
                desc = re.sub(r"\s+", " ", str(it.get("description") or "")).strip()
                rx = r"\b(uživo|uzivo|live)\b|\(už\)|\(uz\)"
                live = bool(it.get("live") is True or re.search(rx, title, re.I))
                title = re.sub(r"(?i)\s*[-(:,]?\s*(\b(uživo|uzivo|live)\b|\(u[žz]\))\s*\)?\s*$", "", title).strip() or title
                rows[name][start] = {"start": start, "stop": stop, "title": title,
                                     "sub": sub if sub != title else "", "live": live,
                                     "desc": short_desc(desc) if desc not in (title, sub) else ""}
    out = {}
    for name, evs in rows.items():
        if evs:
            out[name] = [evs[k] for k in sorted(evs)]
        print(f"  mts {name}: {len(evs)} programmes, {sum(e['live'] for e in evs.values())} live")
    return out


def maxtv_headers():
    """Guest headers for MAXtv's API (fresh tracking id + x-txn-id each request, like the web app)."""
    import hashlib
    h = {"app_key": MAXTV_APP_KEY, "app_version": MAXTV_APP_VERSION, "device-id": MAXTV_DEVICE,
         "tenant": "tv", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                       "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
         "Origin": "https://mojmaxtv.hrvatskitelekom.hr", "x-call-type": "GUEST_USER",
         "x-call-time": str(int(time.time() * 1000)), "x-request-session-id": MAXTV_SESSION,
         "x-request-tracking-id": str(uuid.uuid4()), "x-tv-step": "EPG_SCHEDULES", "x-tv-flow": "EPG",
         "x-user-agent": f"web|web|Chrome-149|{MAXTV_APP_VERSION}|1", "Accept": "application/json, */*"}
    h["x-txn-id"] = hashlib.sha256("".join((h["x-request-tracking-id"], MAXTV_SESSION, MAXTV_DEVICE,
                                            h["x-call-time"])).encode()).hexdigest()[:32]
    return h


MAXTV_DEVICE, MAXTV_SESSION = str(uuid.uuid4()), str(uuid.uuid4())


def fetch_maxtv(days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for MAXTV_CHANNELS (Croatia)."""
    rows = {sid: {} for sid in MAXTV_CHANNELS}
    shown, got_any = False, False
    for day in days:
        for offset in range(0, 24, 3):
            url = (f"{MAXTV_API}/epg/channel/schedules?date={day:%Y-%m-%d}&hour_offset={offset}&hour_range=3"
                   f"&channelMap_id=&filler=true&app_language=hr&natco_code=hr")
            data = get_json_url(url, maxtv_headers(), quiet=True)
            chans = data.get("channels") if isinstance(data, dict) else None
            if not isinstance(chans, dict):
                if day == days[0] and offset == 0 and not got_any:
                    print("  WARNING: MAXtv gave no schedule (blocked or changed?) - skipping Croatia", file=sys.stderr)
                    return {}
                continue
            got_any = True
            for sid in MAXTV_CHANNELS:
                for it in chans.get(sid) or []:
                    if not isinstance(it, dict):
                        continue
                    if not shown:
                        print(f"    MAXtv programme fields: {sorted(it)}")
                        shown = True
                    try:
                        start, stop = (datetime.fromisoformat(str(it.get(k)).replace("Z", "+00:00"))
                                       for k in ("start_time", "end_time"))
                        start = (start if start.tzinfo else start.replace(tzinfo=ZAGREB)).astimezone(timezone.utc)
                        stop = (stop if stop.tzinfo else stop.replace(tzinfo=ZAGREB)).astimezone(timezone.utc)
                    except (TypeError, ValueError):
                        continue
                    title = re.sub(r"\s+", " ", str(it.get("description") or "")).strip()
                    if not title or stop <= start:
                        continue
                    sub = re.sub(r"\s+", " ", str(it.get("episode_name") or "")).strip()
                    flag = (any(v is True for k, v in it.items() if "live" in k.lower())
                            or "live" in str(it.get("airing_type") or "").lower())   # MAXtv field (29 Oct log)
                    rx = r"\b(uživo|uzivo|live)\b|\(u\)|\(už\)"
                    live = flag or bool(re.search(rx, title, re.I) or re.search(rx, sub, re.I))
                    title = re.sub(r"(?i)\s*[-(:,]?\s*(\b(uživo|uzivo|live)\b|\(u\)|\(už\))\s*\)?\s*$", "", title).strip() or title
                    title = re.sub(r"(?i)^\s*(uživo|uzivo|live)\s*[:\-–]\s*", "", title).strip() or title   # leading "UŽIVO:"
                    rows[sid][start] = {"start": start, "stop": stop, "title": title,
                                        "sub": sub if sub != title else "", "live": live, "desc": ""}
    out = {}
    for sid, (part, name) in MAXTV_CHANNELS.items():
        evs = [rows[sid][k] for k in sorted(rows[sid])]
        if evs:
            out[part] = evs
        if debug or not evs:
            print(f"  MAXtv {name}: {len(evs)} programmes")
    return out


def fetch_arena(days, debug=False, url=ARENA_PAGE, lang="sr-RS,sr;q=0.9"):
    """{channel_name: [{start, title, sub, live}]} for the dates in days."""
    page = get_text(url, {}, headers={"User-Agent": HEADERS["User-Agent"], "Accept-Language": lang})
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


# Slovenian titles (29 Oct 2026, late): "Am. nogomet (M): Broncos - Chiefs, NFL 2026/2027". Google does these badly
# ("Football (M)", "Soccer (M)", "Am. football"), so the sport word, the (M)/(Ž) tag and common round/league words
# are put into English first; anything left is translated as usual.
SI_SPORTS = [("am. nogomet", "American football"), ("ameriški nogomet", "American football"), ("nogomet", "Football"),
             ("košarka", "Basketball"), ("hokej na ledu", "Ice hockey"), ("hokej", "Ice hockey"),
             ("rokomet", "Handball"), ("odbojka na mivki", "Beach volleyball"), ("odbojka", "Volleyball"),
             ("bejzbol", "Baseball"), ("boks", "Boxing"), ("tenis", "Tennis"), ("smučanje", "Skiing"),
             ("kolesarstvo", "Cycling"), ("atletika", "Athletics"), ("plavanje", "Swimming"), ("golf", "Golf"),
             ("futsal", "Futsal"), ("mali nogomet", "Futsal"), ("vaterpolo", "Water polo"), ("pikado", "Darts"),
             ("snooker", "Snooker"), ("borilne veščine", "Martial arts"), ("motociklizem", "Motorcycling")]
SI_WORDS = [(r"\bosmina finala\b", "Round of 16"), (r"\bčetrtfinale\b", "Quarter-final"), (r"\bpolfinale\b", "Semi-final"),
            (r"\bfinale\b", "Final"), (r"\bkončnica\b", "Play-offs"), (r"\bzaključni del\b", "Final stage"),
            (r"\bskupina\b", "Group"), (r"\bpremier liga\b", "Premier League"), (r"\bliga prvakov\b", "Champions League"),
            (r"\bprva liga\b", "First League"), (r"\bargentinska liga\b", "Argentine League"),
            (r"\bškotska liga\b", "Scottish League"), (r"\bnizozemska liga\b", "Dutch League"),
            (r"\bšvedska liga\b", "Swedish League"), (r"\bgrška liga\b", "Greek League"), (r"\balpska liga\b", "Alps League"),
            (r"\bbolgarska\b", "Bulgarian"), (r"\bšpanska liga\b", "Spanish League"), (r"\bturška liga\b", "Turkish League"),
            (r"\bdunaj\b", "Vienna"), (r"\bboks\b", "Boxing"), (r"\bliga\b", "League"), (r"\bženski nogometni magazin\b", "Women's football magazine")]


def si_title(title):
    """Slovenian sport title -> English where it's fixed wording (sport, gender, round, league)."""
    t = title or ""
    m = re.match(r"(?i)^\s*([^():]{2,25}?)\s*\((m|ž|z|w)\)\s*:\s*", t)
    if m:
        sport = m.group(1).strip().lower()
        eng = next((e for k, e in SI_SPORTS if sport == k), None) or m.group(1).strip()
        women = m.group(2).lower() in ("ž", "z", "w")
        t = f"{eng}{' (Women)' if women else ''}: " + t[m.end():]
    else:
        m = re.match(r"(?i)^\s*([^():]{2,25}?)\s*:\s*", t)
        if m and any(m.group(1).strip().lower() == k for k, _ in SI_SPORTS):
            t = next(e for k, e in SI_SPORTS if m.group(1).strip().lower() == k) + ": " + t[m.end():]
    for rx, eng in SI_WORDS:
        t = re.sub("(?i)" + rx, eng, t)
    return re.sub(r"\s+,", ",", re.sub(r"\s{2,}", " ", t)).strip()


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
                evs[key] = {"start": key, "title": si_title(title),
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


def _it_12h(h, m):
    """12-hour clock, lower case, no space, minutes dropped on the hour: 12:30am, 3pm, 5:45pm (6 Nov 2026, user's style)"""
    return f"{(h % 12) or 12}{(':%02d' % m) if m else ''}{'am' if h < 12 else 'pm'}"


CLOCK_24H = re.compile(r"(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])(?!\s?[AaPp]\.?[Mm])(?!\.\d)")
CLOCK_SHORT = re.compile(r"(?<![\w:.])(\d{1,2})(?:[:.]([0-5]\d))?\s?([AaPp])(?:\.[Mm]\.|[Mm])(?!\w)")


def clock12(text):
    """EVERY clock time in a title / secondary title / description -> 12-hour with AM / PM (6 Nov 2026, user request, whole Sport
    guide; applied last, in add_programme, so nothing that parses the 24-hour text is affected): "19:00" -> "7pm", "00:15" ->
    "12:15am", "9:00 PM" / "3.30pm" style -> "9pm" / "3:30pm". Skipped: lap times ("1:23.456"), h:mm:ss, anything already "7:45 PM"."""
    t = CLOCK_24H.sub(lambda m: _it_12h(int(m.group(1)), int(m.group(2))), text or "")

    def short(m):
        h = int(m.group(1))
        if not 1 <= h <= 12:
            return m.group(0)
        mm = m.group(2)
        return f"{h}{(':' + mm) if mm and mm != '00' else ''}{'am' if m.group(3).lower() == 'a' else 'pm'}"
    return CLOCK_SHORT.sub(short, t)


it_12h = clock12                                       # (the Italian-only name used earlier on 6 Nov)


def it_desc_en(desc, start=None):
    """Sky Italia's fixed match-description wording, rewritten to English WITHOUT Google (6 Nov 2026): the translator returned it
    half done (46 of 298 cached ones). User's wording: no code number, 12-hour clock with AM / PM, "Matchday 11".
    "Cod. 418446 - Serie A - 11a giornata. Calcio d'inizio ore 20:45." -> "Serie A - Matchday 11. Kick-off at 7:45 PM." The kick-off
    (and any other clock time) in Sky's text is ITALIAN time; it is converted to UK time for the event's own date, because the
    guide's blocks and its \"Coverage from\" line are UK time. Other text is left alone (the normal translation handles it)."""
    t = desc or ""
    if not t:
        return t

    def uk(h, m):
        if start is None:
            return _it_12h(h, m)
        day = start.astimezone(ROME).date()
        local = datetime(day.year, day.month, day.day, h, m, tzinfo=ROME)
        if local < start.astimezone(ROME) - timedelta(hours=6):       # a kick-off just after midnight belongs to the next day
            local += timedelta(days=1)
        uk_dt = local.astimezone(LONDON)
        return _it_12h(uk_dt.hour, uk_dt.minute)

    t = re.sub(r"\bCod\.?\s*\d{3,9}\s*(?:[-\u2013]\s*)?", "", t)                         # "Cod. 418446 - " (any position)
    t = re.sub(r"\b(\d{1,2})\s*[ao]\s+giornata\b", r"Matchday \1", t)
    t = re.sub(r"(?i)\bCalcio d['\u2019]inizio(?:\s+alle)?(?:\s+ore)?\s*(\d{1,2})[:.](\d{2})",
               lambda m: "Kick-off at " + uk(int(m.group(1)), int(m.group(2))), t)
    t = re.sub(r"(?i)\bCalcio d['\u2019]inizio(?:\s+alle)?(?:\s+ore)?\s*(\d{1,2})\b(?![:.\d])",
               lambda m: "Kick-off at " + uk(int(m.group(1)), 0), t)
    t = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b(?!\s?[AaPp][Mm])", lambda m: uk(int(m.group(1)), int(m.group(2))), t)   # "Dalle 18:45"
    t = it_shorthand(_it_dedupe(t))
    return re.sub(r"\s{2,}", " ", t).strip()


IT_FOOTBALL_RE = re.compile(r"(?i)\b(calcio|serie [abc]|champions|europa league|conference|campionato|giornata|giallorossi|rossoneri|nerazzurri|"
                            r"bianconeri|biancocelesti|punti|pari|gare|partita|stadio|olimpico|derby|squadra|panchina|trasferta)\b")
IT_NOT_FOOTBALL_RE = re.compile(r"(?i)\b(pugil\w*|round|ring|pesi?|mondiale|wbc|wba|ibf|wbo|ufc|mma)\b")


def it_shorthand(t):
    """Sky Italia's football shorthand that Google mistranslates (8 Nov 2026, Roma - Sassuolo: \"4 ko di fila\" came out as \"4 kb of film\",
    \"12 gare\" as \"12 station\", \"5 pari\" as \"5 bet\", \"TC:\" stayed): spelled out in plain Italian first. \"N ko\" means defeats ONLY in a
    football text (in boxing it is knockouts), so it needs football words in the text and no boxing words."""
    if not t:
        return t
    t = re.sub(r"\bTC:", "Telecronaca:", t)
    if IT_FOOTBALL_RE.search(t) and not IT_NOT_FOOTBALL_RE.search(t):
        t = re.sub(r"\b(\d+)\s*(?:ko|k\.o\.)(?![\w'])", r"\1 sconfitte", t, flags=re.I)
        t = re.sub(r"\bsconfitte consecutivi\b", "sconfitte consecutive", t)
        t = re.sub(r"\b(\d+)\s*pari\b", r"\1 pareggi", t, flags=re.I)
        t = re.sub(r"\bun pari\b", "un pareggio", t, flags=re.I)
        t = re.sub(r"\b(\d+)\s*gare\b", r"\1 partite", t, flags=re.I)
    return t


def _it_dedupe(t):
    """Sky's description is often the same fragment 3-4 times, each cut short with \"... \" (\"... Ep.4 06/11/2026 Europa & Conference
    League Remix. - ... Ep.4 ... - ... Ep.4 ... - Europa & Conference League Remix\"): said once. Only text that has those \"... \" fragments is
    touched, and a fragment is dropped only when it repeats (or sits inside) one already kept."""
    if not t or not re.search(r"(?:^|\s-\s)\.\.\.\s", t):
        return t
    keep, parts_n, dropped = [], 0, False             # keep: [(normalised, text)]
    for part in re.split(r"\s+-\s+", t):
        q = re.sub(r"^\.{3}\s*", "", part.strip()).strip()
        n = re.sub(r"\W+", " ", q).lower().strip()
        if not n:
            continue
        parts_n += 1
        if any(n == k or (len(n) >= 20 and n in k) for k, _ in keep):
            dropped = True
            continue
        if any(len(k) >= 20 and k in n for k, _ in keep):
            dropped = True
        keep = [(k, x) for k, x in keep if not (len(k) >= 20 and k in n)] + [(n, q)]
    # nothing repeated: the text is left exactly as it was (its cached translation stays valid)
    return " - ".join(x for _, x in keep) if dropped else t


IT_POPUP_RE = re.compile(r"(?i)^sky sport 25[1-8]$")
IT_TEAMS_RE = re.compile(r"^[^:/()]+?\s+[-\u2013]\s+[^:/()]+$")                  # "Venezia - Udinese" (no colon, slash or brackets)
# Italian names of foreign clubs and countries -> the English names (8 Nov 2026, user: "Mainz vs FC Bayern Monaco" should be "Bayern Munich").
# Team titles are not translated (Google damaged them), so these are swapped by a list; Italian clubs (Roma, Inter, Napoli ...) keep their names.
IT_TEAM_NAMES = {
    # Germany
    "FC Bayern Monaco": "Bayern Munich", "Bayern Monaco": "Bayern Munich", "Lipsia": "Leipzig", "Stoccarda": "Stuttgart", "Colonia": "Cologne",
    "Francoforte": "Frankfurt", "Amburgo": "Hamburg", "Norimberga": "Nuremberg", "Brema": "Bremen", "Friburgo": "Freiburg", "Magonza": "Mainz",
    "Herta Berlino": "Hertha Berlin", "Hertha Berlino": "Hertha Berlin", "Union Berlino": "Union Berlin", "Berlino": "Berlin",
    # Spain / Portugal
    "Siviglia": "Sevilla", "Valenza": "Valencia", "Saragozza": "Zaragoza", "Maiorca": "Mallorca", "Lisbona": "Lisbon",
    # France / Belgium / Netherlands / Switzerland / Austria
    "Marsiglia": "Marseille", "Lione": "Lyon", "Nizza": "Nice", "Tolosa": "Toulouse", "Lilla": "Lille", "Strasburgo": "Strasbourg",
    "Bruges": "Brugge", "Anversa": "Antwerp", "Gand": "Gent", "Liegi": "Liege", "Basilea": "Basel", "Zurigo": "Zurich", "Ginevra": "Geneva",
    "Berna": "Bern", "Salisburgo": "Salzburg",
    # elsewhere in Europe
    "Copenaghen": "Copenhagen", "Atene": "Athens", "Praga": "Prague", "Mosca": "Moscow", "Dinamo Kiev": "Dynamo Kyiv", "Kiev": "Kyiv",
    "Zagabria": "Zagreb", "Belgrado": "Belgrade", "Stella Rossa": "Red Star Belgrade", "Bucarest": "Bucharest", "Varsavia": "Warsaw",
    "Lubiana": "Ljubljana", "San Pietroburgo": "St Petersburg", "Edimburgo": "Edinburgh", "Cracovia": "Krakow",
    # national teams
    "Repubblica Ceca": "Czech Republic", "Spagna": "Spain", "Germania": "Germany", "Francia": "France", "Inghilterra": "England",
    "Scozia": "Scotland", "Galles": "Wales", "Irlanda del Nord": "Northern Ireland", "Irlanda": "Ireland", "Paesi Bassi": "Netherlands",
    "Olanda": "Netherlands", "Belgio": "Belgium", "Portogallo": "Portugal", "Svizzera": "Switzerland", "Croazia": "Croatia",
    "Polonia": "Poland", "Ucraina": "Ukraine", "Turchia": "Turkey", "Grecia": "Greece", "Danimarca": "Denmark", "Svezia": "Sweden",
    "Norvegia": "Norway", "Finlandia": "Finland", "Islanda": "Iceland", "Ungheria": "Hungary", "Slovacchia": "Slovakia",
    "Macedonia del Nord": "North Macedonia", "Israele": "Israel", "Lettonia": "Latvia", "Lituania": "Lithuania", "Lussemburgo": "Luxembourg",
    "Cipro": "Cyprus", "Moldavia": "Moldova", "Bielorussia": "Belarus", "Isole Faer Oer": "Faroe Islands", "Gibilterra": "Gibraltar",
    "Azerbaigian": "Azerbaijan", "Kazakistan": "Kazakhstan", "Stati Uniti": "United States", "Messico": "Mexico", "Giappone": "Japan",
    "Corea del Sud": "South Korea", "Marocco": "Morocco", "Egitto": "Egypt", "Brasile": "Brazil", "Cile": "Chile", "Per\u00f9": "Peru",
}
_IT_TEAM_RE = re.compile(r"(?<![\w])(" + "|".join(re.escape(k) for k in sorted(IT_TEAM_NAMES, key=len, reverse=True)) + r")(?![\w])", re.I)
_IT_TEAM_LOWER = {k.lower(): v for k, v in IT_TEAM_NAMES.items()}


def it_teams_en(title):
    """English names for the foreign clubs / countries in an Italian "A - B" title (not for other titles)."""
    return _IT_TEAM_RE.sub(lambda m: _IT_TEAM_LOWER.get(m.group(1).lower(), m.group(1)), title) if title else title
IT_NOT_LIVE_RE = re.compile(r"(?i)\b(replica|differita|highlights?|sintesi|magazine|speciale|studio|post ?partita|pre ?partita|"
                            r"gol|goal|diretta gol)\b")


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
                ev = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                      "desc": it_desc_en(pick_desc(it, "eventSynopsis", "epgEventSynopsis"), start)}
                # Every Italian channel (5 Nov 2026): a title "Team A - Team B" holds team names, which Google damaged (Como -> "How",
                # Vado -> "I go", Roma -> "Rome", Savoia - Potenza -> "Savoy - Power"), so it is NOT translated (en() skips it).
                teams = bool(IT_TEAMS_RE.match(title)) and not IT_NOT_LIVE_RE.search(title)
                if teams:
                    ev["no_translate"] = True
                    ev["title"] = it_teams_en(title)                    # "Mainz - FC Bayern Monaco" -> "Mainz - Bayern Munich"
                if IT_POPUP_RE.match(names[cid]) and teams:
                    # Sky Sport 251-258 are the pop-up match channels: Sky flags only some of their matches "Diretta",
                    # but every match on them is live (unless the title says replay / highlights).
                    ev["live"] = True
                evs[start] = ev
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
    warned = set()
    for day in days:
        data = get_json_url(ALLENTE_GUIDE.format(tld=tld, day=day), hdrs) or {}
        chans = data.get("channels") if isinstance(data, dict) else None
        chans = {str(c.get("id")): c for c in chans if isinstance(c, dict)} if isinstance(chans, list) else {}
        found = {}                                     # "re:" entry -> Allente channel numbers whose text matches
        for key in wanted:
            if key.startswith("re:"):
                rx = re.compile(key[3:], re.I)
                found[key] = [c for c, ch in chans.items()
                              if any(isinstance(v, str) and rx.search(v) for v in ch.values())]
                if not found[key] and chans and key not in warned:
                    warned.add(key)
                    names = sorted({v for ch in chans.values() for v in ch.values()
                                    if isinstance(v, str) and len(v) < 60 and re.search(r"sport|motor|urheilu", v, re.I)})
                    print(f"  WARNING: Allente .{tld}: no channel matches {key[3:]!r}; channels with sport/motor in "
                          f"their text: {', '.join(names[:20]) or 'none'}", file=sys.stderr)
        if debug:
            print(f"  Allente .{tld} {day}: {len(chans)} channels, "
                  f"{sum(len((chans.get(c) or {}).get('programs') or []) for c in wanted)} programmes on the chosen ones"
                  + "".join(f"; {k[3:]!r} -> {v}" for k, v in found.items()))
        for cid in wanted:
            progs = [pr for src in (found.get(cid) or [cid]) for pr in (chans.get(src) or {}).get("programs") or []]
            for pr in progs:
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


# DStv's guide sometimes answers "404 Not Found" for a day it has (29 Oct 2026: 5 of 7 South
# Africa days in one run). Days that fail are asked again after the others, in DSTV_RETRY_WAITS
# more rounds (seconds to wait first), with a cache-busting extra so a stale CDN answer isn't
# reused. Days still missing are listed in DSTV_MISSING (DStv country -> [(start, end) UTC]) and
# filled from the previous guide after the build (fill_missing_days).
DSTV_RETRY_WAITS = (30, 90)
DSTV_MISSING = {}


def fetch_dstv(country, extra, zone, days, lo, hi, debug=False):
    """{tidy channel name: [{start, stop, title, sub, live}]} for DStv channel numbers lo..hi"""
    tz, events, names = ZoneInfo(zone), {}, {}
    pages, todo = {}, list(days)
    for rnd in range(len(DSTV_RETRY_WAITS) + 1):
        if rnd:
            print(f"  DStv {country}: {len(todo)} day(s) failed - trying again in {DSTV_RETRY_WAITS[rnd - 1]} s")
            time.sleep(DSTV_RETRY_WAITS[rnd - 1])
        failed = []
        for day in todo:
            url = DSTV_GUIDE.format(day=day, extra=extra, country=country)
            if rnd:
                url += f"&_={int(time.time())}"
            data = get_json_url(url, DSTV_HEADERS, quiet=bool(rnd))
            chans = data.get("Channels") if isinstance(data, dict) else None
            if isinstance(chans, list) and chans:
                pages[day] = chans
                if rnd:
                    print(f"  DStv {country} {day}: OK on retry")
            else:
                failed.append(day)
        todo = failed
        if not todo:
            break
    if todo:
        print(f"  WARNING: DStv {country}: no guide for {', '.join(str(d) for d in todo)} - "
              f"those days are kept from the previous guide")
        DSTV_MISSING[country] = [
            (datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc),
             (datetime(d.year, d.month, d.day, tzinfo=tz) + timedelta(days=1)).astimezone(timezone.utc))
            for d in todo]
    for day in days:
        chans = pages.get(day, [])
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
            sub = comp if comp and comp.lower() != title.lower() else ""
            desc = pick_desc(it, "description", "synopsis")
            fixed = bein_show_fix(title, it.get("category") or (it.get("data") or {}).get("categoryName"), desc)
            if fixed:                                    # "Tue" + category "The UCL Preview Show 2026/27"
                title, sub, desc = fixed
            per[cid][start] = {"start": start, "stop": stop, "title": title,
                               "sub": sub, "live": live, "desc": desc}
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


def fetch_canal(n_days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for CANAL_CHANNELS from the myCANAL guide API."""
    auth = get_json_url(CANAL_AUTH, CANAL_HEADERS)
    token = auth.get("token") if isinstance(auth, dict) else None
    if not token:
        print("  WARNING: Canal+ gave no guide token - Eurosport 360 / Canal+ Premier League / Infosport+ "
              "left to epgshare01's FR1 backup", file=sys.stderr)
        return {}
    out, shown_fields = {}, False
    for cid, (part, name) in CANAL_CHANNELS.items():
        rows = {}
        for n in range(n_days):
            data = get_json_url(CANAL_DAY.format(token=token, cid=cid, n=n), CANAL_HEADERS, quiet=True)
            slices = data.get("timeSlices") if isinstance(data, dict) else None
            items = [c for sl in (slices or []) if isinstance(sl, dict) for c in (sl.get("contents") or [])
                     if isinstance(c, dict)]
            if not items:
                if n == 0:
                    break                                # nothing today: the channel isn't served
                continue
            if not shown_fields:                         # once per run, to check the fields on GitHub
                print(f"    Canal+ programme fields: {sorted(items[0])}")
                shown_fields = True
            for it in items:
                st = it.get("startTime")
                try:
                    if isinstance(st, (int, float)) or str(st).isdigit():
                        st = int(st)
                        start = datetime.fromtimestamp(st / 1000 if st > 10**11 else st, timezone.utc)
                    else:
                        start = datetime.fromisoformat(str(st).replace("Z", "+00:00")).astimezone(timezone.utc)
                except (TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", str(it.get("title") or "")).strip()
                sub = re.sub(r"\s+", " ", str(it.get("subtitle") or "")).strip()
                if not title:
                    continue
                flag = any(v is True for k, v in it.items() if "live" in k.lower())
                live = flag or bool(CANAL_LIVE.search(title) or CANAL_LIVE.search(sub))
                title = re.sub(r"(?i)\s*[(\-:]?\s*\b(en direct|direct|live)\b\s*\)?\s*$", "", title).strip() or title
                rows[start] = {"start": start, "title": title, "sub": sub if sub != title else "",
                               "live": live, "desc": ""}
        starts = sorted(rows)
        evs = []
        for k, a in enumerate(starts):
            stop = starts[k + 1] if k + 1 < len(starts) else a + timedelta(hours=1)
            if stop - a > timedelta(hours=12):           # a gap, not a 12-hour programme
                stop = a + timedelta(hours=2)
            evs.append(dict(rows[a], stop=stop))
        if evs:
            out[part] = evs
        print(f"  Canal+ {name}: {len(evs)} programmes, {sum(e['live'] for e in evs)} live")
    return out


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
    missing = []
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
        else:
            missing.append(slug)
    if missing:                                            # 4 Nov 2026: Tring Sport 1-7 are tried, IPKO may not list them all
        print(f"  IPKO has no guide for: {', '.join(missing)}")
    return out


def fetch_neo(days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for NEO_CHANNELS (Slovenia)."""
    out = {}
    for slug, (part, name) in NEO_CHANNELS.items():
        evs = {}
        for day in days:
            frm = int(datetime(day.year, day.month, day.day, tzinfo=LJUBLJANA).timestamp())
            nxt = day + timedelta(days=1)
            to = int(datetime(nxt.year, nxt.month, nxt.day, tzinfo=LJUBLJANA).timestamp())
            data = post_json(NEO_EPG, {"ch_ext_id": slug, "from": frm, "to": to}, NEO_HEADERS) or {}
            shows = data.get("shows") if isinstance(data, dict) else None
            shows = shows if isinstance(shows, list) else []
            if not shows and day == days[0]:
                break                                  # channel not in NEO's guide
            for sh in shows:
                try:
                    start = datetime.fromtimestamp(int(sh["show_start"]), timezone.utc)
                    stop = datetime.fromtimestamp(int(sh["show_end"]), timezone.utc)
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", sh.get("title") or "").strip()
                if not title or stop <= start:
                    continue
                rx = r"\b(live|v živo|neposredni prenos|prenos v živo|uživo)\b"
                live = bool(sh.get("is_live")) or bool(re.search(rx, title, re.I))
                title = re.sub(r"\s*[-(,:]?\s*" + rx + r"\s*\)?\s*$", "", title, flags=re.I).strip() or title
                desc = pick_desc(sh, "summary", "description", "desc", "synopsis")
                title = si_title(title)                # Slovenian sport / round words -> English
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": desc if desc != title else ""}
        if evs:
            out[part] = [evs[k] for k in sorted(evs)]
        print(f"  NEO {name}: {len(evs)} programmes, {sum(e['live'] for e in evs.values())} live")
    return out


def fetch_rikstv(days, debug=False):
    """{RiksTV channel id: [{start, stop, title, sub, live, desc}]} for RIKSTV_CHANNELS."""
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json", "Accept-Language": "nb-NO,nb;q=0.9"}
    out = {}
    for cid, (part, name) in RIKSTV_CHANNELS.items():
        evs = {}
        for day in days:
            data = get_json_url(RIKSTV_EPG.format(cid=cid, day=day), hdrs, quiet=True)
            for it in data if isinstance(data, list) else []:
                if not isinstance(it, dict):
                    continue
                try:
                    start, stop = (datetime.fromisoformat(str(it.get(k)).replace("Z", "+00:00"))
                                   for k in ("broadcastedTime", "broadcastedTimeEnd"))
                    start = (start if start.tzinfo else start.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
                    stop = (stop if stop.tzinfo else stop.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
                except (TypeError, ValueError):
                    continue
                series = re.sub(r"\s+", " ", str(it.get("seriesName") or "")).strip()
                ep = re.sub(r"\s+", " ", str(it.get("name") or "")).strip()
                title, sub = (series or ep), (ep if series and ep != series else "")
                if not title or stop <= start:
                    continue
                flag = any(v is True for k, v in it.items() if "live" in k.lower())
                live = flag or bool(re.search(r"\b(direkte|live)\b", f"{title} {sub}", re.I))
                desc = re.sub(r"\s+", " ", str(it.get("description") or it.get("synopsis") or "")).strip()
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": sub, "live": live,
                              "desc": short_desc(desc) if desc and desc not in (title, sub) else ""}
        if evs:
            out[cid] = [evs[k] for k in sorted(evs)]
        print(f"  RiksTV {name}: {len(evs)} programmes, {sum(e['live'] for e in evs.values())} live")
    return out


def fetch_sms(days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for SMS_CHANNELS (m.tv.sms.cz)."""
    out = {}
    for slug, (part, name) in SMS_CHANNELS.items():
        rows = []
        for day in days:
            raw = fetch(SMS_PAGE.format(slug=slug, day=day), headers=HEADERS, parse="bytes", retries=2, quiet=True)
            if not raw:
                continue
            try:
                page = raw.decode("utf-8")
            except UnicodeDecodeError:
                page = raw.decode("cp1250", "replace")   # the site's own pages are windows-1250
            cur = day
            prev = None
            for block in re.split(r"<div[^>]*class=[\"']porad[\"' ]", page)[1:]:
                m = re.search(r"<span[^>]*>\s*(\d{1,2})[.:](\d{2})\s*</span>", block)
                t = re.search(r"<a[^>]*class=[\"']nazev[^\"']*[\"'][^>]*>\s*<div[^>]*>(.*?)</div>", block, re.S)
                if not m or not t:
                    continue
                start = datetime(cur.year, cur.month, cur.day, int(m.group(1)), int(m.group(2)), tzinfo=PRAGUE)
                if prev and start < prev:                  # past midnight
                    cur += timedelta(days=1)
                    start += timedelta(days=1)
                prev = start
                title = html.unescape(re.sub(r"<[^>]+>|\s+", " ", t.group(1))).strip()
                title = re.sub(r"\s+", " ", title)
                d = re.search(r"<div[^>]*class=[\"']detail[^\"']*[\"'][^>]*>(.*?)</div>", block, re.S)
                desc = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", d.group(1)))).strip() if d else ""
                live = bool(re.search(r"\b(živě|zive|live|přímý přenos)\b", f"{title} {desc}", re.I))
                title = re.sub(r"(?i)\s*[-(,]?\s*\b(živě|live)\b\s*\)?\s*$", "", title).strip() or title
                if title:
                    rows.append({"start": start.astimezone(timezone.utc), "title": title, "sub": "",
                                 "live": live, "desc": short_desc(desc) if desc and desc != title else ""})
        uniq = {r["start"]: r for r in rows}
        starts = sorted(uniq)
        evs = []
        for k, a in enumerate(starts):
            stop = starts[k + 1] if k + 1 < len(starts) else a + timedelta(hours=1)
            if stop - a > timedelta(hours=8):
                stop = a + timedelta(hours=2)
            evs.append(dict(uniq[a], stop=stop))
        if evs:
            out[part] = evs
        print(f"  sms.cz {name}: {len(evs)} programmes, {sum(e['live'] for e in evs)} live")
    return out


def fetch_yes(days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for YES_CHANNELS."""
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json", "Accept-Language": "he-IL"}
    out = {}
    for cid, (part, name) in YES_CHANNELS.items():
        evs = {}
        for day in days:
            data = get_json_url(YES_EPG.format(cid=cid, day=day), hdrs, quiet=True)
            for it in (data.get("items") or []) if isinstance(data, dict) else []:
                if not isinstance(it, dict):
                    continue
                try:
                    start, stop = (datetime.fromisoformat(str(it.get(k)).replace("Z", "+00:00"))
                                   for k in ("starts", "ends"))
                    start = (start if start.tzinfo else start.replace(tzinfo=ISRAEL)).astimezone(timezone.utc)
                    stop = (stop if stop.tzinfo else stop.replace(tzinfo=ISRAEL)).astimezone(timezone.utc)
                except (TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", str(it.get("title") or "")).strip()
                if not title or stop <= start:
                    continue
                desc = re.sub(r"\s+", " ", str(it.get("description") or "")).strip()
                flag = any(v is True for k, v in it.items() if "live" in k.lower())
                live = flag or bool(re.search(r"\bלייב\b|בשידור חי|\(ש\.ח\)|\blive\b", title, re.I))
                evs[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                              "desc": short_desc(desc) if desc and desc != title else ""}
        if evs:
            out[part] = [evs[k] for k in sorted(evs)]
        print(f"  yes {name}: {len(evs)} programmes, {sum(e['live'] for e in evs.values())} live")
    return out


# Turkey (29 Oct 2026, late): Turkcell TV+ guide (as iptv-org's tvplus.com.tr reader) - has DESCRIPTIONS, unlike
# epgshare's TR1 file. A guest login gives a cookie, then one request per channel and day. Not beIN (Digiturk only).
TVPLUS_API = "https://izmaottvsc14.tvplus.com.tr:33207/EPG/JSON/"
TVPLUS_CHANNELS = {"11": "SSport", "170": "SSport2", "3": "ASpor", "31": "TRTSpor",
                   "77": "Eurosport1", "106": "Eurosport2"}               # Eurosport added 30 Oct 2026   # TV+ id -> TR1 group id part


# Digiturk (beIN Turkey's own platform, 30 Oct 2026, as iptv-org's digiturk.com.tr reader): one HTML page per day
# with every channel; titles and durations only. Fills beIN SPORTS 5 / MAX 1 / MAX 2 when TR1 has nothing.
DIGITURK_PAGE = "https://www.digiturk.com.tr/Ajax/GetTvGuideFromDigiturk?Day={day:%m}%2F{day:%d}%2F{day:%Y}+00%3A00%3A00"
DIGITURK_CHANNELS = {"506": "beINSPORTS5", "507": "beINSPORTSMAX1", "508": "beINSPORTSMAX2"}


def fetch_digiturk(days, debug=False):
    """{TR id part: [{start, stop, title, sub, live, desc}]} from Digiturk's guide page."""
    hdrs = {"User-Agent": HEADERS["User-Agent"], "X-Requested-With": "XMLHttpRequest", "Accept-Language": "tr-TR"}
    ist = ZoneInfo("Europe/Istanbul")
    rows = {p: {} for p in DIGITURK_CHANNELS.values()}
    for day in days:
        page = get_text(DIGITURK_PAGE.format(day=day), {}, headers=hdrs, retries=2, quiet=True) or ""
        for block in re.split(r'<div[^>]*class="[^"]*channelDetail', page)[1:]:
            t = re.search(r'class="[^"]*tvGuideResult-box-wholeDates-title[^"]*"[^>]*onclick="[^"]*?\s(\d+)\)[^"]*"[^>]*>(.*?)</',
                          block, re.S)
            if not t or t.group(1) not in DIGITURK_CHANNELS:
                continue
            hm = re.search(r'tvGuideResult-box-wholeDates-time-hour[^>]*>\s*(\d{1,2}):(\d{2})', block)
            mins = re.search(r'tvGuideResult-box-wholeDates-time-totalMinute[^>]*>\D*(\d+)', block)
            if not hm or not mins:
                continue
            title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t.group(2)))).strip()
            start = datetime(day.year, day.month, day.day, int(hm.group(1)), int(hm.group(2)), tzinfo=ist)
            start = start.astimezone(timezone.utc)
            live = bool(re.search(r"(?i)\bcanl[ıi]\b", title))
            title = re.sub(r"(?i)\s*[-(]?\s*\bcanl[ıi]\b\s*\)?\s*$|^\s*canl[ıi]\s*[:\-]\s*", "", title).strip() or title
            if title:
                rows[DIGITURK_CHANNELS[t.group(1)]][start] = {"start": start, "stop": start + timedelta(minutes=int(mins.group(1))),
                                                             "title": title, "sub": "", "live": live, "desc": ""}
    out = {p: [r[k] for k in sorted(r)] for p, r in rows.items() if r}
    for p in DIGITURK_CHANNELS.values():
        print(f"  Digiturk {p}: {len(out.get(p, []))} programmes")
    return out


def fetch_tvplus(days, debug=False):
    """{TR id part: [{start, stop, title, sub, live, desc}]} from Turkcell TV+."""
    import http.cookiejar
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar),
                                         urllib.request.HTTPSHandler(context=CTX))
    hdrs = {"User-Agent": HEADERS["User-Agent"], "Content-Type": "application/json", "Accept": "application/json"}

    def post(path, body):
        req = urllib.request.Request(TVPLUS_API + path, data=json.dumps(body).encode(), headers=hdrs, method="POST")
        try:
            with opener.open(req, timeout=FETCH_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8", "replace") or "{}")
        except Exception as exc:                        # noqa: BLE001 - any failure: report and carry on
            if debug:
                print(f"    TV+ {path}: {exc}", file=sys.stderr)
            return None

    if post("Authenticate", {"terminaltype": "webtv", "terminalvendor": HEADERS["User-Agent"][13:],
                             "osversion": "Win32", "userType": "3", "utcEnable": "1",
                             "timezone": "Europe/Istanbul"}) is None:
        print("  WARNING: TV+ (Turkey) login failed - S Sport / A Spor / TRT Spor stay on epgshare", file=sys.stderr)
        return {}
    out = {}
    for cid, part in TVPLUS_CHANNELS.items():
        rows = {}
        for day in days:
            a = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
            data = post("PlayBillList", {"type": "2", "channelid": cid, "begintime": a.strftime("%Y%m%d%H%M%S"),
                                         "endtime": (a + timedelta(days=1)).strftime("%Y%m%d%H%M%S"),
                                         "isFillProgram": 1})
            for it in (data or {}).get("playbilllist") or []:
                try:
                    times = []
                    for k in ("starttime", "endtime"):
                        m = re.match(r"(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)\s*(?:UTC)?\s*([+-]\d\d):?(\d\d)?",
                                     str(it.get(k)))
                        off = timedelta(hours=int(m.group(3)), minutes=int(m.group(4) or 0) * (1 if m.group(3)[0] == "+" else -1))
                        t = datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}").replace(tzinfo=timezone(off))
                        times.append(t.astimezone(timezone.utc))
                except (AttributeError, TypeError, ValueError):
                    continue
                start, stop = times
                title = re.sub(r"\s+", " ", str(it.get("name") or "")).strip()
                if not title or stop <= start:
                    continue
                desc = re.sub(r"\s+", " ", str(it.get("introduce") or "")).strip()
                flag = any(str(v) in ("1", "true", "True") for k, v in it.items() if "live" in k.lower())
                live = flag or bool(re.search(r"(?i)\bcanl[ıi]\b", title))
                title = re.sub(r"(?i)\s*[-(]?\s*\bcanl[ıi]\b\s*\)?\s*$|^\s*canl[ıi]\s*[:\-]\s*", "", title).strip() or title
                rows[start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live,
                               "desc": short_desc(desc) if desc and desc != title else ""}
        evs = [rows[k] for k in sorted(rows)]
        if evs:
            out[part] = evs
        print(f"  TV+ {part}: {len(evs)} programmes, {sum(e['live'] for e in evs)} live, "
              f"{sum(bool(e['desc']) for e in evs)} with a description")
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
# Cyprus: Cyta's own TV guide (from cyta_epg.py)
# --------------------------------------------------------------------------
NICOSIA = ZoneInfo("Asia/Nicosia")
CYTA_API = "https://epg.cyta.com.cy/api/mediacatalog/"
CYTA_HEADERS = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json",
                "Referer": "https://epg.cyta.com.cy/tv-guide/en", "Connection": "close"}
CYTA_LIVE = r"\b(live|ζωντανά|ζωντανα|ζωντανή|ζωντανη)\b|\(\s*[ΖZ]\s*\)"


def cyta_json(path, params):
    """Cyta's JSON; when Python's TLS is refused, the system curl is tried (as cyta_epg.py did)."""
    url = CYTA_API + path + "?" + urllib.parse.urlencode(params)
    time.sleep(0.3)
    data = fetch(url, headers=CYTA_HEADERS, parse="json", retries=3, quiet=True)
    if data is None and urllib.parse.urlsplit(url).hostname not in HOST_GIVEN_UP:
        import shutil
        import subprocess
        if shutil.which("curl"):
            cmd = ["curl", "-sS", "--fail", "--max-time", "30", url]
            for k, v in CYTA_HEADERS.items():
                cmd += ["-H", f"{k}: {v}"]
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                data = json.loads(out.stdout) if out.returncode == 0 else None
            except (subprocess.SubprocessError, ValueError, OSError):
                data = None
    return data


def cyta_part(name):
    """'Cytavision Sports 1 HD' / 'Cyta Vision Sports 1' -> 'CytavisionSports1' (steady ids)."""
    n = re.sub(r"\s*\b(hd|uhd|4k)\b", "", name, flags=re.I)
    n = re.sub(r"(?i)^cyta\s*vision", "Cytavision", n.strip())
    n = re.sub(r"(?i)\bsport\b", "Sports", n)
    words = [w if not w.isupper() or len(w) <= 3 else w.capitalize() for w in n.split()]
    return re.sub(r"[^A-Za-z0-9]+", "", "".join(w[:1].upper() + w[1:] for w in words)) or "Channel"


def cyta_details(pid):
    """(description, genre) for one programme from fetchEpgDetails, or ('', '')."""
    data = cyta_json("fetchEpgDetails", {"language": 0, "id": pid})
    d = data.get("playbillDetail") if isinstance(data, dict) else None
    d = d if isinstance(d, dict) else (data if isinstance(data, dict) else {})
    desc = pick_desc(d, "introduce", "description", "longDescription", "shortDescription", "synopsis")
    genres = [g.get("genreName") for g in d.get("genres") or [] if isinstance(g, dict) and g.get("genreName")]
    return desc, (genres[0] if genres else "")


def fetch_cyprus(days, keywords, details=True, debug=False):
    """{channel name: [{start, stop, title, sub, live, desc}]} from Cyta's guide."""
    data = cyta_json("fetchChannels", {"language": 0})
    chans = (data.get("channels") if isinstance(data, dict) else None) or []
    kws = [k.strip().lower().split() for k in keywords.split(",") if k.strip()]
    names = {}
    for c in chans:
        if not isinstance(c, dict):
            continue
        cid = c.get("id") or c.get("channelId")
        name = re.sub(r"\s+", " ", str(c.get("name") or c.get("title") or "")).strip()
        name = re.sub(r"\s*\b(HD|UHD)\b", "", name).strip() or name      # 'Cytavision Sports 1 HD' -> '... 1'
        if "real time" in name.lower() or "realtime" in name.lower():
            continue                      # 19 Nov 2026 (user): never the Cytavision Real Time channels - we don't have them
        if cid is not None and name and any(all(w in name.lower() for w in k) for k in kws):
            names[str(cid)] = name
    if debug:
        print(f"  Cyta: {len(chans)} channels, {len(names)} matching: {sorted(names.values())}")
    if not names:
        if not chans:
            print("  WARNING: Cyta's channel list could not be read", file=sys.stderr)
        return {}
    per = {cid: {} for cid in names}
    ids = sorted(names)
    for day in days:
        frm = datetime(day.year, day.month, day.day, tzinfo=NICOSIA)
        to = frm + timedelta(days=1)
        for i in range(0, len(ids), 8):                  # 8 channels per request, as cyta_epg.py
            batch = ids[i:i + 8]
            got = cyta_json("fetchEpg", {"startTimeEpoch": int(frm.timestamp() * 1000),
                                         "endTimeEpoch": int(to.timestamp() * 1000),
                                         "language": 0, "channelIds": ",".join(batch)}) or {}
            n = 0
            for ch in (got.get("channelEpgs") if isinstance(got, dict) else None) or []:
                ch_id = str(ch.get("channelId") or ch.get("id") or "")
                for pr in ch.get("epgPlayables") or []:
                    cid = str(pr.get("channelId") or ch_id or batch[0])
                    if cid not in per:
                        continue
                    try:
                        start, stop = tataplay_time(pr.get("startTime") or pr.get("start")), \
                            tataplay_time(pr.get("endTime") or pr.get("end"))
                    except (TypeError, ValueError):
                        continue
                    title = re.sub(r"\s+", " ", str(pr.get("name") or pr.get("title") or "")).strip()
                    if not title or stop <= start:
                        continue
                    live = bool(re.search(CYTA_LIVE, title, re.I))
                    title = re.sub(r"^\s*(live|ζωντανά|ζωντανα)\b\s*[:\-]?\s*|\s*[(\-:]?\s*\(?\b(live|ζωντανά|ζωντανα|ζωντανή|ζωντανη)\b\)?\s*$"
                                   r"|\s*\(\s*[ΖZ]\s*\)", "", title, flags=re.I).strip() or title
                    genre = str(pr.get("programEvent") or pr.get("category") or pr.get("genre") or "").strip()
                    per[cid][start] = {"start": start, "stop": stop, "title": title,
                                       "sub": genre if genre.lower() != title.lower() else "", "live": live,
                                       "desc": pick_desc(pr, "description", "shortDescription", "synopsis"),
                                       "_id": pr.get("id")}
                    n += 1
            if debug:
                print(f"  Cyta {day} channels {i + 1}-{i + len(batch)}: {n} programmes")
    if details:
        todo = sorted({str(ev["_id"]) for evs in per.values() for ev in evs.values()
                       if ev.get("_id") and not ev["desc"]})
        if todo:
            from concurrent.futures import ThreadPoolExecutor
            print(f"  Cyta: fetching descriptions for {len(todo)} programme(s) ...")
            with ThreadPoolExecutor(max_workers=2) as pool:
                found = dict(zip(todo, pool.map(cyta_details, todo)))
            for evs in per.values():
                for ev in evs.values():
                    desc, genre = found.get(str(ev.get("_id")), ("", ""))
                    ev["desc"] = ev["desc"] or desc
                    if genre and not ev["sub"] and genre.lower() != ev["title"].lower():
                        ev["sub"] = genre
            print(f"  Cyta: {sum(1 for d, _ in found.values() if d)} of {len(todo)} have a description")
    out = {}
    for cid, evs in per.items():
        name = names[cid]
        for ev in evs.values():
            ev.pop("_id", None)
        if evs and (name not in out or len(evs) > len(out[name])):
            out[name] = [evs[k] for k in sorted(evs)]   # same name twice (e.g. HD copy): keep the fuller
    return out


# Cyta writes fixtures as "Shakhtar Donetsk - Sporting Lisbon 3/11/26" (the date is the match date, so it also shows a replay);
# 3 Nov 2026: shown as "Shakhtar Donetsk vs Sporting Lisbon 3/11/26". Only for a fixture: a trailing d/m/yy date, or a live
# block, and no digits / "Round", "Ep.", "Day" ... in the names (so "Jet Ski World Series 2025 - Round 3" stays as it is).
CY_FIXTURE = re.compile(r"^(?P<a>.+?) - (?P<b>.+?)(?P<tail>(?: \([^()]*\))?(?: \d{1,2}/\d{1,2}/\d{2,4})?)$")
CY_NOT_TEAMS = re.compile(r"(?i)\d|\b(round|day|ep\.?|episode|session|stage|heat|race|practice|qualifying|film|special|highlights|"
                          r"preview|review|show|week|time for ball)\b")


def cy_versus(title, live=False):
    m = CY_FIXTURE.match(title or "")
    if not m or CY_NOT_TEAMS.search(m.group("a") + " " + m.group("b")):
        return title
    if not (re.search(r"\d{1,2}/\d{1,2}/\d{2,4}$", m.group("tail")) or live):
        return title
    return f"{m.group('a')} vs {m.group('b')}{m.group('tail')}"


# Portuguese-style "Juventus x Napoli - Serie A" (Brazil, Portugal, and the AD Sports / Starzplay / Champions TV channels that
# copy it): shown as "Juventus vs Napoli - Serie A" (3 Nov 2026). Only these regions, and only a lone " x " between two words:
# MUTV's "Kobbie Mainoo x Academy" and Motorvision's "FIM X -- Trial ..." are not fixtures and are left alone.
X_VS_REGIONS = ("BR.", "PT.", "AE.", "ID.")
X_BETWEEN = re.compile(r"(?<=[^\s-]) [xX\u00d7] (?=[^\s-])")


def x_versus(title):
    if len(X_BETWEEN.findall(title or "")) != 1:
        return title
    return X_BETWEEN.sub(" vs ", title, count=1)


# "Team A - Team B" / "Team A x Team B" / "Team A X Team B" -> "Team A vs Team B" on EVERY channel of the Sport guide (5 Nov 2026,
# user request: "ideally applied everywhere", incl. the Portuguese-style "x", short replays and names with digits: "if it looks like a
# matchup between two teams, people or countries"). A title is a candidate when the WHOLE title is exactly two names with ONE separator
# (a dash " - " / en dash, or a lone " x " / " X " / " \u00d7 "), optionally after "Next match: ", with a trailing date or ", finale G5"
# style tail kept; no colon / slash / bar / existing v or vs; each name 1-5 words with a capital letter, no bracket, no word from
# MATCH_NOT_TEAMS (competitions, studio / magazine / highlights / round / ep. / stories / legends ...), no episode / round / year code
# (E8, MD4, R16, 2003, '26) and not starting or ending with of / the / and / a / in ... Then:
#   STRONG - the block is live, dated, or at least 75 minutes long: converted (digits in names are fine: "Philadelphia 76ers",
#            "Mainz 05", "TSG 1899 Hoffenheim");
#   WEAK   - a short undated, non-live block (a 15-45 minute replay / highlights): converted only when the SAME two names also
#            appear as a STRONG fixture somewhere in the guide this run (MATCH_PAIRS, filled by collect_match_pairs() before the
#            build), so "Feyenoord - Inter" (30 min) follows the 120-minute live one, while shows like "PL Stories - Fabricio
#            Coloccini", "Chloe x Halle" or "Strictly - It Takes Two" (no strong twin) keep their dash / x.
# cy_versus() and x_versus() above still run first for their regions.
MATCH_NOT_TEAMS = re.compile(
    r"(?i)\b(round|day|days|ep\.?|episode|episodes|session|stage|heat|race|practice|qualifying|film|special|speciale|highlights?|"
    r"preview|review|show|shows|week|studio|magazine|news|update|replay|classic|classics|history|documentary|interview|talk|report|"
    r"results?|league|liga|ligue|serie|cup|copa|coupe|championships?|bundesliga|premier|nba|nfl|nhl|mlb|formula|grand prix|sports?|"
    r"clubs|tonight|live|matchday|friendly|friendlies|tour|open|masters|world|series|games|zone|time|goals?|gol|top|best|moments|"
    r"inside|extra|pre|post|play-?offs?|final|finals|semi-?finals?|quarter-?finals?|group|play|fixtures|schedule|programme|program|"
    r"announcement|stories|story|legends?|unpacked|build-?up|pregled|vt|atp|wta|itf|challenger|tv|unplugged|meeting|sign up|"
    r"takes two|loco|garage|fan|fans|nascar|euronascar)\b")
MATCH_CODE = re.compile(r"(?i)^(?:E|EP|MD|MW|R|P|T|S|Q|FP|GR|GP|H|SF|QF|J|W|D)\d{1,3}$|^(?:19|20)\d\d$|^'\d\d$|^\d+(?:st|nd|rd|th)$")
MATCH_EDGE = re.compile(r"(?i)^(of|the|and|a|an|in|on|at|for|to|with|by)\s|\s(of|the|and|a|an|in|on|at|for|to|with|by)$")
MATCH_TAIL = r"(?: \(?\s*\d{1,2}[./]\d{1,2}[./]\d{2,4}\s*\)?)?(?:, [^,()]{1,24})?"
MATCH_SHAPE = re.compile(r"^(?P<pre>(?:Next match: )?)(?P<a>\S.*?) (?P<sep>[-\u2013xX\u00d7]) (?P<b>\S.*?)(?P<tail>" + MATCH_TAIL + r")$")
MATCH_CONNECTORS = {"de", "del", "della", "di", "da", "das", "do", "dos", "du", "des", "la", "las", "le", "les", "los", "el", "al", "van", "von", "der", "den", "bin", "ben", "ibn", "y", "e", "af", "av"}
MATCH_PAIRS = set()                       # (a, b) names of every STRONG fixture seen this run (see collect_match_pairs)


def _match_parts(title, live, minutes):
    """(pre, a, b, tail, strong) when `title` is a candidate matchup, else None"""
    t = (title or "").strip()
    pre = ""
    if t.startswith("Next match: "):
        pre, t = "Next match: ", t[len("Next match: "):]
    core = re.sub(MATCH_TAIL + "$", "", t)
    if not t or re.search(r"(?i)\bvs?\.?(?=\s)|[:|/]", core):
        return None
    m = MATCH_SHAPE.match(t)
    if not m or len(re.findall(r" [-\u2013xX\u00d7] ", t)) != 1:
        return None
    a, b, tail = m.group("a"), m.group("b"), m.group("tail")
    for name in (a, b):
        words = name.split()
        if not (1 <= len(words) <= 5) or MATCH_NOT_TEAMS.search(name) or MATCH_EDGE.search(name) or re.search(r"[()]", name):
            return None
        if any(MATCH_CODE.match(w) for w in words) or not any(ch.isupper() for ch in name):
            return None
        # a team / person / country is written with capitals: "Basketball rules - Aleksa Avramovic" is a show (6 Nov), while
        # "Alianza de Lima", "Bayer 04 Leverkusen", "Van Gerwen" keep their small connecting words
        if any(w[:1].islower() and w.lower() not in MATCH_CONNECTORS for w in words[1:]):
            return None
    dated = bool(re.search(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", tail))
    return pre, a, b, tail, bool(live or dated or minutes >= 75)


def _pair_key(a, b):
    return tuple(re.sub(r"\W+", " ", n).casefold().strip() for n in (a, b))


def match_versus(title, live=False, minutes=0):
    parts = _match_parts(title, live, minutes)
    if not parts:
        return title
    pre, a, b, tail, strong = parts
    if not strong and _pair_key(a, b) not in MATCH_PAIRS:
        return title
    return f"{pre}{a} vs {b}{tail}"


def collect_match_pairs(records):
    """fill MATCH_PAIRS with the names of every strong fixture in all records (before the guide is built)"""
    MATCH_PAIRS.clear()
    for rec in records:
        for ev in rec.get("events") or []:
            try:
                minutes = (ev["stop"] - ev["start"]).total_seconds() / 60
            except (KeyError, TypeError):
                continue
            parts = _match_parts(ev.get("title"), ev.get("live"), minutes)
            if parts and parts[4]:
                MATCH_PAIRS.add(_pair_key(parts[1], parts[2]))


# ALL CAPS -> normal case (Cyta writes most titles in capitals), from cyta_epg.py
KEEP_CAPS = set("""
UFC NBA NFL NHL MLB MLS WNBA NCAA UEFA FIFA FA EFL EPL WWE AEW ATP WTA PGA LPGA LIV DP
IPL ICC ODI GP MMA PFL BKFC DAZN ESPN BBC CNN BT TNT TV HD UHD PPV VAR USA UK UAE EU
FC SC AC AS CF CD FK SK BK AEK AEL APOEL PAOK OFI ENP AEP PAEEK GR PL MW GB ISO LIVE
""".split())
SMALL_WORDS = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "v", "vs"}
CAPS_WORD = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*")
ROMAN = re.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")


def fix_caps(text):
    """Words written entirely in capitals -> normal case; acronyms, roman numerals,
    single letters and words touching digits are left alone."""
    if not text:
        return text

    def repl(m):
        w = m.group(0)
        if w == "V" and m.start() > 0 and text[m.start() - 1] == " ":
            return "v"                                  # 'ARSENAL V CHELSEA' -> 'Arsenal v Chelsea'
        if len(w) < 2 or not w.isupper() or w in KEEP_CAPS or (len(w) <= 4 and ROMAN.match(w)):
            return w
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if before.isdigit() or after.isdigit():
            return w
        lead = text[:m.start()].rstrip()
        low = w.lower()
        if low in SMALL_WORDS and lead and lead[-1] not in "-\u2013\u2014:|/(\"'.!?":
            return low
        return low.capitalize()
    return CAPS_WORD.sub(repl, text)


# "and" written as a lone capital letter (8 Nov 2026, user: "Europa E Conference League Remix" -> "Europa & Conference League Remix"). fix_caps
# leaves single letters alone, so the Italian / Portuguese "E" and Spanish "Y" of an ALL CAPS title stayed capitals. Not touched after a
# label word ("Group E", "Pool B"), because there the letter is a name.
AND_LABEL_WORDS = {"group", "pool", "class", "series", "division", "zone", "category", "tier", "level", "type", "section", "part",
                   "grade", "vitamin", "plan", "option", "team", "squad", "league", "cup", "tour", "round", "heat", "court", "lane", "stage"}
AND_LETTER_RE = re.compile(r"([^\W\d_][\w'\u2019.-]*) ([EY]) (?=[^\W\d_a-z])")


def conj_and(text):
    """Italian / Portuguese "E" and Spanish "Y" (a lone capital between two words) -> "&"."""
    if not text or " E " not in text and " Y " not in text:
        return text
    return AND_LETTER_RE.sub(lambda m: m.group(0) if m.group(1).lower().strip(".-") in AND_LABEL_WORDS
                             else f"{m.group(1)} & ", text)


def it_and(text):
    """On the Italian channels a lower-case "e" between two capitalised words is "and" too: "Europa e Conference League" -> "Europa &"."""
    return re.sub(r"(?<=[^\W\d_]) e (?=[A-Z])", " & ", text) if text else text


# --------------------------------------------------------------------------
# Hong Kong: Now TV's public guide (nowplayer.now.com), sports channels
# --------------------------------------------------------------------------
NOW_GUIDE = "https://nowplayer.now.com/tvguide/epglist?{ids}&day={day}"
NOW_HEADERS = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json, text/javascript, */*",
               "X-Requested-With": "XMLHttpRequest", "Cookie": "LANG=en",
               "Referer": "https://nowplayer.now.com/tvguide?filterType=G07"}
# mewatch (Mediacorp, Singapore; added 29 Oct 2026) - for beIN SPORTS 4 and 5 SG, which beIN's own
# API doesn't list (only 1-3). JSON, several channels per request, with a "live" flag per programme.
MEWATCH_API = ("https://cdn.mewatch.sg/api/schedules?channels={ids}&date={day:%Y-%m-%d}&duration=24"
               "&ff=idp,ldp,rpt,cd&hour=0&intersect=true&lang=en&segments=all")
MEWATCH_CHANNELS = {"572425": "beINSPORTS4", "572409": "beINSPORTS5"}   # mewatch id -> SG.<id part>

STARHUB_API = "https://waf-starhub-metadata-api-p001.sh-ifs.com/v3.1/epg/"
STARHUB_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                   "Accept": "application/json, */*", "Referer": "https://www.starhubtvplus.com/"}
STARHUB_NAME_RE = re.compile(r"(?i)^\s*hub\s+(sports|premier)\s+(\d+)\b")   # "Hub Sports 5 HD" -> (S, 5)
# (30 Oct 2026: Hub Premier N too - epgshare's SG1 only has Premier 1-6; StarHub's own guide wins over SG1)
STARHUB_KNOWN = {      # from iptv-org's StarHub list (Oct 2026), used if the channel list fails
    1: "b5c3d45b-e2c9-462b-bcf1-06a149d68f25", 2: "347fa620-e966-423c-8d46-98469f0fc974",
    3: "4ff7b357-9338-41a3-b7be-ede530555279", 4: "753b50fe-262e-48da-9b5e-3fd9894ff531",
    5: "38df8124-1bcd-49b6-abb3-ee230a1f40d2", 6: "cc214bae-ddf2-4c17-84e2-7690fe4e65db",
    7: "679c2e9d-474d-4d9d-9f94-28e0a6905bc0"}
# StarHub's own live flag (31 Oct 2026, read from the diagnostic log): schedule_type is "original" for a FIRST airing and "rerun" for
# a repeat (100 / 748 in one run). A first airing of an EVENT (match, round, session, final, fight card) is live; first airings
# of magazine / highlights / series titles ("ATP Tour 2026", "Badminton Weekly 2026", "... HLs", "ASO Cycling Programming 2026") are not.
STARHUB_EVENT = re.compile(r"(?i)\b(vs?\.?|sf\s*\d?|qf\s*\d?|r(16|32|64|128)|finals?|semi-?finals?|quarter-?finals?|sessions?|prelims?|"
                           r"main card|fight night|day \d+|round \d+|qualifiers?|3rd place|play-?offs?|grand prix|practice|qualifying|race|"
                           r"leg \d|game \d)\b")
STARHUB_NOT_LIVE = re.compile(r"(?i)\b(hls?|highlights?|weekly|programming|unlimited|originals?|this week|the cut|racing on the edge|"
                              r"series|review|preview|magazine|best of|classic|legends|rewind|recap|show|extra)\b")
STARHUB_LIVE_TITLE = re.compile(r"(?i)^\s*(live\s*[:\-]|\(l\)|\[l\])\s*|\s*\((live|l)\)\s*$")

NOW_CHANNELS = {         # Now TV channel number -> (id part, name); same IDs as epgshare01's HK file
    "611": ("NowSports4K1", "Now Sports 4K 1"), "612": ("NowSports4K2", "Now Sports 4K 2"),
    "613": ("NowSports4K3", "Now Sports 4K 3"),
    "620": ("NowSportsPLTV", "Now Sports Premier League TV"),
    **{str(620 + n): (f"NowSportsPL{n}", f"Now Sports Premier League {n}") for n in range(1, 10)},
    "630": ("NowSportsPrime", "Now Sports Prime"),
    **{str(630 + n): (f"NowSports{n}", f"Now Sports {n}") for n in range(1, 8)},
    "638": ("beINSPORTS1", "beIN SPORTS 1 HK"), "639": ("beINSPORTS2", "beIN SPORTS 2 HK"),
    "643": ("beINSPORTS3", "beIN SPORTS 3 HK"), "644": ("beINSPORTS4", "beIN SPORTS 4 HK"),
    "645": ("beINSPORTS5", "beIN SPORTS 5 HK"), "646": ("beINSPORTS6", "beIN SPORTS 6 HK"),
    "640": ("MUTV", "MUTV"),            # (642 NBATV, 647, 668, 680 Now Sports Plus removed 4 Nov 2026 - user: not important)
    **{n: (f"NowSports{n}", f"Now Sports {n}") for n in ("641", "650", "651", "652")},
    "674": ("Cricbuzz", "Cricbuzz"), "679": ("PremierSports", "Premier Sports HK"),
    "683": ("NowGolf2", "Now Golf 2"), "684": ("NowGolf3", "Now Golf 3"),
}


def fetch_mewatch(days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for MEWATCH_CHANNELS (days are UTC days)."""
    found = {}
    utc_days = sorted({d for d in days} | {days[0] - timedelta(days=1)})
    for day in utc_days:
        data = get_json_url(MEWATCH_API.format(ids=",".join(MEWATCH_CHANNELS), day=day),
                            {"User-Agent": STARHUB_HEADERS["User-Agent"], "Accept": "application/json"})
        blocks = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        for block in blocks:
            for it in (block.get("schedules") or []) if isinstance(block, dict) else []:
                part = MEWATCH_CHANNELS.get(str(it.get("channelId") or block.get("channelId") or ""))
                info = it.get("item") or {}
                if not part or it.get("isGap"):
                    continue
                try:
                    start = datetime.fromisoformat(str(it["startDate"]).replace("Z", "+00:00"))
                    stop = datetime.fromisoformat(str(it["endDate"]).replace("Z", "+00:00"))
                except (KeyError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", str(info.get("title") or "")).strip()
                sub = re.sub(r"\s+", " ", str(info.get("episodeTitle") or "")).strip()
                if sub and title.endswith(f" - {sub}"):
                    title = title[: -len(sub) - 3].strip()
                if sub == title:
                    sub = ""
                if not title or stop <= start:
                    continue
                found.setdefault(part, {})[start] = {
                    "start": start, "stop": stop, "title": title, "sub": sub, "live": bool(it.get("live")),
                    "desc": re.sub(r"\s+", " ", str(info.get("description") or "")).strip()}
    out = {part: [evs[k] for k in sorted(evs)] for part, evs in found.items()}
    for part in MEWATCH_CHANNELS.values():
        evs = out.get(part, [])
        print(f"  mewatch SG.{part}: {len(evs)} programmes, {sum(e['live'] for e in evs)} live")
    return out


def fetch_starhub(days, debug=False):
    """{n: [{start, stop, title, sub, live, desc}]} for Hub Sports n from StarHub TV+."""
    chans = {}
    for page in range(1, 20):
        data = get_json_url(f"{STARHUB_API}channels?locale=en_US&locale_default=en_US&device=1"
                            f"&limit=50&page={page}", STARHUB_HEADERS, quiet=page > 1)
        res = (data or {}).get("resources") if isinstance(data, dict) else None
        for ch in res or []:
            m = STARHUB_NAME_RE.match(str(ch.get("title") or ""))
            if m and ch.get("id"):
                chans.setdefault((m.group(1)[0].upper(), int(m.group(2))), ch["id"])
        pg = (data or {}).get("page") if isinstance(data, dict) else None
        if not res or not isinstance(pg, dict) or page >= int(pg.get("total") or 0):
            break
    if not chans:
        print("  StarHub channel list not available - using the known Hub Sports ids")
        chans = {("S", n): sid for n, sid in STARHUB_KNOWN.items()}
    if debug:
        print(f"  StarHub channels: {sorted(chans)}")
    tz, out = ZoneInfo("Asia/Singapore"), {}
    sh_keys, sh_types, sh_sample = set(), {}, {}      # diagnostics (31 Oct 2026): what flags does StarHub send?
    for n, sid in sorted(chans.items()):
        evs = {}
        for day in days:
            a = int(datetime(day.year, day.month, day.day, tzinfo=tz).timestamp())
            for page in range(1, 10):
                data = get_json_url(f"{STARHUB_API}schedules?locale=en_US&locale_default=en_US&device=1"
                                    f"&in_channel_id={sid}&gt_end={a}&lt_start={a + 86400}&limit=100&page={page}",
                                    STARHUB_HEADERS, quiet=True)
                res = (data or {}).get("resources") if isinstance(data, dict) else None
                for it in res or []:
                    try:
                        start = datetime.fromtimestamp(int(it["start"]), timezone.utc)
                        stop = datetime.fromtimestamp(int(it["end"]), timezone.utc)
                    except (KeyError, TypeError, ValueError):
                        continue
                    series = re.sub(r"\s+", " ", str(it.get("serie_title") or "")).strip()
                    ep = re.sub(r"\s+", " ", str(it.get("title") or "")).strip()
                    title, sub = (series, ep if ep != series else "") if series else (ep, "")
                    if not title or stop <= start:
                        continue
                    sh_keys.update(it)
                    st = str(it.get("schedule_type"))
                    sh_types[st] = sh_types.get(st, 0) + 1
                    for tag in ("UFC", "ATP", "Premier", ""):               # one sample item of each kind
                        if tag in title + " " + ep and tag not in sh_sample:
                            sh_sample[tag] = {k: (str(v)[:50] + "…" if len(str(v)) > 50 else v)
                                              for k, v in it.items() if k not in ("description", "short_description")}
                    stype = str(it.get("schedule_type") or "").lower()
                    ev_text = f"{title} {sub}"
                    live = stype == "live" or (stype == "original" and bool(STARHUB_EVENT.search(ev_text))
                                               and not STARHUB_NOT_LIVE.search(ev_text))
                    if STARHUB_LIVE_TITLE.search(title):
                        live, title = True, STARHUB_LIVE_TITLE.sub("", title).strip() or title
                    evs[start] = {"start": start, "stop": stop, "title": title, "sub": sub, "live": live,
                                  "desc": re.sub(r"\s+", " ", str(it.get("description") or
                                                                 it.get("short_description") or "")).strip()}
                pg = (data or {}).get("page") if isinstance(data, dict) else None
                if not res or not isinstance(pg, dict) or page >= int(pg.get("total") or 0):
                    break
        if evs:
            out[n] = [evs[k] for k in sorted(evs)]
        if debug:
            print(f"  StarHub Hub Sports {n}: {len(evs)} programmes, {sum(e['live'] for e in evs.values())} live")
    if sh_keys:                                       # always printed - read this to find StarHub's live flag
        print(f"  StarHub schedule fields: {sorted(sh_keys)}")
        print(f"  StarHub schedule_type values: {sh_types}")
    return out


def fetch_now(days, ids, debug=False):
    """{channel number: [{start, stop, title, sub, live, desc}]} from Now TV, days 1..len(days)."""
    wanted = [c.strip() for c in ids.split(",") if c.strip()]
    per = {c: {} for c in wanted}

    def take(cid, items):
        n = 0
        for it in items if isinstance(items, list) else []:
            if not isinstance(it, dict):
                continue
            try:
                start = datetime.fromtimestamp(int(it["start"]) / 1000, timezone.utc)
                stop = datetime.fromtimestamp(int(it["end"]) / 1000, timezone.utc)
            except (KeyError, TypeError, ValueError):
                continue
            title = re.sub(r"\s+", " ", str(it.get("name") or "")).strip()
            if not title or stop <= start:
                continue
            # Now TV marks live matches "[Live]" (and "[Live Chat]"), e.g.
            # "Premier League 26/27 -Nottingham Forest vs Arsenal [Live Chat][Live]"
            live = bool(re.search(r"\[\s*live\s*\]|^\s*live\s*[:\-]|[(\-:]\s*\(?live\)?\s*$|直播", title, re.I))
            title = re.sub(r"\s*\[\s*live(\s+chat)?\s*\]|^\s*live\s*[:\-]\s*|\s*[(\-:]\s*\(?live\)?\s*$",
                           "", title, flags=re.I).strip() or title
            title = re.sub(r"\s+-(?=\S)", " - ", title)   # "26/27 -Nottingham" -> "26/27 - Nottingham"
            per[cid][start] = {"start": start, "stop": stop, "title": title, "sub": "", "live": live, "desc": ""}
            n += 1
        return n

    for d in range(1, len(days) + 1):
        q = "&".join("channelIdList%5B%5D=" + c for c in wanted)
        data = get_json_url(NOW_GUIDE.format(ids=q, day=d), NOW_HEADERS)
        if isinstance(data, list) and len(data) == len(wanted):    # one list per channel, in order
            got = sum(take(c, lst) for c, lst in zip(wanted, data))
            how = "one request"
        else:                                                    # one channel at a time instead
            got = 0
            for c in wanted:
                one = get_json_url(NOW_GUIDE.format(ids="channelIdList%5B%5D=" + c, day=d), NOW_HEADERS,
                                   quiet=True)
                got += take(c, one[0] if isinstance(one, list) and one else [])
                time.sleep(0.3)
            how = "channel by channel"
        if debug:
            print(f"  Now TV day {d}: {got} programmes ({how})")
    return {c: [evs[k] for k in sorted(evs)] for c, evs in per.items() if evs}


# --------------------------------------------------------------------------
# UK / Ireland: Sky's public TV guide (behind sky.com's TV guide; no login or key)
# --------------------------------------------------------------------------
SKY_HAWK = "https://awk.epgsky.com/hawk/linear/schedule/{date}/{sids}"
SKY_ATLANTIS = "https://atlantis.epgsky.com/as/schedule/{date}/{sid}"
SKY_HEADERS = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json", "X-SkyOTT-Territory": "GB"}
SKY_UHD_HEADERS = {**SKY_HEADERS, "X-SkyOTT-Proposition": "SKYQ", "X-SkyOTT-Provider": "SKY"}
SKY_CHANNELS = {   # our ID -> (name, [Sky service ids, best first], 4K?); epgshare01's UK/IE files are the backup
    "UK.SkySportsMainEvent": ("Sky Sports Main Event", ["4002", "1701", "4005"], False),
    "UK.SkySportsPremierLeague": ("Sky Sports Premier League", ["4010", "1096", "4011"], False),
    "UK.SkySportsFootball": ("Sky Sports Football", ["3939", "3843", "3942"], False),
    "UK.SkySportsCricket": ("Sky Sports Cricket", ["4081", "1702", "4085"], False),
    "UK.SkySportsGolf": ("Sky Sports Golf", ["4026", "1704", "4027"], False),
    "UK.SkySportsF1": ("Sky Sports F1", ["3835", "3836", "4202"], False),
    "UK.SkySportsAction": ("Sky Sports Action", ["4022", "1703", "4024"], False),
    "UK.SkySportsMix": ("Sky Sports Mix", ["4090", "4092"], False),
    "UK.SkySportsNews": ("Sky Sports News", ["4049", "1340", "4036"], False),
    "UK.SkySportsRacing": ("Sky Sports Racing", ["4032", "4038"], False),
    "UK.SkySportsTennis": ("Sky Sports Tennis", ["1705", "1284"], False),
    "UK.SkySportsPlus": ("Sky Sports+", ["3940", "3858", "3945"], False),
    "UK.SkySportsBoxOffice": ("Sky Sports Box Office", ["1035"], False),
    "UK.SkySportsMainEvent4K": ("Sky Sports Main Event 4K", ["7201", "7211"], True),
    "UK.SkySportsF14K": ("Sky Sports F1 4K", ["7202", "7212"], True),
    "UK.TNTSports1": ("TNT Sports 1", ["1120", "3625", "1125"], False),
    "UK.TNTSports2": ("TNT Sports 2", ["3627", "3628"], False),
    "UK.TNTSports3": ("TNT Sports 3", ["3629", "3630"], False),
    "UK.TNTSports4": ("TNT Sports 4", ["4040", "4041"], False),
    "UK.TNTSports5": ("TNT Sports 5", ["1242"], False),
    "UK.TNTSports6": ("TNT Sports 6", ["1239", "5382"], False),
    "UK.TNTSports7": ("TNT Sports 7", ["1240", "5383"], False),
    "UK.TNTSports8": ("TNT Sports 8", ["1241", "5384"], False),
    "UK.TNTSports9": ("TNT Sports 9", ["1237", "5385"], False),
    "UK.TNTSports10": ("TNT Sports 10", ["1243", "5386"], False),
    "UK.TNTSportsBoxOffice": ("TNT Sports Box Office", ["1210", "6014"], False),
    "UK.TNTSportsBoxOffice2": ("TNT Sports Box Office 2", ["1099", "1218"], False),
    "UK.TNTSportsUltimate": ("TNT Sports Ultimate", ["1336", "1337"], True),
    "IE.PremierSports1": ("Premier Sports 1", ["1192", "1289"], False),
    "IE.PremierSports2": ("Premier Sports 2", ["1193", "1290"], False),
    # UK feeds (29 Oct 2026): different from the Irish ones (only the Irish feed has the Premier League).
    # Same two Sky services per channel; SKY_SPLIT below gives the Irish ID the one with Premier League
    # matches and the UK ID the other.
    "UK.PremierSports1": ("Premier Sports 1 UK", ["1192", "1289"], False),
    "UK.PremierSports2": ("Premier Sports 2 UK", ["1193", "1290"], False),
    "IE.RTEOne": ("RTÉ One", ["2816"], False),
    "IE.RTE2": ("RTÉ2", ["1270"], False),
    "IE.VirginMediaOne": ("Virgin Media One", ["3881"], False),
    "IE.VirginMediaTwo": ("Virgin Media Two", ["1046"], False),
    "IE.VirginMediaThree": ("Virgin Media Three", ["2817"], False),
    "IE.VirginMediaFour": ("Virgin Media Four", ["1316"], False),
    # General UK channels (added 29 Oct 2026) - only their live sport gets LIVE (see GENERAL_CHANNELS).
    # Sky service ids from iptv-org's sky.com channel list (London HD feeds, a second feed as backup).
    "UK.BBCOne": ("BBC One", ["3000", "3008"], False),      # BBC One London HD, South East HD
    "UK.BBCTwo": ("BBC Two", ["2075"], False),              # BBC Two HD
    "UK.ITV1": ("ITV1", ["6504", "1043"], False),           # ITV1 London HD (two Sky feeds)
    "UK.ITV4": ("ITV4", ["6534"], False),                   # ITV4 HD
    "UK.Channel4": ("Channel 4", ["4075", "1202"], False),  # Channel 4 HD (UK, two Sky feeds)
    "UK.Channel5": ("Channel 5", ["4058"], False),          # 5 HD
    # Club/racing channels (added 29 Oct 2026; sids from iptv-org's sky.com list)
    "UK.RacingTV": ("Racing TV", ["5272"], False),          # Racing TV HD
    "UK.MUTV": ("MUTV", ["1003"], False),                   # MUTV HD
    "UK.LFCTV": ("LFCTV", ["3845"], False),                 # LFCTV HD
    # Sky Cinema (UK.SkyCinema* - Action, Drama, Family, Greats, Premiere, Sci-fi & Horror, Thriller): MOVED to GENERAL_epg.py on
    # 14 Nov 2026 (user: all Sky Cinema channels in the General guide). Same ids, so nothing changes in PlaylistLabs.
}
SKY_CINEMA = "UK.SkyCinema"      # films: never tagged live (titles like "Live Free or Die Hard" / "Live and Let Die" must stay as they are)
SKY_LIVE = re.compile(r"^\s*live\b|\(\s*live\s*\)|\blive\s*$", re.I)
# Sky Sports UHD 1 / UHD 2 (added 28 Oct 2026): part-time 4K channels showing selected live events
# (e.g. "Live SPFL: Hearts v Rangers"), "This is Ultra HD" / "UHD Downtime" in between. Sky service
# ids found 28 Oct 2026 by probing Sky's 4K address (atlantis): 7221 = UHD 1, 7222 = UHD 2 (7223 also
# exists - probably UHD 3; 7211/7212 = Main Event / F1 4K). Every programme except the filler is LIVE.
SKY_UHD_EVENT = {"UK.SkySportsUHD1": ("Sky Sports UHD 1", "7221"), "UK.SkySportsUHD2": ("Sky Sports UHD 2", "7222")}
UHD_FILLER = re.compile(r"(?i)^\s*(this is ultra hd|ultra hd|uhd downtime|sky sports (uhd|ultra hd)( \d)?)\b[\s.!]*$")


SKY_SPLIT = {"UK.PremierSports1": "IE.PremierSports1", "UK.PremierSports2": "IE.PremierSports2"}   # UK id -> IE id


def fetch_sky(days, debug=False):
    """{our id: [events]} from Sky's guide for the given days (UK dates)."""
    per_sid = {}
    for cid, (name, sid) in SKY_UHD_EVENT.items():      # Sky Sports UHD 1/2 (4K address)
        SKY_CHANNELS[cid] = (name, [sid], True)
    hd = [sid for _, sids, uhd in SKY_CHANNELS.values() if not uhd for sid in sids]
    uhd = [sid for _, sids, is_uhd in SKY_CHANNELS.values() if is_uhd for sid in sids]
    first = datetime(days[0].year, days[0].month, days[0].day, tzinfo=LONDON).astimezone(timezone.utc)
    last = days[-1] + timedelta(days=1)
    end = datetime(last.year, last.month, last.day, tzinfo=LONDON).astimezone(timezone.utc)
    cinema = {sid for cid, (_n, sids, _u) in SKY_CHANNELS.items() if cid.startswith(SKY_CINEMA) for sid in sids}

    def take(data):
        for sched in (data or {}).get("schedule") or [] if isinstance(data, dict) else []:
            if not isinstance(sched, dict):
                continue
            sid = str(sched.get("sid"))
            for ev in sched.get("events") or []:
                try:
                    start = datetime.fromtimestamp(int(ev["st"]), timezone.utc)
                    stop = start + timedelta(seconds=int(ev["d"]))
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", str(ev.get("t") or "")).strip()
                if not title or stop <= first or start >= end:
                    continue
                film = sid in cinema                                  # Sky Cinema: titles and flags left alone
                live = bool(SKY_LIVE.search(title)) and not film
                if live:   # "Live PL: Nott'm Forest v Arsenal" -> "PL: Nott'm Forest v Arsenal"
                    title = re.sub(r"^\s*live\b\s*[:\-]?\s*|\s*\(\s*live\s*\)|\s*[-:]?\s*\blive\s*$", "",
                                   title, flags=re.I).strip() or title
                m = re.match(r"^([^:]{2,12}):\s*(.+)$", title)    # "PL: Chelsea v Man United" ->
                if m and not film and m.group(1).strip().upper() in SKY_COMP_NAMES:   # "Premier League: Chelsea v Man United"
                    title = f"{SKY_COMP_NAMES[m.group(1).strip().upper()]}: {m.group(2).strip()}"
                synopsis = re.sub(r"\s+", " ", str(ev.get("sy") or "")).strip()
                synopsis = re.sub(r"^live\s*[.:!-]\s*", "", synopsis, flags=re.I)   # Sky's own "LIVE. ..."
                m = re.match(r"(.{10,110}?[.!?])(\s|$)", synopsis)
                sub = m.group(1) if m else ""     # "Bayern Munich v Arsenal (Kick-off 8.00pm)."
                rest = synopsis[len(sub):].strip() if sub else synopsis   # the summary after the sub-title
                if sub and not rest:                     # one sentence only: description, not also a sub-title
                    sub, rest = "", synopsis
                per_sid.setdefault(sid, {})[start] = {
                    "start": start, "stop": stop, "title": title, "sub": sub if sub != title else "",
                    "live": live, "desc": short_desc(rest) if rest not in (title, sub) else ""}
                if film:
                    per_sid[sid][start]["never_live"] = True

    dates = sorted({(datetime.combine(d, datetime.min.time(), LONDON).astimezone(timezone.utc) + timedelta(hours=h))
                    .strftime("%Y%m%d") for d in days for h in (0, 23)})
    for ymd in dates:
        for i in range(0, len(hd), 20):                 # Sky answers up to 20 channels at once
            take(get_json_url(SKY_HAWK.format(date=ymd, sids=",".join(hd[i:i + 20])), SKY_HEADERS))
        for sid in uhd:                                 # 4K channels: Sky's other address
            take(get_json_url(SKY_ATLANTIS.format(date=ymd, sid=sid), SKY_UHD_HEADERS, quiet=True))
    out = {}
    chosen = {}
    for uk, ie in SKY_SPLIT.items():                    # Premier Sports: Irish feed = the one with Premier League
        sids = [x for x in SKY_CHANNELS[ie][1] if per_sid.get(x)]
        if len(sids) < 2:
            continue                                    # only one feed answered: leave it to the IE id
        pl = lambda x: sum("premier league" in e["title"].lower() for e in per_sid[x].values())
        if max(pl(x) for x in sids):
            irish = max(sids, key=pl)
        else:                                           # no Premier League on either this run: the 29 Oct run showed
            irish = SKY_CHANNELS[ie][1][0]              # the first service is the Irish one (1192 for Premier Sports 1)
            if irish not in sids:
                continue
        chosen[ie], chosen[uk] = irish, next(x for x in sids if x != irish)
        print(f"  Sky: {SKY_CHANNELS[ie][0]} Irish feed = service {irish} ({pl(irish)} Premier League), "
              f"UK feed = service {chosen[uk]} ({pl(chosen[uk])})")
    for cid, (name, sids, _) in SKY_CHANNELS.items():
        if cid in SKY_SPLIT and cid not in chosen:
            continue                                    # UK feed not identified: no UK listing this run
        best = chosen.get(cid) or max(sids, key=lambda x: len(per_sid.get(x) or {}))
        evs = per_sid.get(best) or {}
        if debug:
            print(f"    {name}: {len(evs)} programmes from Sky service {best}")
        if evs:
            out[cid] = [evs[k] for k in sorted(evs)]
            if cid in SKY_UHD_EVENT:
                out[cid] = uhd_next_event(out[cid])
    return out


# Sky title prefixes -> competition names (UHD channels' secondary titles). Unknown prefixes are shown as given.
SKY_COMP_NAMES = {"PL": "Premier League", "EPL": "Premier League", "EFL CUP": "Carabao Cup", "EFL": "Football League",
                  "SPFL": "Scottish Premiership", "SPFL CUP": "Premier Sports Cup", "WSL": "Women's Super League",
                  "F1": "Formula 1", "PREM": "Gallagher Premiership", "NFL": "NFL", "NBA": "NBA", "NHL": "NHL",
                  "MLB": "MLB", "IPL": "Indian Premier League", "WPL": "Women's Premier League",
                  "SNF": "Premier League", "MNF": "Premier League",
                  "UCL": "Champions League", "UEFA CHAMPIONS LEAGUE": "Champions League", "CHAMPIONS LEAGUE": "Champions League",
                  "UEL": "Europa League", "UEFA EUROPA LEAGUE": "Europa League", "EUROPA LEAGUE": "Europa League",
                  "UECL": "Conference League", "UEFA CONFERENCE LEAGUE": "Conference League",
                  "UEFA EUROPA CONFERENCE LEAGUE": "Conference League", "EUROPA CONFERENCE LEAGUE": "Conference League",
                  "CONFERENCE LEAGUE": "Conference League", "UEFA CONF LEAGUE": "Conference League",
                  "CONF LEAGUE": "Conference League"}   # (SNF/MNF = Sky's Saturday/Monday Night Football)
SPORT_WORD_END = re.compile(r"^(.{3,}?)\s+(golf|tennis|cricket|darts|snooker|rugby|boxing|racing|athletics|"
                            r"netball|football|motorsport)$", re.I)


def uhd_comp(title):
    """(competition, event) from a Sky title (without "Live"):
    "PL: Chelsea v Man United" -> ("Premier League", "Chelsea v Man United");
    "LPGA Tour Golf" -> ("LPGA Tour", "LPGA Tour Golf"); "The Open" / "Wimbledon" -> (title, title)."""
    m = re.match(r"^([^:]{2,40}):\s*(.+)$", title)
    if m:
        abbr = m.group(1).strip()
        return SKY_COMP_NAMES.get(abbr.upper(), abbr), m.group(2).strip()
    m = SPORT_WORD_END.match(title)
    if m:
        return m.group(1).strip(), title
    if re.search(r"\S\s+vs?\.?\s+\S", title):          # a bare match - competition unknown
        return "", title
    return title, title


def uhd_next_event(evs):
    """Sky Sports UHD 1/2: mark the real events live ("uhd_live") and turn the filler before each
    one into a "Next Event" block, like the football guide's "Next Match":
      title  Hearts v Rangers (Wed 28th, 19:00)      sub  ⏭ Next Event: SPFL
      desc   Next Event: Hearts v Rangers. Heart of Midlothian v Rangers. Kick-off: Wed 28th, 19:00.
    Filler after the last known event stays "This is Ultra HD" (the next one isn't listed yet)."""
    for ev in evs:
        ev["uhd_live"] = not UHD_FILLER.match(ev["title"] or "")
        if ev["uhd_live"]:
            comp, match = uhd_comp(ev["title"])
            ev["comp"], ev["match"] = comp, match
            ev["line"] = (ev.get("sub") or "").strip()          # Sky's first line, e.g. "Heart of Midlothian v Rangers."
            if not ev["line"] and re.fullmatch(r"[^.!?]{2,60}\s+vs?\.?\s+[^.!?]{2,60}[.!?]?", (ev.get("desc") or "").strip()):
                ev["line"], ev["desc"] = ev["desc"].strip(), ""   # the whole synopsis is just the teams
            if re.fullmatch(r"[^.!?]{2,60}\s+vs?\.?\s+[^.!?]{2,60}[.!?]?(\s*\([^)]*\)\.?)?", ev["line"]):
                if not re.search(r"\S\s+vs?\.?\s+\S", match):  # title "Scottish Premiership Football",
                    match = ev["line"].rstrip(".")                 # line "Heart of Midlothian v Rangers": the match
                    ev["match"] = match
                ev["line"] = ""                                  # (otherwise just the teams again - not needed)
            if comp and (comp != ev["title"] or match != ev["title"]):
                ev["desc"] = " ".join(x for x in (ev["line"], ev.get("desc") or "") if x)
                ev["sub"], ev["no_lead"] = comp, True            # "Scottish Premiership", as in the football guide
                ev["title"] = match                              # "Hearts v Rangers" (competition is the sub)
    for i, ev in enumerate(evs):
        if ev["uhd_live"]:
            continue
        nxt = next((e for e in evs[i + 1:] if e["uhd_live"]), None)
        if nxt is None:
            ev["sub"], ev["no_lead"] = "", True
            ev["desc"] = "This is Ultra HD. The next event will be listed when Sky's schedule has it."
            continue
        comp, match = nxt["comp"], nxt["match"]                  # ("Scottish Premiership", "Hearts v Rangers")
        uk = nxt["start"].astimezone(LONDON)
        when = "Kick-off" if re.search(r"\S\s+vs?\.?\s+\S", match) else "Starts"
        detail = nxt.get("line", "")
        day = f"{uk:%a} {uk.day}{'th' if 10 <= uk.day % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(uk.day % 10, 'th')}"
        ev["title"] = f"{match} ({day}, {uk:%H:%M})"                  # "Hearts v Rangers (Wed 28th, 19:00)"
        ev["sub"] = f"⏭ Next Event: {comp}" if comp else "⏭ Next Event"
        lead = f"Next Event: {comp} – {match}." if comp and comp not in match else f"Next Event: {match}."
        ev["desc"] = " ".join(x for x in (lead, detail if detail.rstrip('.') != match else "") if x)
        # (no kick-off time here - it is in the title, "Spurs v C. Palace (Sat 31st, 17:00)")
        ev["live"], ev["no_lead"] = False, True
    return evs


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
                   # 30 Oct 2026: Eurosport 1/2 TR (from TV+, TVPLUS_CHANNELS) and beIN SPORTS 5 (also Digiturk)
                   "Eurosport1": ("Eurosport 1 TR", ["EUROSPORT.1.HD.tr"]),       # TR1 ids from the 30 Oct log
                   "Eurosport2": ("Eurosport 2 TR", ["EUROSPORT.2.TR.HD.tr"]),    # (backup for TV+)
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
                   # 29 Oct 2026 - ids GUESSED in LV1's style; if wrong, the log names similar ids
                   "Eurosport1": ("Eurosport 1 LV", ["Eurosport.1.HD.lv", "Eurosport.1.lv", "Eurosport.HD.lv",
                                                     "Eurosport.lv"]),
                   "Eurosport2": ("Eurosport 2 LV", ["Eurosport.2.HD.lv", "Eurosport.2.lv"]),
                   "TV3Life": ("TV3 Life", ["TV3.Life.HD.lv", "TV3.Life.lv", "TV3Life.lv"]),   # general channel
               }},
    "hk": {"file": "HK1", "prefix": "HK", "place": "Hong Kong", "tz": "Asia/Hong_Kong", "english": True,
           "backup": True, "channels": {                  # backup for Now TV's own guide
               **{f"beINSPORTS{n}": (f"beIN SPORTS {n} HK", [f"beIN.SPORTS.{n}.hk"]) for n in range(1, 7)},
               **{f"NowSports{n}": (f"Now Sports {n}", [f"Now.Sports.{n}.hk"]) for n in range(1, 8)},
               "NowSportsPrime": ("Now Sports Prime", ["Now.Sports.Prime.hk"]),
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
             "calibrate": True,      # its times were 2 h late (28 Oct 2026) - see calibrate_times()
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
             }},
}
# Backups: channels your own sources list but send nothing for. Same IDs as those sources;
# a channel your own source does fill is kept from there and the backup copy is dropped.
EPGSHARE.update({
    "france": {"file": "FR1", "prefix": "FR", "place": "France", "tz": "Europe/Paris", "english": False,
               "backup": True, "channels": {
                   "Eurosport1": ("Eurosport 1 FR", ["Eurosport.1.fr", "Eurosport.1..fr"]),
                   "Eurosport2": ("Eurosport 2 FR", ["Eurosport.2.fr", "Eurosport.2..fr"]),
                   "DAZN1": ("DAZN 1 FR", ["DAZN.1.fr"]),
                   **{f"beINSPORTSMAX{n}": (f"beIN SPORTS MAX {n} FR", [f"beIN.SPORTS.MAX.{n}.fr"])
                      for n in range(4, 11)},             # not in SFR's guide at all
                   # 29 Oct 2026: backups for Canal+'s guide (fetch_canal); ids GUESSED in epgshare's style
                   "InfosportPlus": ("Infosport+", ["INFOSPORT+.fr", "Infosport+.fr", "InfoSport+.fr",
                                                    "Infosport.Plus.fr", "INFOSPORT.PLUS.fr"]),
                   "SportEnFrance": ("Sport en France", ["Sport.en.France.fr", "SPORT.EN.FRANCE.fr",
                                                         "Sport.En.France.fr"]),   # backup for SFR 2837
               }},
    "golfplus": {"file": "CH1", "prefix": "FR", "place": "France", "tz": "Europe/Paris", "english": False,
                 "backup": True, "channels": {"GolfPlus": ("Golf+", ["GOLF+.ch"])}},
    # beIN SPORTS Asia-Pacific: backups for beIN's own site (same IDs), plus SG 4-5 and Rugby
    "sg": {"file": "SG1", "prefix": "SG", "place": "Singapore", "tz": "Asia/Singapore", "english": True,
           "backup": True, "channels": {
               "beINSPORTS1": ("beIN SPORTS 1 SG", ["beIN.SPORTS.(HD).sg"]),
               **{f"beINSPORTS{n}": (f"beIN SPORTS {n} SG", [f"beIN.SPORTS.{n}.(HD).sg"]) for n in range(2, 6)},
               "beINSPORTSRUGBY": ("beIN SPORTS RUGBY SG", ["beIN.SPORTS.RUGBY.HD.sg"]),
               **{f"HubPremier{n}": (f"Hub Premier {n}", [f"Hub.Premier.{n}.sg"]) for n in range(1, 7)},
                                                          # backup for StarHub (7-11 only come from StarHub)
               **{f"HubSports{n}": (f"Hub Sports {n}", [f"Hub.Sports.{n}.sg", f"Hub.Sports.{n}.HD.sg"])
                  for n in range(1, 9)},                   # backup for StarHub (if epgshare has them)
           }},
    "my": {"file": "MY1", "prefix": "MY", "place": "Malaysia", "tz": "Asia/Kuala_Lumpur", "english": True,
           "backup": True, "channels": {
               **{f"beINSPORTS{n}": (f"beIN SPORTS {n} MY", [f"beIN.SPORTS.{n}.my"]) for n in range(1, 4)},
               "AstroArena": ("Astro Arena", ["Astro.Arena.my"]),
               "AstroArena2": ("Astro Arena 2", ["Astro.Arena.2.my"]),
               "AstroFootball": ("Astro Football", ["Astro.Football.my"]),
               "AstroPremierLeague": ("Astro Premier League", ["Astro.Premier.League.my"]),
               **{f"AstroPremierLeague{n}": (f"Astro Premier League {n}", [f"Astro.Premier.League.{n}.my"])
                  for n in range(2, 6)},
               "AstroGrandstand": ("Astro Grandstand", ["Astro.Grandstand.my"]),
               "AstroGolf": ("Astro Golf", ["Astro.Golf.my", "Astro.Golf.HD.my", r"re:(?i)^astro\W*golf"]),   # 30 Oct 2026
               "AstroBadminton": ("Astro Badminton", ["Astro.Badminton.my"]),
               "AstroCricket": ("Astro Cricket", ["Astro.Cricket.my"]),
               "AstroSportsPlus": ("Astro Sports Plus", ["Astro.Sports.Plus.my"]),
               "AstroSportsUHD": ("Astro Sports UHD", ["Astro.Sports.UHD.my"]),
           }},
    "au": {"file": "AU1", "prefix": "AU", "place": "Australia", "tz": "Australia/Sydney", "english": True,
           "backup": True, "channels": {
               # (beIN SPORTS 1-3 + XTRA AU removed 31 Oct 2026 - the streams are unreliable)
               # Fox Sports + ESPN AU: since 4 Nov 2026 the main source is YourTV's Foxtel guide (fetch_yourtv_au);
               # AU1 is the per-channel fallback (and fills today before YourTV's first programme). Listed in "main"
               # so an empty one is reported in the log
               "FoxCricket": ("Fox Cricket", ["FoxCricket.au", "Fox.Cricket.au"]),
               "FoxLeague": ("Fox League", ["FoxLeague.au", "Fox.League.au"]),
               "FoxSports503": ("Fox Sports 503", ["FoxSports503.au", "Fox.Sports.503.au"]),
               "FoxFooty": ("Fox Footy", ["FoxFooty.au", "Fox.Footy.au"]),
               "FoxSports505": ("Fox Sports 505", ["FoxSports505.au", "Fox.Sports.505.au"]),
               "FoxSports506": ("Fox Sports 506", ["FoxSports506.au", "Fox.Sports.506.au"]),
               "FoxSports507": ("Fox Sports 507", ["FoxSportsMore.au", "FoxSports507.au", "Fox.Sports.More.au"]),
               "FoxSportsNews": ("Fox Sports News", ["FoxSportsNews.au", "Fox.Sports.News.au"]),
               "ESPN": ("ESPN AU", ["ESPN.au"]),
               "ESPN2": ("ESPN2 AU", ["ESPN2.au", "ESPN.2.au"]),
           },
           "main": {"FoxCricket", "FoxLeague", "FoxSports503", "FoxFooty", "FoxSports505", "FoxSports506",
                    "FoxSports507", "FoxSportsNews", "ESPN", "ESPN2"}},
    # Caribbean (29 Oct 2026): Flow's Rush Sports 1-3 and RUSH Prime - epgshare's Barbados file BB1
    # (found in epgshare's ALL_SOURCES1.txt list; no other source); LIVE only where the title or
    # description says so ("Live: Test Cricket")
    "barbados": {"file": "BB1", "prefix": "CARIB", "place": "Barbados", "tz": "America/Barbados", "english": True,
                 "channels": {
                     "RushSports1": ("Rush Sports", ["Rush.Sports.bb"]),
                     "RushSports2": ("Rush Sports 2", ["Rush.Sports.2.bb"]),
                     "RushSports3": ("Rush Sports 3", ["Rush.Sports.3.bb"]),
                     "RushPrime": ("RUSH Prime", ["RUSH.Prime.bb"]),
                 }},
    # UAE (29 Oct 2026): Abu Dhabi Sports (AD Sports 1, 2 and Premium) - epgshare's AE1 file (listed in its
    # ALL_SOURCES1 list: AD.Sports.1.HD.ae, AD.Sports.2.HD.ae, "en:" English copies, and an Arabic-named
    # "Abu Dhabi Sports Premium" entry whose id the list shows garbled). An alternative starting "re:" is a
    # pattern tried against every id in the file, so the exact spelling doesn't matter. The one with most
    # programmes is used; Arabic titles are translated.
    "uae": {"file": "AE1", "prefix": "AE", "place": "UAE", "tz": "Asia/Dubai", "english": True,
            "channels": {
                "ADSports1": ("AD Sports 1", ["AD.Sports.1.HD.ae", "en:.Abu.Dhabi.Sports.1.ae",
                                              r"re:^(en:\W*)?(abu\W*dhabi\W*sports|ad\W*sports)\W*1(\W*hd)?\W*ae$"]),
                "ADSports2": ("AD Sports 2", ["AD.Sports.2.HD.ae", "en:.Abu.Dhabi.Sports.2.ae",
                                              r"re:^(en:\W*)?(abu\W*dhabi\W*sports|ad\W*sports)\W*2(\W*hd)?\W*ae$"]),
                "ADSportsPremium": ("AD Sports Premium", [r"re:(abu\W*dhabi\W*sports|ad\W*sports)\W*premium(?!\W*[23])",
                                                           "re:أبوظبي.*بريميوم|بريميوم.*أبوظبي"]),
                # STARZPLAY (30 Oct 2026) - exact ids from epgshare's AE1 list (epg_ripper_AE1.txt)
                **{f"StarzplaySports{n}": (f"STARZPLAY Sports {n}", [f"en:.STARZPLAY.Sports.{n}.ae"]) for n in (1, 2, 3)},
                "Cricbuzz1": ("Cricbuzz 1", ["en:.Cricbuzz.1.ae"]),
                "Cricbuzz2": ("Cricbuzz 2", ["en:.Cricbuzz.2.ae"]),
            },
            "main": {"StarzplaySports1", "StarzplaySports2", "StarzplaySports3",
                     "Cricbuzz1", "Cricbuzz2"}},
    # Brazil: backup for Claro (same IDs, BR.SporTV ...), used only for channels Claro leaves empty
    "brazil": {"file": "BR1", "prefix": "BR", "place": "Brasilia", "tz": "America/Sao_Paulo", "english": False,
               "backup": True, "channels": {
                   "SporTV": ("SporTV", ["São.Paulo/SP..SporTV.HD.³.br", "São.Paulo/SP..SporTV.br"]),
                   "SporTV2": ("SporTV 2", ["São.Paulo/SP..SporTV.2.HD.³.br", "São.Paulo/SP..SporTV.2.br"]),
                   "SporTV3": ("SporTV 3", ["São.Paulo/SP..SporTV.3.HD.³.br", "São.Paulo/SP..SporTV.3..br"]),
                   "ESPN": ("ESPN", ["ESPN.br"]),
                   "ESPN2": ("ESPN 2", ["ESPN.2.br"]),
                   "ESPN3": ("ESPN 3", ["São.Paulo/SP..ESPN.3.HD.br"]),
                   "ESPN4": ("ESPN 4", ["São.Paulo/SP..ESPN.4.HD.br", "São.Paulo/SP..Espn.4.br"]),
                   "ESPN5": ("ESPN 5", ["ESPN.5.br"]),
                   "ESPN6": ("ESPN 6", ["ESPN.6.br"]),
                   "Premiere2": ("Premiere 2", ["São.Paulo/SP..Premiere.HD.2.br", "São.Paulo/SP..Premiere.2.br"]),
                   **{f"Premiere{n}": (f"Premiere {n}", [f"São.Paulo/SP..PREMIERE.HD.{n}.³.br", f"São.Paulo/SP..Premiere.{n}.br"])
                      for n in (3, 4, 5)},
                   **{f"Premiere{n}": (f"Premiere {n}", [f"São.Paulo/SP..Premiere.{n}.br", f"Belo.Horizonte/MG..Premiere.{n}.br"])
                      for n in (6, 7)},
                   "PremiereClubes": ("Premiere Clubes", ["São.Paulo/SP..Premiere.Clubes.HD.br",
                                                          "São.Paulo/SP..Premiere.Clubes.br"]),
                   "BandSports": ("BandSports", ["São.Paulo/SP..BandSports.HD.br", "São.Paulo/SP..BandSports.br",
                                                 "São.Paulo/SP..Band.Sports.HD.br", "BandSports.br"]),   # 29 Oct 2026, guessed
                   "Combate": ("Combate", ["São.Paulo/SP..Combate.HD.br", "São.Paulo/SP..Combate.br",
                                           "São.Paulo/SP..COMBATE.HD.³.br", "Combate.br"]),          # 29 Oct 2026, guessed
               }},
    # UK and Ireland: backups for Sky's own guide (see SKY_CHANNELS), plus Sky Sports NFL
    "uk": {"file": "UK1", "prefix": "UK", "place": "UK", "tz": "Europe/London", "english": True,
           "backup": True, "channels": {
               "SkySportsMainEvent": ("Sky Sports Main Event", ["SkySpMainEvHD.uk"]),
               # BBC Four (30 Oct 2026): not in our Sky list; general channel (only live sport gets LIVE)
               "BBCFour": ("BBC Four", ["BBC.Four.HD.uk", "BBC.Four.uk", "BBCFourHD.uk", r"re:(?i)^BBC\.?Four"]),
               "RacingTV": ("Racing TV", ["Racing.TV.HD.uk", "Racing.TV.uk"]),   # backups (29 Oct 2026)
               "MUTV": ("MUTV", ["MUTV.HD.uk"]),
               "LFCTV": ("LFCTV", ["LFCTV.HD.uk"]),
               "SkySportsPremierLeague": ("Sky Sports Premier League", ["SkySp.PL.HD.uk"]),
               "SkySportsFootball": ("Sky Sports Football", ["SkySp.Fball.HD.uk", "Sky.Sports.Football.HD.uk"]),
               "SkySportsCricket": ("Sky Sports Cricket", ["SkySpCricket.HD.uk"]),
               "SkySportsGolf": ("Sky Sports Golf", ["SkySp.Golf.HD.uk"]),
               "SkySportsF1": ("Sky Sports F1", ["SkySp.F1.HD.uk"]),
               "SkySportsAction": ("Sky Sports Action", ["SkySp.ActionHD.uk"]),
               "SkySportsMix": ("Sky Sports Mix", ["SkySp.Mix.HD.uk"]),
               "SkySportsNews": ("Sky Sports News", ["SkySp.News.HD.uk"]),
               "SkySportsRacing": ("Sky Sports Racing", ["SkySp.Racing.HD.uk"]),
               "SkySportsTennis": ("Sky Sports Tennis", ["SkySp.Tennis.HD.uk"]),
               "SkySportsNFL": ("Sky Sports NFL", ["Sky.Sports.NFL.uk"]),
               "SkySportsPlus": ("Sky Sports+", ["SkySp+HD.uk"]),
               "SkySportsBoxOffice": ("Sky Sports Box Office", ["SkySpBoxOff.uk"]),
               **{f"TNTSports{n}": (f"TNT Sports {n}", [f"TNT.Sports.{n}.HD.uk"]) for n in range(1, 11)},
               "TNTSportsUltimate": ("TNT Sports Ultimate", ["TNT.Sports.Ultimate.HD.uk"]),
               "TNTSportsBoxOffice": ("TNT Sports Box Office", ["TNT.Sport.BoxOffice.HD.uk"]),
               "TNTSportsBoxOffice2": ("TNT Sports Box Office 2", ["TNTSBoxOff2HD.uk"]),
           },
           "main": {"BBCFour"}},
    "ireland": {"file": "IE1", "prefix": "IE", "place": "Ireland", "tz": "Europe/Dublin", "english": True,
                "backup": True, "channels": {
                    "PremierSports1": ("Premier Sports 1", ["Premier.Sports.1.HD.ie", "Premier.Sports.1.ie"]),
                    "PremierSports2": ("Premier Sports 2", ["Premier.Sports.2.HD.ie", "Premier.Sports.2.ie"]),
                }},
    "nz": {"file": "NZ1", "prefix": "NZ", "place": "New Zealand", "tz": "Pacific/Auckland", "english": True,
           "channels": {
               **{f"SkySport{n}NZ": (f"Sky Sport {n} NZ", [f"Sky.Sport.{n}.nz"]) for n in range(1, 10)},
               "SkySportPremierLeagueNZ": ("Sky Sport Premier League NZ", ["Sky.Sport.Premier.League.nz"]),
               "SkySportSelectNZ": ("Sky Sport Select NZ", ["Sky.Sport.Select.nz"]),
           }},
    "usa": {"file": "US2", "prefix": "US", "place": "USA", "tz": "America/New_York", "english": True,
            "channels": {"USANetwork": ("USA Network", ["USA.Network.HD.us2"]),
                         "NBC": ("NBC", ["NBC.East.Stream.us2"])}},
    "canada": {"file": "CA2", "prefix": "CA", "place": "Canada", "tz": "America/Toronto", "english": True,
               "channels": {
                   "SportsnetOntario": ("Sportsnet Ontario", ["Sportsnet.Ontario.HD.ca2"]),
                   "SportsnetEast": ("Sportsnet East", ["Sportsnet.East.HD.ca2"]),
                   "SportsnetWest": ("Sportsnet West", ["Sportsnet.West.HD.ca2"]),
                   "SportsnetPacific": ("Sportsnet Pacific", ["Sportsnet.(Pacific).HD.ca2"]),
                   "SportsnetOne": ("Sportsnet One", ["Sportsnet.One.HD.ca2"]),
                   "Sportsnet360": ("Sportsnet 360", ["Sportsnet.360.HD.ca2"]),
                   "SportsnetWorld": ("Sportsnet World", ["Sportsnet.World.HD.ca2"]),
                   "Sportsnet4K": ("Sportsnet 4K", ["Sportsnet.4K.ca2"]),
               }},
    "italy": {"file": "IT1", "prefix": "IT", "place": "Italy", "tz": "Europe/Rome", "english": False,
              "backup": True, "channels": {
                  **{f"SkySport{n}": (f"Sky Sport {n}", [f"Sky.Sport..{n}.it"]) for n in range(253, 259)},   # Sky Sport 259 removed 4 Nov 2026
                  "SkySportNBA": ("Sky Sport NBA", ["Sky.Sport.NBA.it"]),
                  "DAZN4": ("DAZN 4", ["DAZN4.it"]),
              }},
})
EPGSHARE_LIVE = (r"^\s*\(L\)|\(L\)\s*$|\(\s*[ZΖ]\s*\)|\b(live|ao vivo|canlı|canli|tiešraide|tiesraide|langsung|siaran langsung|"
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
    wanted = {eid for _, alts in cfg["channels"].values() for eid in alts if not eid.startswith("re:")}
    patterns = [(a, re.compile(a[3:], re.I)) for _, alts in cfg["channels"].values() for a in alts
                if a.startswith("re:")]                # "re:..." alternatives match any id in the file

    def key_for(eid):
        """The alternative an epgshare id belongs to: itself, or the first matching "re:" pattern."""
        if eid in wanted:
            return eid
        for a, rx in patterns:
            if eid and rx.search(eid):
                return a
        return None

    def in_file(a, ids):
        if a.startswith("re:"):
            rx = re.compile(a[3:], re.I)
            return any(i and rx.search(i) for i in ids)
        return a in ids
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
            key = key_for(eid)
            if key:
                try:
                    start, stop = xmltv_stamp(el.get("start")), xmltv_stamp(el.get("stop"))
                except ValueError:
                    start = stop = None
                title = pick(el, "title")
                if start and stop and stop > start and title and start < end and stop > first:
                    sub, desc = pick(el, "sub-title"), pick(el, "desc")
                    live = bool(re.search(EPGSHARE_LIVE, title, re.I) or el.find("live") is not None)
                    title = re.sub(r"^\s*\(L\)\s*|\s*\(\s*[ZΖ]\s*\)|^\s*(live|ao vivo|canlı|canli)\s*[:\-]\s*|^\s*live\s+(?=[^\s:]{1,14}:)|\s*[-(:]?\s*\(?\b(live|ao vivo|canlı|canli|"
                                   r"tiešraide|langsung)\b\)?\s*$|\s*\(c\)\s*$", "", title, flags=re.I).strip() or title
                    per.setdefault(key, {})[start] = {
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
                  + ("" if any(in_file(a, seen_ids) for a in alts) else " (channel not in the file)"))
        elif not evs and (not cfg.get("backup") or part in cfg.get("main", ())):   # say why a main channel is empty
            if any(in_file(a, seen_ids) for a in alts):
                print(f"    {name}: in the file but no programmes in these days")
                EMPTY_CHANNELS[f"{cfg['prefix']}.{part}"] = name       # gets a placeholder (add_empty_placeholders)
            else:
                words = [w for w in re.findall(r"[a-z]{3,}", name.lower()) if w not in ("the", "sports", "sport", "channel")]
                like = sorted(i for i in seen_ids if i and words and all(w in i.lower() for w in words))[:8]
                print(f"    {name}: not in the file ({len(seen_ids)} channels in it)"
                      + (f" - similar ids: {', '.join(like)}" if like else ""))
        if evs:
            out[part] = [evs[k] for k in sorted(evs)]
    if cfg.get("calibrate") and out:
        calibrate_times(cfg, out)
    return out


# Sky Go (NZ) guide (2 Nov 2026). Sky Sport NZ now comes from Sky's own TV-guide service (the request the skygo.co.nz
# TV guide page makes - no login, no key) instead of epgshare01's NZ1 file: it runs 7+ days ahead (NZ1 gave about
# 3), follows Sky's live changes to the running order, and has the same descriptions. Checked from the GitHub
# runner on 2 Nov 2026 (skygo_check.py). It is Sky's private service, so it can change or refuse us without notice:
# any channel it fills with fewer than SKYGO_MIN_EVENTS programmes simply keeps its epgshare NZ1 listing, and
# --no-skygo turns it off. Sky's own "live" flag is only trusted when true (it is false for live cricket and
# A-League), the rest of the live marking is unchanged.
def gh_warn(title, msg):
    """GitHub Actions turns this line into a yellow warning on the run's page (it is only text anywhere else)."""
    print(f"::warning title={title}::{msg}", flush=True)


SKYGO_API = "https://api.skyone.co.nz/exp/graph"
SKYGO_HEADERS = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json",
                 "Origin": "https://www.skygo.co.nz", "Referer": "https://www.skygo.co.nz/"}
SKYGO_MIN_EVENTS = 10
SKYGO_QUERY = """query getSlots($from: DateTime!, $to: DateTime!) { channels { __typename
 ... on LinearChannel { id title number slots(from: $from, to: $to) { id start end live
  programme { __typename ... on Title { id title synopsis }
   ... on Movie { synopsis }
   ... on Episode { id title synopsis show { id title synopsis } } } } } } }"""
SKYGO_NZ_CHANNELS = {          # Sky Go channel title -> the EPGSHARE["nz"] id parts it fills
    "sky sport 1": ["SkySport1NZ"], "sky sport 2": ["SkySport2NZ"], "sky sport 3": ["SkySport3NZ"],
    "sky sport 4": ["SkySport4NZ"], "sky sport 5": ["SkySport5NZ"], "sky sport 6": ["SkySport6NZ"],
    "sky sport 7": ["SkySport7NZ"], "sky sport 9": ["SkySport9NZ"], "sky sport select": ["SkySportSelectNZ"],
    "sky sport premier league": ["SkySport8NZ", "SkySportPremierLeagueNZ"],      # Sky Sport 8 IS the Premier League channel
}


def fetch_skygo_nz(days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for the Sky Sport NZ channels, same shape as
    fetch_epgshare (title = the show, sub = the episode title, desc = the synopsis). Only channels with at least
    SKYGO_MIN_EVENTS programmes are returned, so a failed or thin answer leaves epgshare's listing in place."""
    tz = ZoneInfo(EPGSHARE["nz"]["tz"])
    first = datetime(days[0].year, days[0].month, days[0].day, tzinfo=tz).astimezone(timezone.utc)
    last_day = days[-1] + timedelta(days=1)
    end = datetime(last_day.year, last_day.month, last_day.day, tzinfo=tz).astimezone(timezone.utc)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    params = {"query": SKYGO_QUERY,
              "variables": json.dumps({"from": iso(first - timedelta(hours=6)), "to": iso(end)})}
    data = fetch(f"{SKYGO_API}?{urllib.parse.urlencode(params)}", headers=SKYGO_HEADERS, parse="json",
                 retries=2, label="Sky Go TV guide")
    if not isinstance(data, dict):
        return {}
    if data.get("errors"):
        print(f"  WARNING: Sky Go answered with errors: {str(data['errors'][0].get('message'))[:200]}", file=sys.stderr)
    chans = ((data.get("data") or {}).get("channels")) or []
    clean = lambda t: re.sub(r"\s+", " ", str(t or "")).strip()
    out = {}
    for ch in chans:
        parts = SKYGO_NZ_CHANNELS.get(clean(ch.get("title")).lower()) if isinstance(ch, dict) else None
        if not parts:
            continue
        evs = {}
        for sl in ch.get("slots") or []:
            try:
                start = datetime.fromisoformat(sl["start"].replace("Z", "+00:00")).astimezone(timezone.utc)
                stop = datetime.fromisoformat(sl["end"].replace("Z", "+00:00")).astimezone(timezone.utc)
            except (KeyError, ValueError, AttributeError):
                continue
            prog = sl.get("programme") or {}
            show = prog.get("show") or {}
            ep_title = clean(prog.get("title"))
            title = clean(show.get("title")) or ep_title
            if not (title and stop > start and start < end and stop > first):
                continue
            sub = ep_title if ep_title != title else ""
            desc = clean(prog.get("synopsis")) or clean(show.get("synopsis"))
            evs[start] = {"start": start, "stop": stop, "title": title, "sub": sub, "live": bool(sl.get("live")),
                          "desc": short_desc(desc) if desc not in (title, sub) else ""}
        listing = [evs[k] for k in sorted(evs)]
        if debug:
            print(f"    {ch.get('title')}: {len(listing)} programmes from Sky Go")
        if len(listing) >= SKYGO_MIN_EVENTS:
            for part in parts:
                out[part] = [dict(e) for e in listing]       # own copies: later steps edit titles in place
    return out


# YourTV / Foxtel (4 Nov 2026). epgshare01's AU1 file had stalled at about one day ahead, so Fox Sports + ESPN AU now come
# from YourTV (Nine's public TV guide, yourtv.com.au - the requests its own page makes, no login, no key). Checked from the
# GitHub runner on 4 Nov 2026 (au_sources_check.py, rounds 1-6): the guide call GET /api/guide/?day=<slug>&timezone=
# Australia/Sydney&format=html&region=168 (168 = the page's "Foxtel" pay-TV choice) answers an HTML grid for all Foxtel
# channels - the day must be a SLUG (today, thu, fri ... ; ISO dates are a 404). Today is partial (it starts around
# 16:30 Sydney time when checked), every other day is the full 00:00-24:00, and the weekdays reach 6 days ahead.
# The grid has titles + start times + block widths (% of 24 h = duration); /api/airings/<id> adds the synopsis, the
# episode title and a live flag (trusted only when true, like Sky Go's). Descriptions are only fetched for programmes
# in the next YOURTV_DETAIL_HOURS (about 720 requests), the rest keep a title. It is Nine's site, so it can change or
# refuse us without notice: a channel with fewer than YOURTV_MIN_EVENTS programmes keeps its AU1 listing, if YourTV
# fails everything stays on AU1, and if the airing start times disagree with the grid's (wrong day mapping) the whole
# YourTV reading is dropped. --no-yourtv turns it off.
YOURTV_BASE = "https://www.yourtv.com.au"
YOURTV_PAY_REGION = 168            # Foxtel (the page's pay list: 168 Foxtel, 371 Foxtel Now, 192 Optus TV, 284 Fetch)
YOURTV_MIN_EVENTS = 5
YOURTV_DETAIL_HOURS = 72           # raised from 48 on 4 Nov 2026 (user)
YOURTV_MAX_DAYS = 7                # today + the next six weekdays (a weekday slug is only unambiguous for those)
YOURTV_HEADERS = {"User-Agent": HEADERS["User-Agent"], "Accept": "text/html, */*; q=0.01",
                  "Accept-Language": "en-AU,en;q=0.9", "Referer": YOURTV_BASE + "/guide/",
                  "X-Requested-With": "XMLHttpRequest"}
YOURTV_JSON_HEADERS = {**YOURTV_HEADERS, "Accept": "application/json, text/javascript, */*; q=0.01"}
YOURTV_CHANNELS = {                # YourTV channel name (lower case) -> EPGSHARE["au"] channel key
    "fox cricket hd": "FoxCricket", "fox league hd": "FoxLeague", "fox sports 503 hd": "FoxSports503",
    "fox footy hd": "FoxFooty", "fox sports 505 hd": "FoxSports505", "fox sports 506 hd": "FoxSports506",
    "fox sports 507 hd": "FoxSports507", "fox sports news hd": "FoxSportsNews", "espn hd": "ESPN", "espn2hd": "ESPN2",
}
YOURTV_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def yourtv_minutes(text):
    """'5:00 PM' -> minutes after midnight (None when it isn't a time)."""
    m = re.match(r"\s*(\d{1,2}):(\d{2})\s*([AaPp])[Mm]", str(text or ""))
    if not m:
        return None
    return (int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)) * 60 + int(m.group(2))


def parse_yourtv_day(body, day, tz):
    """{channel key: [{id, title, start, stop}]} for one day's HTML grid (only the wanted channels).
    Block widths are % of 24 h (4.1666% = 60 min); only the first block carries margin-left (its offset from 00:00). A
    first block that began the evening before shows its true start time but is clipped at 00:00, so its end is
    00:00 + its width; a block running past midnight is clipped at 24:00 (the next day's page has its true end)."""
    out = {}
    local = lambda mins: datetime(day.year, day.month, day.day, tzinfo=tz) + timedelta(minutes=mins)
    for chunk in re.split(r'(?=data-channel-id=")', body)[1:]:
        nm = re.search(r'data-channel-name="([^"]*)"', chunk)
        key = YOURTV_CHANNELS.get(re.sub(r"\s+", " ", html.unescape(nm.group(1))).strip().lower()) if nm else None
        if not key:
            continue
        prev = None
        for i, seg in enumerate(chunk.split('<div class="guide__row__block')[1:]):
            link = re.search(r'<a class="show-link"[^>]*data-event-id="(\d+)"[^>]*>\s*<h4>(.*?)</h4>\s*<p>(.*?)</p>', seg, re.S)
            if not link:
                continue
            style = seg[:seg.find(">")]
            width = re.search(r"width:\s*([\d.]+)%", style)
            margin = re.search(r"margin-left:\s*(-?[\d.]+)%", style)
            mins = yourtv_minutes(link.group(3))
            title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", link.group(2)))).strip()
            if mins is None or not width or not title:
                continue
            dur = float(width.group(1)) * 14.4
            if prev is None:                                  # the first block of the row
                at = float(margin.group(1)) * 14.4 if margin else 0.0
                if mins > at + 30:                             # began yesterday: clipped on the left
                    start, stop = mins - 1440, at + dur
                else:
                    start, stop = mins, mins + dur
            else:
                while mins < prev:
                    mins += 1440
                start, stop = mins, mins + dur
            prev = start
            if stop - start < 1:
                continue
            out.setdefault(key, []).append({"id": link.group(1), "title": title,
                                            "start": local(start).astimezone(timezone.utc),
                                            "stop": local(round(stop)).astimezone(timezone.utc)})
    return out


def yourtv_airing(eid):
    """The /api/airings/<id> JSON of one programme (None if it can't be read)."""
    d = fetch(f"{YOURTV_BASE}/api/airings/{eid}", headers=YOURTV_JSON_HEADERS, parse="json", retries=2, quiet=True,
              label="YourTV airing")
    return d if isinstance(d, dict) else None


def fetch_yourtv_au(days, debug=False):
    """{channel key: [{start, stop, title, sub, live, desc}]} for the Fox Sports + ESPN AU channels, same shape as
    fetch_epgshare. A channel with fewer than YOURTV_MIN_EVENTS programmes is left out (it keeps its AU1 listing)."""
    tz = ZoneInfo(EPGSHARE["au"]["tz"])
    first = datetime(days[0].year, days[0].month, days[0].day, tzinfo=tz).astimezone(timezone.utc)
    last_day = days[-1] + timedelta(days=1)
    end = datetime(last_day.year, last_day.month, last_day.day, tzinfo=tz).astimezone(timezone.utc)
    per = {}                                                  # channel key -> {start: event}
    pages = 0
    for i in range(min(len(days), YOURTV_MAX_DAYS)):
        day = days[0] + timedelta(days=i)
        slug = "today" if i == 0 else YOURTV_WEEKDAYS[day.weekday()]
        query = urllib.parse.urlencode({"day": slug, "timezone": EPGSHARE["au"]["tz"], "format": "html",
                                        "region": YOURTV_PAY_REGION})
        body = fetch(f"{YOURTV_BASE}/api/guide/?{query}", headers=YOURTV_HEADERS, retries=2, label=f"YourTV guide ({slug})")
        if not body or "data-channel-id" not in body:
            continue
        pages += 1
        got = parse_yourtv_day(body, day, tz)
        if debug:
            print(f"    YourTV {slug} ({day}): {sum(len(v) for v in got.values())} programmes on {len(got)} channel(s)")
        for key, evs in got.items():
            slot = per.setdefault(key, {})
            for ev in evs:
                old = slot.get(ev["start"])
                if old is None or ev["stop"] > old["stop"]:   # the next day's page has the true end of a late programme
                    slot[ev["start"]] = {**ev, "sub": "", "desc": "", "live": False}
    if not pages:
        return {}
    # descriptions: the next YOURTV_DETAIL_HOURS only (one request per programme)
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=YOURTV_DETAIL_HOURS)
    todo = [ev for slot in per.values() for ev in slot.values() if ev["stop"] > now and ev["start"] < horizon]
    checked = differ = with_desc = 0
    if todo:
        from concurrent.futures import ThreadPoolExecutor
        print(f"  YourTV: fetching details for {len(todo)} programme(s) in the next {YOURTV_DETAIL_HOURS} h ...")
        with ThreadPoolExecutor(max_workers=4) as pool:
            found = list(pool.map(lambda ev: yourtv_airing(ev["id"]), todo))
        for ev, a in zip(todo, found):
            if not a:
                continue
            try:
                air = datetime.fromisoformat(str(a["date"]).replace("Z", "+00:00")).astimezone(timezone.utc)
            except (KeyError, ValueError):
                continue
            checked += 1
            if abs((air - ev["start"]).total_seconds()) > 300:
                differ += 1
                continue
            sq = lambda t: re.sub(r"\s+", " ", str(t or "")).strip()
            sub, desc = sq(a.get("episodeTitle")), sq(a.get("synopsis"))
            ev["sub"] = sub if sub.lower() != ev["title"].lower() else ""
            ev["desc"] = short_desc(desc) if desc and desc.lower() not in (ev["title"].lower(), sub.lower()) else ""
            ev["live"] = a.get("live") is True               # only trusted when true
            with_desc += bool(ev["desc"])
        print(f"  YourTV: {checked} details read, {with_desc} with a description; start times differing from the grid: {differ}")
        if checked >= 8 and differ > checked * 0.25:
            print("  WARNING: YourTV's start times don't match its own grid (day mapping wrong?) - not used", file=sys.stderr)
            return {}
    out = {}
    for key, slot in per.items():
        listing = [slot[k] for k in sorted(slot) if slot[k]["start"] < end and slot[k]["stop"] > first]
        for ev in listing:
            ev.pop("id", None)
        if debug:
            print(f"    {EPGSHARE['au']['channels'][key][0]}: {len(listing)} programmes from YourTV")
        if len(listing) >= YOURTV_MIN_EVENTS:
            out[key] = listing
    if out:
        lasts = sorted(v[-1]["stop"] for v in out.values())
        starts = sorted(v[0]["start"] for v in out.values())
        fmt = lambda d: d.astimezone(tz).strftime("%a %d %b %H:%M")
        print(f"  YourTV: first programme {fmt(starts[0])} .. {fmt(starts[-1])}, last ends {fmt(lasts[0])} .. {fmt(lasts[-1])} (Sydney)")
    return out


# Astro Malaysia's own guide (5 Nov 2026, user request): the call astro.com.my's TV schedule page makes - open, no login, no key,
# works from the GitHub runner (astro_check.py, two rounds). One request per day (scheduleDate=YYYY-MM-DD, Malaysia time) returns
# all 166 channels with titles and times (eventStartMyt / eventEndMyt, +08:00) - NO descriptions - for 7 days (5 Nov .. 11 Nov on
# 5 Nov). A live programme's title starts with "(L) ". Its UHD times and titles are identical to epgshare MY1's, which is why the
# two can be joined by start time. epgshare MY1 keeps the descriptions but runs only about 1-2 days ahead, so:
#   * a channel epgshare has listings for keeps them; Astro's programmes that START AFTER epgshare's last one are added (title +
#     time only) and epgshare's last block is cut where Astro's next one begins. Checked first: at least half of the epgshare
#     programmes in the overlap must start within 2 minutes of an Astro one - otherwise that channel is left on epgshare;
#   * a channel epgshare has nothing for (Premier League 3 / 4, and 5 / Cricket if Astro ever lists them) comes from Astro alone.
# ASTRO_MY_CHANNELS: our id part -> (Astro's channel number "stbNumber", regex its title must match, or "" for none). Only the
# channels the user named (Premier League 1-5, Grandstand, Football, Cricket, Arena 1 + 2, UHD, Sports Plus). On 5 Nov the feed had
# no Premier League 5 (CH 809) and no "Astro Cricket" (only a different channel, CricBuzz 832) - they are picked up if they appear.
# Astro Golf, Tennis, Badminton etc. are not touched. A failed / empty read changes nothing (epgshare as before); --no-astro turns it off.
ASTRO_MY_URL = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
ASTRO_MY_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
                    "Accept": "application/json, text/plain, */*", "Origin": "https://www.astro.com.my",
                    "Referer": "https://www.astro.com.my/"}
ASTRO_MY_MAX_DAYS = 7
ASTRO_MY_CHANNELS = {
    "AstroArena": ("801", r"(?i)^astro arena$"),
    "AstroArena2": ("802", ""),                  # CH 802 is titled \"Stadium Astro\" - the time check below confirms the match
    "AstroFootball": ("814", r"(?i)astro football"),
    "AstroPremierLeague": ("811", r"(?i)^astro premier league$"),
    "AstroPremierLeague2": ("812", r"(?i)premier league 2$"),
    "AstroPremierLeague3": ("813", r"(?i)premier league 3$"),
    "AstroPremierLeague4": ("808", r"(?i)premier league 4$"),
    "AstroPremierLeague5": ("809", r"(?i)premier league 5$"),
    "AstroGrandstand": ("810", r"(?i)astro grandstand"),
    "AstroCricket": ("", r"(?i)^astro cricket$"),  # matched by title only (CH 832 CricBuzz is another channel)
    "AstroSportsPlus": ("817", r"(?i)sports plus"),
    "AstroSportsUHD": ("805", r"(?i)sports uhd"),
}
ASTRO_MY_MATCH_SECONDS = 120


def astro_my_clean(title):
    """(title without the \"(L) \" flag, live)"""
    t = re.sub(r"\s+", " ", str(title or "")).strip()
    live = bool(re.match(r"^\(L\)\s*", t))
    return (re.sub(r"^\(L\)\s*", "", t).strip() or t), live


def astro_my_channel_dicts(o):
    """every dict in Astro's answer that is a channel (has a stbNumber and a schedule list), wherever it sits"""
    out = []
    if isinstance(o, dict):
        if "stbNumber" in o and isinstance(o.get("schedule"), list):
            out.append(o)
        else:
            for v in o.values():
                if isinstance(v, (dict, list)):
                    out += astro_my_channel_dicts(v)
    elif isinstance(o, list):
        for x in o:
            out += astro_my_channel_dicts(x)
    return out


def fetch_astro_my(days, debug=False):
    """{our id part: [{start, stop, title, sub, live, desc}]} for ASTRO_MY_CHANNELS, same shape as fetch_epgshare
    (titles and times only). {} when Astro gave nothing usable."""
    tz = ZoneInfo(EPGSHARE["my"]["tz"])
    first = datetime(days[0].year, days[0].month, days[0].day, tzinfo=tz).astimezone(timezone.utc)
    last_day = days[-1] + timedelta(days=1)
    end = datetime(last_day.year, last_day.month, last_day.day, tzinfo=tz).astimezone(timezone.utc)
    per = {}                                                   # our part -> {start: event}
    got_days = 0
    for i in range(min(len(days), ASTRO_MY_MAX_DAYS)):
        day = days[0] + timedelta(days=i)
        query = urllib.parse.urlencode({"channelGuide": "true", "platform": "acm", "channelOrderBy": "stbNumber,asc",
                                        "scheduleDate": day.isoformat(), "channelLimit": 200, "channelPage": 1}, safe=",")
        data = fetch(f"{ASTRO_MY_URL}?{query}", headers=ASTRO_MY_HEADERS, parse="json", retries=2, label=f"Astro guide ({day})")
        chans = astro_my_channel_dicts(data)
        if not chans:
            resp = data.get("response") if isinstance(data, dict) else None
            print(f"  Astro {day}: no channels found (answer: {type(data).__name__} "
                  f"{list(data)[:6] if isinstance(data, dict) else ''}; response: {type(resp).__name__}"
                  f"{(' ' + str(list(resp)[:6])) if isinstance(resp, dict) else ''})")
            continue
        n_day = 0
        for ch in chans:
            if not isinstance(ch, dict):
                continue
            stb, name = str(ch.get("stbNumber") or "").strip(), str(ch.get("title") or "")
            for part, (want_stb, rx) in ASTRO_MY_CHANNELS.items():
                if want_stb and stb != want_stb:
                    continue
                if rx and not re.search(rx, name):
                    continue
                if not want_stb and not rx:
                    continue
                for pr in ch.get("schedule") or []:
                    try:
                        st = datetime.fromisoformat(str(pr["eventStartMyt"])).astimezone(timezone.utc)
                        sp = datetime.fromisoformat(str(pr["eventEndMyt"])).astimezone(timezone.utc)
                    except (KeyError, ValueError):
                        continue
                    title, live = astro_my_clean(pr.get("title"))
                    if not title or sp <= st or st >= end or sp <= first:
                        continue
                    old = per.setdefault(part, {}).get(st)
                    if old is None or sp > old["stop"]:
                        per[part][st] = {"start": st, "stop": sp, "title": title, "sub": "", "live": live, "desc": ""}
                    n_day += 1
        if n_day:
            got_days += 1
        if debug:
            print(f"    Astro {day}: {n_day} programmes on the channels we carry")
    out = {part: [slot[k] for k in sorted(slot)] for part, slot in per.items() if slot}
    if out:
        print(f"  Astro: {got_days} day(s) read; {sum(len(v) for v in out.values())} programmes on {len(out)} channel(s)")
    return out


def merge_astro_my(my_eps, astro):
    """Join Astro's listing into epgshare's (my_eps, changed in place) as described above. Returns log lines."""
    lines = []
    tol = timedelta(seconds=ASTRO_MY_MATCH_SECONDS)
    for part in ASTRO_MY_CHANNELS:
        ast = astro.get(part)
        if not ast:
            continue
        base = my_eps.get(part) or []
        name = EPGSHARE["my"]["channels"][part][0]
        if not base:
            my_eps[part] = ast
            lines.append(f"{name}: no epgshare listing - {len(ast)} programmes from Astro "
                         f"(to {ast[-1]['stop'].strftime('%a %d %b %H:%M')} UTC)")
            continue
        starts = [a["start"] for a in ast]
        overlap = [b for b in base if starts[0] - tol <= b["start"] <= ast[-1]["stop"]]
        hits = sum(1 for b in overlap if any(abs(b["start"] - s) <= tol for s in starts))
        if len(overlap) < 3 or hits < len(overlap) * 0.5:
            lines.append(f"{name}: Astro's times don't match epgshare ({hits} of {len(overlap)}) - left on epgshare")
            continue
        base.sort(key=lambda e: e["start"])
        last = base[-1]
        same = next((a for a in ast if abs(a["start"] - last["start"]) <= tol), None)
        later = [a for a in ast if a["start"] > last["start"] + tol]
        if same and same["stop"] < last["stop"]:
            last["stop"] = same["stop"]                       # epgshare stretched its last block; Astro has the real end
        if later and later[0]["start"] < last["stop"]:
            last["stop"] = later[0]["start"]
        if later:
            my_eps[part] = base + later
            lines.append(f"{name}: epgshare kept ({len(base)}), {len(later)} programmes added from Astro "
                         f"(to {later[-1]['stop'].strftime('%a %d %b %H:%M')} UTC)")
        else:
            lines.append(f"{name}: epgshare already as far as Astro - nothing added")
    return lines


# beIN SPORTS Middle East - beIN's own guide (2 Nov 2026). epgshare's BEIN1 file was patchy for these channels (English 1
# had 17 programmes and missed the Youth Olympics; MAX channels ran 5 h ahead). beIN's public API for the region
# "en-mena" (the page beinsports.com/en-mena/tv-guide) has the real schedule 2-6 days ahead, a real "live" flag that matches
# the LIVE badges on its page, and the competition in the title / category. Checked from the GitHub runner on 2 Nov 2026
# (beinmena_check.py). Same API as Australia / Malaysia, with two quirks: tv-event takes ONE channel id per request, and
# answers at most 100 rows per request (a busy channel over a week is cut off) - so a capped window is split in halves.
# A channel with fewer than BEIN_MENA_MIN_EVENTS programmes keeps epgshare's listing (AFC, 4K HDR, NBA, the plain
# "beIN SPORTS" channel have none from beIN); --no-bein-mena turns it off.
BEIN_MENA_MIN_EVENTS = 5
BEIN_MIN_LIVE = timedelta(minutes=40)       # beIN's own "live" flag is also set on 30-minute replay slots (Nice vs PSG on English 1, 25 Nov 2026)
BEIN_GENERIC_CATEGORY = {"entertainment", "sports general", "football", "sports news", "other", ""}
# beIN flags every hour of the XTRA overflow channels as live, but those hours are one filler ("beIN SPORTS XTRA For Live And
# Exclusive Coverage of Premium Sporting Events - November 2026"): never mark a channel-name filler live (2 Nov 2026).
BEIN_FILLER = re.compile(r"(?i)^\s*beIN SPORTS (?:XTRA|MAX)\b")


def bein_mena_parts(name):
    """beIN's channel name -> the EPGSHARE["mena"] id part it fills ([] if we don't carry it)."""
    n = re.sub(r"\s+", " ", name or "").strip().upper()
    part = None
    m = re.fullmatch(r"BEIN SPORTS EN (\d)", n)
    if m:
        part = f"beINSPORTSEnglish{m[1]}"
    elif (m := re.fullmatch(r"BEIN SPORTS FR (\d)", n)):
        part = f"beINSPORTSFrench{m[1]}"
    elif (m := re.fullmatch(r"BEIN SPORTS (\d)", n)):
        part = f"beINSPORTS{m[1]}"
    elif (m := re.fullmatch(r"BEIN SPORTS (MAX|XTRA) (\d)", n)):
        part = f"beINSPORTS{m[1]}{m[2]}"
    elif n == "BEIN SPORTS NEWS":
        part = "beINSPORTSNews"
    return [part] if part and part in EPGSHARE["mena"]["channels"] else []


def bein_mena_title(raw, category=""):
    """"Newcastle United vs Everton - English Premier League 2026/2027 - Week 9" ->
    ("Newcastle United vs Everton", "English Premier League 2026/2027 - Week 9"); "x" between teams becomes "vs"."""
    segs = [x.strip() for x in re.split(r"\s+-\s+", re.sub(r"\s+", " ", raw or "").strip()) if x.strip()]
    if not segs:
        return "", ""
    head = re.sub(r"\s+x\s+", " vs ", segs[0])
    rest = " - ".join(segs[1:])
    if not rest and (category or "").strip().lower() not in BEIN_GENERIC_CATEGORY:
        rest = category.strip()
    return head, rest


def fetch_bein_mena(days, debug=False):
    """{id part: [{start, stop, title, sub, live, desc}]} for the beIN SPORTS MENA channels, same shape as fetch_epgshare."""
    code, chans = bein_region_channels(["en-mena"], debug)
    if not chans:
        return {}
    first, last = days[0], days[-1]

    def rows_window(cid, d0, d1):
        window = f"startBefore={d1 + timedelta(days=1):%Y-%m-%d}T00:00:00.000Z&endAfter={d0:%Y-%m-%d}T00:00:00.000Z"
        data = get_json_url(f"{BEIN_API}tv-event?&{window}&channelIds={cid}", BEIN_HEADERS, quiet=True)
        rows = [r for r in ((data.get("rows") if isinstance(data, dict) else data) or []) if isinstance(r, dict)]
        if len(rows) >= 100 and d1 > d0:                  # cut off at 100 rows: ask for each half separately
            mid = d0 + timedelta(days=(d1 - d0).days // 2)
            return rows_window(cid, d0, mid) + rows_window(cid, mid + timedelta(days=1), d1)
        return rows

    out = {}
    for cid, name in sorted(chans.items(), key=lambda kv: kv[1]):
        parts = bein_mena_parts(name)
        if not parts:
            continue
        evs = {}
        for it in rows_window(cid, first, last):
            try:
                start = datetime.fromisoformat(it["startDate"].replace("Z", "+00:00")).astimezone(timezone.utc)
                stop = datetime.fromisoformat(it["endDate"].replace("Z", "+00:00")).astimezone(timezone.utc)
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
            title, sub = bein_mena_title(it.get("title"), it.get("category"))
            if not title or stop <= start:
                continue
            filler = bool(BEIN_FILLER.match(title))
            short = (stop - start) < BEIN_MIN_LIVE        # 25 Nov 2026 (user): a 30-minute "live" listing is a replay / highlights slot, not a live match
            evs[start] = {"start": start, "stop": stop, "title": title, "sub": sub,
                          "live": bool(it.get("live")) and not filler and not short,
                          "desc": pick_desc(it, "description", "synopsis")}
            if filler or short:           # its description says "Live And Exclusive", which would otherwise still turn it red (2 Nov 2026)
                evs[start]["never_live"] = True
        listing = [evs[k] for k in sorted(evs)]
        if debug:
            print(f"    {name}: {len(listing)} programmes from beIN")
        if len(listing) >= BEIN_MENA_MIN_EVENTS:
            for part in parts:
                out[part] = [dict(e) for e in listing]
    return out


# Time check against the football guide (28 Oct 2026). epgshare01's beIN MENA file (BEIN1) had every
# programme 2 h late: Carabao Cup ties kicking off 19:45 UK were listed from 21:35, Saturday's 15:00
# Premier League games from 16:50 (beIN's coverage starts 10 min before kick-off) - probably Qatar
# clock times written with a European offset. Rather than a fixed correction (which would break if
# epgshare01 fixes it, or the error changes with the clocks), each run compares the group's football
# matches with the real kick-offs: if most of them line up only after moving by whole hours, the whole
# group is moved by that much. Log: "Time check: ... corrected" / "times OK". Groups with
# "calibrate": True in EPGSHARE are checked.
CALIBRATE_MIN_MATCHES = 3


def _fixture_kickoffs(title):
    """Kick-offs (UTC) of every football-guide match with the same two teams as `title`."""
    t = re.sub(r"(?i)^live\b[\s.,:;!-]*", "", title or "")
    t = re.sub(r"^[^:]{2,30}:\s*", "", t)
    sides = re.split(r"\s+(?:v|vs\.?)\s+", t, maxsplit=1)
    if len(sides) != 2:
        sides = re.split(r"\s+(?:x|lwn|[-–])\s+", t, maxsplit=1)
    if len(sides) != 2:
        return []
    sides[1] = re.split(r"[,(]", sides[1])[0]
    a, b = _team_words(sides[0]), _team_words(sides[1])
    return [ko for ko, h, w, _ in load_kickoffs() if (a & h and b & w) or (a & w and b & h)]


def calibrate_times(cfg, out):
    """Move every programme of one epgshare group by whole hours when its football matches only
    line up with the real kick-offs after that move (see above). Changes `out` in place."""
    cands = []                                         # (programme start, [real kick-offs])
    for evs in out.values():
        for ev in evs:
            kos = _fixture_kickoffs(ev["title"])
            if kos:
                cands.append((ev["start"], kos))
    if not cands:
        print(f"  Time check ({cfg['place']}): no football matches to compare - times left as they are")
        return

    def hits(hours):
        """Programmes that start 0-45 min before (or up to 5 min after) a real kick-off once
        moved by `hours`."""
        d = timedelta(hours=hours)
        return sum(1 for st, kos in cands
                   if any(timedelta(minutes=-5) <= ko - (st - d) <= timedelta(minutes=45) for ko in kos))

    score = {h: hits(h) for h in range(-12, 13)}
    best = max(score, key=lambda h: (score[h], -abs(h)))
    if best == 0 or score[best] < CALIBRATE_MIN_MATCHES or score[best] <= 2 * score[0]:
        print(f"  Time check ({cfg['place']}): times OK ({score[0]} live match(es) start at kick-off)")
        return
    d = timedelta(hours=best)
    for evs in out.values():
        for ev in evs:
            ev["start"] -= d
            ev["stop"] -= d
    print(f"  Time check ({cfg['place']}): source times were {abs(best)} h {'late' if best > 0 else 'early'} "
          f"({score[best]} match(es) line up after the move, {score[0]} before) - corrected")


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
                  "South Africa", "Africa", "India", "Qatar", "UK", "Ireland", "New Zealand", "USA", "Canada", "Cyprus", "UAE"}   # their guides are already in English


# A "translation" that is just the source text back (sometimes cut short) - seen 29 Oct 2026 on German
# descriptions ("Aktuell liegt eine Sendepause vor ..." cached as itself). Only counted as a failure when
# the text clearly isn't English, so English or name-only texts ("Bayern - Dortmund") stay as they are.
NON_EN_WORDS = re.compile(
    r"(?i)\b(der|das|und|ist|nicht|mit|einen?|eine|wir|sind|aus|auf|für|von|zum|zur|werden|wird|bei|nach|über|"
    r"auch|noch|dem|des|gezeigt|aktuell|die|im|ein|eines|einer|sich|wie|oder|als|sie|hat|haben|wurde|alle|"
    r"mehr|zwischen|heute|gegen|direkt|le|les|et|est|une|du|pour|dans|avec|sur|aux|el|los|las|del|por|para|"
    r"con|una|il|gli|della|che|per|è|os|em|com|het|een|voor|niet|się|jest|oraz|już|je|ve|na|za|od|které?|"
    r"koji|koja|su|uživo|prenos|"
    # 29 Oct 2026 (late): Nordic, Finnish, Czech, Croatian, Turkish - so their untranslated / half-translated
    # descriptions are caught too
    r"och|på|med|för|av|från|som|är|inte|det|till|har|efter|matchen|säsong|omgång|möter|fotboll|sändningar?|"
    r"fotball|jalkapallo|jääkiekko|fotbal|hokej|nogomet|košarka|futbol|basketbol|"
    r"og|fra|er|ikke|etter|kampen|sesong|runde|møter|høydepunkter|magasin|ukentlig|"
    r"ja|ottelu|kierros|kauden|vastaan|enemmän|lisää|jossa|myös|koe|suora|lähetys|"
    r"se|ve|ze|pro|který|která|které|jsou|muži|ženy|přenos|utkání|zápas|kolo|moderátora|hosty|"
    r"za|od|sa|utakmica|prijenos|emisija|muški|ženski|"
    r"bir|ile|için|maç|maçı|canlı|haftası|ligi|özet|karşılaşması)\b")
EN_WORDS = re.compile(r"(?i)\b(the|and|of|to|is|for|with|on|at|from|by|are|this|that|will|live|match)\b")


def looks_foreign(text):
    f = len(NON_EN_WORDS.findall(text or ""))
    return f >= 2 and f > len(EN_WORDS.findall(text or ""))


def untranslated(src, out):
    """True when out is src handed back (possibly cut short) and src isn't English."""
    if not out:
        return True
    a = re.sub(r"\W+", " ", src).strip().lower()
    b = re.sub(r"\W+", " ", out).strip().lower()
    same = a == b or (len(b) >= 15 and a.startswith(b[:-4]))
    # (29 Oct 2026, Switzerland) also a result still mostly in the source language - half translated
    return looks_foreign(src) and (same or looks_foreign(out))


# Italian descriptions that an earlier run translated badly (language guessed as "auto"): left untranslated, or half Italian
# ("Riviviamo tutti i gol and the principal azioni ...", "Dalla Mewa Arena di Magonza, Germania.") - 8 Nov 2026. They are dropped from the
# cache on load and translated again, now as Italian (see translate_descriptions).
IT_FUNC_RE = re.compile(r"(?i)\b(il|lo|la|le|gli|di|del|della|dello|dei|degli|delle|con|per|che|dopo|dalla|dalle|dal|nel|nella|nelle|sono|viene|"
                        r"restano|punti|alla|allo|agli|alle|ai|dai|sul|sulla|hanno|pi\u00f9|anche|tutti|tutte|ancora)\b")
IT_LEFT_RE = re.compile(r"\b(della|dello|degli|delle|dalla|dalle|nella|nelle|sulla|riviviamo|principali|azioni|giornata|stasera|squadra|partita|"
                        r"viene|restano|sono i|tutti i|le principali|dal vivo|gli|Dal|Dalla|Il [A-Z])\b")


def it_poor(src, out):
    return len(src) >= 25 and len(IT_FUNC_RE.findall(src)) >= 2 and (out == src or bool(IT_LEFT_RE.search(out)))


# French descriptions that were translated badly (language guessed as "auto"): word-for-word or half French ("an intense
# advertisement with seize clubs in license to décrocher the title", "Après a season difficult, Jamie s'interroge sur son
# avenir") - 20 Nov 2026 (user: Canal+ Sport Rugby Pro D2). Dropped from the cache on load and translated again as French.
FR_FUNC_RE = re.compile(r"(?i)\b(le|la|les|des|du|une|dans|avec|apr\u00e8s|pour|sur|qui|est|son|ses|aux|cette|face|contre|chez)\b")
FR_LEFT_RE = re.compile(r"(?i)\b(le|les|des|une|dans|avec|apr\u00e8s|pour|sur|qui|ses|aux|cette|du|accueille|journ\u00e9e|d\u00e9crocher|"
                        r"affiches?|seize|rencontre|d\u00e9place\w*|\u00e9quipe|saison|victoire|d\u00e9faite|disput\u00e9|s['\u2019]\w+|[ld]['\u2019]\w+)\b")


def fr_poor(src, out):
    return (len(src) >= 25 and len(FR_FUNC_RE.findall(src)) >= 3
            and (out == src or len(FR_LEFT_RE.findall(out)) >= 2))


def fix_padel(src, out):
    """Google / MyMemory turn the sport name into a word of the English sentence: "Premier Padel" -> "Prime Minister has fallen",
    "Padel: Kuwait Major - Premier Padel" -> "Dropped: Kuwait Major - Premier Dropped", "Padel" -> "Fell" (25 Nov 2026, user: beIN English
    1 / 2 "Prime Minister has fallen"). Put the name back whenever the source has it and the result lost it."""
    try:
        if not isinstance(out, str) or not re.search(r"(?i)padel", src or "") or re.search(r"(?i)padel", out):
            return out
        word = "Padel" if "Padel" in src else "padel"
        o = re.sub(r"(?i)\b(?:Prime Minister|Premier)\s+(?:has\s+fallen|fallen|fell|dropped|falls?)\b", "Premier Padel", out)
        o = re.sub(r"(?i)\bPrime Minister Padel\b", "Premier Padel", o)
        if re.match(r"(?i)\s*padel\b", src):            # the source starts with the sport name: so must the result
            o = re.sub(r"^(\s*)(?:Has fallen|Fallen|Dropped|Fell)\b", r"\1" + word, o)
        if not re.search(r"(?i)padel", o):
            o = re.sub(r"\b(?:Has fallen|Fallen|Dropped|Fell|fallen|dropped|fell)\b", word, o)
        return o
    except re.error:
        return out


def load_cache():
    path = CACHE_FILE if os.path.exists(CACHE_FILE) else OLD_CACHE_FILE
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        good = {k: (fix_padel(k, v) if k != "__desc_used__" else v) for k, v in data.items() if isinstance(v, str)}
        bad = [k for k, v in good.items() if k != "__desc_used__" and (untranslated(k, v) or it_poor(k, v) or fr_poor(k, v))]
        for k in bad:                                  # retranslated this run (29 Oct 2026 fix)
            good.pop(k)
        if bad:
            print(f"Translation cache: {len(bad)} entr(y/ies) were the untranslated text - trying them again")
        TRANSLATIONS.update(good)
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


def google_translate(text, short=True, sl="auto"):
    """One text through the first translator that still answers (None if none can)."""
    for name, fn in TRANSLATORS:
        if name in TRANSLATOR_DOWN or (name == "MyMemory" and not short):
            continue
        out = fn([text], sl)
        if out and out[0] and not untranslated(text, out[0]):
            return out[0]                              # (the source handed back: try the next translator)
    return None


def translate_all(texts, force=()):
    """Translate texts in Hebrew/Greek/Cyrillic/Indian scripts, plus everything in force."""
    todo = sorted({t for t in texts if t and FOREIGN.search(t) and t not in TRANSLATIONS} |
                  {t for t in force if t and t not in TRANSLATIONS})
    if todo:
        print(f"Translating {len(todo)} new text(s) (about {int(len(todo) * 1.5)}s)...")
    done = 0
    for t in todo:
        if not translators_left(short=True):
            break
        out = google_translate(t, short=True)
        if out:
            TRANSLATIONS[t] = fix_padel(t, out)
            done += 1
    if todo:
        why = f" - {translator_report()}" if done < len(todo) and TRANSLATOR_WHY else ""
        stop = "; stopped, the rest will be tried next run" if not translators_left(short=True) else ""
        print(f"  translated {done}/{len(todo)}{why}{stop}")
        save_cache()


# Words Google often leaves in otherwise translated titles (29 Oct 2026, late): Czech / Finnish / Croatian ...
LEFTOVER_WORDS = [(r"\bmuži\b", "men"), (r"\bmužů\b", "men's"), (r"\bženy\b", "women"), (r"\bžen\b", "women's"),
                  (r"\bkierros\b", "round"), (r"\bmiehet\b", "men"), (r"\bnaiset\b", "women"),
                  (r"\bherrer\b", "men"), (r"\bdamer\b", "women"), (r"\bherrar\b", "men"),
                  (r"\bmuški\b", "men's"), (r"\bženski\b", "women's"), (r"\bLIGA\b", "LEAGUE")]


# Ziggo Sport (20 Nov 2026, user: Ziggo Sport 4 tennis needs translating): Ziggo GO's "English" guide still has Dutch in many
# titles and sub-titles ("Finale, Mannen", "Groepsfase: Dag 6", "ATP Tennis Hoogtepunten", "Finals: Tsjechië - Canada").
# Texts with a Dutch word are sent to the translator, plus the description form ("sub." - the description repeats the
# sub-title). Moto "GP van Portugal: ..." lines are left for ziggo_moto(), which does its own English wording.
NL_MARK_RE = re.compile(r"(?i)\b(hoogtepunten|finale|halve|mannen|vrouwen|dag \d+|groepsfase|kwalificatie\w*|vrije|ronde|wedstrijd|"
                        r"tegen|gras|punten|onwerkelijke|het|van|verenigde|hongarije|tsjechië|groot-brittanni\w+|duitsland|spanje|"
                        r"oostenrijk|italië|zuid-korea|nederland|frankrijk|zweden|argentinië|brazilië|australië|zwitserland|"
                        r"belgië|kroatië|polen|servië|slowakije|noorwegen|denemarken)\b")


def dutch_to_translate(events):
    out = []
    for e in events:
        for key in ("title", "sub"):
            t = (e.get(key) or "").strip()
            if t and NL_MARK_RE.search(t) and not re.match(r"^(?:Moto2&3 )?GP van ", t):
                out.append(t)
                if key == "sub":
                    out.append(t + ".")
    return out


def en(text):
    out = TRANSLATIONS.get(text, text)
    if out is not text:                                # only touch text that went through translation
        for rx, word in LEFTOVER_WORDS:
            out = re.sub(rx, word, out)
    return out


def _translator_get(name, url):
    """GET url as JSON for translator name; marks it down (with the reason) when it refuses."""
    time.sleep(1.0)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        TRANSLATOR_WHY[name] = f"HTTP {e.code} {e.reason}"
        if e.code in (403, 429):
            TRANSLATOR_DOWN.add(name)              # refused: don't ask it again this run
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        TRANSLATOR_WHY[name] = f"{type(e).__name__}: {e}"[:100]
    return None


def _gtx(texts, sl="auto"):
    """Google's free translator; several texts joined by new lines. sl = the source language when it is known (\"it\" for the Italian
    channels, 8 Nov 2026: with \"auto\" short Italian sentences were guessed wrongly and came back half translated)."""
    params = {"client": "gtx", "sl": sl, "tl": "en", "dt": "t", "q": "\n".join(texts)}
    data = _translator_get("Google", "https://translate.googleapis.com/translate_a/single?"
                           + urllib.parse.urlencode(params))
    try:
        lines = [ln.strip() for ln in "".join(seg[0] for seg in data[0] if seg and seg[0]).split("\n")]
    except (TypeError, IndexError, KeyError):
        return None
    return lines if len(lines) == len(texts) and all(lines) else None


def _chrome(texts, sl="auto"):
    """Google's second free address (used by Chrome's translate); one 'q' per text."""
    url = (f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={sl}&tl=en&"
           + urllib.parse.urlencode([("q", t) for t in texts]))
    data = _translator_get("Google (Chrome)", url)
    if isinstance(data, dict):                         # older answer shape, one text
        out = ["".join(x.get("trans", "") for x in data.get("sentences") or [] if isinstance(x, dict))]
    elif isinstance(data, list):
        out = [(d[0] if isinstance(d, list) and d else d) for d in data]
        if len(texts) == 1 and len(out) > 1 and all(isinstance(x, str) for x in out):
            out = [out[0]]                             # ["text", "tr"] for a single text
    else:
        return None
    out = [x.strip() if isinstance(x, str) else "" for x in out]
    return out if len(out) == len(texts) and all(out) else None


MYMEMORY_BUDGET = [4500]                               # its free daily allowance is about 5000 characters


def _mymemory(texts, sl="auto"):
    """MyMemory's free service (no key): short texts only, one at a time."""
    if len(texts) != 1 or len(texts[0]) > 300 or MYMEMORY_BUDGET[0] < len(texts[0]):
        return None
    MYMEMORY_BUDGET[0] -= len(texts[0])
    data = _translator_get("MyMemory", "https://api.mymemory.translated.net/get?"
                           + urllib.parse.urlencode({"q": texts[0], "langpair": (sl if sl != "auto" else "Autodetect") + "|en"}))
    if not isinstance(data, dict):
        return None
    text = str((data.get("responseData") or {}).get("translatedText") or "").strip()
    if str(data.get("responseStatus")) != "200" or not text or "MYMEMORY WARNING" in text.upper():
        TRANSLATOR_WHY["MyMemory"] = str(data.get("responseDetails") or text or "no answer")[:100]
        if "QUOTA" in TRANSLATOR_WHY["MyMemory"].upper() or "WARNING" in text.upper():
            TRANSLATOR_DOWN.add("MyMemory")
        return None
    return [text]


TRANSLATORS = [("Google", _gtx), ("Google (Chrome)", _chrome), ("MyMemory", _mymemory)]
TRANSLATOR_DOWN = set()                                # translators that refused this run
TRANSLATOR_WHY = {}                                    # translator -> last failure reason


def translators_left(short):
    """Is any translator still answering? (MyMemory only counts for short texts.)"""
    return any(n not in TRANSLATOR_DOWN and (short or n != "MyMemory") for n, _ in TRANSLATORS)


def translator_report():
    return "; ".join(f"{n}: {w}" for n, w in TRANSLATOR_WHY.items())


def google_translate_batch(texts, sl="auto"):
    """Several texts in one request, from the first translator that can; None if none could."""
    for name, fn in TRANSLATORS[:2]:
        if name not in TRANSLATOR_DOWN:
            out = fn(texts, sl)
            if out:
                return out
    return None


def translate_descriptions(records, limit):
    """Translate the guide's descriptions (nearest programmes first, at most limit new ones),
    about ten per request. Ones not translated yet go into DESC_PENDING and are left out."""
    today = date.today().isoformat()
    need = {}                                          # text -> earliest start
    lang = {}                                          # text -> source language when the channel's country tells us
    for rec in records:
        english = rec["place"] in ENGLISH_PLACES
        for ev in rec["events"]:
            d = ev.get("desc")
            if d and not (english and not FOREIGN.search(d)):
                need[d] = min(need.get(d, ev["start"]), ev["start"])
                if rec["place"] == "Italy":
                    lang.setdefault(d, "it")
                elif rec["place"] == "France":                 # (20 Nov 2026) "auto" gave word-for-word French
                    lang.setdefault(d, "fr")
    for d in need:
        if d in TRANSLATIONS:
            DESC_USED[d] = today
    todo = sorted((d for d in need if d not in TRANSLATIONS), key=lambda d: need[d])[:max(limit, 0)]
    if todo:
        print(f"Translating {len(todo)} new description(s), about ten at a time ...")
    done, i = 0, 0
    while i < len(todo) and translators_left(short=False):
        batch = []
        sl = lang.get(todo[i], "auto")
        while i < len(todo) and len(batch) < 10 and lang.get(todo[i], "auto") == sl and \
                len(urllib.parse.quote("\n".join(batch + [todo[i]]))) <= 6000:
            batch.append(todo[i])
            i += 1
        if not batch:                                  # one very long text: on its own
            batch, i = [todo[i]], i + 1
        out = google_translate_batch(batch, sl) if len(batch) > 1 else None
        if out is None:                                # the batch didn't split cleanly: one by one
            out = [google_translate(t, short=False, sl=sl) for t in batch]
        for t, tr_ in zip(batch, out):
            if tr_ and untranslated(t, tr_):           # came back untranslated: once more on its own
                tr_ = google_translate(t, short=False, sl=sl)
            if tr_:
                TRANSLATIONS[t] = tr_
                DESC_USED[t] = today
                done += 1
    if todo:
        why = f" - {translator_report()}" if done < len(todo) and TRANSLATOR_WHY else ""
        stop = "; stopped, the rest will be tried next run" if not translators_left(short=False) else ""
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


KICKOFF_RE = re.compile(r"kick-?\s?off:?\s*(\d{1,2})[.:](\d{2})\s*([ap]\.?m\.?)?", re.I)


def kickoff_now(text, *local_times):
    """True if `text` gives a kick-off time ("Kick-off: 16:30", "Kick-off 8.00pm") that
    matches the programme's start in any of the given local times (to 15 minutes)."""
    m = KICKOFF_RE.search(text or "")
    if not m:
        return False
    h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower()
    if ap.startswith("p") and h < 12:
        h += 12
    elif ap.startswith("a") and h == 12:
        h = 0
    ko = h * 60 + mi
    return any(abs((t.hour * 60 + t.minute) - ko) % 1440 <= 15 or
               abs((t.hour * 60 + t.minute) - ko) % 1440 >= 1425 for t in local_times)


def live_sub(sub):
    """Secondary title for a live programme: the sub-title without a "Live" label
    (LIVE is in the title), or None."""
    s = (sub or "").strip()
    if not s or re.fullmatch(r"(?i)live[.!]?", s):
        return None
    s = re.sub(r"(?i)^live\b[\s.,:;-]*", "", s) or s       # "Live. Northern Ireland..." -> "Northern Ireland..."
    return s


# Descriptions that mention "live" without the programme being live
NOT_LIVE_WORDS = re.compile(
    r"\b(highlights?|replay(ed|s)?|repeat(ed|s)?|recap|review|rewind|classic|best of|"
    r"look(s|ing)? back|catch[- ]?up|relive|reliving|archive|delayed|previously)\b", re.I)
# "live" used as a promo phrase rather than describing this programme
LIVE_PROMO = re.compile(
    r"\b(watch|stream(ed|ing)?|available|see it|catch it|follow)\s+(it\s+|all\s+|every\s+\w+\s+)?live\b"
    r"|\blive\s+(and|&)\s+on[- ]demand\b|\blive\s+on\s+(sky\+?|now|the app)\b", re.I)


def desc_says_live(desc):
    """True if the description says the programme is live (not a highlights/replay
    show, and not a promo line like "watch live on Sky+")."""
    d = desc or ""
    if NOT_LIVE_WORDS.search(d):
        return False
    return bool(re.search(r"\blive\b", LIVE_PROMO.sub(" ", d), re.I))


# Start of a live programme's title. Live sports EVENTS on every channel are "🔴 LIVE: ..."
# (since 28 Oct 2026, see live_event); live studio shows keep plain "LIVE: ".
LIVE_PREFIX = "LIVE: "
# Exception (28 Oct 2026): part-time event-only channels are titled like the event streams.
EVENT_LIVE_PREFIX = {"UK.SkySportsUHD1": "🔴 LIVE: ", "UK.SkySportsUHD2": "🔴 LIVE: ",
                     "UK.TNTSportsUltimate": "🔴 LIVE: "}    # (Ultimate: live = Sky's own "Live" flag)
# Never live, whatever the source says (27 Oct 2026: Hub Premier 2 showed "LIVE: End of
# Transmission" between matches).
OFF_AIR_RE = re.compile(r"(?i)^\s*(end of transmission|off[- ]?air|close ?down|station close|"
                        r"no transmission|transmission ends?|test card)\b[\s.!]*$")
# Channels whose source flags magazine shows as live ("LIVE: PL Stories"): there a programme
# only counts as live when its title is a match ("Sunderland vs Leeds United (MW08) - ...")
# and not highlights or a classic match. IDs starting with these:
MATCH_ONLY_LIVE = ("SG.HubPremier",)
# Channels whose source never marks anything live (beIN MENA, 28 Oct 2026): there a football match
# is LIVE when it starts 0-45 min before the real kick-off in the football guide (and runs at least
# 90 min); its secondary title becomes the football guide's competition ("Carabao Cup 4th Round"
# instead of beIN's "Round 4"). IDs starting with these:
KICKOFF_LIVE = ("MENA.", "SG.HubPremier", "SG.HubSports")   # + Hub Premier / Hub Sports 31 Oct 2026: StarHub's own guide flags nothing live
MATCH_TITLE_RE = re.compile(r"\S\s+vs?\.?\s+\S", re.I)
# General (non-sports) channels (29 Oct 2026): ONLY live sport events get a LIVE tag, always
# "🔴 LIVE: ..."; everything else - live chat shows, news, reality TV, studio sport shows such as
# Football Focus or Final Score - is never LIVE there, whatever the source or description says (the
# description test wrongly made "The Late Late Show", "Judge Judy" and "The Neighbourhood" LIVE).
# A programme counts when it is live AND its title or secondary title names a sport/competition
# (GENERAL_SPORT_RE), or its title is a match ("England v Wales") and Sky flags it live or the
# description names a sport, or Sky flags it live and the description says "live coverage" of a
# sport. IDs starting with these:
GENERAL_CHANNELS = ("UK.BBCOne", "UK.BBCTwo", "UK.ITV1", "UK.ITV4", "UK.Channel4", "UK.Channel5",
                    "IE.RTEOne", "IE.RTE2", "IE.VirginMedia", "US.NBC", "US.USANetwork",
                    "CH.blueZoom", "LV.TV3Life", "UK.BBCFour",
                    "PL.CanalPlusPremium")           # blue Zoom F/D (29 Oct 2026): mixed channel, only live sport tagged
GENERAL_SPORT_RE = re.compile(
    r"(?i)\b(football|soccer|rugby|gaa|gaelic|hurling|camogie|cricket|tennis|golf|snooker|darts|"
    r"racing|grand prix|formula (1|one)|f1|moto ?gp|boxing|ufc|mma|wrestling|nfl|nba|nhl|mlb|"
    r"athletics|cycling|tour de france|swimming|diving|gymnastics|netball|hockey|basketball|baseball|"
    r"volleyball|handball|bowls|rowing|boat race|sailing|skiing|equestrian|show ?jumping|triathlon|"
    r"marathon|olympics?|paralympics?|commonwealth games|champions league|europa league|"
    r"conference league|premier league|premiership|super league|nations league|league of ireland|"
    r"six nations|world cup|euro \d{4}|fa cup|carabao|scottish cup|urc|wimbledon|test match|odi|t20i?|"
    r"the open|ryder cup|solheim cup|grand national|cheltenham|royal ascot|ascot|epsom|"
    r"leopardstown|punchestown|galway races|all-ireland|ulster|munster|leinster|connacht|"
    r"provincial|national league|wsl|matchday|kick-?off|"
    r"wnba|ncaa|nascar|indycar|imsa|figure skating|skating|breeders'? cup|kentucky derby|preakness|"
    r"belmont stakes|stanley cup|world series|super bowl|playoffs?|mls)\b")
# Studio sport shows on those channels (in addition to STUDIO_RE) - never LIVE there
GENERAL_STUDIO_RE = re.compile(
    r"(?i)\b(focus|final score|match of the day|motd|sportscene|special|question of sport|"
    r"sports personality|soccer republic|league sunday|inside|goals|sport(s)? (round-?up|bulletin)|"
    r"results|scores?|quiz|a league of their own|mornings?|breakfast|countdown|kickoff show|"
    r"pre-?show|post-?show|wrap|tonight)\b")


def general_sport_live(title, sub, desc, flagged):
    """True for a live sport EVENT on a GENERAL_CHANNELS channel (see there). `flagged` = the
    source itself marks it live (Sky's "Live ..."), not just a "live" in the description."""
    t = re.sub(r"(?i)^live\b[\s.,:;!-]*", "", (title or "").strip())
    sub = (sub or "").strip()
    if OFF_AIR_RE.match(t) or STUDIO_RE.search(t) or GENERAL_STUDIO_RE.search(t) or NOT_LIVE_WORDS.search(t):
        return False
    if GENERAL_SPORT_RE.search(t):
        return True
    if sub and GENERAL_SPORT_RE.search(sub) and not NOT_LIVE_WORDS.search(sub) \
            and not (len(sub) <= 40 and (STUDIO_RE.search(sub) or GENERAL_STUDIO_RE.search(sub))):
        return True
    if MATCH_TITLE_RE.search(t) and (flagged or GENERAL_SPORT_RE.search(desc or "")):
        return True
    # Sky flags it live and the description says it is live sport ("The Sunday Game" - "Live
    # coverage of the All-Ireland football final")
    return bool(flagged and re.search(r"(?i)\blive (coverage|action|commentary)\b", desc or "")
                and GENERAL_SPORT_RE.search(desc or "") and not NOT_LIVE_WORDS.search(desc or ""))


MINI_RE = re.compile(r"(?i)\bmini\b(?:\s*[-–:]|\s*$)")


def really_live(title, cid):
    """False for a programme the source wrongly marks live (off-air blocks; non-match
    programmes on MATCH_ONLY_LIVE channels)."""
    if OFF_AIR_RE.match(title or ""):
        return False
    if MINI_RE.search(title or ""):                    # "AFL Mini - Round 22" (condensed/preview, 20 min)
        return False
    if cid.startswith(MATCH_ONLY_LIVE):
        return bool(MATCH_TITLE_RE.search(title or "")) and not NOT_LIVE_WORDS.search(title or "")
    return True


# (Hub Premier 2 UHD, Ch 232, closed 8 Oct 2026 and merged into Hub Premier 2, Ch 222, which now carries
# the 4K games - its schedule is SG.HubPremier2. A copied "SG.HubPremier2UHD" channel was tried on
# 27 Oct 2026 and removed the same day.)
# Live sports EVENTS get the 🔴 - matches, races, sessions, rounds - but not studio shows ("Sky Sports
# News", "The F1 Show", "Soccer Saturday Reaction", "First Take", "PL Studio"). UK/Ireland since
# 28 Oct 2026, every channel since 28 Oct 2026 (evening). The test reads the title AND the secondary
# title (many sources put the teams in the secondary title: "UEFA Champions League" / "Galatasaray -
# VfB Stuttgart"). Match separators: v, vs, @, x ("Santos x Palmeiras"), lwn (Malay), "A - B",
# "Team at Team". The description gets the kick-off (and venue) from the football guide when it has
# the match, other real start times where known, otherwise "Coverage from: HH:MM.".
EVENT_RE = re.compile(
    r"(?i)\S\s+(v|vs\.?|@|x|lwn)\s+\S"                         # Arsenal v Spurs, Santos x Palmeiras
    r"|\w[\w.)']*\s+[-–]\s+\w"                                 # Anderlecht - Westerlo
    r"|(?-i:[A-Z][\w.']*\s+at\s+[A-Z])"                         # Milwaukee Brewers at Tampa Bay Rays
    r"|\b(test|odi|t20i?|grand prix|gp|practice|free training|qualifying|sprint|warm-?up|"
    r"finals?|semi-?finals?|quarter-?finals?|sfs|qfs|hf\d|qf\d|round of \d+|matchday|match ?day|"
    r"(day|dag|tag|dia|día|jour|giorno) #?\d+|leg|race|rally|stage|golf|tennis|ténis|tenis|atp|wta|itf|"
    r"padel|racing|raceday|marathon|world series|champs|championships?|cup|tour|curling|cyclocross|"
    r"bmx|climbing|darts|snooker|boxing|fight night|ufc|derby|stakes|open|masters|"
    r"league|liga|ligue|serie a|bundesliga|eredivisie|euroleague|nba|nfl|nhl|mlb|f1|formula \d|"
    r"moto ?gp|moto[23]|indycar|nascar|superbike|wrc|football|soccer|futsal|basketball|handball|"
    r"volleyball|hockey|rugby|cricket|baseball|cycling|athletics|swimming|biathlon|skiing|ski|"
    r"table tennis|badminton|squash|wrestling|mma|tournament|grand slam|judo|karate|taekwondo|"
    r"weightlifting|fencing|rowing|sailing|triathlon|gravel\w*|motorsport|cykel|giro|wtcr|trail|"
    r"(?<!['\u2019])pool|billiards|(?:8|9|nine|eight)-?ball|abu dhabi t10|t10 (?:league|cup|cricket|blast|world)|ferrari challenge|carrera cup|supercars|btcc|dtm|formula e|"   # 17 Nov 2026 (user: "LIVE: Ultimate Pool" had no red ball)
    r"netball|lacrosse|bowls|pickleball)\b")
STUDIO_RE = re.compile(
    r"(?i)\b(show|news|social|reaction|weekend|ref watch|sky sports fc|sports? cent(re|er)|"
    r"desk|stateside|total football|lunchtime|preview|gameday|good morning|insiders|fantasy|"
    r"notebook|paddock|uncut|chequered flag|grand prix sunday|football night|"
    r"soccer (saturday|sunday|special)|this is|reload(ed)?|highlights|review|debate|podcast|"
    r"magazine|magazin|countdown|build-?up|press conference|studio|talk|extra|round ?table|"
    r"football club|auction|post[- ]?(show|match|game)|pre[- ]?(match|game|race)|analysis|analyse|"
    r"voorbeschouwing|nabeschouwing|vorbericht|nachbericht|first take|get up|"
    r"documentary|docu|draw ceremony|awards?|today|tonight|central|nba tip-?off|inside the nba|"
    r"sportscenter|now|blitz|courtside|nfl live|following|good evening|avant-match|plateau|"
    r"emission|time for\b.{0,25}\bballs?|"
    r"college football live|saturday league kick[- ]?off|"            # ESPN2 / Fox League studio shows (29 Oct 2026)
    r"scoreboard|run home|full time live|"                            # ESPN2 / Fox League / Fox Sports News (29 Oct, late)
    r"summar(y|ies))\b")
UK_EVENT_RE, UK_STUDIO_RE = EVENT_RE, STUDIO_RE                   # (older names)

# Carabao Cup round (28 Oct 2026): "EFL Carabao Cup 2026-27" (Cyta) -> "Carabao Cup 4th Round" in
# secondary titles and descriptions. Same dates as CUP_ROUNDS["Carabao Cup"] in football_epg.py -
# UPDATE BOTH for 2027-28 (summer 2027). Round = the latest one starting on or before the match
# date (a date in the title, e.g. Cyta's replays "Liverpool - Chelsea 28/10/26", else the
# programme's UK date). Outside the table: just "Carabao Cup".
CARABAO_ROUNDS = [
    ("2026-07-25", "Preliminary Round"),
    ("2026-08-06", "1st Round"),
    ("2026-08-22", "2nd Round"),
    ("2026-09-05", "3rd Round"),
    ("2026-10-24", "4th Round"),
    ("2026-12-12", "Quarter-final"),
    ("2027-01-09", "Semi-final, 1st Leg"),
    ("2027-01-30", "Semi-final, 2nd Leg"),
    ("2027-03-20", "Final"),
    ("2027-03-28", None),            # season over
]
# Only Cyta's form - "EFL" in front and/or a season after ("EFL Carabao Cup 2026-27"); others such as
# beIN's "Carabao Cup Classic"/"Mini"/"Highlights" or Diema's "Carabao Cup Round 4" are left alone
# (narrowed 28 Oct 2026 after the first run).
CARABAO_RE = re.compile(r"(?i)\bEFL\s+Carabao\s+Cup\b(?:\s+\d{4}\s*[-/]\s*\d{2,4})?"
                        r"|\bCarabao\s+Cup\s+\d{4}\s*[-/]\s*\d{2,4}")


def carabao_round(day):
    rnd = None
    for since, name in CARABAO_ROUNDS:
        if day.isoformat() >= since:
            rnd = name
    return rnd


def carabao_name(text, title, start):
    """'EFL Carabao Cup 2026-27' -> 'Carabao Cup 4th Round' (see CARABAO_ROUNDS)."""
    if not text or not CARABAO_RE.search(text):
        return text
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2})\b", title or "")
    try:
        day = date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        day = None
    rnd = carabao_round(day or start.astimezone(LONDON).date())
    return CARABAO_RE.sub("Carabao Cup" + (f" {rnd}" if rnd else ""), text)


def live_event(title, sub=""):
    """True for a live sports event (not a studio show) - gets the 🔴 on every channel.
    The title decides when it names an event; otherwise the secondary title is read too
    ("NBA" / "Cleveland Cavaliers - Oklahoma City Thunder"). A studio word in the title always
    wins; one in the secondary title only counts when that is where the event was found
    (Sky's secondary titles are often a synopsis: "... get the weekend up and running")."""
    t = re.sub(r"(?i)^live\b[\s.,:;!-]*", "", (title or "").strip())
    t = TITLE_DATE_SUFFIX.sub("", t)
    sub = (sub or "").strip()
    if STUDIO_RE.search(t) or NOT_LIVE_WORDS.search(t):
        return False
    if EVENT_RE.search(t):
        return True
    return bool(sub and EVENT_RE.search(sub) and not STUDIO_RE.search(sub)
                and not NOT_LIVE_WORDS.search(sub))


# (A studio word in a SHORT secondary title also rules out a title that names an event:
# "Cricket: Women's Premier League" / "WPL Auction 2027". Long ones are synopses - ignored.)
_live_event_title = live_event

# A date or episode number after a dash ("Pardon The Interruption - Friday 30 October 2026", "Saturday
# League Kick Off - Episode 35") looked like the "A - B" match pattern and gave studio shows the 🔴
# (Fox/ESPN AU, 29 Oct 2026). It is dropped before the event test (the title itself is not changed).
TITLE_DATE_SUFFIX = re.compile(
    r"(?i)\s+[-–]\s+(?:(?:mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)(?:day)?\.?,?\s+\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+(?:\s+\d{4})?"
    r"|(?:episode|ep\.?)\s*\d+)\s*$")


def live_event(title, sub=""):
    sub = (sub or "").strip()
    if sub and len(sub) <= 40 and (STUDIO_RE.search(sub) or NOT_LIVE_WORDS.search(sub)):
        return False
    return _live_event_title(title, sub)


def uk_event(title):
    return live_event(title)


FOOTBALL_GUIDE = "football_epg.xml"                 # in the repo (built by football_epg.py)
FOOTBALL_GUIDE_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/football_epg.xml"
_KICKOFFS = None
_KICKOFF_COMP = []          # competition of each _KICKOFFS entry ("Carabao Cup 4th Round"), same order
TEAM_ALIASES = [(r"\bman\b", "manchester"), (r"\butd\b", "united"), (r"\bspurs\b", "tottenham"),
                (r"\bc\.?\s*palace\b", "crystal palace"), (r"\bwest brom\b", "west bromwich"),
                (r"\bwolves\b", "wolverhampton"), (r"\bforest\b", "nottingham forest"),
                (r"\bb\.?\s*munich\b", "bayern munich"), (r"\bpsg\b", "paris saint germain"),
                (r"\bsheff\b", "sheffield"), (r"\bqpr\b", "queens park rangers")]
TEAM_GENERIC = {"fc", "afc", "city", "united", "town", "rovers", "athletic", "county", "the", "and", "of",
                "hotspur", "albion", "wanderers", "north", "end", "sc", "cf", "ne"}


def _team_words(name):
    n = unicodedata.normalize("NFKD", (name or "").lower())
    n = re.sub(r"[^a-z0-9. ]+", " ", "".join(c for c in n if not unicodedata.combining(c)))
    for pat, rep_ in TEAM_ALIASES:
        n = re.sub(pat, rep_, n)
    n = re.sub(r"[.]", " ", n)
    return {w for w in n.split() if len(w) >= 3 and w not in TEAM_GENERIC} or {n.strip()}


def load_kickoffs():
    """[(kick-off UTC, home words, away words, "Anfield, Liverpool. Kick-off: 20:00.")] from the
    football guide's LIVE programmes."""
    global _KICKOFFS
    if _KICKOFFS is not None:
        return _KICKOFFS
    _KICKOFFS = []
    text = ""
    try:
        if os.path.exists(FOOTBALL_GUIDE):
            with open(FOOTBALL_GUIDE, encoding="utf-8") as f:
                text = f.read()
        else:
            req = urllib.request.Request(FOOTBALL_GUIDE_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", "replace")
    except Exception as err:
        print(f"  NOTE: football guide not available for kick-off times ({err})")
        return _KICKOFFS
    seen = set()
    for m in re.finditer(r'<programme start="(\d{14}) ([+-]\d{4})"[^>]*>\s*<title[^>]*>🔴 LIVE: ([^<]*)</title>'
                         r'(?:\s*<sub-title[^>]*>([^<]*)</sub-title>)?\s*<desc[^>]*>([^<]*)', text):
        ko = re.search(r"Kick-off: (\d{1,2})(?::(\d{2}))?\s?([AaPp][Mm])?", m.group(5))   # "20:00", "8:00 PM", "8pm", "8:30pm" (12-hour since 6 Nov 2026)
        if ko and not (ko.group(2) or ko.group(3)):
            ko = None
        sides = re.split(r"\s+(?:v|vs\.?)\s+", html.unescape(m.group(3)), maxsplit=1)
        if not ko or len(sides) != 2:
            continue
        start = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S%z").astimezone(LONDON)
        ko_hour = int(ko.group(1))
        if ko.group(3):
            ko_hour = ko_hour % 12 + (12 if ko.group(3)[0].lower() == "p" else 0)
        when = start.replace(hour=ko_hour, minute=int(ko.group(2) or 0), second=0)
        if when < start - timedelta(hours=1):
            when += timedelta(days=1)
        key = (when, m.group(3))
        if key in seen:
            continue
        seen.add(key)
        rest = html.unescape(m.group(5)).split(". ", 1)[1] if ". " in m.group(5) else ""
        _KICKOFFS.append((when.astimezone(timezone.utc), _team_words(sides[0]), _team_words(sides[1]),
                          rest.strip()))
        _KICKOFF_COMP.append(html.unescape(m.group(4) or "").strip())
    print(f"  Football guide: {len(_KICKOFFS)} kick-off times for the 🔴 events")
    return _KICKOFFS


def find_fixture(title, start, before=timedelta(minutes=30), after=timedelta(hours=3)):
    """The football guide's match for a programme titled "A v B" (also vs / x / lwn / -) whose
    kick-off is between start - before and start + after: (kick-off UTC, "Anfield, Liverpool.
    Kick-off: 20:00.", competition) - or None."""
    t = re.sub(r"(?i)^live\b[\s.,:;!-]*", "", title or "")
    t = re.sub(r"^[^:]{2,30}:\s*", "", t)                         # "Carabao Cup: Liverpool v Chelsea"
    sides = re.split(r"\s+(?:v|vs\.?)\s+", t, maxsplit=1)
    if len(sides) != 2:                                          # "Udinese x Roma", "Bavaria - Magdeburg"
        sides = re.split(r"\s+(?:x|lwn|[-–])\s+", t, maxsplit=1)
    if len(sides) != 2:
        return None
    sides[1] = re.split(r"[,(]", sides[1])[0]                    # "..., 10th matchday"
    a, b = _team_words(sides[0]), _team_words(sides[1])
    for i, (ko, h, w, rest) in enumerate(load_kickoffs()):
        if start - before <= ko <= start + after and ((a & h and b & w) or (a & w and b & h)):
            return ko, rest, (_KICKOFF_COMP[i] if i < len(_KICKOFF_COMP) else "")
    return None


def kickoff_info(title, start):
    """"Anfield, Liverpool. Kick-off: 20:00." for a football match in the football guide whose
    kick-off is within 3 h of the programme start, else ""."""
    found = find_fixture(title, start)
    return found[1] if found else ""


# Real start times for 🔴 events other than football (28 Oct 2026). Sky's programme starts with the
# build-up, so the description gets the actual first ball / lights out / tip-off when a source has it:
#   cricket  ESPN (series list + scoreboards)      "First ball: 08:30."  (Test day N: the match's start time)
#   F1       OpenF1 session times                   "Lights out: 20:00." / "Session starts: 18:30."
#   NFL/NBA/NHL/MLB  ESPN scoreboards               "Kick-off:" / "Tip-off:" / "Puck drop:" / "First pitch:"
# Otherwise "Coverage from: HH:MM." (the programme's start). Each lookup is read at most once a run.
ESPN_HDR = {"User-Agent": "Mozilla/5.0"}
CRICKET_HEADER = "https://site.web.api.espn.com/apis/personalized/v2/scoreboard/header?sport=cricket&region=gb&tz=Europe/London"
CRICKET_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/cricket/{series}/scoreboard"
OPENF1_SESSIONS = "https://api.openf1.org/v1/sessions?year={year}"
US_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={ymd}"
US_LEAGUES = {"NFL": ("football/nfl", "Kick-off"), "NBA": ("basketball/nba", "Tip-off"),
              "NHL": ("hockey/nhl", "Puck drop"), "MLB": ("baseball/mlb", "First pitch")}
_START_CACHE = {}
_START_LOGGED = set()


def _espn_events(data):
    """Events (dicts) anywhere in an ESPN header/scoreboard reply."""
    out = []
    if isinstance(data, dict):
        if isinstance(data.get("events"), list):
            out += [e for e in data["events"] if isinstance(e, dict)]
        for k in ("sports", "leagues"):
            for x in data.get(k) or []:
                out += _espn_events(x)
    return out


def _competitor_names(ev):
    names = []
    comps = ev.get("competitors") or []
    if not comps:
        for c in ev.get("competitions") or []:
            comps += c.get("competitors") or []
    for c in comps:
        team = c.get("team") if isinstance(c.get("team"), dict) else c
        names.append({str(team.get(k) or "").lower() for k in
                      ("displayName", "shortDisplayName", "name", "abbreviation", "location", "nickname")} - {""})
    return names


def _side_hits(side, names):
    s = re.sub(r"[^a-z0-9 ]", "", side.lower()).strip()
    return bool(s) and any(s == n or (len(s) > 3 and (s in n or n in s)) for n in names if n)


def _parse_iso(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _log_start(text):
    if text not in _START_LOGGED:
        _START_LOGGED.add(text)
        print(f"  {text}")


def cricket_matches():
    """[(start UTC, [name sets], label)] for current/upcoming cricket matches (ESPN)."""
    if "cricket" in _START_CACHE:
        return _START_CACHE["cricket"]
    head = get_json_url(CRICKET_HEADER, ESPN_HDR, quiet=True)
    evs = _espn_events(head)
    series = set()
    for sp in (head or {}).get("sports") or [] if isinstance(head, dict) else []:
        for lg in sp.get("leagues") or []:
            if lg.get("id"):
                series.add(str(lg["id"]))
    for sid in sorted(series)[:40]:
        evs += _espn_events(get_json_url(CRICKET_SCOREBOARD.format(series=sid), ESPN_HDR, quiet=True))
    out, full = [], []
    for e in evs:
        when = _parse_iso(e.get("date"))
        names = _competitor_names(e)
        if when and len(names) >= 2:
            out.append((when, names, e.get("shortName") or e.get("name") or ""))
            comps = e.get("competitors") or [c for cc in e.get("competitions") or [] for c in cc.get("competitors") or []]
            shown = [str((c.get("team") if isinstance(c.get("team"), dict) else c).get("displayName") or "") for c in comps]
            full.append(" v ".join(shown[:2]) if len(shown) >= 2 and all(shown[:2]) else "")
    _START_CACHE["cricket_full"] = full                          # "New Zealand v India", same order as the matches
    print(f"  Cricket (ESPN): {len(out)} matches from {len(series)} series" if out
          else "  NOTE: cricket start times not available (ESPN)")
    _START_CACHE["cricket"] = out
    return out


def cricket_start(title, start):
    m = re.search(r"([A-Za-z][A-Za-z .']{1,30}?)\s+v\s+([A-Za-z][A-Za-z .']{1,30}?)\s*(?::[^:]*)?$", title)
    if not m:
        return ""
    a, b = m.group(1).strip(), m.group(2).strip()
    day = re.search(r"(?i)\bday\s*(\d)", title)
    for when, names, label in cricket_matches():
        if not ((_side_hits(a, names[0]) and _side_hits(b, names[1])) or
                (_side_hits(a, names[1]) and _side_hits(b, names[0]))):
            continue
        if day:                                   # Test day N: same time of day, N-1 days on
            first = when + timedelta(days=int(day.group(1)) - 1)
        else:                                     # one-day match: its start
            first = when
        if start - timedelta(hours=3) <= first <= start + timedelta(hours=4):
            uk = first.astimezone(LONDON)
            _log_start(f"Cricket start: {title} -> {uk:%a %d %b %H:%M} UK ({label})")
            return f"First ball: {uk:%H:%M}."
    return ""


JOLPICA_SEASON = "https://api.jolpi.ca/ergast/f1/{year}.json"      # Ergast's successor: fixed timetable, always up
JOLPICA_KEYS = [("FirstPractice", "Practice 1"), ("SecondPractice", "Practice 2"), ("ThirdPractice", "Practice 3"),
                ("SprintQualifying", "Sprint Qualifying"), ("SprintShootout", "Sprint Qualifying"), ("Sprint", "Sprint"),
                ("Qualifying", "Qualifying"), ("Race", "Race")]


def jolpica_f1_sessions(year):
    """OpenF1-shaped sessions ({session_name, date_start}) from Jolpica - the backup when OpenF1 gives nothing
    (it refuses free requests while an F1 session is live: 30 Oct 2026, the football run during FP1 got nothing)."""
    data = get_json_url(JOLPICA_SEASON.format(year=year), ESPN_HDR, quiet=True)
    races = (((data or {}).get("MRData") or {}).get("RaceTable") or {}).get("Races") or [] if isinstance(data, dict) else []
    out = []
    for r in races:
        for key, name in JOLPICA_KEYS:
            x = r if key == "Race" else r.get(key)
            if isinstance(x, dict) and x.get("date") and x.get("time"):
                out.append({"session_name": name, "date_start": f"{x['date']}T{x['time']}"})
    return out


def f1_sessions(year):
    key = f"f1{year}"
    if key not in _START_CACHE:
        data = get_json_url(OPENF1_SESSIONS.format(year=year), ESPN_HDR, quiet=True)
        sess, src = (data if isinstance(data, list) else []), "OpenF1"
        if not sess:
            sess, src = jolpica_f1_sessions(year), "Jolpica"
        _START_CACHE[key] = sess
        print(f"  F1 ({src}): {len(sess)} sessions in {year}" if sess
              else f"  NOTE: F1 session times not available (OpenF1 and Jolpica)")
    return _START_CACHE[key]


def f1_start(title, start):
    t = title.lower()
    pm = re.search(r"practice\s*([123])", t)
    if pm:
        want = "practice " + pm.group(1)
    elif "sprint" in t and "qualif" in t:
        want = "sprint qualifying"
    elif "sprint" in t:
        want = "sprint"
    elif "qualif" in t:
        want = "qualifying"
    elif re.search(r"grand prix|\bgp\b|\brace\b", t):
        want = "race"
    else:
        return ""
    for sess in f1_sessions(start.year):
        if str(sess.get("session_name") or "").lower() != want:
            continue
        when = _parse_iso(sess.get("date_start"))
        if when and start - timedelta(minutes=30) <= when <= start + timedelta(hours=3):
            uk = when.astimezone(LONDON)
            _log_start(f"F1 start: {title} -> {uk:%a %d %b %H:%M} UK")
            return f"Lights out: {uk:%H:%M}." if want in ("race", "sprint") else f"Session starts: {uk:%H:%M}."
    return ""


# F1 repeats marked live (31 Oct 2026): some sources flag EVERY airing of a session live (Sky Sport F1 DE listed "F1: Race - GP
# Mexico" red 17 times, DAZN F1 ES 9 times). With OpenF1's real session times, an F1 session programme only counts as live when
# it overlaps the real session (from F1_LEAD_IN before it starts to F1_SLACK after it should end); other airings are replays and
# are shown plain. A title with no session word (\"F1 World Cup - Mexican GP\") is checked against ANY session. Studio/magazine
# shows, F1 Academy/F2/F3 and e-sports are left alone, and nothing changes when OpenF1 has no sessions (it is down).
F1_NOT_SESSION = re.compile(r"(?i)\b(parade|preliminary|press|conference|review|highlights?|magazine|weekend|reaction|show|"
                            r"countdown|build-?up|preview|pre-?race|post-?race|grid|bullfight|launch|academy|f2|f3|"
                            r"formula [23]|esports?|replay|rewind|classic|documentary|story)\b")
F1_SESSION_MINUTES = {"practice 1": 60, "practice 2": 60, "practice 3": 60, "qualifying": 60, "sprint qualifying": 45,
                      "sprint shootout": 45, "sprint": 35, "race": 120}
F1_LEAD_IN = timedelta(minutes=60)
F1_SLACK = timedelta(minutes=30)


def f1_kind(t):
    """OpenF1 session name a title asks for (\"race\", \"qualifying\" ...), or None for a generic F1 title."""
    t = t.lower()
    pm = re.search(r"practice\s*([123])(?!\d)|fp\s*([123])(?!\d)", t)      # not "Practice 2026"
    if pm:
        return "practice " + (pm.group(1) or pm.group(2))
    om = re.search(r"\b(1st|first|2nd|second|3rd|third)\s+free practice", t)
    if om:
        return "practice " + {"1": "1", "f": "1", "2": "2", "s": "2", "3": "3", "t": "3"}[om.group(1)[0]]
    if re.search(r"sprint", t) and re.search(r"qualif|shootout", t):
        return "sprint qualifying"
    if "sprint" in t:
        return "sprint"
    if re.search(r"qualif", t):
        return "qualifying"
    if re.search(r"\brace\b|\bcarrera\b|\brennen\b", t):
        return "race"
    return None


F1_REPLAYS = []                 # channels of the F1 repeats set plain this run (for the log)


def f1_is_replay(title, start, stop):
    """True when an F1 session programme does not overlap the real session (a repeat); False when it does or when
    this can't be decided (not an F1 session title, or no session times)."""
    t = re.sub(r"(?i)^live\b[\s.,:;!-]*", "", title or "")
    if not re.search(r"(?i)\bf1\b|formula (1|one)", t) or F1_NOT_SESSION.search(t):
        return False
    sessions = f1_sessions(start.year)
    if not sessions:
        return False
    want = f1_kind(t)
    stop = stop or start + timedelta(hours=2)
    for sess in sessions:
        name = str(sess.get("session_name") or "").lower()
        if name not in F1_SESSION_MINUTES or (want and name != want):
            continue
        when = _parse_iso(sess.get("date_start"))
        if when and start <= when + timedelta(minutes=F1_SESSION_MINUTES[name]) + F1_SLACK \
                and stop >= when - F1_LEAD_IN:
            return False
    return True


def us_start(title, start):
    m = re.search(r"\b(NFL|NBA|NHL|MLB)\b", title)
    if not m:
        return ""
    path, word = US_LEAGUES[m.group(1)]
    rest = title[m.end():]
    sides = re.split(r"\s+(?:@|at|v|vs\.?)\s+", re.sub(r"^[\s:,-]+", "", rest), maxsplit=1)
    for ymd in sorted({(start - timedelta(hours=8)).strftime("%Y%m%d"), start.strftime("%Y%m%d")}):
        key = f"{path}{ymd}"
        if key not in _START_CACHE:
            _START_CACHE[key] = _espn_events(get_json_url(US_SCOREBOARD.format(path=path, ymd=ymd),
                                                          ESPN_HDR, quiet=True))
        for e in _START_CACHE[key]:
            when = _parse_iso(e.get("date"))
            if not when or not (start - timedelta(minutes=30) <= when <= start + timedelta(hours=3)):
                continue
            names = _competitor_names(e)
            if len(sides) == 2:
                if len(names) < 2 or not ((_side_hits(sides[0], names[0]) and _side_hits(sides[1], names[1])) or
                                          (_side_hits(sides[0], names[1]) and _side_hits(sides[1], names[0]))):
                    continue
            elif not re.search(r"(?i)world series|game \d|super bowl|finals?", title):
                continue                              # no teams named: only for a one-game-a-day final
            uk = when.astimezone(LONDON)
            _log_start(f"{m.group(1)} start: {title} -> {uk:%a %d %b %H:%M} UK")
            return f"{word}: {uk:%H:%M}."
    return ""


# Rugby union (28 Oct 2026): ESPN's rugby scoreboards, one request per competition per day, read only
# for 🔴 "A v B" programmes no other lookup matched (TNT Sports' "Bristol Bears v Leicester" has no
# competition in Sky's data). A match gets "Kick-off: HH:MM." in the description and the competition
# (with "Round N" when ESPN gives the round) as the secondary title if it has none. ESPN league ids
# below - if one stops working its log line shows 0 games; that competition just keeps "Coverage from".
RUGBY_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/rugby/{league}/scoreboard?dates={ymd}"
RUGBY_LEAGUES = {
    "267979": "Gallagher Premiership",
    "270557": "United Rugby Championship",
    "270559": "Top 14",
    "271937": "Investec Champions Cup",
    "272073": "EPCR Challenge Cup",
    "289234": "Rugby International",             # ESPN's "International Test Match" list (Autumn Nations Series, summer tours)
    "180659": "Six Nations",
    "244293": "The Rugby Championship",
    "242041": "Super Rugby Pacific",
}
_RUGBY_COMP = {}            # title -> competition found by rugby_start (for the secondary title)

# Sky Sport NZ secondary titles (28 Oct 2026): short competition prefixes written out ("PL: Spurs v
# Crystal Palace" -> "Premier League: Spurs v Crystal Palace"), and on 🔴 events the kick-off is added
# at the end ("... – Kick-off 17:30") when a lookup found it. Regions listed in SUB_KICKOFF_REGIONS.
SUB_KICKOFF_REGIONS = ("NZ.",)
NZ_SUB_PREFIXES = [("PL", "Premier League"), ("PREM", "Gallagher Premiership"), ("WSL", "Women's Super League"),
                   ("ALM", "A-League Men"), ("ALW", "A-League Women"), ("AFLW", "AFL Women's"),
                   ("WBBL", "Women's Big Bash League"), ("BBL", "Big Bash League"),
                   ("RLWC Wheelchair", "Rugby League World Cup Wheelchair"), ("RLWC", "Rugby League World Cup"),
                   ("UCL", "UEFA Champions League"), ("UEL", "UEFA Europa League"), ("NRL", "NRL"),
                   ("NPC", "Bunnings NPC"), ("ANZ PL Darts", "ANZ Premier League Darts"),
                   ("WST", "World Snooker Tour")]       # 2 Nov 2026: Sky Go has "WST: International Champ D3 Evening"


def nz_sub(sub):
    """'PL: Spurs v Crystal Palace' -> 'Premier League: Spurs v Crystal Palace'."""
    sub = re.sub(r"\s+Hls$", " Highlights", sub or "")              # "... Hls" -> "... Highlights"
    for short, full in NZ_SUB_PREFIXES:
        if re.match(rf"{re.escape(short)}\b:?\s", sub or ""):
            return re.sub(rf"^{re.escape(short)}\b:?\s*", f"{full}: ", sub, count=1)
    return sub


SESSION_WORDS = {"aft": "Afternoon", "eve": "Evening", "morn": "Morning", "arvo": "Afternoon"}


def nz_session(title, sub):
    """Sky NZ (21 Nov 2026): title "Grand Slam Of Darts" + secondary "Grand Slam of Darts: D9 Aft" ->
    title "Grand Slam of Darts", secondary "Day 9, Afternoon". The repeated competition is dropped from the
    secondary title, "D9" becomes "Day 9" and "Aft"/"Eve"/"Morn" are written out."""
    if not sub:
        return title, sub
    h = re.match(r"^(?P<comp>.+?)\s+Highlights$", sub.strip())            # 21 Nov 2026: "Grand Slam Of Darts" + "Grand Slam Of Darts Highlights" -> "Grand Slam of Darts" + "Highlights"
    if h and h["comp"].strip().lower() == (title or "").strip().lower():
        return re.sub(r"\bOf\b", "of", h["comp"].strip()), "Highlights"
    b = re.match(r"^Bowls New Zealand:\s*(?P<comp>.+?)\s*$", title or "")       # "Bowls New Zealand: Oceania Champs" + "Oceania Champs: Day Four"
    if b:
        comp = re.sub(r"\bChamps\b", "Championships", b["comp"])
        rest = re.sub(rf"^{re.escape(b['comp'])}\s*:\s*", "", sub, flags=re.I)
        return f"Bowls. {comp}", rest or sub
    m = re.match(r"^(?P<comp>[^:]{2,60}):\s*(?P<rest>.+)$", sub)
    if m and m["comp"].strip().lower() == (title or "").strip().lower():
        title, sub = m["comp"].strip(), m["rest"].strip()      # the secondary title's capitals ("of") are the proper ones
    new = re.sub(r"\bD(\d{1,2})\b", r"Day \1", sub)
    new = re.sub(r"\b(Aft|Eve|Morn|Arvo)\b", lambda x: SESSION_WORDS[x.group(1).lower()], new)
    if new != sub:
        sub = re.sub(r"^(Day \d{1,2})\s+(?=[A-Z])", r"\1, ", new)     # "Day 9 Afternoon" -> "Day 9, Afternoon"
    return title, sub


def nz_teams_first(title, sub):
    """Sky NZ: title "Premier League" + secondary "Premier League: Spurs v Crystal Palace" ->
    title "Spurs v Crystal Palace", secondary "Premier League" (28 Oct 2026). Only for the
    "Competition: Team v Team" form; anything else (golf rounds, "BLACKCAPS v India: 4th T20") is kept."""
    m = re.match(r"^(?P<comp>[^:]{2,60}):\s*(?P<teams>.+?\S\s+(?:v|vs\.?)\s+\S.*)$", sub or "")
    if not m or re.search(r"\s(?:v|vs\.?)\s", m["comp"]):
        return title, sub
    return m["teams"].strip(), m["comp"].strip()


# Nicknames Sky Sport NZ uses (28 Oct 2026). Rugby clubs - used ONLY in rugby_start (football has
# "Saints"/"Tigers" too); national team names - used by every lookup (cricket, rugby).
RUGBY_CLUB_NICKNAMES = {"bears": "Bristol Bears", "tigers": "Leicester Tigers", "saints": "Northampton Saints",
                        "quins": "Harlequins", "sarries": "Saracens", "chiefs": "Exeter Chiefs",
                        "sharks": "Sale Sharks", "falcons": "Newcastle", "red bulls": "Newcastle",
                        "cherry and whites": "Gloucester"}
# 21 Nov 2026 (user, Sky Sport 1 NZ: "...between the New Zealand and India"): a nickname used with "the" ("the Black Caps") left a rogue "the" in front of the
# country name, so every pattern here (and NZ_TEAM_RE / NZ_WOMEN_RE below) takes the "the" with it.
TEAM_NICKNAMES = [(r"(?i)\b(?:the\s+)?(?:black ?caps|all blacks)\b", "New Zealand"),
                  (r"(?i)\b(?:the\s+)?(?:white ferns|black ferns)\b", "New Zealand Women"),
                  (r"(?i)\b(?:the\s+)?wallabies\b", "Australia"), (r"(?i)\b(?:the\s+)?wallaroos\b", "Australia Women"),
                  (r"(?i)\b(?:the\s+)?(?:springboks|proteas)\b", "South Africa"),
                  (r"(?i)\b(?:the\s+)?red roses\b", "England Women")]

# Rugby round (28 Oct 2026): ESPN gives none, so it is read from other listings in the same run -
# Sky Sport NZ writes "... Round 5 of the Gallagher Premiership between the Bristol Bears and Leicester
# Tigers at Ashton Gate ...". collect_rugby_rounds() gathers (team, team, round) from all the run's
# programmes; rugby_start() uses the entry whose two teams match the ESPN match.
RUGBY_ROUND_RE = re.compile(
    r"\bRound (\d{1,2}) of (?:the )?[A-Z][\w' ]{2,40}? between (?:the )?(.{3,40}?) and (?:the )?(.{3,40}?)"
    r"(?: at |[.,]|$)")
_RUGBY_ROUNDS = []          # [(team a, team b, "Round 5")]


def collect_rugby_rounds(records):
    seen = set()
    for rec in records:
        for ev in rec.get("events") or []:
            for text in (ev.get("desc"), ev.get("sub"), ev.get("title")):
                for m in RUGBY_ROUND_RE.finditer(text or ""):
                    key = (m.group(2).strip(), m.group(3).strip(), f"Round {int(m.group(1))}")
                    if key not in seen:
                        seen.add(key)
                        _RUGBY_ROUNDS.append(key)
    if _RUGBY_ROUNDS:
        print(f"  Rugby rounds from other listings: {len(_RUGBY_ROUNDS)} matches")


def rugby_round_for(names_a, names_b):
    """'Round N' for the ESPN match with these two teams' names, from the other listings
    ("" when none - or when the listings disagree, e.g. a pairing played in two rounds)."""
    found = {rnd for ta, tb, rnd in _RUGBY_ROUNDS
             if (_side_hits(ta, names_a) and _side_hits(tb, names_b)) or
                (_side_hits(ta, names_b) and _side_hits(tb, names_a))}
    return found.pop() if len(found) == 1 else ""


def rugby_round_same_day(events, when):
    """Round of the competition's other matches the same day (Saracens v Newcastle isn't on Sky NZ,
    but Bath v Sale that afternoon is Round 5) - "" unless they all agree."""
    found = set()
    for e in events:
        w = _parse_iso(e.get("date"))
        names = _competitor_names(e)
        if w and abs(w - when) <= timedelta(hours=14) and len(names) >= 2:
            r = rugby_round_for(names[0], names[1])
            if r:
                found.add(r)
    return found.pop() if len(found) == 1 else ""


def _rugby_round(data, ev):
    for src in (ev, data):
        wk = src.get("week") if isinstance(src, dict) else None
        if isinstance(wk, dict) and str(wk.get("number") or "").isdigit():
            return f"Round {wk['number']}"
    return ""


def rugby_start(title, start):
    m = re.search(r"([A-Za-z][A-Za-z .'&-]{1,40}?)\s+(?:v|vs\.?)\s+([A-Za-z][A-Za-z .'&-]{1,40})$",
                  re.sub(r"^[^:]{2,30}:\s*", "", title))
    if not m:
        return ""
    a, b = m.group(1).strip(), m.group(2).strip()
    a = RUGBY_CLUB_NICKNAMES.get(a.lower(), a)                  # Sky NZ: "Bears v Tigers"
    b = RUGBY_CLUB_NICKNAMES.get(b.lower(), b)
    days = sorted({(start - timedelta(hours=6)).strftime("%Y%m%d"), start.strftime("%Y%m%d"),
                   (start + timedelta(hours=3)).strftime("%Y%m%d")})
    for league, label in RUGBY_LEAGUES.items():
        for ymd in days:
            key = f"rugby{league}{ymd}"
            if key not in _START_CACHE:
                data = get_json_url(RUGBY_SCOREBOARD.format(league=league, ymd=ymd), ESPN_HDR, quiet=True)
                _START_CACHE[key] = (data if isinstance(data, dict) else {}, _espn_events(data))
                _RUGBY_COUNT[label] = _RUGBY_COUNT.get(label, 0) + len(_START_CACHE[key][1])
            data, events = _START_CACHE[key]
            for e in events:
                when = _parse_iso(e.get("date"))
                if not when or not (start - timedelta(minutes=30) <= when <= start + timedelta(hours=3)):
                    continue
                names = _competitor_names(e)
                if len(names) < 2 or not ((_side_hits(a, names[0]) and _side_hits(b, names[1])) or
                                          (_side_hits(a, names[1]) and _side_hits(b, names[0]))):
                    continue
                rnd = (_rugby_round(data, e) or rugby_round_for(names[0], names[1])
                       or rugby_round_same_day(events, when))
                _RUGBY_COMP[title] = f"{label} {rnd}".strip()
                uk = when.astimezone(LONDON)
                _log_start(f"Rugby start: {title} -> {uk:%a %d %b %H:%M} UK ({_RUGBY_COMP[title]})")
                return f"Kick-off: {uk:%H:%M}."
    return ""


_RUGBY_COUNT = {}


def event_start_info(title, start):
    """The real start for a 🔴 event's description (see above), or "Coverage from: HH:MM."."""
    t = re.sub(r"(?i)^live\b[\s.,:;!-]*", "", title or "")
    for pat, full in TEAM_NICKNAMES:                               # "BLACKCAPS" -> "New Zealand"
        t = re.sub(pat, full, t)
    info = ""
    try:
        if re.search(r"(?i)\b(test|odi|t20i?)\b", t):
            info = cricket_start(t, start)
        elif re.search(r"(?i)\bf1\b|formula 1", t):
            info = f1_start(t, start)
        elif re.search(r"\b(NFL|NBA|NHL|MLB)\b", t):
            info = us_start(t, start)
        else:
            info = kickoff_info(t, start)
            if not info and re.search(r"\s(?:v|vs\.?)\s", t):
                info = rugby_start(t, start)                # rugby union (28 Oct 2026)
    except Exception as err:                       # a lookup must never stop the guide
        print(f"  NOTE: start time lookup failed for {t!r} ({err})")
    return info or f"Coverage from: {start.astimezone(LONDON):%H:%M}."


# Vague descriptions (2 Nov 2026). Some epgshare feeds (beIN MENA / HK / MY, Champions TV, Ziggo) give only an
# episode or match code as the description ("M4.", "E22.", "MD10.", "Eps 10.", "Dag 4."). The code stays as the
# secondary title; the description becomes a sentence built from the competition name in the title instead:
#   FIP World Cup Qatar 2026 | M4 | M4.   ->   ... | M4 | Coverage of the FIP World Cup Qatar 2026.
# Left alone: match titles ("A vs B" - the competition isn't in the title) and junk titles ("Tue").
VAGUE_CODE = re.compile(r"(?:[A-Za-z]{1,3}\.?\s?\d{1,3}[A-Za-z]?"
                        r"|(?:Eps?|Episode|Dag|Day|Round|Rnd|MD|Matchday|Match|Game|Part|Pt|Leg)\.?\s?\d{1,3})", re.I)
COMP_WORDS = re.compile(r"\b(?:Cup|League|Championships?|Open|Tour|Games|Grand Prix|Trophy|Series|Classic|Masters|"
                        r"Qualifiers?|Euros?|World|Olympics?|Olympic|Slam|Final|Finals|Premiership|Liga|Serie|Bundesliga|"
                        r"Ligue|Super|Challenge|Nations|Invitational)\b|20\d\d", re.I)
SHOW_WORDS = re.compile(r"\b(?:Magazine|Stories|Weekly|Review|Film|Show|Fanzone|Preview|Rewind|Round-?up|Reaction|Talk|Special|Documentary)\b", re.I)
JUNK_TITLE = re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?", re.I)


def fuller_about(title, about):
    """Replace a code-only description with a sentence from the competition name (see VAGUE_CODE)."""
    core = (about or "").strip().rstrip(".!").strip()
    if not core or not VAGUE_CODE.fullmatch(core):
        return about
    comp = re.sub(r"^(?:EN|AR|FR|ES)\s+", "", (title or "").strip())
    comp = re.sub(r"^(?:Eps?\.?|Episode)\s*\d+\s*[:\-\u2013]\s*", "", comp, flags=re.I).strip()
    if (len(comp) < 5 or JUNK_TITLE.fullmatch(comp) or re.search(r"\s(?:vs?\.?)\s", comp, re.I)
            or VAGUE_CODE.fullmatch(comp)):
        return about
    hl = re.fullmatch(r"(.*?)\s*\bHighlights\b\s*(.*)", comp, re.I)
    if hl and (hl.group(1) or hl.group(2)):
        return f"Highlights from the {' '.join(x for x in (hl.group(1), hl.group(2)) if x)}."
    if SHOW_WORDS.search(comp) or not COMP_WORDS.search(comp):
        return f"{comp}."                                   # a programme, not a competition
    return f"Coverage of the {comp}."


def live_title(title, cid="", red=False):
    """Title for a live programme: "LIVE: <title>" (without doubling a leading "Live");
    "🔴 LIVE: <title>" for event channels and (red=True) live events."""
    t = (title or "").strip()
    t = re.sub(r"^🔴\s*", "", t)
    t = re.sub(r"(?i)^live\b[\s.,:;!-]*", "", t) or t
    if red and not cid.startswith(tuple(EVENT_LIVE_PREFIX)):
        return f"🔴 {LIVE_PREFIX}{t}"
    if cid.startswith(tuple(EVENT_LIVE_PREFIX)):       # event-only channels get the 🔴 like event streams
        return f"{EVENT_LIVE_PREFIX[next(k for k in EVENT_LIVE_PREFIX if cid.startswith(k))]}{t}"
    return f"{LIVE_PREFIX}{t}"


def dedupe_sentences(text):
    """Drop sentences that repeat an earlier one, and any "Original title: ..." part:
    "LIVE. UEFA Champions League 2026-27. UEFA Champions League 2026-27." ->
    "LIVE. UEFA Champions League 2026-27."""
    if not text:
        return text
    text = re.sub(r"\s*Original title:.*$", "", text, flags=re.I | re.S).strip()
    parts = re.split(r"(?<=[.!?…])\s+", text)
    seen, out = set(), []
    for part in parts:
        key = re.sub(r"[\W_]+", " ", part).strip().lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(part)
    return " ".join(out).strip()


def fix_names(text):
    """Repair names a source has mangled, e.g. "Rpool" -> "Liverpool"."""
    return re.sub(r"\bRpool\b", "Liverpool", text) if text else text


# Cricket competitions whose name doesn't say "cricket" (20 Nov 2026, user: Premier Sports 2 "LIVE: Abu Dhabi T10:
# Qualifier" needs Cricket in it) -> "Abu Dhabi T10 Cricket: Qualifier". Add other such names here.
CRICKET_COMP_RE = re.compile(r"(?i)\b(Abu Dhabi T10(?: League)?)\b(?!\s+(?:League|Cricket))")   # "...T10: Qualifier" / "...T10 League"
# 20 Nov 2026 (user: Sony Sports Ten 1 "ACC Men's Asia Cup" is cricket): "...-2026 ACC Men's Asia Cup Rising Stars" ->
# "... Rising Stars Cricket"; the feed cuts some titles short ("Asia Cup Rising") - those are completed too.
ASIA_CUP_RE = re.compile(r"(?i)\b(ACC Men['\u2019]s (?:U19 )?Asia Cup|Asia Cup)( Rising(?: Stars)?)?\s*$")


def add_cricket(text):
    if not text or re.search(r"(?i)cricket", text):
        return text
    text = CRICKET_COMP_RE.sub(lambda m: m.group(1) + " Cricket", text)
    if "Cricket" in text:
        return text
    m = ASIA_CUP_RE.search(text)
    if m and (m.group(2) or "ACC" in m.group(1).upper()):      # a bare "Asia Cup" could be another sport (Moto4 Asia Cup)
        return text[:m.start()] + m.group(1) + (" Rising Stars" if m.group(2) else "") + " Cricket"
    return text


# 20 Nov 2026 (user): every listing gets its sport at the start of the title unless the title already says it -
# "🔴 LIVE: Tennis. ATP Finals", "🔴 LIVE: Cricket. WBBL Hobart Hurricanes v Sydney Thunder", "NBA" -> "Basketball. NBA ...".
# The sport is worked out from the title + sub-title (competition names / abbreviations), first matching rule wins.
# NOT done for football (the clubs and leagues are obvious and nearly every listing is football) or motorsport / horse racing
# (the series names say it). To add a sport or a competition, add it to SPORT_RULES; SPORT_SAID says which words in the
# title already name the sport.
SPORT_RULES = [
    ("Tennis", r"\bATP\b|\bWTA\b|Wimbledon|Roland[- ]Garros|French Open|Australian Open|Davis Cup|Billie Jean King|(?i:\bBJK Cup)|Laver Cup|\bNitto\b|Next Gen Finals|Hopman Cup|United Cup|Stockholm Open"),
    ("Cricket", r"\bBaggy Greens\b|\bBlack ?caps\b|\bWhite ?Ferns\b|\b(?:T-?20I?|T-?10|Twenty-?20|Test Twenty|ODIs?|IPL|WBBL|WPL|PSL|CPL|SA20|ILT20|MLC|LPL|BPL|ICC|Ashes|The Hundred|Big Bash|Sheffield Shield|Ranji Trophy|County Championship|Vitality Blast|Metro Bank One.Day Cup|Nepal Premier League|Indian Premier League|Syed Mushtaq Ali|Champions Trophy|Extraaa Innings|Cricbuzz|Lords Of England|Vijay Hazare|Test Match Special)\b|\b\d(?:st|nd|rd|th) (?:Test|ODI|T20I?)\b"),
    ("Netball", r"\bSilver Ferns\b|\bNet Blacks\b|Super Netball|Quad Series"),
    ("Rugby League", r"\bNRLW?\b|State of Origin|\bRLWC\d*\b|Challenge Cup Final"),
    ("Rugby Union", r"Nations Championship|Nations Cup|\bAll Blacks\b|\bWallabies\b|Six Nations|Rugby Championship|\bURC\b|United Rugby|Top 14|Pro D2|Super Rugby|Gallagher (?:PREM|Premiership)|\bPREM\b|\bPWR\b|Premiership Rugby|Champions Cup|Autumn Nations|Nations Series|Bunnings NPC|Currie Cup|Lions Tour"),
    ("Golf", r"\b(?:PGA|LPGA|LIV Golf|DP World Tour|Ryder Cup|Solheim Cup|Presidents Cup|Korn Ferry|Race to Dubai|Q-School|USPGA|Asian Tour|Rolex Grand Final)\b|Open Championship|Augusta National|\bW?TGL\b"),
    ("Basketball", r"\b(?:NBA|WNBA|NBL|WNBL|FIBA|EuroLeague|EuroCup|NCAAB|G League|East Asia Super League|Liga ACB)\b|March Madness|\bRapid League\b"),
    ("American Football", r"\b(?:NFL|NCAAF|CFL|CFP|CFB)\b|Super Bowl|Pro Football Talk|Football Night In America|College GameDay"),
    ("Ice Hockey", r"\b(?:NHL|KHL|AHL|EIHL|IIHF|SHL)\b|Stanley Cup"),
    ("Baseball", r"\b(?:MLB|NPB|KBO)\b|World Series(?! of)"),
    ("Aussie Rules", r"\bAFLW?\b"),
    ("Darts", r"\bPDC\b|World Matchplay"),
    ("Snooker", r"\bWST(?::| Tour| Snooker)|Crucible|Champion of Champions|In The Frame"),
    ("MMA", r"\b(?:UFC|PFL|KSW|Oktagon|Bellator)\b|The Ultimate Fighter|Total Combat|ONE Championship|ONE Fight Night|ONE Friday Fights|Cage Warriors"),
    ("Boxing", r"Matchroom|Queensberry|Top Rank|\bGolden Boy\b|\bKOTV\b"),
    ("Wrestling", r"\b(?:WWE|AEW|TNA)\b|SmackDown|WrestleMania"),
    ("Cycling", r"\bUCI\b|Tour de France|Giro d.Italia|La Vuelta|Paris-Roubaix|Tour Down Under|Arctic Race of Norway|Colocross"),
    ("Athletics", r"Diamond League"),
    ("Volleyball", r"\b(?:VNL|CEV)\b|SuperLega|Volleyball Nations"),
    ("Sailing", r"\bSailGP\b|America.s Cup|Vend[ée]e Globe"),
    ("Show Jumping", r"\bLongines\b|Global Champions|\bGCL\b|\bLGCT\b|\bFEI\b|(?<!ski )(?<!ski-)Jumping World Cup|Show Jumping|Grand Prix Jumping"),
    ("Badminton", r"\bBWF\b|Thomas (?:&|and) Uber"),
    ("Biathlon", r"\bIBU\b"),
    ("Swimming", r"Aquatics|\bFINA\b"),
    ("Handball", r"\bEHF\b"),
]
SPORT_RULES = [(n, re.compile(rx, re.I)) for n, rx in SPORT_RULES]
SPORT_SAID = {
    "Tennis": r"t[eé]nn?is", "Cricket": r"cricket", "Rugby League": r"rugby", "Rugby Union": r"rugby", "Golf": r"golf",
    "Basketball": r"basket|baloncesto|pallacanestro|basquet", "American Football": r"american football|college football|football am[eé]ricain|futebol americano",
    "Ice Hockey": r"hockey", "Baseball": r"baseball|b[eé]isbol|beisebol", "Aussie Rules": r"aussie rules|australian rules",
    "Darts": r"darts", "Snooker": r"snooker", "MMA": r"\bmma\b|martial arts", "Boxing": r"\bbox(?:ing|e|eo|en)\b",
    "Wrestling": r"wrestl|lucha", "Cycling": r"cycl|ciclismo|cyclisme|radsport", "Athletics": r"athletic|atletica|athl[eé]tisme",
    "Volleyball": r"volley|voleibol", "Sailing": r"sail", "Show Jumping": r"show[- ]?jumping|equestri|horse riding|riding:|ridebane|ecuestre|reiten|hípica|hippique", "Badminton": r"badminton", "Biathlon": r"biathl", "Swimming": r"swim|nuoto|natation", "Netball": r"netball", "Handball": r"handball|balonmano",
}
SPORT_SAID = {k: re.compile(v, re.I) for k, v in SPORT_SAID.items()}
LIVE_LEAD_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE[:,]\s*)?)")


# Fixtures ("A v B", "A vs B") with no recognisable competition: if the description names exactly one sport, that is the sport
# ("New Zealand vs India" + "...cricket...", "Atlanta v Boston" + "...golf...").
FIXTURE_RE = re.compile(r"\S\s(?:v|vs\.?)\s\S")
DESC_SPORT = {"Cricket": r"cricket|\bwickets?\b", "Tennis": r"(?<!table )tennis", "Basketball": r"basketball", "American Football": r"american football|\bNFL\b|college football",
              "Ice Hockey": r"ice hockey|\bNHL\b", "Baseball": r"baseball|\bMLB\b", "Golf": r"\bgolf", "Rugby League": r"rugby league", "Handball": r"handball", "Volleyball": r"volleyball", "Netball": r"netball",
              "Aussie Rules": r"\bAFL\b|aussie rules|australian rules"}
DESC_SPORT = {k: re.compile(v, re.I) for k, v in DESC_SPORT.items()}


# 20 Nov 2026 (user: TNT Sports 4 "Leicester v Saracens" - Leicester could be anything, but Saracens only ever means rugby):
# the guide teaches itself which teams belong to which sport. learn_team_sports() runs once over every listing, takes the
# fixtures whose sport is already known (competition name / description), and remembers each team name. A fixture with no
# recognisable competition then takes the sport of either side, provided that team is only ever seen in ONE sport and its name
# does not occur in the football guides (so "Leicester", "Barcelona", "Arsenal" never decide anything - football teams share
# names with other sports). Names are matched on the main word(s): "Saracens Women" = "Saracens W" = "Saracens".
TEAM_SPORT = {}                     # normalised team -> {sport: count}
TEAM_TOTAL = {}                     # normalised team -> how many fixtures it appears in at all (any sport / unknown)
FOOTBALL_TOKENS = set()
SIDE_SPLIT_RE = re.compile(r"\s+(?:v|vs\.?|-|\u2013|/|@)\s+")


def team_key(name):
    name = re.sub(r"(?i)\b(?:women(?:'s)?|w|men(?:'s)?|m|u\d\d|o\d\d|ii|2|b|a)\b\.?", " ", name or "")
    name = re.sub(r"[^\w ]+|\d+", " ", name.lower())
    return " ".join(name.split())


def fixture_sides(body):
    body = re.sub(r"^[^:]{2,40}:\s*", "", body.strip()) if body.count(":") == 1 and re.search(r"\s(?:v|vs\.?)\s", body.split(":", 1)[1]) else body
    body = re.sub(r"\s*[-\u2013(].*$", "", body) if re.search(r"\s(?:v|vs\.?)\s", body) else body
    parts = SIDE_SPLIT_RE.split(body.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    a, b = (team_key(x) for x in parts)
    return (a, b) if a and b and len(a) < 40 and len(b) < 40 else None


def load_football_tokens():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for fn in ("football_epg.xml", "scottish_epg.xml", "TEAMS_epg.xml"):
        for base in (here, os.getcwd()):
            path = os.path.join(base, fn)
            if os.path.exists(path):
                try:
                    txt = open(path, encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                for t in re.findall(r"<title[^>]*>([^<]*)</title>", txt):
                    sides = fixture_sides(re.sub(r"^(?:🔴\s*)?(?:LIVE:\s*)?(?:Next \w+:\s*)?", "", html_unescape(t)))
                    for side in sides or ():
                        FOOTBALL_TOKENS.update(w for w in side.split() if len(w) >= 3)
                break


def html_unescape(t):
    import html
    return html.unescape(t)


GENERIC_CRICKET_RE = re.compile(r"(?i)\bcricket action\b|\bcricket coverage\b")


def share_tnt_text(records):
    """20 Nov 2026 (user: TNT Sports 2 "Cricket. New Zealand v India" live block has only "Test match cricket action from
    New Zealand."; TNT Sports 1 has the day's summary): the same fixture on another TNT Sports channel, starting within 30
    minutes, lends its sentence to the thin description (sub-title + description of the richer listing)."""
    tnt = [r for r in records if r["id"].startswith("UK.TNTSports")]
    for rec in tnt:
        for ev in rec.get("events", []):
            d = (ev.get("desc") or "").strip()
            if ev.get("sub") or not d or len(d) > 90 or not GENERIC_CRICKET_RE.search(d):
                continue
            sides = fixture_sides(LIVE_LEAD_RE.sub("", ev.get("title") or ""))
            if not sides:
                continue
            best = None
            for other in tnt:
                if other is rec:
                    continue
                for o in other.get("events", []):
                    if abs((o["start"] - ev["start"]).total_seconds()) > 1800:
                        continue
                    if fixture_sides(LIVE_LEAD_RE.sub("", o.get("title") or "")) != sides:
                        continue
                    text = " ".join(x.strip() for x in (o.get("sub") or "", o.get("desc") or "") if x and x.strip())
                    if len(text) > len(d) + 30 and (best is None or len(text) > len(best)) and not GENERIC_CRICKET_RE.search(o.get("desc") or "x"):
                        best = text
            if best:
                ev["desc"] = best


def learn_team_sports(records):
    TEAM_SPORT.clear()
    TEAM_TOTAL.clear()
    FOOTBALL_TOKENS.clear()
    load_football_tokens()
    for rec in records:
        for ev in rec.get("events", []):
            title, sub, desc = ev.get("title") or "", ev.get("sub") or "", ev.get("desc") or ""
            sp = add_sport(title, sub, rec["id"], desc, learn=True)
            sides = fixture_sides(LIVE_LEAD_RE.sub("", title))
            for side in sides or ():
                TEAM_TOTAL[side] = TEAM_TOTAL.get(side, 0) + 1
            if sp:
                for side in sides or ():
                    TEAM_SPORT.setdefault(side, {}).setdefault(sp, 0)
                    TEAM_SPORT[side][sp] += 1


COUNTRY_RE = re.compile(r"(?i)^(?:usa|uk|uae|england|scotland|wales|ireland|northern ireland|france|germany|spain|italy|portugal|netherlands|belgium|"
                        r"switzerland|austria|poland|czechia|czech republic|slovakia|hungary|romania|bulgaria|greece|turkey|ukraine|russia|sweden|norway|"
                        r"denmark|finland|iceland|croatia|serbia|slovenia|bosnia|montenegro|albania|kosovo|georgia|armenia|israel|egypt|morocco|tunisia|"
                        r"algeria|nigeria|ghana|senegal|south africa|kenya|canada|mexico|brazil|argentina|chile|colombia|uruguay|paraguay|peru|ecuador|"
                        r"venezuela|bolivia|costa rica|panama|jamaica|guatemala|honduras|cuba|japan|china|korea|south korea|india|pakistan|bangladesh|"
                        r"sri lanka|nepal|iran|iraq|saudi arabia|qatar|australia|new zealand|fiji|samoa|tonga|hong kong|singapore|malaysia|thailand|"
                        r"indonesia|philippines|vietnam|kazakhstan|uzbekistan|faroe islands|luxembourg|malta|cyprus|estonia|latvia|lithuania|belarus|"
                        r"moldova|north macedonia|united states|great britain|west indies)$")
FOOTBALL_HINT_RE = re.compile(r"(?i)africa cup of nations|afcon|\bcaf\b|concacaf|uefa|fifa|conmebol|nations league|bundesliga|la ?liga|serie [ab]|ligue [12]|premier league|eredivisie|"
                              r"\bcopa\b|\bfc\b|football|soccer|world cup qual|friendl")


def team_sport(body):
    if FOOTBALL_HINT_RE.search(body):
        return None
    sides = fixture_sides(body)
    if not sides:
        return None
    found = set()
    for side in sides:
        seen = TEAM_SPORT.get(side)
        if not seen or len(seen) != 1 or COUNTRY_RE.match(side):
            continue
        n = next(iter(seen.values()))
        if n < 2 or n < 0.75 * TEAM_TOTAL.get(side, n):     # must be (nearly) always seen in that one sport
            continue
        if any(w in FOOTBALL_TOKENS for w in side.split() if len(w) >= 3):
            continue
        found.add(next(iter(seen)))
    return found.pop() if len(found) == 1 else None


# Names that are never anything but this sport, whatever the title looks like (checked against the description too).
# 20 Nov 2026 (user, TNT Sports 4 "LIVE: Brisbane W v Melbourne C W"): A-League fixtures get "Australian A-League Football." at the
# start, full club names, and "Women" after each side when it is the women's league (a trailing "W" / "Women", or the
# secondary title / description says A-League Women). Highlights shows and anything that is not a "Team v Team" fixture are left.
ALEAGUE_TEAMS = {"adelaide": "Adelaide United", "adelaide u": "Adelaide United", "adelaide utd": "Adelaide United", "adelaide united": "Adelaide United",
                 "auckland": "Auckland FC", "auckland fc": "Auckland FC", "brisbane": "Brisbane Roar", "brisbane roar": "Brisbane Roar",
                 "canberra": "Canberra United", "canberra utd": "Canberra United", "canberra united": "Canberra United",
                 "cc mariners": "Central Coast Mariners", "central coast": "Central Coast Mariners", "mariners": "Central Coast Mariners",
                 "central coast mariners": "Central Coast Mariners", "macarthur": "Macarthur FC", "macarthur fc": "Macarthur FC",
                 "melbourne c": "Melbourne City", "melb city": "Melbourne City", "melbourne city": "Melbourne City",
                 "melbourne v": "Melbourne Victory", "melb victory": "Melbourne Victory", "melbourne vic": "Melbourne Victory",
                 "melb vic": "Melbourne Victory", "melbourne victory": "Melbourne Victory",
                 "newcastle": "Newcastle Jets", "newcastle jets": "Newcastle Jets", "perth": "Perth Glory", "perth glory": "Perth Glory",
                 "sydney fc": "Sydney FC", "sydney": "Sydney FC", "western sydney": "Western Sydney Wanderers", "wsw": "Western Sydney Wanderers",
                 "wanderers": "Western Sydney Wanderers", "western sydney wanderers": "Western Sydney Wanderers",
                 "wellington": "Wellington Phoenix", "phoenix": "Wellington Phoenix", "wellington phoenix": "Wellington Phoenix"}
ALEAGUE_RE = re.compile(r"(?i)A-?League")
ALEAGUE_WOMEN_RE = re.compile(r"(?i)A-?League Women|Women.s A-?League")
ALEAGUE_FIXTURE_RE = re.compile(r"^(?P<a>.+?)\s+(?:v|vs\.?)\s+(?P<b>.+?)(?P<tail>\s+(?:Ext\.?\s+)?Highlights)?$")


def _aleague_side(raw):
    m = re.match(r"^(.*?)(?:\s+(W|Women|Women's))?$", raw.strip())
    key = re.sub(r"[.\s]+", " ", m.group(1).lower()).strip()
    return ALEAGUE_TEAMS.get(key), bool(m.group(2))


def a_league(title, sub, desc):
    if not title or not (ALEAGUE_RE.search(sub or "") or ALEAGUE_RE.search((desc or "")[:300])):
        return title
    lead = LIVE_LEAD_RE.match(title)
    body = title[lead.end():]
    if re.search(r"(?i)football|A-?League", body):
        return title
    m = ALEAGUE_FIXTURE_RE.match(body.strip())
    if not m or m.group("tail"):
        return title
    (a, wa), (b, wb) = _aleague_side(m.group("a")), _aleague_side(m.group("b"))
    if not a or not b:
        return title
    women = wa or wb or bool(ALEAGUE_WOMEN_RE.search(f"{sub or ''} {(desc or '')[:300]}"))
    if women:
        a, b = f"{a} Women", f"{b} Women"
    return f"{lead.group(1)}Australian A-League Football. {a} v {b}"


CRICKET_BARE_RE = re.compile(r"(?i)^(?:Test(?: Mini| Classic| Wrap| Day)?|ODIs?(?: Mini)?|T20Is?(?: Mini)?)(?:\s*[-:].*)?$")
# 20 Nov 2026 (user, TNT Sports 2 "LIVE: NWSL Final: Spirit v Current"): NWSL fixtures -> "National Women's Soccer League. Washington Spirit v
# Kansas City Current" with the round ("Final", "Semi-final") as the secondary title. Same layout as the A-League.
NWSL_TEAMS = {"washington": "Washington Spirit", "spirit": "Washington Spirit", "washington spirit": "Washington Spirit",
              "kansas": "Kansas City Current", "kansas city": "Kansas City Current", "current": "Kansas City Current", "kc current": "Kansas City Current",
              "kansas city current": "Kansas City Current", "utah": "Utah Royals", "royals": "Utah Royals", "utah royals": "Utah Royals", "utah royals fc": "Utah Royals",
              "gotham": "Gotham FC", "gotham fc": "Gotham FC", "ny/nj gotham": "Gotham FC", "angel city": "Angel City FC", "angel city fc": "Angel City FC",
              "bay": "Bay FC", "bay fc": "Bay FC", "chicago": "Chicago Stars", "stars": "Chicago Stars", "chicago stars": "Chicago Stars",
              "houston": "Houston Dash", "dash": "Houston Dash", "houston dash": "Houston Dash", "north carolina": "North Carolina Courage",
              "courage": "North Carolina Courage", "nc courage": "North Carolina Courage", "orlando": "Orlando Pride", "pride": "Orlando Pride",
              "orlando pride": "Orlando Pride", "portland": "Portland Thorns", "thorns": "Portland Thorns", "portland thorns": "Portland Thorns",
              "louisville": "Racing Louisville", "racing louisville": "Racing Louisville", "san diego": "San Diego Wave", "wave": "San Diego Wave",
              "san diego wave": "San Diego Wave", "seattle": "Seattle Reign", "reign": "Seattle Reign", "seattle reign": "Seattle Reign",
              "boston": "Boston Legacy", "boston legacy": "Boston Legacy", "denver": "Denver Summit", "denver summit": "Denver Summit"}
NWSL_RE = re.compile(r"^NWSL(?:\s+(?P<rnd>Final|Championship|Semi-?finals?|Quarter-?finals?|Playoffs?))?\s*:\s*(?P<a>.+?)\s+(?:v|vs\.?)\s+(?P<b>.+?)(?P<tail>\s+Highlights)?$", re.I)


def nwsl(title, sub, desc):
    if not title:
        return title, sub
    lead = LIVE_LEAD_RE.match(title)
    m = NWSL_RE.match(title[lead.end():].strip())
    if not m or m.group("tail"):
        return title, sub
    a, b = (NWSL_TEAMS.get(re.sub(r"[.\s]+", " ", m.group(x).lower()).strip()) for x in ("a", "b"))
    if not a or not b:
        return title, sub
    rnd = m.group("rnd") or ""
    if not rnd:
        d = re.search(r"(?i)\b(semi-?final|quarter-?final|final)\b", (desc or "")[:200])
        rnd = d.group(1) if d else ""
    rnd = re.sub(r"(?i)^semi-?final.*", "Semi-final", rnd) if rnd else rnd
    rnd = re.sub(r"(?i)^quarter-?final.*", "Quarter-final", rnd)
    rnd = rnd.capitalize() if rnd and rnd.lower() in ("final", "playoffs", "playoff", "championship") else rnd
    new_sub = (sub or "").strip() or rnd
    return f"{lead.group(1)}National Women's Soccer League. {a} v {b}", new_sub


# 20 Nov 2026 (user: Hub Premier channels): StarHub writes titles in CAPITALS ("PL STORIES", "FANTASY SHOW - FRI 20 NOV") - fix_caps now runs on
# SG.HubPremier* too (PL / MW / GB kept as capitals) - and the Classic Match / Premier League three-letter codes ("NEW v ARS") become club names.
PL_TLA = {"ARS": "Arsenal", "AVL": "Aston Villa", "BOU": "Bournemouth", "BRE": "Brentford", "BHA": "Brighton & Hove Albion", "BUR": "Burnley",
          "CHE": "Chelsea", "COV": "Coventry City", "CRY": "Crystal Palace", "EVE": "Everton", "FUL": "Fulham", "HUL": "Hull City", "IPS": "Ipswich Town",
          "LEE": "Leeds United", "LEI": "Leicester City", "LIV": "Liverpool", "MCI": "Manchester City", "MUN": "Manchester United", "NEW": "Newcastle United",
          "NFO": "Nottingham Forest", "SOU": "Southampton", "SUN": "Sunderland", "TOT": "Tottenham Hotspur", "WHU": "West Ham United",
          "WOL": "Wolverhampton Wanderers", "WBA": "West Bromwich Albion", "BLB": "Blackburn Rovers", "WIG": "Wigan Athletic", "MID": "Middlesbrough",
          "NOR": "Norwich City", "STK": "Stoke City", "SWA": "Swansea City", "WAT": "Watford", "CAR": "Cardiff City", "BOL": "Bolton Wanderers",
          "POR": "Portsmouth", "SHU": "Sheffield United", "QPR": "Queens Park Rangers", "REA": "Reading", "BIR": "Birmingham City", "DER": "Derby County"}
PL_PRODUCTIONS = ("SG.HubPremier", "NZ.SkySport8NZ")        # channels carrying the Premier League Productions shows in capitals (20 Nov 2026)
PL_TLA_RE = re.compile(r"\b([A-Za-z]{3}) v ([A-Za-z]{3})\b")     # fix_caps runs first: "NEW v ARS" has already become "New v Ars"


def hub_premier_codes(cid, text):
    if not cid.startswith(PL_PRODUCTIONS) or not text:
        return text
    text = re.sub(r"(?<=[a-z]) s (?=[A-Za-z])", "'s ", text)                     # source drops the apostrophe: "Matic s journey"
    text = re.sub(r"(?<=\w) LIVE$", "", text) if cid.startswith("NZ.") else text   # "Newcastle United v Arsenal LIVE" under a 🔴 LIVE: title
    text = re.sub(r"\((?i:[a-z]{3})\)", lambda m: f"({PL_TLA[m.group(0)[1:-1].upper()]})" if m.group(0)[1:-1].upper() in PL_TLA else m.group(0), text)   # "(LEI)"
    return PL_TLA_RE.sub(lambda m: f"{PL_TLA[m.group(1).upper()]} v {PL_TLA[m.group(2).upper()]}" if m.group(1).upper() in PL_TLA and m.group(2).upper() in PL_TLA else m.group(0), text)


# 20 Nov 2026 (user: "remove the current date if the title / description has it"): a date that is the programme's OWN date is noise
# ("FANTASY SHOW - FRI 20 NOV", "NFL Blitz - Friday 20 November 2026", "Show jumping: Global Champions Tour: 20.11.2026 6:25pm.", a
# secondary title that is just "Saturday 21 November 2026"). Only a date equal to the day the programme starts (channel's own day, UK day
# or UTC day) is removed; other dates (a match played on another day, "2016/2017") stay. Never emptied: if removing leaves nothing, the
# original text is kept (and a description is never blanked). "Coming up" blocks keep their dates - they are the point of those blocks.
_MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
_DAY = r"(?:(?:Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)[a-z]*\.?,?\s+)?"
_MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
OWN_DATE_RE = re.compile(
    rf"(?P<text>\b{_DAY}(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m1>{_MON})\b\.?(?:,?\s+(?P<y1>\d{{4}}))?"       # Fri 20 Nov / Friday 20 November 2026
    rf"|\b{_DAY}(?P<m2>{_MON})\.?\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(?P<y2>\d{{4}}))?"                # Nov 20, 2026
    rf"|\b(?P<d3>\d{{1,2}})[./](?P<m3>\d{{1,2}})[./](?P<y3>\d{{4}}|\d{{2}})\b"                                          # 20.11.2026 / 20/11/26
    rf"|\b(?P<y4>\d{{4}})-(?P<m4>\d{{2}})-(?P<d4>\d{{2}})\b)"                                                          # 2026-11-20
    rf"(?:\s+(?:at\s+)?\d{{1,2}}(?::\d{{2}})?\s*(?:am|pm)\b\.?)?", re.I)                                              # optional clock time after it
_SEP = r"[\s\-\u2013\u2014:|,.]*"


def _own_date_hit(m, days, year):
    g = m.groupdict()
    try:
        if g["d1"]:
            d, mo, y = int(g["d1"]), _MONTHS[g["m1"][:3].lower()], int(g["y1"] or year)
        elif g["m2"]:
            d, mo, y = int(g["d2"]), _MONTHS[g["m2"][:3].lower()], int(g["y2"] or year)
        elif g["d3"]:
            d, mo, y = int(g["d3"]), int(g["m3"]), int(g["y3"])
            y += 2000 if y < 100 else 0
        else:
            d, mo, y = int(g["d4"]), int(g["m4"]), int(g["y4"])
        return date(y, mo, d) in days
    except (ValueError, KeyError):
        return False


def drop_own_date(text, days, year, keep_if_empty=True):
    """Removes the programme's own date where it stands apart: at the start, at the end, in brackets, or between separators
    ("Title - FRI 20 NOV", "FRI 20 NOV - Join the crew", "Show (20.11.2026)"). A date in the middle of a sentence
    ("On Friday, November 20, 2026, five matches...") is left alone."""
    if not text or not days:
        return text
    out, removed = text, False
    seps = ".-\u2013\u2014:|,"
    for m in list(OWN_DATE_RE.finditer(text))[::-1]:
        if not _own_date_hit(m, days, year):
            continue
        before, after = out[:m.start()], out[m.end():]
        bs, as_ = before.rstrip(), after.lstrip()
        if re.search(r"\(\s*$", before) and re.match(r"^\s*\)", after):                 # "(DATE)"
            new = re.sub(r"\(\s*$", "", before).rstrip() + re.sub(r"^\s*\)", "", after)
        elif not bs:                                                                       # at the start
            new = after.lstrip(" " + seps)
        elif not as_.strip(" " + seps):                                                    # at the end
            new = bs.rstrip(" " + seps)
        elif bs[-1] in seps and (as_[0] in seps or as_[0] == "("):                         # between separators
            new = (bs.rstrip(" -\u2013\u2014:|,") + (" " if bs[-1] in ".," else " - ") if bs.rstrip(" -\u2013\u2014:|,") else "") + as_.lstrip(" -\u2013\u2014:|,")
            if bs[-1] in "." or as_[0] == "(":
                new = (bs.rstrip(" -\u2013\u2014:|,") if as_[0] == "(" else bs) + " " + as_.lstrip(" -\u2013\u2014:|,.")
        else:
            continue                                                                       # inside a sentence: leave it
        out, removed = new.strip(), True
    if not removed:
        return text
    out = re.sub(r"\s{2,}", " ", out).strip(" -\u2013:|,")
    if not re.search(r"\w", out):                  # nothing but the date was there
        return text if keep_if_empty else ""
    return out


_CUR_TZ = None


def own_dates(start):
    days = {start.astimezone(timezone.utc).date(), start.astimezone(LONDON).date()}
    if _CUR_TZ is not None:
        days.add(start.astimezone(_CUR_TZ).date())
    return days


# 20 Nov 2026 (user, Sky Sport NZ "LIVE: BLACKCAPS v India"): BLACKCAPS is the New Zealand cricket team -> "New Zealand" (WHITE FERNS ->
# "New Zealand Women"). "BLACKCAPS v India" + "BLACKCAPS v India: 1st Test D3 Highlights" -> title "Cricket. New Zealand v India Highlights",
# sub-title "1st Test, Day 3" (D3 = Day 3, L2H = Last Two Hours, HLs = Highlights); the repeated start of the description is dropped.
NZ_TEAM_RE = re.compile(r"(?i)\b(?:the\s+)?black ?caps\b")
NZ_WOMEN_RE = re.compile(r"(?i)\b(?:the\s+)?white ?ferns\b")
NZ_CRICKET_SUB_RE = re.compile(r"^(?P<match>.+?)(?:\s+D(?P<day>\d))?(?:\s+(?P<tail>Highlights|HLs?|L2H|Wrap))?$")
NZ_TAILS = {"highlights": " Highlights", "hl": " Highlights", "hls": " Highlights", "l2h": " Last Two Hours", "wrap": " Wrap"}


INTL_CRICKET_RE = re.compile(r"(?i)^(?:intl|international)\s+cricket\s*:\s*")


def nz_cricket(cid, title, sub, desc):
    """Sky Sport NZ cricket: "BLACKCAPS v India" / "Intl Cricket: Australia v England" with the sub-title "<teams>: 2nd T20 Highlights"
    -> title "Cricket. <teams> Highlights", sub-title "2nd T20" (Test days: "1st Test, Day 3")."""
    if not title:
        return title, sub, desc
    lead = LIVE_LEAD_RE.match(title)
    body = title[lead.end():]
    intl = bool(INTL_CRICKET_RE.match(body))
    if not (intl or NZ_TEAM_RE.search(title) or NZ_WOMEN_RE.search(title)):
        return title, sub, desc
    teams = INTL_CRICKET_RE.sub("", body).strip()
    if sub and sub.startswith(teams + ":"):
        rest = sub[len(teams) + 1:].strip()
        m = NZ_CRICKET_SUB_RE.match(rest)
        if m and re.search(r"(?i)\b(?:test|odi|t20i?)\b", m["match"]):
            tail = NZ_TAILS.get((m["tail"] or "").lower(), "")
            new_sub = m["match"] + (f", Day {m['day']}" if m["day"] else "")
            if desc and desc.startswith(sub):                       # "BLACKCAPS v India: 1st Test D3. LIVE coverage..." - repeated sentence
                desc = desc[len(sub):].lstrip(". ").strip() or desc
            title, sub = f"{lead.group(1)}Cricket. {teams}{tail}", new_sub
    elif intl:
        title = f"{lead.group(1)}Cricket. {teams}"
    fix = lambda t: NZ_WOMEN_RE.sub("New Zealand Women", NZ_TEAM_RE.sub("New Zealand", t)) if t else t
    return fix(title), fix(sub), fix(desc)


# 20 Nov 2026 (user): national-team nicknames written as the country - Wallabies (rugby union) -> Australia, Baggy Greens (Australia Men's
# cricket) -> Australia Men. (Silver Ferns, All Blacks and Springboks stay as they are - user, 20 Nov 2026.) Runs AFTER the sport prefix, which
# reads the nickname to know the sport. BLACKCAPS / WHITE FERNS are handled in nz_cricket().
NICKNAMES = [(re.compile(r"(?i)\b(?:the\s+)?wallabies\b"), "Australia"), (re.compile(r"(?i)\b(?:the\s+)?baggy greens\b"), "Australia Men")]


# 21 Nov 2026 (user, "between the New Zealand and India"): safety net - "the" directly in front of a bare country / team name that is followed by
# and / v / vs / at / a full stop or comma or the end of the text ("the New Zealand and India", "beat the Australia.") is dropped.
THE_COUNTRY_RE = re.compile(r"(?i)\bthe\s+((?:New Zealand|Australia|South Africa|England|Ireland|India|Pakistan|Sri Lanka|Bangladesh|West Indies)"
                            r"(?:\s+(?:Women|Men))?(?=\s+(?:and|v|vs\.?|at)\b|\s*[.,;:!]|\s*$))")


def national_names(text):
    if not text:
        return text
    for rx, name in NICKNAMES:
        text = rx.sub(name, text)
    return THE_COUNTRY_RE.sub(r"\1", text)             # a left-over "the" in front of a bare country name (21 Nov 2026, user)


# 20 Nov 2026 (user, Sky Sport NZ "LIVE: Ireland v South Africa" + "NC"): the secondary title "NC" is the Nations Championship - written out, with the
# round from the description ("Round 6 of the Nations Championship") - and the repeated "NC." at the start of the description goes.
NC_DESC_RE = re.compile(r"^NC\.\s*")
NC_ROUND_RE = re.compile(r"(?i)\bRound (\d{1,2}) of (?:the )?Nations Championship")


# 21 Nov 2026 (user, Sky Sport NZ "whai v pouakai - Rapid League"): the Rapid League is New Zealand Basketball. The sport comes from SPORT_RULES; here the
# competition is written out ("New Zealand Basketball, Rapid League") and lower-case team names are capitalised ("Whai v Pouakai").
NZ_RAPID_RE = re.compile(r"(?i)^(?P<lead>(?:🔴\s*)?(?:LIVE[:,]\s*)?)(?P<teams>.+?)\s*[-\u2013:]\s*Rapid League\s*$")
NZ_RAPID_SUB = "New Zealand Basketball, Rapid League"


def _cap_teams(t):
    return " ".join(w if w.lower() in ("v", "vs", "vs.", "at") else w.capitalize() for w in t.split())


def nz_basketball(cid, title, sub, desc):
    if not cid.startswith("NZ.") or not title:
        return title, sub, desc
    m = NZ_RAPID_RE.match(title)
    if m:
        teams = m["teams"].strip()
        title = f"{m['lead']}{_cap_teams(teams) if teams.islower() else teams}"
        sub = NZ_RAPID_SUB
    elif (sub or "").strip().lower() == "rapid league":
        sub = NZ_RAPID_SUB
        lead = LIVE_LEAD_RE.match(title)
        body = title[lead.end():]
        if body.islower():
            title = lead.group(1) + _cap_teams(body)
    return title, sub, desc


# 21 Nov 2026 (user, Sky Sport 3 NZ "Georgia v USA - NC", Sky Sport 4 NZ "Portugal v Uruguay - NC"): "NC" is also the World Rugby Nations Cup (the second
# division: Canada, Chile, Georgia, Hong Kong China, Portugal, Romania, Samoa, Spain, Tonga, Uruguay, USA, Zimbabwe). It is the Nations Cup when the description
# says so, or when both teams in the title are Nations Cup teams and the description does not say Nations Championship.
NATIONS_CUP_TEAMS = {"canada", "chile", "georgia", "hong kong china", "hong kong", "portugal", "romania", "samoa", "spain", "tonga", "uruguay", "usa",
                     "united states", "zimbabwe"}
NATIONS_CHAMP_TEAMS = {"england", "france", "ireland", "italy", "scotland", "wales", "argentina", "australia", "new zealand", "south africa", "fiji", "japan"}


# 21 Nov 2026 (user): Sky NZ "NSW v Queensland D1" + "SS" = "New South Wales v Queensland", "Sheffield Shield, Day 1"
SHIELD_TEAMS = {"nsw": "New South Wales", "qld": "Queensland", "vic": "Victoria", "wa": "Western Australia", "sa": "South Australia",
                "tas": "Tasmania"}
SHIELD_TITLE_RE = re.compile(r"^(?P<lead>(?:🔴\s*)?(?:LIVE[:,]\s*)?)(?P<a>.+?)\s+v\s+(?P<b>.+?)\s+D(?P<d>\d)(?:\s*-\s*SS)?$")


def nz_shield(cid, title, sub, desc):
    if not cid.startswith("NZ."):
        return title, sub, desc
    m = SHIELD_TITLE_RE.match((title or "").strip())
    if not m or not ((sub or "").strip() == "SS" or re.search(r"-\s*SS$", title.strip())):
        return title, sub, desc
    a, b = (SHIELD_TEAMS.get(x.strip().lower(), x.strip()) for x in (m["a"], m["b"]))
    d = re.sub(r"^SS\.\s*", "", (desc or "").strip()) or desc
    return f"{m['lead']}{a} v {b}", f"Sheffield Shield, Day {m['d']}", d


# 21 Nov 2026 (user): Sky NZ "Harlequins v Bristol Bears" + "PWR" is Premiership Women's Rugby
PWR_ROUND_RE = re.compile(r"(?i)\bRound (\d{1,2}) of Premiership Women.s Rugby")


def nz_pwr(cid, title, sub, desc):
    if not cid.startswith("NZ.") or (sub or "").strip() != "PWR":
        return title, sub, desc
    d = re.sub(r"^PWR\.\s*", "", (desc or "").strip()) or desc
    r = PWR_ROUND_RE.search(d or "")
    return title, "Premiership Women's Rugby" + (f", Round {int(r.group(1))}" if r else ""), d


# 21 Nov 2026 (user): TNT Sports' placeholder "LIVE: This is TNT Sports 5" -> "LIVE: TNT Sports 5", and the web address is taken out of its description
TNT_PLACEHOLDER_RE = re.compile(r"^(?P<lead>(?:🔴\s*)?(?:LIVE[:,]\s*)?)This is (?P<name>TNT Sports \d)\s*$", re.I)
TNT_WEB_RE = re.compile(r"\s*For more information,? (?:please )?visit tntsports\.co\.uk\.?", re.I)


def tnt_placeholder(cid, title, sub, desc):
    m = TNT_PLACEHOLDER_RE.match((title or "").strip())
    if not m:
        return title, sub, desc
    name = m["name"]
    # 21 Nov 2026 (user): TNT Sports 5+ are overflow channels, only on air for the odd live event
    return (f"{m['lead']}{name}", sub,
            f"{name} is an overflow channel. It shows live events when TNT Sports 1 to 4 are busy, and is not on air 24/7.")


def nz_nations(cid, title, sub, desc):
    if not cid.startswith("NZ.") or (sub or "").strip() != "NC":
        return title, sub, desc
    d = desc or ""
    body = LIVE_LEAD_RE.sub("", title or "", count=1)
    sides = [x.strip().lower() for x in re.split(r"\s+v(?:s\.?)?\s+", body, maxsplit=1)] if re.search(r"\sv(?:s\.?)?\s", body) else []
    if re.search(r"(?i)Nations Championship", d):
        name = "Nations Championship"
    elif re.search(r"(?i)Nations Cup", d) or (len(sides) == 2 and all(x in NATIONS_CUP_TEAMS for x in sides)):
        name = "Nations Cup"
    elif len(sides) == 2 and all(x in NATIONS_CHAMP_TEAMS for x in sides):
        name = "Nations Championship"                       # both sides are Nations Championship teams
    else:
        return title, sub, desc
    r = re.search(r"(?i)\bRound (\d{1,2}) of (?:the )?Nations (?:Championship|Cup)", d)
    return title, name + (f", Round {int(r.group(1))}" if r else ""), NC_DESC_RE.sub("", d.strip()) or desc


# 20 Nov 2026 (user, Sky Sport NZ): the Women's Super League was named three times (sub-title, start of the description, inside the description).
# Now: title "Football. Man City v Spurs", sub-title "Women's Super League, Round 11", description "Highlights of the match between Manchester City
# and Tottenham Hotspur at Joie Stadium in Manchester." (club names in the title are left as Sky writes them).
WSL_DESC_RE = re.compile(r"(?i)\bthe Women.s Super League Round (\d{1,2}) match")


def nz_wsl(cid, title, sub, desc):
    if not cid.startswith("NZ.") or (sub or "").strip() != "Women's Super League" or not desc:
        return title, sub, desc
    d = re.sub(r"^Women's Super League\.\s*", "", desc.strip())
    r = WSL_DESC_RE.search(d)
    if r:
        d = WSL_DESC_RE.sub("the match", d, count=1)
        sub = f"Women's Super League, Round {int(r.group(1))}"
    lead = LIVE_LEAD_RE.match(title)
    if not re.search(r"(?i)football", title):
        title = f"{lead.group(1)}Football. {title[lead.end():]}"
    return title, sub, d or desc


TEAM_WORD_RE = re.compile(r"\b([A-Z][\w'-]+)\s+(?:Rugby|Cricket)(?:\s+Club)?(?=\s*$|\s+(?:v|vs\.?)\s|\s*[-(])")
DESC_STRONG = {"Show Jumping": re.compile(r"(?i)show[- ]jumping"),
               "Rugby Union": re.compile(r"(?i)PREM Rugby|Gallagher PREM|Premiership Women.s Rugby|Premiership Rugby|Rugby Union")}


def add_sport(title, sub, cid="", desc="", learn=False):
    if not title:
        return title
    m = LIVE_LEAD_RE.match(title)
    body = title[m.end():]
    hay = f"{body} {sub or ''}"
    sport = "Cricket" if CRICKET_BARE_RE.match(body) else None
    if sport is None and cid.startswith("NZ.") and re.match(r"(?i)^(?:the\s+)?breakdown\b", body):
        sport = "Rugby Union"                          # Sky Sport NZ's rugby talk show (ESPN's "The Breakdown" is NFL - not touched)     # Fox: "Test", "Test - NZL v IND", "Test Mini", "Test Wrap"
    for name, rx in ([] if sport else SPORT_RULES):
        if rx.search(hay):
            sport = name
            break
    if sport is None and desc:
        if not re.search(r"(?i)pentathlon|triathlon|racing|^This is\b", hay):
            sport = next((n for n, rx in DESC_STRONG.items() if rx.search(desc[:400])), None)
    if sport is None and desc and FIXTURE_RE.search(body):
        found = [n for n, rx in DESC_SPORT.items() if rx.search(desc[:400])]
        if len(found) == 1:
            sport = found[0]
    if sport is None and not learn and TEAM_SPORT and FIXTURE_RE.search(body):
        sport = team_sport(hay)                        # "Leicester v Saracens": Saracens only ever appear in rugby
    if sport is None and not (CRICKET_COMP_RE.search(hay) or (ASIA_CUP_RE.search(hay) and re.search(r"(?i)ACC|Rising", hay))):
        return None if learn else title
    sport = sport or "Cricket"
    if learn:
        return sport
    said_in = TEAM_WORD_RE.sub(r"\1", body)              # "Bath Rugby" is a club name, not the sport being said
    if SPORT_SAID[sport].search(said_in) or said_in.lower().startswith(sport.lower()):
        return title
    return f"{m.group(1)}{sport}. {body}"


# Racing TV (20 Nov 2026, user): the race meetings go in the title - "Racing Replay" + "...action from Warwick."
# -> "Racing Replay: Warwick"; "LIVE: Racing" + "...from Catterick and Meydan." -> "LIVE: Racing: Catterick and Meydan".
RACING_MEETING_RE = re.compile(r"(?i)\bracing action from ([^.]+?)\s*\.")
RACING_TITLE_RE = re.compile(r"(?i)^(?:🔴\s*)?(?:live:\s*)?(?:irish )?racing(?: replay)?$|^(?:🔴\s*)?(?:live:\s*)?the \w+ club$")
# Sky Sports Racing (20 Nov 2026, user: same as Racing TV). Per programme name, a pattern that finds the venue(s) in the
# description. Only a clear list is used: "around the UK" / "Australia" / "the USA" and Raceday double-headers
# (several courses with different presenters) are left as they are. More than 3 venues -> first 3 + "and more".
SKY_RACING_PATTERNS = {
    "australian racing":    r"racing from ([^.]+?)\s*\.",
    "international raceday": r"racing from ([^.]+?)(?:\s*\.|\s+and a look|\s+as well)",
    "stateside":            r"racing from ([^.]+?)\s*\.",
    "raceday":              r"action (?:live )?from ([A-Z][\w'\u2019.-]*(?: [A-Z][\w'\u2019.-]*)*)(?= with| featuring|\.|,|$)",
    "monday night racing":  r"\bwith ([A-Z][^.]+?)\s*\.",
    "the box seat":         r"racing from ([^.]+?)\s*\.",
}
NOT_VENUES = re.compile(r"(?i)^(australia|the usa|usa|the uk|around the uk|the us|america)$")


def _venue_list(raw):
    parts = [p.strip() for p in re.split(r",\s*|\s+and\s+|\s+&(?:amp;)?\s+", raw) if p.strip()]
    if not parts or any(NOT_VENUES.match(p) for p in parts):
        return ""
    if len(parts) > 3:
        return ", ".join(parts[:3]) + " and more"
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def racing_meetings(cid, title, desc):
    if cid not in ("UK.RacingTV", "UK.SkySportsRacing") or not title or not desc:
        return title
    base = re.sub(r"(?i)^(?:🔴\s*)?(?:live:\s*)?", "", title.strip())
    if ":" in base:
        return title
    if cid == "UK.RacingTV":
        m = RACING_MEETING_RE.search(desc)
        if not m or not RACING_TITLE_RE.match(title.strip()):
            return title
        raw = m.group(1)
    else:
        pat = SKY_RACING_PATTERNS.get(base.lower())
        if not pat or (base.lower() == "raceday" and re.search(r"(?i)double-header|\bevening card\b", desc)):
            return title
        m = re.search(pat, desc)
        if not m:
            return title
        raw = m.group(1)
    venues = _venue_list(raw)
    return f"{title.strip()}: {venues}" if venues else title


# 20 Nov 2026 (user, ESPN: "LIVE: 2026 Nitto ATP Finals"): ATP listings that don't say Tennis get it, at the start
# ("LIVE: Tennis 2026 Nitto ATP Finals", "Tennis ATP Tour: This Week"). Not on Tennis channels (it is obvious there).
ATP_NAME_RE = re.compile(r"\bATP(?:(?i: Masters 1000| Finals| Final| Tour| \d{3,4}))?\b(?!/)")
TENNIS_WORD_RE = re.compile(r"(?i)\bt[eé]nn?is\w*")


def add_tennis(text, cid=""):
    if not text or "tennis" in cid.lower() or TENNIS_WORD_RE.search(text):
        return text
    if not ATP_NAME_RE.search(text):
        return text
    m = re.match(r"^((?:🔴\s*)?(?:LIVE:\s*)?)", text)
    return f"{m.group(1)}Tennis {text[m.end():]}"


def drop_repeated_name(title):
    """Star Sports Select 2 (20 Nov 2026, user): "LIVE: ONE Championship-ONE Championship" -> "LIVE: ONE Championship".
    The feed glues "event-competition" with a hyphen; when both halves are the same, keep one."""
    if not title:
        return title
    m = re.match(r"^((?:🔴\s*)?(?:LIVE:\s*)?)(.+?)\s*[-\u2013]\s*(.+)$", title.strip(), re.I)
    if m and re.sub(r"\W+", "", m.group(2)).lower() == re.sub(r"\W+", "", m.group(3)).lower():
        return m.group(1) + m.group(2)
    return title


# Fox Sports 506 MotoGP (20 Nov 2026, user): the feed swaps title and sub-title between listings and repeats
# "DAZN ONLY - FIM ... World Championship" three times. One layout: title "<class> <session>", sub "FIM World Championship",
# the repeated sentence dropped from the description; the session is worked out from the description wording.
MOTO_FIM_RE = re.compile(r"(?i)\bFIM (Moto3|Moto2|MotoGP) World Championship")
MOTO_SESSIONS = [(r"first practice", "Practice 1"), (r"second practice", "Practice 2"), (r"third practice", "Practice 3"),
                 (r"interviews from the \w+ grid", "Grid"), (r"final look around", "Warm Up"),
                 (r"\bsprint\b", "Sprint"), (r"\bpole\b|qualifying", "Qualifying"),
                 (r"race start|title fight|crown is within|race for", "Race")]


def fox_motogp(cid, title, sub, desc):
    if cid != "AU.FoxSports506" or not title:
        return title, sub, desc
    m = re.match(r"^((?:🔴\s*)?(?:LIVE:\s*)?)(.*)$", title.strip(), re.I)
    prefix, base = m.group(1), m.group(2).strip()
    fim = MOTO_FIM_RE.search(sub or "") or MOTO_FIM_RE.search(base)
    if fim:
        cls = fim.group(1).replace("Motogp", "MotoGP")
        d = (desc or "").strip()
        d = re.sub(r"(?i)^DAZN only - FIM (?:Moto3|Moto2|MotoGP) World Championship\.\s*", "", d)
        d = re.sub(r"^(?:MotoGP|Moto2|Moto3)\.\s+", "", d)
        low = d.lower()
        session = next((name for pat, name in MOTO_SESSIONS if re.search(pat, low)), "")
        return f"{prefix}{cls} {session}".rstrip(), "FIM World Championship", d
    if re.match(r"^MotoGP(?::| After the Flag| Mini)", base) and sub and len(sub) < 30:     # "MotoGP: Inside Ducati" + "Australia"
        return f"{title.strip()} ({sub.strip()})", "", re.sub(rf"^{re.escape(sub.strip())}\.\s*", "", desc or "")
    return title, sub, desc


# Ziggo Sport MotoGP / Moto2 / Moto3 (20 Nov 2026, user: tidy like Fox 506): title "<class> <session>" in English, sub-title
# "Portugal Grand Prix" (was Dutch "GP van Portugal: Vrije Training 1"), description without the repeated sub-title.
ZIGGO_TITLE_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE:\s*)?)(Moto ?GP|Moto ?2|Moto ?3)( Highlights)?$", re.I)
ZIGGO_SUB_RE = re.compile(r"^(Moto2&3 )?(?:GP van ([\w ]+?)|Grand Prix of ([\w ]+?))(?:: (.+))?$")
ZIGGO_SESSIONS = {"vrije training 1": "Practice 1", "training": "Practice 2", "vrije training 2": "Practice 3",   # (Fox 506 numbering)
                  "kwalificatie 1": "Qualifying 1", "kwalificatie 2": "Qualifying 2", "kwalificaties": "Qualifying",
                  "sprint race": "Sprint", "race": "Race", "warm up": "Warm Up"}


def ziggo_moto(cid, title, sub, desc):
    if not cid.startswith("NL.ZiggoSport") or not title or not sub:
        return title, sub, desc
    mt, ms = ZIGGO_TITLE_RE.match(title.strip()), ZIGGO_SUB_RE.match(sub.strip())
    if not mt or not ms:
        return title, sub, desc
    cls = re.sub(r"(?i)moto ?gp", "MotoGP", mt.group(2))
    cls = re.sub(r"(?i)moto ?([23])", r"Moto\1", cls)
    if ms.group(1):
        cls = "Moto2 & Moto3"
    raw_session = (ms.group(4) or "").strip()
    session = ZIGGO_SESSIONS.get(raw_session.lower(), raw_session)
    gp = f"{(ms.group(2) or ms.group(3)).strip()} Grand Prix"
    new_title = f"{mt.group(1)}{cls}{' ' + session if session else ''}{' Highlights' if mt.group(3) else ''}"
    rest = re.sub(rf"^{re.escape(sub.strip())}\.\s*", "", (desc or "").strip())
    lead = f"{gp}, {session}." if session else f"{gp}."
    return new_title, gp, f"{lead} {rest}".strip()


def drop_repeated_subtitle(sub, desc):
    """Sky Sports Main Event 3pm (20 Nov 2026, user: "title and description are the same"): Sky's one-line synopsis is the
    secondary title AND the first sentence of the description ("Join the featured groups on day two of the RSM Classic ...
    Island." twice). The description keeps only what follows it. Only a sentence-like secondary title (25+ characters) that
    starts the description at a sentence boundary, and only when something else follows - a description that IS the
    secondary title is left alone."""
    sub, desc = (sub or "").strip(), (desc or "").strip()
    if len(sub) < 8 or not desc.startswith(sub.rstrip(".")):          # 8+ characters (was 25, 20 Nov 2026: "Duke vs. Clemson")
        return sub, desc
    rest = desc[len(sub.rstrip(".")):]
    if rest[:1] not in (".", " ") or not rest.strip(". "):
        return sub, desc
    if len(sub) < 25 and (rest[:2] != ". " or len(rest.strip(". ")) < 20):    # short ones only when a real sentence follows
        return sub, desc
    return sub, rest.lstrip(". ").strip()


# 20 Nov 2026 (user, Sky Sports Cricket "1st Test Day 2: SA v BAN Hlts" - the title repeats what the description says in full):
#   Sky:  "1st Test Day 2: SA v BAN Hlts"  ->  title "South Africa v Bangladesh Highlights", sub-title "1st Test, Day 2"
#         "ICC Women's WC: ENG v SA 2017"  ->  title "England v South Africa", sub-title "ICC Women's World Cup 2017"
#   Only country codes are expanded (both sides must be national teams); football clubs are NOT touched (QPR, WBA, MU v Chel stay).
#   "Hlts" -> "Highlights" in every Sky title.
#   India (Star / Sony) glue "A vs B-Competition" with a hyphen: "India A vs. Nepal-2026 ACC Men's Asia Cup Rising Stars" ->
#   title "India A vs. Nepal", sub-title "ACC Men's Asia Cup Rising Stars Cricket"; "A;comp text" in the description loses the repeated "A;".
NATIONS = {"SA": "South Africa", "ENG": "England", "BAN": "Bangladesh", "IND": "India", "AUS": "Australia", "NZ": "New Zealand",
           "WI": "West Indies", "SL": "Sri Lanka", "PAK": "Pakistan", "AFG": "Afghanistan", "ZIM": "Zimbabwe", "IRE": "Ireland",
           "SCO": "Scotland", "NED": "Netherlands", "NEP": "Nepal", "UAE": "UAE", "USA": "USA", "CAN": "Canada", "OMA": "Oman"}
# Sky cricket: "WBBL Hobart.H v Sydney.T" -> "WBBL Hobart Hurricanes v Sydney Thunder" (city.initial code -> full team name)
BBL_TEAMS = {"Adelaide.S": "Adelaide Strikers", "Brisbane.H": "Brisbane Heat", "Hobart.H": "Hobart Hurricanes",
             "Melbourne.R": "Melbourne Renegades", "Melbourne.S": "Melbourne Stars", "Perth.S": "Perth Scorchers",
             "Sydney.S": "Sydney Sixers", "Sydney.T": "Sydney Thunder"}
BBL_CODE_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in BBL_TEAMS) + r")(?![\w.])")


def bbl_teams(text):
    return BBL_CODE_RE.sub(lambda m: BBL_TEAMS[m.group(1)], text) if text else text


SKY_CODE_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE:\s*)?)(?:(?P<pre>[^:]{3,45}?):\s*)?(?P<a>[A-Z]{2,3}) v (?P<b>[A-Z]{2,3})(?P<post>(?:\s+(?:Hlts|Highlights|\d{4}(?:/\d{2})?|\d{4}'?))*)\s*$")
CRICKET_PRE_FIX = [(r"\bICC (Women['\u2019]s |Men['\u2019]s )?WC\b", r"ICC \1Cricket World Cup"), (r"\bWC\b", "World Cup"), (r"\b(\d(?:st|nd|rd|th) (?:Test|ODI|T20I?))\s+(Day \d)\b", r"\1, \2")]


def sky_titles(cid, title, sub, desc):
    if not cid.startswith("UK.Sky") or not title:
        return title, sub, desc
    title, sub = bbl_teams(title), bbl_teams(sub)
    m = SKY_CODE_RE.match(title.strip())
    if m and m["a"] in NATIONS and m["b"] in NATIONS:
        post = m["post"].split()
        year = " ".join(p for p in post if re.fullmatch(r"\d{4}(?:/\d{2})?'?", p)).rstrip("'")
        hl = any(p in ("Hlts", "Highlights") for p in post)
        is_cr = cid == "UK.SkySportsCricket" or bool(re.search(r"(?i)cricket", desc or ""))
        cr = "Cricket. " if is_cr else ""                    # "🔴 LIVE: Cricket. South Africa v Bangladesh" (20 Nov 2026, user)
        new_title = f"{m.group(1)}{cr}{NATIONS[m['a']]} v {NATIONS[m['b']]}{' Highlights' if hl else ''}"
        pre = m["pre"] or ""
        for rx, rep in CRICKET_PRE_FIX:
            pre = re.sub(rx, rep, pre)
        new_sub = " ".join(x for x in (pre, year) if x)
        old = (sub or "").strip()
        if old and not (desc or "").strip().startswith(old.rstrip(".")):
            desc = f"{old} {desc or ''}".strip()          # Sky's one-line synopsis is kept (in the description)
        return new_title, (new_sub or old), desc
    return re.sub(r"\bHlts\b", "Highlights", title), sub, desc


STAR_GLUE_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE:\s*)?)(?:(?P<pre>[^:]{2,40}?):\s*)?(?P<match>.+?\s(?:vs?\.?)\s[^-]*?)-(?P<comp>[A-Z0-9].*)$")


def star_glue(cid, title, sub, desc):
    if not cid.startswith("IN.") or not title or (sub or "").strip():
        return title, sub, desc
    m = STAR_GLUE_RE.match(title.strip())
    if not m:
        return title, sub, desc
    if re.search(r"(?:^|\s)(?:Al|El|Abu|Ben|Bin|St|Saint)$", m["match"].strip()):     # "Al-Ahli vs. Al-Nassr": that hyphen is in a team name
        return title, sub, desc
    comp = m["comp"].strip()
    hl = bool(re.search(r"\s+Highlights$", comp))
    comp = re.sub(r"\s+Highlights$", "", comp)
    pre = (m["pre"] or "").strip()
    year = ""
    if re.fullmatch(r"\d{4}", pre):
        year, pre = pre, ""
    new_sub = ", ".join(x for x in (f"{comp} {year}".strip(), pre) if x)
    new_title = f"{m.group(1)}{m['match'].strip()}{' Highlights' if hl else ''}"
    d = (desc or "").strip()
    d = re.sub(r"^[^;]{3,120};\s*", "", d) if ";" in d[:130] else d
    return new_title, new_sub, d.strip(" .") + "." if d.strip(" .") else new_sub + "."


# 20 Nov 2026 (user: "fix them all") - tidy-ups found in the published SPORT guide:
# German Sportdigital "Brisbane Roar - Sydney FC, A-League (5th matchday)", Spanish "Inglaterra - Nueva Zelanda" rugby text,
# the junk "Sports." sub-title / description, Fox Footy "AFL Draft" with no description, Cricbuzz "... - Test Cricket" tails.
ALEAGUE_DE_RE = re.compile(r"^(?P<a>.+?)\s+-\s+(?P<b>.+?),\s*A-?League(?P<w>\s+Women)?\s*\((?P<n>\d+)(?:st|nd|rd|th)\s+matchday\)$", re.I)


def a_league_de(title, sub, desc):
    """"🔴 LIVE: Brisbane Roar - Sydney FC, A-League (5th matchday)" -> "🔴 LIVE: Australian A-League Football. Brisbane Roar v Sydney FC", sub "Matchday 5"."""
    if not title:
        return title, sub
    lead = LIVE_LEAD_RE.match(title)
    m = ALEAGUE_DE_RE.match(title[lead.end():].strip())
    if not m:
        return title, sub
    (a, wa), (b, wb) = _aleague_side(m.group("a")), _aleague_side(m.group("b"))
    a, b = a or m.group("a").strip(), b or m.group("b").strip()
    if m.group("w") or wa or wb:
        a, b = (x if x.endswith(" Women") else f"{x} Women" for x in (a, b))
    return f"{lead.group(1)}Australian A-League Football. {a} v {b}", f"Matchday {m.group('n')}"


ES_COUNTRIES = {"inglaterra": "England", "nueva zelanda": "New Zealand", "irlanda": "Ireland", "sudáfrica": "South Africa",
                "sudafrica": "South Africa", "francia": "France", "escocia": "Scotland", "gales": "Wales", "italia": "Italy",
                "australia": "Australia", "argentina": "Argentina", "fiyi": "Fiji", "japón": "Japan", "japon": "Japan",
                "georgia": "Georgia", "españa": "Spain", "portugal": "Portugal", "uruguay": "Uruguay", "chile": "Chile",
                "samoa": "Samoa", "tonga": "Tonga", "rumanía": "Romania", "rumania": "Romania", "canadá": "Canada",
                "canada": "Canada", "estados unidos": "USA", "países bajos": "Netherlands", "alemania": "Germany",
                "namibia": "Namibia", "brasil": "Brazil", "kenia": "Kenya", "hong kong": "Hong Kong"}
ES_PAIR_RE = re.compile(r'^[\"“”]?\s*(?P<a>[^-–\"“”]+?)\s+[-–]\s+(?P<b>[^-–\"“”]+?)\s*[\"“”]?(?P<dot>\.?)$')


def es_pair(text):
    """'"Inglaterra - Nueva Zelanda"' -> 'England v New Zealand' (only when both sides are known countries)."""
    m = ES_PAIR_RE.match((text or "").strip())
    if not m:
        return text
    a, b = (ES_COUNTRIES.get(m.group(x).strip().lower()) for x in ("a", "b"))
    return f"{a} v {b}{m.group('dot')}" if a and b else text


def junk_text(x):
    return None if (x or "").strip() in ("Sports.", "Sports", "Sport.") else x


CRICKET_LEAGUES = [(r"\bNZ\b", "New Zealand"), (r"\bCPL\b", "Caribbean Premier League"), (r"\bIPL\b", "Indian Premier League"),
                   (r"\bWBBL\b", "Women's Big Bash League"), (r"\bBBL\b", "Big Bash League"),
                   (r"\bPSL\b", "Pakistan Super League"), (r"\bLPL\b", "Lanka Premier League"),
                   (r"\bBPL\b", "Bangladesh Premier League"), (r"\bWPL\b", "Women's Premier League")]


def cricket_leagues(title, sub):
    """20 Nov 2026 (user: "CPL is Caribbean Premier League"): league abbreviations written out in cricket titles / sub-titles."""
    if not title or "Cricket." not in title:
        return title, sub
    for pat, full in CRICKET_LEAGUES:
        title = re.sub(pat, full, title)
        sub = re.sub(pat, full, sub) if sub else sub
    return title, sub


ACRO_TAIL_RE = re.compile(r"^(?P<lead>.*?)\s+-\s+(?P<abbr>[A-Z][A-Z0-9]{1,6})\b[^-]*$")


def acronym_tail(title):
    """20 Nov 2026 (user: "Live Show Jumping?"): "Show Jumping. Longines Global Champions Tour Super Grand Prix 2026 - LGCT Super Grand
    Prix" says the same thing twice -> the abbreviated repeat goes, and so does the year at the end."""
    m = ACRO_TAIL_RE.match(title or "")
    if not m:
        return title
    lead, abbr = m.group("lead"), m.group("abbr")
    words = [w for w in re.split(r"[\s.:]+", lead) if w and w[0].isalpha()]
    initials = "".join(w[0].upper() for w in words)
    if len(abbr) < 3 or abbr not in initials:
        return title
    rest = re.sub(r"^[^\s]+\s*", "", m.group(0)[len(lead):].split(" - ", 1)[1].strip())
    if any(w.lower() not in lead.lower() for w in re.split(r"\s+", rest) if w):      # the tail must add nothing new ("OFF 180", "Verona Super Cup Fin R2" stay)
        return title
    return re.sub(r"\s+20\d\d$", "", lead).strip() or title


CRIC_TAIL_RE = re.compile(r"^(?P<lead>(?:🔴\s*)?(?:LIVE[:,]\s*)?Cricket\.\s+)(?P<body>.+?)\s+-\s+(?P<comp>.+?)\s+Cricket$")


def cricket_tail(title, sub):
    """"Cricket. 3rd ODI: India v West Indies - One-Day International Cricket" -> the tail goes (or becomes the sub-title)."""
    m = CRIC_TAIL_RE.match(title or "")
    if not m:
        m2 = re.match(r"^(?P<lead>(?:🔴\s*)?(?:LIVE[:,]\s*)?Cricket\.\s+)(?P<body>.+?\s+vs?\.?\s+.+?)\s+-\s+(?P<comp>[^-]+?)$", title or "")
        if m2 and re.search(r"(?i)^(?:\d+(?:st|nd|rd|th)\b|(?:one-off |final )?test\b|odi\b|t20|final\b|semi|qualifier|eliminator|day \d)", m2.group("comp").strip()):
            # TNT Sports 2 "Australia v England - 1st T20" -> same layout as TNT Sports 1: "1st T20: Australia v England"
            return f"{m2.group('lead')}{m2.group('comp').strip()}: {re.sub(r'\s+vs\.?\s+', ' v ', m2.group('body'))}", sub
        if m2 and not re.search(r"(?i)highlights|preview|review|replay|classic", m2.group("comp")):   # "A vs. B - Abu Dhabi T10 League"
            return f"{m2.group('lead')}{re.sub(r'\s+vs\.?\s+', ' v ', m2.group('body'))}", sub or m2.group("comp").strip()
        return title, sub
    body, comp = re.sub(r"\s+vs\.?\s+", " v ", m.group("body")), m.group("comp").strip()
    if not re.match(r"(?i)^(?:test|one-day international|odi|twenty20 international|t20i?|international)$", comp) and not sub:
        sub = comp
    return f"{m.group('lead')}{body}", sub


FIXTURE_TITLE_RE = re.compile(r"\S.*\s(?:v|vs\.?|V)\s\S")


def bg_text(cid, text):
    """20 Nov 2026 (user: "Repetition - a bad translation of Repeat?"): Bulgarian guide words that came through the translation wrongly.
    "Repetition." = repeat / rerun; "Live." marker is redundant; "Gurgle" = Gurgl (Austria); in ski jumping "big chance" = large hill
    (Bulgarian "chance" = hill) and "The Four Chances" = the Four Hills Tournament."""
    if not text or not cid.startswith("BG."):
        return text
    if text.startswith("Repetition. "):
        text = text[len("Repetition. "):] if re.search(r"\bRepeat\b", text) else "Repeat. " + text[len("Repetition. "):]
    text = re.sub(r"^Live\.\s+", "", text)
    text = re.sub(r"\bGurgle\b", "Gurgl", text)
    text = re.sub(r"\b[Tt]he [Ff]our [Cc]hances\b", "Four Hills Tournament", text)
    text = re.sub(r"\b[Ff]our [Cc]hances\b", "Four Hills Tournament", text)
    text = re.sub(r"\bbig chance\b", "large hill", text)
    text = re.sub(r"\bBig Chance\b", "Large Hill", text)
    return text


FIX_TAIL_RE = re.compile(r"^(?P<lead>(?:🔴\s*)?(?:LIVE[:,]\s*)?(?:[^:,\-]{2,30}:\s+)?)(?P<fix>[^,:]{2,40}?\s+(?:-|v|vs\.?)\s+[^,:]{2,40}?),\s+(?P<tail>[^()]{6,})$")
TAIL_WORD_RE = re.compile(r"(?i)league|cup|championship|liga|round|matchday|spieltag|group|division|trophy|qualif|\bfinal|semi|play-?off|tour|series|20\d\d|\d+(?:st|nd|rd|th)|competition|bundesliga|serie|ligue|eredivisie|premier")


def fixture_tail_to_desc(title, desc):
    """20 Nov 2026 (user: Tivimate shows only a few characters, anything like a synopsis belongs in the description):
    "Inter - Stuttgart, UEFA Champions League 2026/2027, Real Madrid _ PSV Eindhoven" -> title "Inter - Stuttgart",
    description "UEFA Champions League 2026/2027, Real Madrid _ PSV Eindhoven. ...". Only for a fixture followed by a competition / round tail."""
    m = FIX_TAIL_RE.match(title or "")
    if not m or not TAIL_WORD_RE.search(m.group("tail")):
        return title, desc
    if re.search(r"(?i)\b(?:race|series|draw|show|highlights?|preview|review|magazine|round|episode|ep)\b|\bE\d+\b|\b\d+x\d+\b", m.group("fix")):
        return title, desc                                  # not a match between two sides ("F1 Academy Race 2026 E11 - F1 ACADEMY RACING SERIES")
    tail = m.group("tail").strip().rstrip(".")
    new_title = f"{m.group('lead')}{fixture_v(m.group('fix')) if ' - ' in m.group('fix') else m.group('fix').strip()}"
    d = (desc or "").strip()
    if tail.lower()[:40] in d.lower():
        return new_title, desc
    return new_title, f"{tail}. {d}".strip() if d else f"{tail}."


COMP_ABBR = {"PL": "Premier League", "BL": "Bundesliga", "2. BL": "2. Bundesliga", "DFB": "DFB-Pokal"}
COMP_ABBR_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE[:,]\s*)?)(PL|BL|2\. BL|DFB):\s+(?=\S)")


def comp_abbr(title):
    """20 Nov 2026 (user: "BL: Brentford FC - Everton FC - what is the BL:?"): Sky Germany's short competition codes written out."""
    m = COMP_ABBR_RE.match(title or "")
    if not m:
        return title
    full, rest = COMP_ABBR[m.group(2)], title[m.end():]
    if rest.lower().startswith(full.lower()):                       # "BL: Bundesliga Weekly" - no need to say it twice
        return f"{m.group(1)}{rest}"
    return f"{m.group(1)}{full}: {rest}"


def clean_team(t):
    """Only a trailing " FC" goes ("Brentford FC" -> "Brentford"); "FC Bayern", "1. FC Cologne", "FC Barcelona" keep it (user, 20 Nov 2026)."""
    return re.sub(r"\s+FC$", "", t.strip()) or t.strip()


def fixture_v(fix):
    """"Brentford FC - Everton FC" -> "Brentford v Everton" (20 Nov 2026, user: "v" not a dash, and no "FC")."""
    parts = re.split(r"\s+-\s+", fix.strip())
    if len(parts) != 2:
        return fix
    return f"{clean_team(parts[0])} v {clean_team(parts[1])}"


SPORT_PREFIX_FIX_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE[:,]\s*)?(?:Football|Basketball|Handball|Volleyball|Futsal|Ice Hockey|Rugby|Premier League|Bundesliga|2\. Bundesliga|DFB-Pokal):\s+)([^:,()]{3,45}?\s+-\s+[^:,()]{3,45})$")


def fixtures_with_v(title):
    m = SPORT_PREFIX_FIX_RE.match(title or "")
    return f"{m.group(1)}{fixture_v(m.group(2))}" if m else title


def long_sub_to_desc(title, sub, desc, cid=""):
    """20 Nov 2026 (user, TNT Sports 1 "Bristol Bears v Bath Rugby" + "Action from Group A of the PREM Rugby Cup as ... at
    Ashton Gate."; later "Alpine Skiing World Cup" the same): a sentence-length sub-title makes the player's title far too
    long -> the sentence goes into the description (in front of it), the sub-title goes. Any title, every channel except BG."""
    if not (title and sub):
        return sub, desc
    s = sub.strip()
    long_enough = len(s.split()) >= 8 or len(s) >= 70                     # 20 Nov 2026 (user: "yes"): competition labels / genre text too, BG included
    if not long_enough:
        return sub, desc
    if re.search(r"\s(?:v|vs\.?|V)\s", s) and not FIXTURE_TITLE_RE.search(title):
        return sub, desc                                                  # Fox cricket: the sub-title IS the fixture
    d = (desc or "").strip()
    if d and re.sub(r"^(?:repeat|replay)[.,]\s*", "", s, flags=re.I).rstrip(".").lower()[:60] in d.lower():     # description already says it
        return None, d
    return None, f"{s} {d}".strip()


PL_SEASON_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE[:,]\s*)?)(\[4K\]\s*)?Premier League\s+(?:20)?26/27\s*-\s*(.+?)\s+(?:vs?\.?)\s+(.+?)\s*$", re.I)

def pl_season(title, sub, desc, live=False):
    """Now Sports: "LIVE: Premier League 26/27 - Manchester City vs Fulham" ->
    title "LIVE: Premier League. Manchester City v Fulham", plus a proper description (20 Nov 2026)."""
    m = PL_SEASON_RE.match(title or "")
    if not m or sub:
        return title, sub, desc
    lead, uhd, a, b = m.group(1), m.group(2), m.group(3), m.group(4)
    lead = lead or ""
    is_live = "LIVE" in lead.upper()
    new_title = f"{lead}Premier League. {a} v {b}"
    new_sub = ("Live in 4K Ultra HD" if is_live else "4K Ultra HD") if uhd else "2026/27 Season"
    if is_live:
        text = (f"LIVE Premier League football from the 2026/27 season: {a} v {b}."
                )
    else:
        text = (f"Premier League football from the 2026/27 season: {a} v {b}.")
    d = (desc or "").strip()
    if d:                                                  # keep the channel's own "Coverage from: 2:50pm." note
        d = re.sub(r"^Coverage from:\s*", "Coverage from ", d)
        text = f"{text} {d}"
    return new_title, new_sub, text

# TNT Sports 5 live events (21 Nov 2026, user): TNT Sports 5 is an overflow channel (only on air for the odd live event). tvguide.co.uk lists the matches on it
# ("Tue 24 Nov / 20:00 / Broadcast · 19:55 / Slovan Bratislava vs Real Betis / UEFA Champions League / Match details"). A "LIVE: TNT Sports 5" placeholder block
# that overlaps one of those matches is renamed to the match; with the page unreachable (or its layout changed) the placeholder stays.
TNT5_URL = "https://www.tvguide.co.uk/sport/football/tnt-sports-5"
TNT5_LABEL = "TNT Sports 5 (tvguide.co.uk)"
TNT5_CID = "UK.TNTSports5"
TNT5_MATCH_MINUTES = 130
_TNT5 = {"matches": None, "channel": None}
_TNT_DATE_RE = re.compile(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+(\d{1,2})\s+([A-Z][a-z]{2})[a-z]*$")
_TNT_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_tnt5(page, today=None):
    """[{ko, bc, a, b, comp}] from the tvguide.co.uk football page. As the page is built (22 Nov 2026, read in Chrome): a date heading (<h3>Tue 24 Nov</h3>),
    then per match: the kick-off, "Broadcast · 19:55", the two sides as separate elements with "vs" between, then the competition."""
    today = today or datetime.now(LONDON).date()
    page = re.sub(r"(?s)<!--.*?-->", "", re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page or ""))
    lines = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in re.split(r"<[^>]+>", page)]
    lines = [x for x in lines if x]
    out, cur = [], None
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    for i, ln in enumerate(lines):
        d = _TNT_DATE_RE.match(ln)
        if d and d.group(2) in months:
            mon = months.index(d.group(2)) + 1
            yr = today.year + (1 if mon < today.month - 6 else 0)
            cur = date(yr, mon, int(d.group(1)))
            continue
        b = re.match(r"^Broadcast\s*[·\-|]?\s*(\d{1,2}):(\d{2})$", ln)
        if not (b and cur and i >= 1 and i + 3 < len(lines)):
            continue
        k = _TNT_TIME_RE.match(lines[i - 1])
        if re.match(r"(?i)^vs?\.?$", lines[i + 2]):                      # sides as separate lines: A / vs / B / competition
            a_, b_, comp = lines[i + 1], lines[i + 3], (lines[i + 4] if i + 4 < len(lines) else "")
        else:                                                           # "A vs B" on one line
            teams = re.split(r"\s+(?:vs?\.?)\s+", lines[i + 1], maxsplit=1)
            if len(teams) != 2:
                continue
            a_, b_, comp = teams[0], teams[1], lines[i + 2]
        if not k:
            continue
        mk = lambda h, m: datetime(cur.year, cur.month, cur.day, int(h), int(m), tzinfo=LONDON).astimezone(timezone.utc)
        out.append({"ko": mk(*k.groups()), "bc": mk(*b.groups()), "a": a_.strip(), "b": b_.strip(), "comp": comp.strip()})
    return out


def tnt5_matches():
    if _TNT5["matches"] is None:
        page = fetch(TNT5_URL, retries=2, label=TNT5_LABEL)
        try:
            _TNT5["matches"] = parse_tnt5(page) if page else []
            if page and not _TNT5["matches"]:            # got a page but read nothing from it: show what came back
                print(f"  {TNT5_LABEL}: page came back ({len(page)} characters) but no matches were read; starts: {re.sub(chr(92)+'s+', ' ', re.sub(r'<[^>]+>', ' ', page))[:160]!r}")
        except Exception as e:
            print(f"  WARNING: {TNT5_LABEL}: {e}")
            _TNT5["matches"] = []
        print(f"  {TNT5_LABEL}: {len(_TNT5['matches'])} matches" if _TNT5["matches"] else f"  {TNT5_LABEL}: no matches read (placeholder wording stays)")
    return _TNT5["matches"]


# TNT Sports 5, ALL sports (21 Nov 2026, user): tvguide.co.uk also has the channel's own schedule page, which lists the other sports too ("Live: Ski Jumping World Cup",
# "Live Test Cricket"). Every day is a page: /channel/tnt-sports-5 (today) and ?date=YYYY-MM-DD. Each entry is "6:00 AM / title / subtitle / description" (UK time, 12-hour);
# "This is TNT Sports 5" is the filler. A placeholder block that overlaps a LIVE entry takes its title, sub-title and description, and the normal sport naming then runs on it.
TNT5_CHANNEL_URL = "https://www.tvguide.co.uk/channel/tnt-sports-5"
TNT5_CHANNEL_DAYS = 7
_TNT5_CH = {"entries": None}
_TNT5_CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2})\s?([AaPp][Mm])$")
_TNT5_JUNK_RE = re.compile(r"^(?:today|tomorrow|yesterday|previous|next|watch|more|set reminder|share|live now|on now|now|tonight)$", re.I)


def parse_tnt5_channel(page, day):
    """[{start, end, title, sub, desc}] (UTC) for one day of the channel page. As the page is built (22 Nov 2026, read in Chrome): every entry is a
    block carrying data-date="2026-11-22T10:50:00.000Z" (its start, UTC), whose text is the time (two elements: "10:50" and "AM"), an optional
    "119 minutes remaining", the title ("Live: Ski Jumping World Cup" / "Live Test Cricket" / "This is TNT Sports 5") and a description line."""
    page = re.sub(r"(?s)<!--.*?-->", "", re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page or ""))
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)"', page)]
    rows = []
    for n, (pos, iso) in enumerate(marks):
        chunk = page[pos: marks[n + 1][0] if n + 1 < len(marks) else pos + 6000]
        chunk = chunk.split('"', 2)[2] if chunk.count('"') >= 2 else chunk
        chunk = chunk[chunk.find(">") + 1:] if ">" in chunk else chunk          # the rest of the block's own opening tag
        lines = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in re.split(r"<[^>]+>", chunk)]
        lines = [x for x in lines if x and not re.match(r"(?i)^(?:\d{1,2}:\d{2}|[ap]m|\d+ minutes? remaining|\d+ hours? remaining)$", x) and not _TNT5_JUNK_RE.match(x)]
        if not lines:
            continue
        try:
            start = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            continue
        title = lines[0]
        desc = lines[1] if len(lines) > 1 and re.match(r"(?i)^live\b", title) else ""
        sm = re.match(r"^(.{3,60}? v .{3,60}?)\.(?:\s|$)", desc)
        rows.append({"start": start, "title": title, "sub": sm.group(1).strip() if sm else "", "desc": desc})
    out = []
    for i, r in enumerate(rows):
        end = rows[i + 1]["start"] if i + 1 < len(rows) else r["start"] + timedelta(hours=6)
        out.append({"start": r["start"], "end": end, "title": r["title"], "sub": r["sub"], "desc": r["desc"]})
    return out


def tnt5_channel_entries():
    """LIVE entries (title starts 'Live') of the next few days of the channel page. Empty when the page can't be read."""
    if _TNT5["channel"] is None:
        res, ok = [], 0
        today = datetime.now(LONDON).date()
        for n in range(TNT5_CHANNEL_DAYS):
            d = today + timedelta(days=n)
            page = fetch(TNT5_CHANNEL_URL if n == 0 else f"{TNT5_CHANNEL_URL}?date={d.isoformat()}", retries=2, label=f"{TNT5_LABEL} {d.isoformat()}", quiet=(n > 0))
            try:
                rows = parse_tnt5_channel(page, d) if page else []
                if n == 0 and page and not rows:
                    print(f"  {TNT5_LABEL} channel page: came back ({len(page)} characters) but no entries were read; starts: {re.sub(chr(92)+'s+', ' ', re.sub(r'<[^>]+>', ' ', page))[:160]!r}")
            except Exception as e:
                print(f"  WARNING: {TNT5_LABEL} {d}: {e}")
                rows = []
            ok += bool(rows)
            res += [r for r in rows if re.match(r"(?i)^live\b", r["title"])]
        _TNT5["channel"] = res
        print(f"  TNT Sports 5 channel page: {len(res)} live events in {ok} of {TNT5_CHANNEL_DAYS} days" if res else
              f"  TNT Sports 5 channel page: no live events read ({ok} of {TNT5_CHANNEL_DAYS} days had entries)")
    return _TNT5["channel"]


def tnt5_named_also(start, title, sub, desc):
    """A TNT Sports 5 block the source already names ("Champions League: S. Bratislava v R. Betis", sub-title "New Zealand v India"): the same
    "This match is also available on ..." line is added to its description. Anything without exactly two sides, or already carrying the line, is left alone."""
    try:
        if "available on" in (desc or "") or team_sport_of(title, sub, TNT5_CID, desc):          # team sports: the general pass (two channels)
            return desc
        for text in ((sub or "").strip(), (title or "").strip().rsplit(": ", 1)[-1].strip()):
            parts = re.split(r"\s+vs?\.?\s+", text)
            if len(parts) == 2 and all(2 < len(x.strip()) <= 40 for x in parts):
                a, b = (x.strip() for x in parts)
                also = tnt5_also({"a": a, "b": b, "ko": start})
                if also:
                    return f"{desc} | This match is available on {also}." if desc else f"This match is available on {also}."
                return desc
    except Exception as e:
        print(f"  WARNING: TNT Sports 5 'also available on' lookup failed ({e})")
    return desc


def tnt5_channel_event(lead, start, stop, title, sub, desc):
    best, bo = None, timedelta(0)
    for e in tnt5_channel_entries():
        ov = min(stop, e["end"]) - max(start, e["start"])
        if ov > bo:
            best, bo = e, ov
    if not best or bo < timedelta(minutes=15):
        return title, sub, desc
    name = re.sub(r"(?i)^live\b[:,\s]*", "", best["title"]).strip() or best["title"]
    new_sub = best["sub"]
    new_desc = best["desc"] or best["sub"] or desc
    t = re.match(r"^(.+?) v (.+)$", new_sub)
    if t and not team_sport_of(f"{lead}{name}", new_sub, TNT5_CID, new_desc):        # two sides in the sub-title (football): the other channels with the same game
        also = tnt5_also({"a": t.group(1).strip(), "b": t.group(2).strip(), "ko": best["start"]})
        if also:
            new_desc = f"{new_desc} | This match is available on {also}."
    return f"{lead}{name}", new_sub, new_desc


def tnt5_event(cid, start, stop, title, sub, desc):
    """a TNT Sports 5 placeholder block that overlaps a listed match -> that match"""
    if cid != TNT5_CID:
        return title, sub, desc
    if not TNT_PLACEHOLDER_RE.match((title or "").strip()):
        return title, sub, tnt5_named_also(start, title, sub, desc)          # a real event already named by the source: only the other channels are added
    best, bo = None, timedelta(0)
    for m in tnt5_matches():
        a, z = m["bc"], m["ko"] + timedelta(minutes=TNT5_MATCH_MINUTES)
        ov = min(stop, z) - max(start, a)
        if ov > bo:
            best, bo = m, ov
    lead = TNT_PLACEHOLDER_RE.match(title.strip())["lead"]
    if not best or bo < timedelta(minutes=15):
        return tnt5_channel_event(lead, start, stop, title, sub, desc)           # not a football match listed: the channel page (all sports)
    bc = best["bc"].astimezone(LONDON)
    cov = f"{bc.hour % 12 or 12}{'' if bc.minute == 0 else f':{bc.minute:02d}'}{'am' if bc.hour < 12 else 'pm'}"
    text = f"{best['comp']}: {best['a']} v {best['b']}. Coverage from: {cov}."
    also = tnt5_also(best)
    if also:
        text += f" | This match is available on {also}."          # the channels come LAST after a "|", as on the football channels
    return f"{lead}Football. {best['a']} v {best['b']}", best["comp"], text


# Other channels carrying the same match (21 Nov 2026, user): the same lookup football_epg.py uses for "This match is also available on ..." -
# watch_channels.CHANNELS whose own listing in our guides is on air at kick-off + 20 to 30 minutes and names both teams, plus the Paramount+ / Peacock /
# Stan Sport slots in the events guide. TNT Sports 5 itself is left out. Anything that goes wrong just means no extra sentence.
_TNT5_ALSO = {"listings": None, "slots": None}
_TNT5_GENERIC = {"real", "city", "united", "utd", "town", "county", "albion", "athletic", "rovers", "wanderers", "rangers", "hotspur", "wednesday", "villa",
                 "forest", "palace", "club", "fc", "afc", "sc", "sporting", "inter", "olympique", "borussia", "paris", "sporting", "dynamo", "red", "star"}


def _tnt5_norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9&']+", " ", text.replace(" and ", " & ")) + " "


def _tnt5_aliases(name):
    n = _tnt5_norm(name)
    words = n.split()
    out = {n}
    for w in (words[-1:] + words[:1]):                    # a distinctive single word ("betis", "slovan") as the event titles often shorten club names
        if len(w) > 4 and w not in _TNT5_GENERIC:
            out.add(f" {w} ")
    return sorted(out)


def tnt5_also(m):
    try:
        import watch_channels as wc
    except Exception as e:
        print(f"  NOTE: watch_channels.py not available ({e}) - no 'also available on' line for TNT Sports 5")
        return ""
    try:
        if _TNT5_ALSO["listings"] is None:
            _TNT5_ALSO["listings"] = wc.load_listings()
            try:
                _TNT5_ALSO["slots"] = wc.load_event_slots()
            except Exception as e:
                print(f"  Events guide not read ({e}) - no event-stream services named")
                _TNT5_ALSO["slots"] = []
        ha, aa = _tnt5_aliases(m["a"]), _tnt5_aliases(m["b"])
        both = lambda txt: (lambda t: any(x in t for x in ha) and any(x in t for x in aa))(_tnt5_norm(txt))
        ko, fams = m["ko"], {}
        for cid, name, family in wc.CHANNELS:
            if cid == TNT5_CID:
                continue
            for s, e, text in _TNT5_ALSO["listings"].get(cid, []):
                if s <= ko + timedelta(minutes=20) and e >= ko + timedelta(minutes=30) and both(text):
                    fams.setdefault(family, []).append(name)
                    break
        names = wc.order_names(fams)
        services = wc.event_services_for(ko, both, _TNT5_ALSO["slots"] or [])
        allnames = names + [x for x in services if x not in names]
        print(f"  {TNT5_LABEL}: {m['a']} v {m['b']} also on {len(allnames)} channels / services")
        return wc.join_names(allnames) if allnames else ""
    except Exception as e:
        print(f"  WARNING: TNT Sports 5 'also available on' lookup failed ({e})")
        return ""


def add_programme(tv, cid, start, stop, title, sub, desc, live):
    title, sub, desc = tnt5_event(cid, start, stop, title, sub, desc)             # TNT Sports 5 overflow: the match on air
    if sub != "Coming up" and not re.search(r"\(\w{3} \d{1,2} \w{3},", title or ""):      # own date out of the title / sub-title / description
        days, yr = own_dates(start), start.year
        title = drop_own_date(title, days, yr)
        sub = drop_own_date(sub, days, yr, keep_if_empty=False) or None if sub else sub
        desc = drop_own_date(desc, days, yr)
    sub, desc = junk_text(sub), junk_text(desc)
    title, sub, desc = (bg_text(cid, x) for x in (title, sub, desc))
    if sub and sub.startswith(('"', '“')) or (desc or '').startswith(('"', '“')):
        sub, desc = es_pair(sub), es_pair(desc)
    title, sub = a_league_de(title, sub, desc)
    title, sub, desc = pl_season(title, sub, desc)
    title, sub, desc = sky_titles(cid, title, sub, desc)
    title, sub, desc = tnt_placeholder(cid, title, sub, desc)
    title, sub, desc = nz_cricket(cid, title, sub, desc)
    title, sub, desc = nz_nations(cid, title, sub, desc)
    title, sub, desc = nz_shield(cid, title, sub, desc)
    title, sub, desc = nz_pwr(cid, title, sub, desc)
    title, sub, desc = nz_basketball(cid, title, sub, desc)
    title, sub, desc = nz_wsl(cid, title, sub, desc)
    title, sub, desc = (hub_premier_codes(cid, x) for x in (title, sub, desc))
    title, sub, desc = star_glue(cid, title, sub, desc)
    sub, desc = drop_repeated_subtitle(sub, desc)
    if cid.startswith("FR."):                          # French spacing: "Rugby : Pro D2" -> "Rugby: Pro D2"
        title, sub = (re.sub(r"\s+:(?=\s)", ":", x) if x else x for x in (title, sub))
    title, sub, desc = fox_motogp(cid, title, sub, desc)
    title, sub, desc = ziggo_moto(cid, title, sub, desc)
    title = drop_repeated_name(title)
    title = racing_meetings(cid, title, desc)
    title, sub = (re.sub(r"\bAFLW\b", "AFL Women's", x) if x else x for x in (title, sub))   # AFLW -> "AFL Women's" (20 Nov 2026)
    title, desc = fixture_tail_to_desc(title, desc)
    title = fixtures_with_v(comp_abbr(title))
    title = a_league(title, sub, desc)
    title, sub = nwsl(title, sub, desc)
    title = add_sport(title, sub, cid, desc)
    title, sub = cricket_tail(title, sub)
    title = acronym_tail(title)
    title, sub = cricket_leagues(title, sub)
    if desc and sub and desc.rstrip(".") == sub and " v " in sub:         # desc only repeats the fixture (Spanish rugby): say what it is
        desc = f"{LIVE_LEAD_RE.sub('', title).replace('. ', ' ', 1)}: {sub}."
    if not desc and re.search(r"\bAFL Draft\b", title or ""):
        desc = "Coverage of the AFL Draft."
    sub, desc = long_sub_to_desc(title, sub, desc, cid)
    title, sub, desc = (national_names(x) for x in (title, sub, desc))               # "🔴 LIVE: Tennis. ATP Finals" (20 Nov 2026)
    title, sub, desc = fix_names(title), fix_names(sub), fix_names(desc)
    title, sub, desc = clock12(title), clock12(sub), clock12(desc)   # 12-hour clock with AM / PM everywhere (6 Nov 2026)
    p = ET.SubElement(tv, "programme", {
        "start": xmltv_time(start), "stop": xmltv_time(stop), "channel": cid})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    if sub:
        ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    if desc:
        ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    ET.SubElement(p, "category", {"lang": "en"}).text = "Movies" if cid.startswith(SKY_CINEMA) else "Sports"
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


# Astro's pop-up Premier League channels (28 Oct 2026): Astro (and epgshare01's copy) only list
# 6-hour placeholder blocks titled with the channel name, whose description names the next match:
#   "Catch the live broadcast of Premier League 2026/27: Match Week 9: Coventry City vs Sunderland
#    at 2300hrs."
# astro_matchday() replaces those blocks with "Coming up" blocks up to the match and a LIVE block from
# ASTRO_LIVE_EARLY minutes before kick-off for ASTRO_MATCH_MINUTES, the kick-off date and time taken from
# the football guide (same two teams, same Malaysian clock time). If the football guide doesn't have the
# match, the placeholders stay but are no longer marked live. Log: "Astro PL4: Coventry City vs
# Sunderland -> Sat 31 Oct 15:00 UK".
ASTRO_PLACEHOLDER_RE = re.compile(r"(?i)^astro (premier league|football|sports uhd|arena)( \d)?$")
ASTRO_MATCH_RE = re.compile(r"(?i)live broadcast of (?P<comp>.+?)(?:\s+\d{4}/\d{2,4})?:\s*(?P<round>(?:match ?week|"
                            r"round|matchday)\s*\d+)?:?\s*(?P<a>.+?)\s+(?:vs?\.?)\s+(?P<b>.+?)\s+at\s+"
                            r"(?P<hh>\d{2})(?P<mm>\d{2})\s*hrs")
ASTRO_LIVE_EARLY = 10
ASTRO_MATCH_MINUTES = 130
MYT = timezone(timedelta(hours=8))


def astro_matchday(records):
    for rec in records:
        if not rec.get("id", "").startswith("MY.Astro"):
            continue
        holders = [ev for ev in rec["events"] if ASTRO_PLACEHOLDER_RE.match((ev.get("title") or "").strip())]
        if not holders:
            continue
        for ev in holders:                                   # never "live" as they stand
            ev["live"], ev["never_live"] = False, True
        m = next((ASTRO_MATCH_RE.search(ev.get("desc") or "") for ev in holders
                  if ASTRO_MATCH_RE.search(ev.get("desc") or "")), None)
        if not m:
            continue
        a, b = m["a"].strip(), m["b"].strip()
        wa, wb = _team_words(a), _team_words(b)
        first = min(ev["start"] for ev in holders)
        ko = None
        for when, h, w, _rest in load_kickoffs():
            if when < first - timedelta(hours=3) or not ((wa & h and wb & w) or (wa & w and wb & h)):
                continue
            local = when.astimezone(MYT)
            if (local.hour, local.minute) == (int(m["hh"]), int(m["mm"])) and (ko is None or when < ko):
                ko = when
        if not ko:
            print(f"  Astro {rec['id']}: {a} vs {b} not in the football guide - placeholders kept (not live)")
            continue
        comp = m["comp"].strip()
        rnd = re.sub(r"\s+", " ", (m["round"] or "").strip())         # "Match Week 9"
        sub = f"{comp} – {rnd}" if rnd else comp
        uk = ko.astimezone(LONDON)
        when_txt = f"{uk:%a} {uk.day} {uk:%b}, {uk:%H:%M}"
        live_from = ko - timedelta(minutes=ASTRO_LIVE_EARLY)
        live_to = ko + timedelta(minutes=ASTRO_MATCH_MINUTES)
        keep = [ev for ev in rec["events"] if not any(ev is h for h in holders)
                and ((ev.get("stop") or ev["start"]) <= first or ev["start"] >= live_to)]
        new = []
        if first < live_from:
            new.append({"start": first, "stop": live_from, "title": f"{a} vs {b} ({when_txt})",
                        "sub": f"⏭ Coming up: {sub}", "live": False, "never_live": True, "no_lead": True,
                        "desc": f"Coming up on {rec['name']}: {a} vs {b}, {comp}"
                                f"{', ' + rnd if rnd else ''}. Kick-off {when_txt} UK time."})
        new.append({"start": live_from, "stop": live_to, "title": f"{a} vs {b}", "sub": sub, "live": True,
                    "no_lead": True, "desc": f"{a} vs {b}, {comp}{', ' + rnd if rnd else ''}."})
        rec["events"] = sorted(keep + new, key=lambda ev: ev["start"])
        print(f"  Astro {rec['id']}: {a} vs {b} -> {uk:%a %d %b %H:%M} UK")


# beIN Sports Indonesia (26 Nov 2026, user): epgshare01's ID1 file titles the European football like
#   "UEL 2026/27: CRY Vs RSO (L)"  - three-letter team codes, no description, and a trailing "(L)" = live.
# code_titles() turns the codes into the two teams (names and kick-off from LiveOnSat's football list,
# liveonsat_fixtures.json - the same file event_epg.py reads), so the programme becomes
#   "Crystal Palace vs Real Sociedad"  /  sub-title "UEFA Europa League"  /  desc "UEFA Europa League, League Phase: Round 5."
# and, with the "(L)", is live (the red ball comes from the normal live handling). Rules:
#   * the competition word must agree (UEL = Europa League, UECL = Conference League, UCL = Champions League);
#   * live programme: the fixture kicks off within 20 min before to 25 min after the programme start; a programme
#     without "(L)" (a repeat) may be a match from up to 72 h earlier;
#   * a code fits a team when its letters appear in order in the team's name, starting at a word's first letter
#     (CRY = Crystal Palace, RSO = Real Sociedad, BHA = Brighton & Hove Albion, UCR = Universitatea Craiova);
#   * both codes must fit one fixture - or, if no fixture fits both, exactly one fixture fits one code ("SUN Vs ME").
#     Anything else is left as beIN wrote it (only the "(L)" is removed).
CODE_TITLE_RE = re.compile(r"^(?P<comp>UECL|UEL|UCL)\s+\d{4}/\d{2}\s*:\s*(?P<a>[A-Za-z0-9]{2,5})\s+V[sS]\.?\s+"
                           r"(?P<b>[A-Za-z0-9]{2,5})(?P<live>\s*\(L\))?\s*$")
CODE_COMP = {"UCL": "champions league", "UEL": "europa league", "UECL": "conference league"}
LIVEONSAT_FIXTURES = "liveonsat_fixtures.json"
LIVEONSAT_FIXTURES_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/liveonsat_fixtures.json"
_CODE_FIXTURES = None
CODE_ALIASES = {"ASM": "monaco", "BJK": "besiktas", "ACS": "sparta praha"}   # codes that are not letters of the name
CODE_NAME_TIDY = {"Brighton H.A.": "Brighton & Hove Albion"}                  # LiveOnSat's short forms


def load_code_fixtures():
    """[(kick-off UTC, competition, home, away)] of the football fixtures in liveonsat_fixtures.json"""
    global _CODE_FIXTURES
    if _CODE_FIXTURES is not None:
        return _CODE_FIXTURES
    _CODE_FIXTURES = []
    try:
        if os.path.exists(LIVEONSAT_FIXTURES):
            with open(LIVEONSAT_FIXTURES, encoding="utf-8") as f:
                data = json.load(f)
        else:
            req = urllib.request.Request(LIVEONSAT_FIXTURES_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
        for fx in ((data.get("football") or {}).get("fixtures") or []):
            try:
                ko = datetime.strptime(fx["start"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                continue
            _CODE_FIXTURES.append((ko, fx.get("comp") or "", fx.get("a") or "", fx.get("b") or ""))
    except Exception as err:                       # never lose the guide over this
        print(f"  NOTE: LiveOnSat fixtures not available for beIN Indonesia's team codes ({err})")
    return _CODE_FIXTURES


def _code_fits(code, team):
    letters = re.sub(r"[^a-z0-9 ]+", "", "".join(c for c in unicodedata.normalize("NFKD", team.lower())
                                                 if not unicodedata.combining(c)).replace("&", " "))
    flat = letters.replace(" ", "")
    code = code.lower()
    if code.upper() in CODE_ALIASES:
        return CODE_ALIASES[code.upper()] in team.lower()
    pos = 0
    for word in letters.split():                   # try every word's first letter as the start
        i = flat.find(word, pos)
        pos = i + len(word)
        if i < 0 or word[0] != code[0]:
            continue
        j = i
        for ch in code:
            j = flat.find(ch, j)
            if j < 0:
                break
            j += 1
        else:
            return True
    return False


def code_fixture(comp_code, a, b, start, live):
    """(home, away, competition, kick-off) for a code title, or None"""
    word = CODE_COMP[comp_code]
    lo, hi = (timedelta(minutes=20), timedelta(minutes=25)) if live else (timedelta(hours=72), timedelta(minutes=25))
    near = [f for f in load_code_fixtures() if word in f[1].lower() and "women" not in f[1].lower()
            and start - lo <= f[0] <= start + hi]
    both = [f for f in near if _code_fits(a, f[2]) and _code_fits(b, f[3])]
    if len(both) == 1:
        return both[0][2], both[0][3], both[0][1], both[0][0]
    if both:
        return None                                # two fixtures fit: not guessing
    one = [f for f in near if _code_fits(a, f[2]) or _code_fits(b, f[3])]
    if live and len(one) == 1:
        return one[0][2], one[0][3], one[0][1], one[0][0]
    return None


def code_titles(records):
    done = left = 0
    for rec in records:
        if not rec.get("id", "").startswith("ID."):
            continue
        for ev in rec["events"]:
            title = re.sub(r"\s*\(L\)\s*$", "", ev.get("title") or "").strip() or ev.get("title")
            m = CODE_TITLE_RE.match(ev.get("title") or "")
            if not m:
                ev["title"] = title
                continue
            fx = code_fixture(m["comp"].upper(), m["a"], m["b"], ev["start"], bool(m["live"]))
            if not fx:
                ev["title"] = title
                left += 1
                continue
            home, away, comp_full, ko = fx
            home, away = CODE_NAME_TIDY.get(home, home), CODE_NAME_TIDY.get(away, away)
            short, _, detail = comp_full.partition(" - ")
            ev["title"] = f"{home} vs {away}"
            ev["sub"], ev["no_lead"] = short.strip(), True
            line = f"{short.strip()}{', ' + detail.strip() if detail.strip() else ''}."
            uk = ko.astimezone(LONDON)
            ev["desc"] = (f"{line} Kick-off: {uk:%H:%M}." if ko >= ev["start"] - timedelta(minutes=30) else
                          f"{line} Match played {uk:%a} {uk.day} {uk:%b}, {uk:%H:%M} UK time.")
            done += 1
    if done or left:
        print(f"  beIN Indonesia team codes: {done} turned into team names, {left} left as beIN wrote them")


# beIN Sports Malaysia (26 Nov 2026, user): beIN's own guide titles a football broadcast "Crystal Palace vs Real Sociedad - MD5"
# with no description, no competition, and no live flag (so no red ball); LaLiga etc. carry only a stock sentence. bein_fixture_titles()
# looks each "A vs B" up in LiveOnSat's football list (liveonsat_fixtures.json, loaded by load_code_fixtures) by team names:
#   * the match kicks off within 30 min after to 25 min before the programme start: LIVE (red ball), competition as the
#     secondary title, "<competition>, <round>. Kick-off: 20:00." first in the description (beIN's own sentence stays after it);
#   * the match was played up to 72 h before: a repeat - same title / secondary title, "Match played Thu 26 Nov, 20:00 UK time.",
#     never live;
#   * no fixture, or more than one: left exactly as beIN wrote it.
# The trailing " - MD5" is dropped from the title. Youth / women's / reserve fixtures are never matched.
BEIN_VS_RE = re.compile(r"^(?P<a>.+?)(?:\s+vs?\.?\s+|\s+-\s+)(?P<b>.+?)(?:\s*-\s*(?:MD|Matchday|Match Day)\s*\d+)?\s*$", re.I)
BEIN_SKIP_FIXTURE_RE = re.compile(r"(?i)\bU-?\d{2}\b|\bwomen\b|\bII\b|\bW\b|reserves|youth")


def bein_fixture_titles(records):
    fixtures = [f for f in load_code_fixtures() if not BEIN_SKIP_FIXTURE_RE.search(f"{f[1]} {f[2]} {f[3]}")]
    live_n = rep_n = 0
    for rec in records:
        if not rec.get("bein_guide"):
            continue
        for ev in rec["events"]:
            title = ev.get("title") or ""
            m = BEIN_VS_RE.match(title)
            if not m or re.search(r"\d{2}/\d{2}|\(\d{4}", title) or len(title) > 70:
                continue
            wa, wb = _team_words(m["a"]), _team_words(m["b"])
            start = ev["start"]
            hit = [f for f in fixtures if start - timedelta(hours=72) <= f[0] <= start + timedelta(minutes=30)
                   and ((wa & _team_words(f[2]) and wb & _team_words(f[3]))
                        or (wa & _team_words(f[3]) and wb & _team_words(f[2])))]
            if not hit:
                continue
            live_hit = [f for f in hit if start - timedelta(minutes=25) <= f[0] <= start + timedelta(minutes=30)]
            hit = live_hit or hit
            if len(hit) > 1:                         # two fixtures fit: take the nearest to the start, unless it is a tie
                hit.sort(key=lambda f: abs((f[0] - start).total_seconds()))
                if len(hit) > 1 and abs((hit[0][0] - start).total_seconds()) == abs((hit[1][0] - start).total_seconds()):
                    continue
            ko, comp_full = hit[0][0], hit[0][1]
            short, _, detail = comp_full.partition(" - ")
            line = f"{short.strip()}{', ' + detail.strip() if detail.strip() else ''}."
            uk = ko.astimezone(LONDON)
            is_live = bool(live_hit)
            extra = (ev.get("desc") or "").strip()
            ev["title"] = f"{m['a'].strip()} vs {m['b'].strip()}"
            if not ev.get("sub"):
                ev["sub"] = short.strip()
            ev["no_lead"] = True
            ev["desc"] = " ".join(x for x in (line, f"Kick-off: {uk:%H:%M}." if is_live else
                                              f"Match played {uk:%a} {uk.day} {uk:%b}, {uk:%H:%M} UK time.", extra) if x)
            if is_live:
                ev["live"] = True
                live_n += 1
            else:
                ev["live"], ev["never_live"] = False, True
                rep_n += 1
    if live_n or rep_n:
        print(f"  beIN guide matches from LiveOnSat's list: {live_n} live, {rep_n} repeats")


# Rush Sports 1-3 (26 Nov 2026, user): the UEFA matches come as "UEFA Europa League Soccer" + "From Karaiskakis Stadium in Piraeus, Attica,
# Greece." - the stadium and city but no teams, and Rush Sports 1 (unlike 2 and 3) without the LIVE flag. The stadium names the HOME
# side, so: (1) the home team is found from the stadium (RUSH_VENUES) or the city appearing in a home team's name, (2) it must be the
# home side of exactly one LiveOnSat fixture in that competition at the right time (live: kick-off from 25 min before to 30 min after
# the programme starts; repeat: up to 72 h earlier). Then the title is "Home vs Away", the secondary title the competition, the red ball
# is set for the live showing (repeats are never live) and the description says where and when. A stadium that is not in the table
# and a city that does not match leave the programme exactly as it was. Domestic football whose description already names the sides
# ("Werder Bremen host Borussia Moenchengladbach in the Bundesliga at Weserstadion") gets "Home vs Away" as the title too.
RUSH_VENUES = {
    "emirates": "Arsenal", "anfield": "Liverpool", "etihad": "Manchester City", "old trafford": "Manchester United",
    "stamford bridge": "Chelsea", "tottenham hotspur": "Tottenham", "villa park": "Aston Villa", "st james": "Newcastle",
    "selhurst": "Crystal Palace", "amex": "Brighton", "falmer": "Brighton", "stadium of light": "Sunderland",
    "city ground": "Nottingham Forest", "london stadium": "West Ham", "molineux": "Wolverhampton",
    "bernabeu": "Real Madrid", "camp nou": "Barcelona", "spotify camp": "Barcelona", "montjuic": "Barcelona",
    "metropolitano": "Atletico Madrid", "san mames": "Athletic Club", "anoeta": "Real Sociedad", "balaidos": "Celta Vigo",
    "sanchez pizjuan": "Sevilla", "mestalla": "Valencia", "villamarin": "Real Betis", "la ceramica": "Villarreal",
    "ciudad de valencia": "Levante", "riazor": "Deportivo", "iberia": "Iberia 1999",
    "allianz arena": "Bayern Munich", "signal iduna": "Borussia Dortmund", "red bull arena in leipzig": "RB Leipzig",
    "bayarena": "Bayer Leverkusen", "deutsche bank park": "Eintracht Frankfurt", "mhp arena": "Stuttgart",
    "prezero": "Hoffenheim", "snp arena": "Hoffenheim", "europa-park": "Freiburg", "volksparkstadion": "Hamburg",
    "weserstadion": "Werder Bremen", "borussia-park": "Borussia Monchengladbach", "rheinenergie": "Koln",
    "wals-siezenheim": "Salzburg", "red bull arena in salzburg": "Salzburg", "merkur arena": "Sturm Graz",
    "wankdorf": "Young Boys", "st. jakob": "Basel", "st jakob": "Basel", "stockhorn": "Thun",
    "san siro": "Inter", "giuseppe meazza": "Inter", "allianz stadium": "Juventus", "olimpico": "Roma",
    "maradona": "Napoli", "gewiss": "Atalanta", "dall'ara": "Bologna", "artemio franchi": "Fiorentina",
    "parc des princes": "Paris Saint-Germain", "velodrome": "Marseille", "parc olympique lyonnais": "Lyon",
    "groupama stadium": "Lyon", "pierre-mauroy": "Lille", "louis ii": "Monaco", "allianz riviera": "Nice",
    "roazhon": "Rennes", "beaujoire": "Nantes",
    "alvalade": "Sporting", "da luz": "Benfica", "dragao": "Porto", "municipal de braga": "Braga", "pedreira": "Braga",
    "johan cruijff": "Ajax", "amsterdam arena": "Ajax", "philips stadion": "PSV", "de kuip": "Feyenoord",
    "afas": "AZ Alkmaar", "goffertstadion": "NEC Nijmegen", "jan breydel": "Club Brugge", "lotto park": "Anderlecht",
    "constant vanden stock": "Anderlecht", "joseph marien": "Union St Gilloise", "ghelamco": "AA Gent",
    "planet group arena": "AA Gent",
    "celtic park": "Celtic", "ibrox": "Rangers", "tynecastle": "Hearts", "aspmyra": "Bodo/Glimt", "brann stadion": "Brann",
    "parken": "Copenhagen", "right to dream": "Midtjylland", "mch arena": "Midtjylland", "ceres park": "AGF Aarhus",
    "strandvallen": "Mjallby", "farum": "Nordsjaelland",
    "karaiskakis": "Olympiacos", "apostolos nikolaidis": "Panathinaikos", "toumba": "PAOK", "opap arena": "AEK Athens",
    "maksimir": "Dinamo Zagreb", "poljud": "Hajduk Split", "rajko mitic": "Red Star Belgrade", "marakana": "Red Star Belgrade",
    "doosan": "Viktoria Plzen", "fortuna arena": "Slavia Prague", "epet arena": "Sparta Prague", "generali arena": "Sparta Prague",
    "ali sami yen": "Galatasaray", "rams park": "Galatasaray", "sukru saracoglu": "Fenerbahce", "vodafone park": "Besiktas",
    "tupras": "Besiktas", "papp laszlo": "Ferencvaros", "groupama arena": "Ferencvaros", "vasil levski": "CSKA Sofia",
    "balgarska armia": "CSKA Sofia", "georgi asparuhov": "Levski Sofia", "huvepharma": "Ludogorets",
    "turner stadium": "Hapoel Be'er Sheva", "sammy ofer": "Maccabi Haifa", "bloomfield": "Maccabi Tel Aviv",
    "gsp stadium": "Omonia Nicosia", "tsirio": "Apollon Limassol", "stelios kyriakides": "Pafos",
    "vazgen sargsyan": "Ararat-Armenia", "central stadium": "Kairat Almaty", "stozice": "Celje", "arena z'dezele": "Celje",
    "air albania": "Egnatia", "estadi nacional": "Inter Escaldes", "victoria stadium": "Lincoln Red Imps",
    "enea stadion": "Lech Poznan", "inea stadion": "Lech Poznan", "pilsudski": "Legia Warsaw",
    "vonovia ruhrstadion": "Bochum", "olympiastadion in berlin": "Hertha", "bremer brucke": "Osnabruck",
    "rosaleda": "Malaga", "martinez valero": "Elche", "olimpiyskiy": "Dynamo Kyiv", "kauno": "Kauno Zalgiris", "darius": "Kauno Zalgiris",
}
RUSH_UEFA_RE = re.compile(r"(?i)\buefa\s+(champions|europa|conference)\s+league\b(?!\s+(?:women|youth))")
RUSH_FROM_RE = re.compile(r"^\s*(?:From|Vom)\s+(?:the\s+)?(?P<venue>.+?)\s+in\s+(?P<city>[^.]+?)\s*\.", re.I)
RUSH_HOST_RE = re.compile(r"^\s*(?:The\s+)?(?P<a>[^,]{2,60}?)\s*(?:\([\d-]+\)\s*)?(?:hosts?|face|faces|welcomes?|visits?|takes?\s+on)\s+(?:the\s+)?(?P<b>[^,]{2,60}?)\s*"
                          r"(?:\([\d-]+\)\s*)?in\s+(?:the\s+)?[A-Z][\w .'-]+?\s+(?:at|action|match|clash|regular)\b", re.U)
RUSH_TEAM_SPORT_RE = re.compile(r"(?i)\b(soccer|football|basketball|hockey|baseball)$")


def _plain(v):
    v = unicodedata.normalize("NFKD", (v or "").lower())
    return "".join(c for c in v if not unicodedata.combining(c))


def rush_fixture_titles(records):
    fixtures = [f for f in load_code_fixtures() if not BEIN_SKIP_FIXTURE_RE.search(f"{f[1]} {f[2]} {f[3]}")]
    live_n = rep_n = host_n = 0
    for rec in records:
        if not str(rec.get("id", "")).startswith("CARIB.RushSports"):
            continue
        for ev in rec["events"]:
            title, desc = ev.get("title") or "", (ev.get("desc") or "")
            title_clean = re.sub(r"(?i)^\s*live\s*[:\-]\s*", "", title)
            u, fm = RUSH_UEFA_RE.search(title_clean), RUSH_FROM_RE.match(desc)
            if " vs " in title:
                continue
            league_game = bool(re.search(r"(?i)\b(soccer|football)$", title_clean)) and not re.search(
                r"(?i)youth|women|nations league|american|nfl|college|ncaa|canadian|gaelic|aussie", title_clean)
            if fm and (u or league_game):
                venue, city = fm["venue"].strip(), fm["city"].strip()
                key = {"champions": "champions league", "europa": "europa league",
                       "conference": "conference league"}[u.group(1).lower()] if u else ""
                start = ev["start"]
                pool = [f for f in fixtures if (not key or key in _plain(f[1])) and start - timedelta(hours=72) <= f[0] <= start + timedelta(minutes=30)]
                v, c = _plain(venue), _plain(city)
                homes = {team for stad, team in RUSH_VENUES.items() if stad in v or stad in f"{v} in {c}"}
                hit = [f for f in pool if any(_team_words(t) & _team_words(f[2]) for t in homes)] if homes else []
                if not hit:                                    # the city is part of the home side's name (Zagreb, Plzen ...)
                    cw = {w for w in re.split(r"[^a-z]+", c.split(",")[0]) if len(w) >= 4}
                    hit = [f for f in pool if cw & set(re.split(r"[^a-z]+", _plain(f[2])))]
                live_hit = [f for f in hit if start - timedelta(minutes=25) <= f[0] <= start + timedelta(minutes=30)]
                hit = live_hit or hit
                if len(hit) > 1:
                    hit.sort(key=lambda f: abs((f[0] - start).total_seconds()))
                    if abs((hit[0][0] - start).total_seconds()) == abs((hit[1][0] - start).total_seconds()):
                        continue
                if not hit:
                    continue
                ko, comp_full, a, b = hit[0][0], hit[0][1], hit[0][2], hit[0][3]
                a, b = CODE_NAME_TIDY.get(a, a), CODE_NAME_TIDY.get(b, b)
                short, _, detail = comp_full.partition(" - ")
                parts = [x.strip() for x in city.split(",") if x.strip()]
                place = f"{parts[0]}, {parts[-1]}" if len(parts) > 1 else city
                uk = ko.astimezone(LONDON)
                is_live = bool(live_hit)
                ev["title"], ev["sub"], ev["no_lead"] = f"{a} vs {b}", short.strip(), True
                ev["desc"] = " ".join((
                    f"{short.strip()}{', ' + detail.strip() if detail.strip() else ''}.", f"At {venue}, {place}.",
                    f"Kick-off: {uk:%H:%M}." if is_live else f"Match played {uk:%a} {uk.day} {uk:%b}, {uk:%H:%M} UK time."))
                if is_live:
                    ev["live"] = True
                    live_n += 1
                elif ko < start - timedelta(minutes=30):             # a showing that starts after the match began: a repeat
                    ev["live"], ev["never_live"] = False, True
                    rep_n += 1
                continue
            m = RUSH_HOST_RE.match(re.sub(r"\s+", " ", desc))
            if m and RUSH_TEAM_SPORT_RE.search(title_clean):
                ev["title"] = f"{m['a'].strip()} vs {m['b'].strip()}"
                ev["sub"] = ev.get("sub") or re.sub(r"(?i)\s+(soccer|football|basketball|hockey|baseball)$", "", title_clean).strip() or title_clean
                ev["no_lead"] = True
                host_n += 1
    if live_n or rep_n or host_n:
        print(f"  Rush Sports: {live_n} live UEFA matches and {rep_n} repeats named from LiveOnSat's list, {host_n} domestic titles from the description")


# Rush Sports cricket (26 Nov 2026, user: the "Test Cricket" block at 10pm on Rush Sports 1 is untitled and not LIVE): the guide only says
# "Test Cricket" / "2nd Test, Day 1." (repeats: "Repeat CRICKET -New Zealand v India 2026 2nd Test Mach Day 3."). The repeat text names the
# teams; for the rest ESPN's cricket list (cricket_matches) is asked which match has its Day N first ball within 3 h before / 1 h after the
# programme - exactly one must, or nothing changes. Then: title "New Zealand v India", secondary title "2nd Test, Day 1", the red ball
# for the live showing (repeats, "catch all action" and highlights never), and the pipeline adds "First ball: HH:MM." by itself.
RUSH_TEST_RE = re.compile(r"(?i)(\d)(?:st|nd|rd|th)\s+test\b.*?\bday\s*(\d)")
RUSH_REPEAT_RE = re.compile(r"(?i)repeat\s+cricket\s*-?\s*(?P<a>[A-Za-z][A-Za-z .']+?)\s+v\s+(?P<b>[A-Za-z][A-Za-z .']+?)\s+(?:20\d\d\s+)?"
                            r"(\d)(?:st|nd|rd|th)\s+test\b.*?\bday\s*(\d)")
_ORD = {"1": "1st", "2": "2nd", "3": "3rd"}


def rush_cricket_titles(records):
    done = 0
    for rec in records:
        if not str(rec.get("id", "")).startswith("CARIB.RushSports"):
            continue
        for ev in rec["events"]:
            title, desc = ev.get("title") or "", ev.get("desc") or ""
            if not re.search(r"(?i)\bcricket\b", title) or " v " in title:
                continue
            rep = RUSH_REPEAT_RE.search(desc)
            if rep:
                n, day = rep.group(3), rep.group(4)
                ev["title"] = f"{rep['a'].strip()} v {rep['b'].strip()}"
                ev["sub"] = f"{_ORD.get(n, n + 'th')} Test, Day {day}"
                ev["desc"], ev["live"], ev["never_live"], ev["no_lead"] = f"Replay of Day {day}.", False, True, True
                done += 1
                continue
            t = RUSH_TEST_RE.search(desc)
            if not t:
                continue
            n, day = t.group(1), int(t.group(2))
            replay = bool(re.search(r"(?i)catch\s*all|highlights|repeat|replay", desc))
            matches, full = cricket_matches(), _START_CACHE.get("cricket_full") or []
            start = ev["start"]
            hit = [i for i, (when, names, label) in enumerate(matches)
                   if i < len(full) and full[i] and start - timedelta(hours=26) <= when + timedelta(days=day - 1) <= start + timedelta(hours=1)]
            live_hit = [i for i in hit if start - timedelta(hours=3) <= matches[i][0] + timedelta(days=day - 1) <= start + timedelta(hours=1)]
            hit = live_hit or hit
            if len(hit) != 1:
                continue
            ev["title"], ev["sub"], ev["no_lead"] = full[hit[0]], f"{_ORD.get(n, n + 'th')} Test, Day {day}", True
            if live_hit and not replay:
                ev["live"] = True
                ev["desc"] = f"Live Test cricket, {ev['sub']}."
            else:
                ev["live"], ev["never_live"] = False, True
                ev["desc"] = f"Replay of Day {day}."
            done += 1
    if done:
        print(f"  Rush Sports: {done} Test cricket programmes titled")


# STARZPLAY Sports 1-3 football (26 Nov 2026, user): epgshare's Starzplay listing stops after the day it is made: from the next day
# the three channels are one-hour "StarzPLAY Sports 1" filler blocks, so Friday's Bundesliga and Serie A games were not listed at all.
# FotMob's Starzplay page (fotmob.com/tv-guide/me/starzplay) carries the Middle East TV guide in the page itself (__NEXT_DATA__,
# "tvguide-groups:me": day -> leagues -> matches with utcTime, home, away and the channel names) - the matches with "STARZPLAY" among
# the channels. FotMob names no Starzplay channel, so a game goes on Sports 1, and on Sports 2 when Sports 1 already has one at the
# same time, then on Sports 3 (which has AEW / racing: only where it is empty filler). A game replaces only filler blocks (a real
# programme is never overwritten); where epgshare already lists the same teams at that time the game is left as epgshare has it. If FotMob can't
# be read the listing stays exactly as epgshare gives it.
STARZ_URL = "https://www.fotmob.com/tv-guide/me/starzplay"
STARZ_CHANNELS = ("AE.StarzplaySports1", "AE.StarzplaySports2", "AE.StarzplaySports3")
STARZ_FILLER_RE = re.compile(r"(?i)^\s*starz\s*play\s+sports\s*\d?\s*$")
STARZ_GAME_MINUTES = 120


def fetch_starz_football():
    page = fetch(STARZ_URL, headers={"User-Agent": HEADERS["User-Agent"], "Accept": "text/html"}, retries=2,
                 label="FotMob Starzplay guide")
    if not page:
        return []
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))["props"]["pageProps"]["fallback"]
    except (ValueError, KeyError, TypeError):
        return []
    out = []
    for days in (v for v in data.values() if isinstance(v, dict)):
        for leagues in days.values():
            for lg in leagues or []:
                for mt in lg.get("matches") or []:
                    if not any(re.search(r"(?i)starz", c.get("name") or "") for c in mt.get("channels") or []):
                        continue
                    try:
                        ko = datetime.fromisoformat(mt["utcTime"].replace("Z", "+00:00"))
                        a, b = mt["home"]["name"], mt["away"]["name"]
                    except (KeyError, ValueError):
                        continue
                    out.append({"ko": ko, "a": a, "b": b, "league": lg.get("leagueName") or "", "round": str(lg.get("leagueStage") or "")})
    return sorted(out, key=lambda x: x["ko"])


def starz_football(records):
    games = fetch_starz_football()
    if not games:
        print("  Starzplay football (FotMob): not available this run - epgshare's listing kept")
        return
    recs = {r["id"]: r for r in records if r.get("id") in STARZ_CHANNELS}
    if not recs:
        return
    placed = skipped = 0
    for g in games:
        s, e = g["ko"], g["ko"] + timedelta(minutes=STARZ_GAME_MINUTES)
        words = (_team_words(g["a"]), _team_words(g["b"]))
        if any(any(abs((ev["start"] - s).total_seconds()) < 3 * 3600 and words[0] & _team_words(ev.get("title") or "")
                   and words[1] & _team_words(ev.get("title") or "") for ev in r["events"]) for r in recs.values()):
            continue                                       # epgshare already lists this game
        for cid in STARZ_CHANNELS:
            r = recs.get(cid)
            if not r:
                continue
            over = [ev for ev in r["events"] if ev["start"] < e and ev.get("stop", ev["start"]) > s]
            if any(not STARZ_FILLER_RE.match(ev.get("title") or "") for ev in over):
                continue                                   # a real programme is there: next channel
            new = []
            for ev in r["events"]:
                if ev not in over:
                    new.append(ev)
                    continue
                if ev["start"] < s:
                    new.append(dict(ev, stop=s))
                if ev.get("stop", ev["start"]) > e:
                    new.append(dict(ev, start=e))
            comp = CODE_NAME_TIDY.get(g["league"], g["league"])
            rnd = f"Round {g['round']}" if g["round"].isdigit() else ""
            uk = s.astimezone(LONDON)
            new.append({"start": s, "stop": e, "title": f"{g['a']} vs {g['b']}", "sub": comp, "live": True, "no_lead": True,
                        "desc": " ".join(x for x in (f"{comp}{', ' + rnd if rnd else ''}.", f"Kick-off: {uk:%H:%M}.") if x)})
            r["events"] = sorted(new, key=lambda ev: ev["start"])
            placed += 1
            break
        else:
            skipped += 1
    print(f"  Starzplay football (FotMob): {len(games)} games, {placed} added to the guide, {skipped} left out (no free channel)")


# Croatian channels (26 Nov 2026, user: Arena Sport Croatia shouts): MAXtv gives "CONFERENCE LEAGUE: HAJDUK - ST. TRUIDEN, football"
# and "NFL: DALLAS - PHILADELPHIA, American football". Anything mostly in capitals becomes: the sides as "Hajduk vs St. Truiden",
# the secondary title "Football - Conference League" (the layout the Bosnian Arena channels use), the sport word's Croatian turned
# into English (nogomet = football, boks = boxing ...), and ordinary capitals ("Red Bull: BTS With a Legend") for the rest. Short
# acronyms stay in capitals (NFL, NHL, ABA, UFC, BIH ...). Titles already in normal case are left alone.
HR_SPORTS = {"football": "Football", "nogomet": "Football", "soccer": "Football", "basketball": "Basketball", "kosarka": "Basketball",
             "handball": "Handball", "rukomet": "Handball", "boks": "Boxing", "boxing": "Boxing", "american football": "American football",
             "ice hockey": "Ice hockey", "hokej": "Ice hockey", "water polo": "Water polo", "vaterpolo": "Water polo",
             "athletics": "Athletics", "atletika": "Athletics", "tennis": "Tennis", "tenis": "Tennis", "volleyball": "Volleyball",
             "odbojka": "Volleyball", "motorsport": "Motorsport", "cycling": "Cycling", "biciklizam": "Cycling", "mma": "MMA",
             "rugby": "Rugby", "golf": "Golf", "baseball": "Baseball", "skiing": "Skiing", "skijanje": "Skiing"}
HR_FORMATS = {"emisija": "Show", "show": "Show", "series": "Series", "serija": "Series", "dokumentarni film": "Documentary",
              "documentary": "Documentary", "film": "Film", "studio": "Studio", "magazin": "Magazine", "magazine": "Magazine",
              "highlights": "Highlights", "sazetak": "Highlights"}
HR_COMPS = {"EUROPE LEAGUE": "Europa League", "EUROPA LEAGUE": "Europa League", "EUROPEALIGA": "Europa League",
            "CONFERENCE LEAGUE": "Conference League", "CHAMPIONS LEAGUE": "Champions League", "LEAGUE PRVAKA M": "Champions League", "CHAMPIONS LEAGUE M": "Champions League",
            "LEAGUE PRVAKA": "Champions League", "ITALIAN LEAGUE": "Serie A", "FRENCH LEAGUE": "Ligue 1", "SPANISH LEAGUE": "LaLiga",
            "GERMAN LEAGUE": "Bundesliga", "ENGLISH LEAGUE": "Premier League", "QUALIFICATIONS FOR WC": "World Cup Qualifiers",
            "ROMANIAN LEAGUE": "Romanian League", "ABA LEAGUE": "ABA League"}
HR_ACRONYMS = {"NFL", "NHL", "NBA", "MLB", "ABA", "UFC", "MMA", "BIH", "WC", "UK", "USA", "HNL", "WBA", "IBF", "WBO", "AEK", "PSV",
               "PSG", "AZ", "FC", "SC", "AC", "AS", "BSK", "NEC", "KK", "HNK", "NK", "GNK", "RB", "VFB", "TSG", "BTS", "UEFA", "FIFA",
               "FIBA", "EHF", "LIVE", "II", "III", "IV", "XC", "UCL", "UEL", "AFC", "CSKA", "SK", "FK", "OFK", "HSK", "WTA", "ATP", "PGA"}
HR_SMALL = {"of", "and", "the", "a", "in", "on", "at", "to", "for", "with", "vs", "de", "la", "del", "da", "do"}
HR_TEAMS = {"Naples": "Napoli", "Leverkuse": "Leverkusen", "Manchester U": "Manchester United", "Union Sg": "Union SG",
            "Bih": "BiH", "BIH": "BiH"}


def _hr_case(text):
    out = []
    for i, w in enumerate(re.split(r"(\s+)", text.strip())):
        if not w.strip():
            out.append(w)
            continue
        core = re.sub(r"[^\w]", "", w)
        if core.upper() in HR_ACRONYMS or (core.isdigit()):
            out.append(w)
        elif w.lower() in HR_SMALL and i:
            out.append(w.lower())
        else:                                              # "ST." -> "St.", "AND/OR" kept simple, "WBA/IBF/WBO" per part
            out.append("/".join("-".join(p[:1].upper() + p[1:].lower() if p.upper() not in HR_ACRONYMS else p
                                         for p in seg.split("-")) for seg in w.split("/")))
    return " ".join("".join(out).split())


def hr_titles(records):
    done = 0
    for rec in records:
        if not str(rec.get("id", "")).startswith("HR."):
            continue
        for ev in rec["events"]:
            title = (ev.get("title") or "").strip()
            letters = [c for c in title if c.isalpha()]
            if len(letters) < 6 or sum(c.isupper() for c in letters) < 0.6 * len(letters):
                continue
            body, sport = title, ""
            parts = [x.strip() for x in title.split(",")]
            while len(parts) > 1:                                        # trailing ", football" / ", show, series"
                last = _plain(parts[-1])
                if last in HR_SPORTS and not sport:
                    sport = HR_SPORTS[last]
                elif last in HR_FORMATS and not sport.endswith(HR_FORMATS[last]):
                    sport = HR_FORMATS[last] if not sport or HR_FORMATS[last] == "Series" else sport
                else:
                    break
                parts.pop()
            body = ", ".join(parts)
            comp, sep, rest = body.partition(": ")
            if not sep:
                comp, rest = "", body
            elif " - " not in rest and not re.search(r"(?i)\bstudio\b", sport):
                pass
            if comp and HR_SPORTS.get(_plain(comp)) and "-" not in rest:      # "FOOTBALL: CONFERENCE LEAGUE, studio"
                comp, rest, sport = "", f"{HR_COMPS.get(rest.strip().upper(), _hr_case(rest))} {sport}".strip() if sport else _hr_case(rest), HR_SPORTS[_plain(comp)]
            comp_en = HR_COMPS.get(comp.strip().upper(), _hr_case(comp)) if comp else ""
            sides = [x.strip() for x in rest.split(" - ")]
            if len(sides) == 2 and all(sides):
                a, b = (HR_TEAMS.get(_hr_case(x), _hr_case(x)) for x in sides)
                ev["title"] = f"{a} vs {b}"
                ev["sub"] = " - ".join(x for x in (sport, comp_en) if x) or ev.get("sub") or ""
            else:
                ev["title"] = f"{comp_en}: {_hr_case(rest)}" if comp_en else _hr_case(rest)
                if sport and not ev.get("sub"):
                    ev["sub"] = sport
            done += 1
    if done:
        print(f"  Croatia: {done} upper-case titles tidied")


# Premier Sports UK, direct (26 Nov 2026, user): Sky's UK feed for Premier Sports 2 (and 1) lists "This is Premier Sports 2 UK Sky"
# where the Irish feed has the live games, leaving 5:40pm - 10:15pm blank on the night. premiersports.com/gb/tv-guide lists every
# programme for 14 days in the page itself (no login, no script call): one <div class="all-channels-container" id="thu_nov_26"> per
# day holding rows (<div class="channel">), each row a spacer <div style="width: 612px;"> then <div class="program-box" style="width:
# 204px" data-program='{"league_title":"NHL","timings":"2:40 - 5:40","title":"Chicago at Seattle"}'>, with <span>LIVE</span> inside a live
# one. 3.4 px = 1 minute (204 px = an hour). The rows have no names: row 1 = Premier Sports 1, row 2 = Premier Sports 2 (confirmed
# on 26 Nov against Sky's listing); the times are 12-hour with no am/pm, so am/pm comes from the pixel position; times are UK time.
# premier_merge() makes this page the primary source for UK.PremierSports1/2 and Sky the backup (26 Nov 2026, user), but only when
# this page's rows agree with Sky's own listing (at least half of Sky's programmes start at the same minute as one of the page's).
PREMIER_URL = "https://www.premiersports.com/gb/tv-guide"
PREMIER_ROWS = {0: "UK.PremierSports1", 1: "UK.PremierSports2"}
PREMIER_PX_PER_MIN = 3.4
PREMIER_FILLER_RE = re.compile(r"(?i)^\s*this is premier sports [12]\b.*$")
PREMIER_DAY_RE = re.compile(r'<div class="all-channels-container[^"]*"\s+id="([a-z]{3})_([a-z]{3})_(\d{1,2})">(.*?)'
                            r'(?=<div class="all-channels-container|\Z)', re.S)
PREMIER_ITEM_RE = re.compile(r'<div class="inline-block text-black"\s+style="width:\s*([\d.]+)px;?"\s*>\s*</div>'
                             r'|<div class="[^"]*program-box[^"]*"[^>]*?width:\s*([\d.]+)px[^>]*?data-program="([^"]*)"[^>]*>(.*?)</div>',
                             re.S)
_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def premier_name(league, team):
    """site competition + match -> "League: A v B" (Sky's short names written out, SHOUTING lower-cased)"""
    league, team = re.sub(r"\s+", " ", league or "").strip(), re.sub(r"\s+", " ", team or "").strip()
    fix = lambda v: (" ".join(w if len(w) <= 4 or not w.isalpha() or w == "LALIGA" else w.capitalize() for w in v.split())
                     if v.isupper() and " " in v else v)       # "UCL MATCH HIGHLIGHTS" -> "UCL Match Highlights"; LALIGA stays
    league = SKY_COMP_NAMES.get(league.upper(), fix(league))
    team = fix(team)
    if not team or league.lower() == team.lower():
        return team or league
    return f"{league}: {team}" if league else team


def parse_premier_sports(page, today):
    """{our channel id: [{start, stop, title, sub, live, desc}]} from the TV guide page (UK time)"""
    out = {cid: [] for cid in PREMIER_ROWS.values()}
    for _, mon, day, body in PREMIER_DAY_RE.findall(page):
        month = _MONTHS.get(mon)
        if not month:
            continue
        year = today.year + (1 if month < today.month - 6 else -1 if month > today.month + 6 else 0)
        try:
            d = datetime(year, month, int(day), tzinfo=LONDON)
        except ValueError:
            continue
        rows = re.split(r'<div class="channel"[^>]*>', body)[1:]
        for idx, cid in PREMIER_ROWS.items():
            if idx >= len(rows):
                continue
            x = 0.0
            for sp, width, raw, inner in PREMIER_ITEM_RE.findall(rows[idx]):
                if sp:
                    x += float(sp)
                    continue
                w = float(width)
                try:
                    info = json.loads(html.unescape(raw))
                    t = re.match(r"\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", info.get("timings") or "")
                    h1, m1, h2, m2 = (int(v) for v in t.groups())
                except (ValueError, AttributeError, TypeError):
                    x += w
                    continue
                where = x / PREMIER_PX_PER_MIN                     # minutes after midnight, from the pixels
                m12 = (h1 % 12) * 60 + m1                           # 12-hour clock minutes
                start_min = min((m12, m12 + 720), key=lambda m: abs(m - where))
                dur = (((h2 % 12) * 60 + m2) - m12) % 720 or 720
                x += w
                league = re.sub(r"\s+", " ", info.get("league_title") or "").strip()
                title = re.sub(r"\s+", " ", info.get("title") or "").strip()
                if not title:
                    continue
                name = premier_name(league, title)
                start = (d + timedelta(minutes=start_min)).astimezone(timezone.utc)
                out[cid].append({"start": start, "stop": start + timedelta(minutes=dur), "title": name, "sub": "",
                                 "live": bool(re.search(r">\s*LIVE\s*<", inner)), "desc": ""})
    for cid in out:
        out[cid].sort(key=lambda e: e["start"])
    return out


def premier_merge(sky, theirs_by_id, label):
    """Premier Sports' own listing is the primary source for its channels; Sky's is the backup.
    Per channel: if the site's rows agree with Sky's (at least half of Sky's programmes start within 2 minutes of one of the site's)
    every Sky programme inside the site's time span is replaced by the site's, keeping Sky's description where the start matches
    (the UK page has none; the Irish page has its own, used when Sky has nothing). Sky's programmes before/after the site's span stay.
    A channel that fails the check, or has no rows, keeps Sky's listing untouched."""
    for cid, theirs in theirs_by_id.items():
        evs = sky.get(cid)
        if not evs or len(theirs) < 5:
            continue
        theirs = sorted(theirs, key=lambda e: e["start"])
        lo, hi = theirs[0]["start"], theirs[-1]["stop"]
        real = [e for e in evs if lo <= e["start"] < hi and not PREMIER_FILLER_RE.match(e.get("title") or "")]
        near = lambda a, b: abs((a - b).total_seconds()) <= 120
        agree = sum(1 for e in real if any(near(e["start"], t["start"]) for t in theirs))
        if len(real) < 5 or agree < len(real) / 2:
            print(f"  Premier Sports {label}: {cid} does not match Sky's listing ({agree} of {len(real)} start times agree)"
                  " - Sky's listing kept")
            continue
        out = []
        for e in evs:
            if e["start"] < lo:
                out.append(dict(e, stop=min(e["stop"], lo)))
            elif e["start"] >= hi:
                out.append(e)
        for t in theirs:
            m = [e for e in evs if near(e["start"], t["start"]) and not PREMIER_FILLER_RE.match(e.get("title") or "")]
            sky_desc = (m[0].get("desc") or "") if m else ""
            ev = {k: v for k, v in t.items() if not k.startswith("_")}
            ev["desc"] = sky_desc if len(sky_desc) >= len(ev.get("desc") or "") else ev.get("desc", "")
            if m and not ev.get("sub"):
                ev["sub"] = m[0].get("sub") or ""
            out.append(ev)
        sky[cid] = sorted(out, key=lambda e: e["start"])
        print(f"  Premier Sports {label}: {cid} {len(theirs)} programmes from the site ({agree} of {len(real)} agree with Sky)")


def premier_fill(sky, days, debug=False):
    page = fetch(PREMIER_URL, headers={"User-Agent": HEADERS["User-Agent"], "Accept": "text/html"},
                 retries=2, label="Premier Sports TV guide")
    if not page or "all-channels-container" not in page:
        print("  Premier Sports TV guide: not available this run - Sky's listing kept")
        return
    premier_merge(sky, parse_premier_sports(page, days[0]), "UK guide")


# Premier Sports Ireland (26 Nov 2026, user: "the same for Ireland?"): premiersportsireland.com lists PS One / PS Two for 12 days in
# the page (one <div class="schedule_list_wrap"> per day, each programme a schedule_list_item with the time "5:40 pm", a
# schedule_ttl (competition), a schedule_team (match, "LIVE: A v B" when live) and a schedule_cnt description). Sky's Irish feed already
# is the primary source for the Irish channels too (26 Nov 2026, user): it also cures Sky's cut-off titles ("UEFA Europa Conference...")
# and run-together names ("Torreensev Celtic"). Sky stays as the backup, see premier_merge().
PREMIER_IE_URL = "https://premiersportsireland.com/"
PREMIER_IE_ALT = {"PS One": "IE.PremierSports1", "PS Two": "IE.PremierSports2"}


def parse_premier_ireland(page, today):
    """{our id: [{start, title, league, team, live}]} - UK/Irish clock times (the same offset)"""
    out = {cid: [] for cid in PREMIER_IE_ALT.values()}
    seen = {cid: 0 for cid in out}
    for wrap in re.split(r'<div class="schedule_list_wrap"[^>]*>', page)[1:]:
        items = re.split(r'<div class="schedule_list_item\b[^"]*"[^>]*>', wrap)[1:]
        cid = None
        for it in items:
            m = re.search(r'alt="(PS (?:One|Two))"', it)
            if m:
                cid = PREMIER_IE_ALT[m.group(1)]
                break
        if not cid:
            continue
        base = today + timedelta(days=seen[cid])
        seen[cid] += 1
        dm = re.search(r"current_date:\s*(\d{4})-(\d{2})-(\d{2})", wrap)
        if dm:
            base = datetime(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)), tzinfo=LONDON)
        day = datetime(base.year, base.month, base.day, tzinfo=LONDON)
        prev = -1
        for it in items:
            tm = re.search(r'<div class="schedule_time"><span>\s*(\d{1,2}):(\d{2})\s*([ap]m)', it, re.I)
            if not tm:
                continue
            h, mi = int(tm.group(1)) % 12 + (12 if tm.group(3).lower() == "pm" else 0), int(tm.group(2))
            if h * 60 + mi < prev:
                day += timedelta(days=1)                                  # past midnight
            prev = h * 60 + mi
            g = lambda cls: re.sub(r"\s+", " ", html.unescape(re.sub(
                r"<[^>]+>", " ", (re.search(r'class="%s[^"]*"[^>]*>(.*?)</(?:h3|span|div)>' % cls, it, re.S) or [0, ""])[1]))).strip()
            league, team = g("schedule_ttl"), g("schedule_team")
            live = bool(re.match(r"(?i)live\s*:", team))
            team = re.sub(r"(?i)^live\s*:\s*", "", team)
            if league.isupper() and len(league) > 4:
                league = league.title()
            desc = g("schedule_cnt")
            out[cid].append({"start": (day + timedelta(hours=h, minutes=mi)).astimezone(timezone.utc),
                             "title": premier_name(league, team), "sub": "", "live": live, "desc": desc})
    for evs in out.values():
        evs.sort(key=lambda e: e["start"])
        for a, b in zip(evs, evs[1:]):
            a["stop"] = b["start"]
        if evs:
            evs.pop()                      # the last row has no end time: Sky's own entry stays for it
    return out


def premier_ireland_fix(sky):
    page = fetch(PREMIER_IE_URL, headers={"User-Agent": HEADERS["User-Agent"], "Accept": "text/html"},
                 retries=2, label="Premier Sports Ireland guide")
    if not page or "schedule_list_item" not in page:
        print("  Premier Sports Ireland guide: not available this run - Sky's listing kept")
        return
    premier_merge(sky, parse_premier_ireland(page, datetime.now(LONDON)), "Ireland guide")


# Astro Premier League 3 / 4 / 5 idle listing (5 Nov 2026, user request): these pop-up channels only have programmes on match days
# (Astro lists nothing in between and sends no filler), so the empty time reads \"no information\" in the player. astro_idle_fill()
# fills every gap with 2-hour blocks titled with the channel name, secondary title ASTRO_IDLE_SUB and description
# ASTRO_IDLE_DESC - from now to the last listed match; after the last match (or with no match at all) for EMPTY_FILLER_HOURS (24 h)
# only, because PlaylistLabs only appends after the last programme it holds, so a longer filler would hide a match Astro lists
# later. A match Astro adds LATER INSIDE a gap that was already filled is hidden for the same reason (rare: Astro lists the
# week ahead). Channels: ASTRO_IDLE_CHANNELS. Runs after astro_matchday().
ASTRO_IDLE_CHANNELS = {"MY.AstroPremierLeague3": "Astro Premier League 3", "MY.AstroPremierLeague4": "Astro Premier League 4",
                       "MY.AstroPremierLeague5": "Astro Premier League 5"}
ASTRO_IDLE_SUB = "No live match scheduled at this time."
ASTRO_IDLE_DESC = "{name}: no live match scheduled at this time. Check back later."


def astro_idle_fill(records):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for cid, name in ASTRO_IDLE_CHANNELS.items():
        rec = next((r for r in records if r.get("id") == cid), None)
        if rec is None:
            rec = {"id": cid, "name": name, "tz": ZoneInfo(EPGSHARE["my"]["tz"]), "place": "Malaysia",
                   "filler": False, "back_to_back": True, "events": []}
            records.append(rec)
        real = sorted((e for e in rec["events"] if e.get("stop") and e["stop"] > now), key=lambda e: e["start"])
        cursor, added, matches = now, [], 0
        for ev in real:
            matches += 1
            if ev["start"] > cursor:
                added.append((cursor, ev["start"]))
            cursor = max(cursor, ev["stop"])
        horizon = now + timedelta(hours=EMPTY_FILLER_HOURS)
        if cursor < horizon:
            added.append((cursor, horizon))
        n = 0
        for a, b in added:
            for x, y in filler_blocks(a, b):
                rec["events"].append({"start": x, "stop": y, "title": name, "sub": ASTRO_IDLE_SUB, "live": False,
                                      "never_live": True, "no_lead": True, "desc": ASTRO_IDLE_DESC.format(name=name)})
                n += 1
        rec["events"].sort(key=lambda e: e["start"])
        print(f"  Astro idle listing {cid}: {matches} match programme(s), {n} idle block(s)")


# Country dividers (5 Nov 2026, user request): the "### FRANCE ###" rows in the user's Continuum playlist are not channels; each needs a
# programme named after its country. One placeholder channel per divider, id DIV.<NAME WITHOUT SPACES/SYMBOLS> (e.g. DIV.FRANCE,
# DIV.UKIRELAND), display name "### FRANCE ###" (the row's own name, so searching "###" in PlaylistLabs' EPG-id search lists them
# all), programmes titled with just the country in capitals ("FRANCE"), no secondary title, no description, 6-hour blocks on a fixed
# UTC grid for DIVIDER_DAYS days from now (nothing changes between runs, so PlaylistLabs' append-only import is no problem).
# The user relinks each divider row to its DIV id; the list below is the 35 dividers of the Continuum playlist (5 Nov 2026).
DIVIDERS = ["UK & IRELAND", "USA", "CANADA", "INDIA", "AUSTRALIA", "JAMAICA", "MIDDLE EAST", "NETHERLANDS", "GERMANY", "FRANCE",
            "SPAIN", "SWITZERLAND", "POLAND", "ITALY", "LATVIA", "GREECE", "ALBANIA", "BULGARIA", "ROMANIA", "BOSNIA", "SERBIA",
            "CROATIA", "SLOVENIA", "TURKEY", "BRAZIL", "CYPRUS", "PORTUGAL", "BELGIUM", "FINLAND", "SWEDEN", "DENMARK", "NORWAY",
            "CZECHIA", "ISRAEL", "TANZANIA",
            "HONG KONG", "SINGAPORE", "INDONESIA", "MALAYSIA", "MIDDLE EAST & NORTH AFRICA"]    # last five added 11 Nov 2026 (user)
# 11 Nov 2026 (user): the five Asian / MENA dividers that were added to the playlists after 5 Nov still had a PlaylistLabs-made id
# (dummy-2848073). They get the NEW-ID family token (see the handover: new-id convention): DIV.HONGKONG.9dg8 ... - the display name
# stays "### HONG KONG ###" (so searching "###" still lists them all) and the guide text is just the country, like the other 35.
DIVIDER_TOKEN = "9dg8"
DIVIDER_TOKEN_NAMES = {"HONG KONG", "SINGAPORE", "INDONESIA", "MALAYSIA", "MIDDLE EAST & NORTH AFRICA"}
# 6 Nov 2026: PlaylistLabs kept showing "EPG data ... not available" for DIV.UKIRELAND and DIV.CANADA (identical to the 33 that worked, even
# after re-linking), so those two got fresh ids; the old ones are no longer written.
DIVIDER_ID_OVERRIDES = {"UK & IRELAND": "UKANDIRELAND", "CANADA": "CANADA1"}
DIVIDER_DAYS = 7
DIVIDER_BLOCK_HOURS = 6


def divider_records():
    now = datetime.now(timezone.utc)
    step = timedelta(hours=DIVIDER_BLOCK_HOURS)
    first = now.replace(hour=(now.hour // DIVIDER_BLOCK_HOURS) * DIVIDER_BLOCK_HOURS, minute=0, second=0, microsecond=0) - step
    end = now + timedelta(days=DIVIDER_DAYS)
    out = []
    for name in DIVIDERS:
        evs, t = [], first
        while t < end:
            evs.append({"start": t, "stop": t + step, "title": name, "sub": "", "desc": "", "live": False, "never_live": True,
                        "no_lead": True, "no_translate": True})
            t += step
        out.append({"id": "DIV." + DIVIDER_ID_OVERRIDES.get(name, re.sub(r"[^A-Za-z0-9]+", "", name))
                          + (f".{DIVIDER_TOKEN}" if name in DIVIDER_TOKEN_NAMES else ""),
                    "name": f"### {name} ###", "tz": timezone.utc,
                    "place": "", "filler": False, "back_to_back": True, "events": evs})
    return out


def build_xmltv(records, suffix, minutes):
    """records: [{id, name, tz, place, filler, back_to_back, events:[{start,title,sub,live}]}]"""
    tv = ET.Element("tv", {"generator-info-name": "SPORT_epg.py",
                           "source-info-name": "Sport 5 + Charlton (IL), Novasports (GR), Ziggo GO (NL), Digi Sport + Prima Play (RO), tv-programa.bg (BG), Arena Sport (RS), Delo (SI), Telenet (BE), Movistar Plus+ (ES), MEO (PT), Claro (BR), IPKO (AL/XK), mujtvprogram.cz (CZ/SK), Onet (PL), Sky Italia (IT), MagentaTV (DE), Tata Play (IN), blue TV (CH), SFR (FR), Allente (SE/NO/DK), Now TV (HK), Sky TV guide (UK/IE), Cyta (CY), epgshare01.online (TR/LV/HK/ID/MENA/AE/FR/IT/SG/MY/AU/BR/UK/IE/NZ/US/CA), beIN SPORTS (AU/MY/SG/HK/TH/ID), DStv (ZA/Africa)"})
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    global _CUR_TZ
    count, listed = 0, []
    collect_rugby_rounds(records)                  # rugby rounds named in other listings
    share_tnt_text(records)                        # TNT Sports 2 cricket borrows TNT Sports 1's day summary (20 Nov 2026)
    learn_team_sports(records)                     # which team belongs to which sport (20 Nov 2026)
    for rec in records:
        cid, name = f"{rec['id']}{suffix}", rec["name"]
        _CUR_TZ = rec["tz"]                        # own-date removal uses the channel's own day too
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
            title = ev["title"] if ev.get("no_translate") else en(ev["title"])
            if ev.get("no_translate") and rec["place"] == "Italy":
                title = it_teams_en(title)
            sub = en(ev.get("sub") or "") or None
            if rec.get("fix_caps") or cid.startswith(PL_PRODUCTIONS):
                title, sub = fix_caps(title), fix_caps(sub) or None
            title, sub = conj_and(title), (conj_and(sub) if sub else sub)          # "Europa E Conference" -> "Europa & Conference"
            if rec["place"] == "Italy" and not ev.get("no_translate"):
                title, sub = it_and(title), (it_and(sub) if sub else sub)          # (not a "Team A - Team B" match title)
            if cid.startswith("CY."):
                title = cy_versus(title, bool(ev.get("live")))   # "A - B 3/11/26" -> "A vs B 3/11/26"
            elif cid.startswith(X_VS_REGIONS):
                title = x_versus(title)                          # "A x B - Serie A" -> "A vs B - Serie A"
            title = match_versus(title, bool(ev.get("live")), (stop - start).total_seconds() / 60)   # every channel (5 Nov 2026)
            loc = ev["start"].astimezone(rec["tz"])
            uk = ev["start"].astimezone(LONDON)
            when = f"{uk:%a %d %b, %H:%M}"
            orig = ""          # the original (untranslated) title is no longer shown
            about = "" if ev.get("desc") in DESC_PENDING else en(ev.get("desc") or "")
            if rec.get("fix_caps") or cid.startswith(PL_PRODUCTIONS):
                about = fix_caps(about)
            if sub and cid.startswith(SUB_KICKOFF_REGIONS):
                sub = nz_sub(sub)                               # "PL:" -> "Premier League:"
                title, sub = nz_teams_first(title, sub)         # teams in the title
                title, sub = nz_session(title, sub)             # "X: D9 Aft" -> "Day 9, Afternoon"
            sub = carabao_name(sub, title, ev["start"])          # "Carabao Cup 4th Round"
            about = carabao_name(about, title, ev["start"])
            about = fuller_about(title, about)                    # "M4." -> "Coverage of the FIP World Cup Qatar 2026."
            if not about.strip() and sub and VAGUE_CODE.fullmatch(sub.strip().rstrip(".")):   # no description, only a code
                alt = fuller_about(title, sub)                 # as the secondary title: "MD 9" + "Highlights from the Ligue 1 2026/27."
                if alt != sub:
                    about = alt
            if cid in PART_TIME_CHANNELS and PART_TIME_FILLER_RE.match(title or ""):    # the standard "no schedule" wording
                title, sub = name, EMPTY_FILLER_SUB
                about = EMPTY_FILLER_DESC.format(name=name)
                ev["no_lead"], ev["never_live"] = True, True
            fixture = None
            if cid.startswith(KICKOFF_LIVE) and stop - start >= timedelta(minutes=90):
                fixture = find_fixture(title, ev["start"], timedelta(minutes=5), timedelta(minutes=45))
                if fixture and fixture[2]:
                    if about.strip().rstrip(".") == (sub or "").strip().rstrip("."):
                        about = ""                              # the description only repeated it
                    sub = fixture[2]                            # "Round 4" -> "Carabao Cup 4th Round"
            about = about + ("" if about[-1:] in ".!?…" else ".") + " " if about else ""
            lead = (sub if sub[-1:] in ".!?…" else sub + ".") + " " if sub and not ev.get("no_lead") else ""
            desc = dedupe_sentences(re.sub(r"\s+", " ",
                                           f"{'LIVE. ' if ev['live'] and not cid.startswith(tuple(EVENT_LIVE_PREFIX)) else ''}"
                                           f"{lead}{about}{orig}").strip())   # (no "LIVE." under a 🔴 title)
            if rec["filler"]:
                for a, b in filler_blocks(last_stop or now, start):
                    add_programme(tv, cid, a, b, f"{title} ({when})", "Coming up",
                                  f"Upcoming on {name}: {title}, {when} UK "
                                  f"({loc:%H:%M} {rec['place']}).", False)
                    count += 1
            is_live = (ev["live"] or kickoff_now(f"{sub or ''} {desc}", loc, uk)
                       or desc_says_live(desc)                 # description says "live"
                       or fixture is not None)                 # starts at a real kick-off (KICKOFF_LIVE)
            if cid.startswith(tuple(SKY_UHD_EVENT)):          # Sky Sports UHD 1/2: all but filler is live
                is_live = bool(ev.get("uhd_live", not UHD_FILLER.match(title or "")))
            if ev.get("never_live"):                           # Astro placeholders / "Coming up"
                is_live = False
            if is_live and not really_live(title, cid):        # e.g. "End of Transmission"
                is_live = False
                desc = re.sub(r"^LIVE\.\s*", "", desc)
            if is_live and f1_is_replay(f"{title} {sub or ''}".strip(), start, stop):   # F1 repeat marked live by the source
                is_live = False
                desc = re.sub(r"^LIVE\.\s*", "", desc)
                F1_REPLAYS.append(cid)
            general = cid.startswith(GENERAL_CHANNELS)
            if general:                                        # BBC/ITV/RTÉ/Virgin: live sport events only
                is_live = is_live and general_sport_live(title, sub, desc, ev["live"])
                if not is_live:
                    desc = re.sub(r"^LIVE\.\s*", "", desc)
            red = is_live and (general or cid.startswith(tuple(EVENT_LIVE_PREFIX)) or live_event(title, sub))
            if red:                                            # 🔴: no "LIVE." in the description, plus
                desc = re.sub(r"^LIVE\.\s*", "", desc)        # kick-off/venue or the start time
                more = event_start_info(title, ev["start"])
                if more.startswith("Coverage from") and sub:   # teams in the secondary title
                    alt = event_start_info(f"{title}: {sub}", ev["start"])
                    if not alt.startswith("Coverage from"):
                        more = alt
                rugby_comp = _RUGBY_COMP.get(re.sub(r"(?i)^live\b[\s.,:;!-]*", "", title or ""))
                if rugby_comp and not sub:                     # rugby: competition (and round)
                    sub = rugby_comp
                ko = re.search(r"Kick-off: (\d{1,2}:\d{2})", more)
                if ko and sub and cid.startswith(SUB_KICKOFF_REGIONS) and "Kick-off" not in sub:
                    sub = f"{sub} – Kick-off {ko[1]}"           # Sky NZ: kick-off in the secondary title
                venue, sep, rest = more.partition("Kick-off:")
                if sep and venue.strip(" .") and venue.strip(" .") in desc:
                    more = sep + rest                          # venue already in the description
                if more not in desc:
                    desc = f"{desc} {more}".strip()
            add_programme(tv, cid, start, stop, live_title(title, cid, red) if is_live else title,
                          live_sub(sub) if is_live else sub, desc, is_live)
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


# Placeholders for empty channels (31 Oct 2026): a channel the script knows (epgshare01 "main" channels such as
# beIN SPORTS MAX 1/2 TR, Champions TV 3) but whose source lists nothing in these days used to be left
# out of the guide, so its rows showed no information at all. It now gets 2-hour blocks naming the channel for
# EMPTY_FILLER_HOURS (24 h, like the events guide: PlaylistLabs keeps what it loads, so a long placeholder would hide
# real listings that appear later). Real listings replace it on the next run; a channel that has programmes this run
# (own source, backup, carried over) is never touched. EXTRA_EMPTY_CHANNELS: channels with no source at all.
# Log: "Placeholders for empty channels: N".
EMPTY_CHANNELS = {}
EXTRA_EMPTY_CHANNELS = {"TR.beINSPORTS5": "beIN SPORTS 5",       # Digiturk refuses GitHub - no source
                        # Hub Premier 7-11 (3 Nov 2026): StarHub's overflow Premier League channels - no listings of their
                        # own (the guide has Hub Premier 1-6), so the standard "no schedule" blocks (user request)
                        **{f"SG.HubPremier{n}": f"Hub Premier {n}" for n in range(7, 12)},
                        # Astro's pop-up channels (5 Nov 2026): when neither epgshare nor Astro lists anything
                        # (Premier League 3 / 4 / 5 have their own idle wording - astro_idle_fill)
                        "MY.AstroCricket": "Astro Cricket"}
EMPTY_FILLER_HOURS = 24
EMPTY_FILLER_SUB = "No schedule available at this time."
OLD_EMPTY_FILLER_SUBS = ("No schedule available",)       # the wording used until 3 Nov 2026 (so old placeholders in the previous guide are still recognised)
EMPTY_FILLER_DESC = ("{name}: no programmes are listed for this channel at the moment. The schedule will appear "
                     "here when the broadcaster publishes it (some channels only run during events).")


# Part-time channels (2 Nov 2026): between events these channels' sources send their own filler ("End of Transmission" on
# beIN SPORTS 4 / 5 Singapore, "Stay tuned for the next broadcast" on beIN SPORTS 4 / 5 Hong Kong, "No information" on beIN SPORTS 3
# Hong Kong). Those blocks are rewritten to the standard wording above (the channel name as the title, "No schedule available at this time.",
# "...: no programmes are listed for this channel at the moment ...") - never live.
PART_TIME_CHANNELS = ("SG.beINSPORTS4", "SG.beINSPORTS5", "HK.beINSPORTS3", "HK.beINSPORTS4", "HK.beINSPORTS5",
                      # StarHub's own "End of Transmission" blocks (3 Nov 2026: user asked for Hub Premier 2 and Hub Sports 8;
                      # the same blocks are on Hub Premier 2-6 and Hub Sports 3-8, so all of them)
                      "SG.HubPremier2", "SG.HubPremier3", "SG.HubPremier4", "SG.HubPremier5", "SG.HubPremier6",
                      "SG.HubSports3", "SG.HubSports4", "SG.HubSports5", "SG.HubSports6", "SG.HubSports7", "SG.HubSports8",
                      # Croatia (26 Nov 2026, user): MAXtv's "Program announcement" blocks on Sport Klub 7-12 and Arena Sport 5, 6, 9, 10
                      *(f"HR.SportKlub{n}" for n in range(7, 13)), "HR.ArenaSport5", "HR.ArenaSport6", "HR.ArenaSport9", "HR.ArenaSport10")
PART_TIME_FILLER_RE = re.compile(r"(?i)^\s*(end of transmission|stay tuned for the next broadcast|no information(?: available)?"
                                 r"|program(?:me)? announcement)\W*$")


def add_empty_placeholders(tv, listed):
    """[(id, name)] of the channels given a placeholder (see EMPTY_CHANNELS)."""
    have = {c.get("id") for c in tv.iter("channel")}
    wanted = {**EMPTY_CHANNELS, **{k: v for k, v in EXTRA_EMPTY_CHANNELS.items() if k not in EMPTY_CHANNELS}}
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    added = []
    for cid in sorted(wanted):
        if cid in have:
            continue
        name = wanted[cid]
        c = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = name
        listed.append((cid, name))
        for a, b in filler_blocks(now, now + timedelta(hours=EMPTY_FILLER_HOURS)):
            add_programme(tv, cid, a, b, name, EMPTY_FILLER_SUB, EMPTY_FILLER_DESC.format(name=name), False)
        added.append((cid, name))
    return added


# Idle-gap fillers (12 Nov 2026, user: "the filler is a good idea"): event-only channels (MySports 2-9, Sky Sport 253-255, Prima Sport PPV 1-4,
# V Sport Live ...) and the odd hole in a normal channel's listings used to show "No information" between programmes. A gap of
# IDLE_GAP_MIN_MINUTES or more between a channel's REAL programmes, within the next EMPTY_FILLER_HOURS (24 h - PlaylistLabs keeps what it
# loads, so a long filler could hide a listing that appears later), now gets the SAME standard "no schedule" blocks as an empty channel (title =
# the channel name, EMPTY_FILLER_SUB, EMPTY_FILLER_DESC). Never overlaps a real programme; channels with no programmes at all are left to
# add_empty_placeholders; the DIV dividers are skipped. Set IDLE_GAP_FILLER = False to switch it off. Log: "Idle-gap fillers: N blocks on M channel(s)".
IDLE_GAP_FILLER = True
IDLE_GAP_MIN_MINUTES = 60
IDLE_GAP_SKIP = ("DIV.",)


def add_idle_gap_fillers(tv):
    """[(id, blocks added)] - fills gaps between a channel's real programmes with the standard 'no schedule' blocks."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    horizon = now + timedelta(hours=EMPTY_FILLER_HOURS)
    names = {c.get("id"): (c.findtext("display-name") or c.get("id")) for c in tv.iter("channel")}
    spans = {}
    for p in tv.findall("programme"):
        try:
            s = datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
            e = datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
        except (TypeError, ValueError):
            continue
        spans.setdefault(p.get("channel"), []).append((s, e))
    added = []
    for cid in sorted(spans):
        if cid.startswith(IDLE_GAP_SKIP) or cid not in names:
            continue
        name, cur, gaps = names[cid], now, []
        for s, e in sorted(spans[cid]):
            if e <= cur:
                continue
            if s > cur:
                gaps.append((cur, min(s, horizon)))
            cur = max(cur, e)
            if cur >= horizon:
                break
        if cur < horizon:
            gaps.append((cur, horizon))
        n = 0
        for a, b in gaps:
            if b - a < timedelta(minutes=IDLE_GAP_MIN_MINUTES):
                continue
            for x, y in filler_blocks(a, b):
                add_programme(tv, cid, x, y, name, EMPTY_FILLER_SUB, EMPTY_FILLER_DESC.format(name=name), False)
                n += 1
        if n:
            added.append((cid, n))
    return added


# Safeguard (28 Oct 2026): when a source fails for one run (seen 28 Oct 16:03 UTC: Cyta and the
# Bulgarian site both returned nothing, so 30 channels vanished from the guide until the next run),
# the channels missing from this run are kept from the previous guide - only their programmes that
# haven't finished yet. A channel this run did fetch is never touched. Carried programmes run out by
# themselves (the SPORT guide lists about a week), so a channel removed on purpose disappears within
# a week, or straight away with --no-carry. Log: "Kept from the previous guide ...".
CARRY_OVER = True
# Channels removed on purpose are never carried over (31 Oct 2026: beIN AU - the streams are unreliable - came
# back from the previous guide for a week after its sources were removed).
CARRY_SKIP = ("AU.beINSPORTS",
              # dropped 1 Nov 2026 (user): Alkass 1-8 - epgshare's BEIN1 data ran out (ended 31 Oct), AE1 looked like filler
              "MENA.Alkass",
              # dropped 31 Oct 2026 (user): sources removed/never matched, only old listings were being carried
              "DK.ViasatSportUltra", "SE.ATGLive", "HK.NowGolf3", "HK.PremierSports",
              # dropped 4 Nov 2026 (user: not important; the playlists lose them too) - only 1-2 old programmes were being carried
              "HK.NBATV", "HK.Now668", "HK.NowSports647", "HK.NowSportsPlus", "IT.SkySport259",
              # dropped 11 Nov 2026 (user): SuperSport / ESPN Africa (DStv ZA. and AF. channels) - removed from the playlists
              "ZA.", "AF.",
              # moved 14 Nov 2026 (user): the 7 Sky Cinema channels now come from GENERAL_epg.py - never carry them here, or the same ids
              # would sit in two guides for a week
              "UK.SkyCinema",
              # dropped 19 Nov 2026 (user): the Cytavision Real Time channels - we don't have them; never carry the old ones over
              ) + tuple(f"CY.CytavisionSports{n}RealTime" for n in range(1, 9))


def carry_over(tv, listed, prev_path):
    """Add channels (and their programmes still to finish) that are in the previous guide at
    prev_path but have no programmes in this run. Returns [(id, name, programmes kept)]."""
    try:
        if prev_path.endswith(".gz"):
            with gzip.open(prev_path, "rb") as f:
                old = ET.parse(f).getroot()
        else:
            old = ET.parse(prev_path).getroot()
    except (OSError, ET.ParseError, EOFError) as err:
        print(f"  NOTE: previous guide not readable for carry-over ({err})")
        return []
    have = {p.get("channel") for p in tv.iter("programme")}
    now = datetime.now(timezone.utc)
    kept_progs = {}
    for p in old.iter("programme"):
        cid = p.get("channel")
        if cid in have or (cid or "").startswith(CARRY_SKIP):
            continue
        if p.findtext("sub-title") in (EMPTY_FILLER_SUB,) + OLD_EMPTY_FILLER_SUBS:      # last run's "No schedule available at this time." placeholder (old wording too) - regenerate, don't carry
            continue
        try:
            stop = datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
        except (TypeError, ValueError):
            continue
        if stop > now:
            kept_progs.setdefault(cid, []).append(p)
    if not kept_progs:
        return []
    names = {c.get("id"): (c.findtext("display-name") or c.get("id")) for c in old.iter("channel")}
    in_tv = {c.get("id") for c in tv.iter("channel")}
    kept = []
    for cid in sorted(kept_progs):
        if cid not in in_tv:
            c = ET.SubElement(tv, "channel", {"id": cid})
            ET.SubElement(c, "display-name", {"lang": "en"}).text = names.get(cid, cid)
            listed.append((cid, names.get(cid, cid)))
        for p in kept_progs[cid]:
            tv.append(p)
        kept.append((cid, names.get(cid, cid), len(kept_progs[cid])))
    return kept


def fill_missing_days(tv, prev_path):
    """For sources that lost whole days this run (DSTV_MISSING), add the previous guide's
    programmes in those days on channels that DO have programmes this run (channels with none
    are carry_over's job), where they don't overlap this run's programmes. [(id, n)]."""
    windows = {}
    for prefix, (country, *_rest) in SS_REGIONS.items():
        if DSTV_MISSING.get(country):
            windows[prefix + "."] = DSTV_MISSING[country]
    if not windows:
        return []
    try:
        if prev_path.endswith(".gz"):
            with gzip.open(prev_path, "rb") as f:
                old = ET.parse(f).getroot()
        else:
            old = ET.parse(prev_path).getroot()
    except (OSError, ET.ParseError, EOFError) as err:
        print(f"  NOTE: previous guide not readable to fill missing days ({err})")
        return []

    def span(p):
        return (datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z"),
                datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z"))

    have = {}
    for p in tv.iter("programme"):
        cid = p.get("channel") or ""
        if any(cid.startswith(w) for w in windows):
            try:
                have.setdefault(cid, []).append(span(p))
            except (TypeError, ValueError):
                pass
    now, added = datetime.now(timezone.utc), {}
    for p in old.iter("programme"):
        cid = p.get("channel") or ""
        wins = next((w for pre, w in windows.items() if cid.startswith(pre)), None)
        if not wins or cid not in have:
            continue
        try:
            a, b = span(p)
        except (TypeError, ValueError):
            continue
        if b <= now or not any(lo <= a < hi for lo, hi in wins):
            continue
        if any(a < y and x < b for x, y in have[cid]):
            continue
        tv.append(p)
        have[cid].append((a, b))
        added[cid] = added.get(cid, 0) + 1
    return sorted(added.items())


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
# ALTERNATIVE CHANNELS on team v team events (22 Nov 2026, user): a LIVE "A v B" block in a team sport (cricket, rugby, basketball, ice hockey ...) gets
# "This match is also available on X and Y." - at most TWO other channels, taken from watch_channels.CHANNELS (the channels the user has) in the order
# UK free-to-air, Sky, TNT, then overseas, ONLY channels with English commentary. Football is left to football_epg.py (all channels) and the US sports to TEAMS_epg.py
# (two). A channel counts when its own listing is on air at kick-off + 20 to 30 minutes and names both sides (same test as football_epg.py). Never fails the run.
ALT_LINE = "This match is available on {chs}."
ALT_MAX = 2
ALT_NOT_ENGLISH = set()          # ids of channels WITHOUT English commentary, left out of the alternatives (22 Nov 2026, user: Cytavision Sport 3, Now Premier League, beIN, Hub all have English commentary)
ALT_SPORTS = {"Cricket", "Netball", "Rugby League", "Rugby Union", "Basketball", "American Football", "Ice Hockey", "Baseball", "Aussie Rules", "Volleyball", "Handball"}
_ALT_SKIP_RE = re.compile(r"(?i)\b(?:highlights|replays?|classic|classics|reload|preview|review|magazine|build-?up|analysis|round-?up|rewind)\b|\bthis is\b")
_ALT_WOMEN_RE = re.compile(r"(?i)\bwomen|\bladies\b|\blpga\b|\bwsl\b|\bnwsl\b|\bwbbl\b|\bwnba\b|\bwpl\b|\bwnbl\b|\bnrlw\b|\baflw\b|\bpwr\b|\bnetball\b")
_ALT_AGE_RE = re.compile(r"(?i)\bu-?(\d{2})\b")


def team_sport_of(title, sub, cid, desc):
    """The team sport ('Rugby Union' ...) a 'A v B' block belongs to, or None (football, individual sports, anything not recognised)"""
    try:
        body = LIVE_LEAD_RE.sub("", title or "")
        said = re.match(r"(?i)^(" + "|".join(sorted(map(re.escape, ALT_SPORTS), key=len, reverse=True)) + r")\.\s", body)
        if said:                                           # the title already says it: "Cricket. New Zealand v India"
            return next(x for x in ALT_SPORTS if x.lower() == said.group(1).lower())
        sport = add_sport(title, sub, cid, desc, learn=True)
        if sport is None and TEAM_SPORT and FIXTURE_RE.search(body):
            sport = team_sport(f"{body} {sub or ''}")
    except Exception:
        return None
    return sport if sport in ALT_SPORTS else None


def alt_sides(title, sub):
    """(side A, side B) from the sub-title or the end of the title ('Rugby Union. Premiership: Harlequins v Bristol Bears'), or None"""
    for text in ((sub or "").strip(), LIVE_LEAD_RE.sub("", (title or "").strip()).rsplit(": ", 1)[-1].strip()):
        text = re.split(r"\s+-\s+|\s+\(|,\s", text)[0]
        parts = re.split(r"\s+v\s+", text)
        if len(parts) == 2 and all(2 < len(x.strip()) <= 40 for x in parts):
            return parts[0].strip(), parts[1].strip()
    return None


# EVENT NAMES instead of sides (22 Nov 2026, user): golf, Formula 1 and MotoGP (one tournament / race weekend = one broadcast). The FULL name must be on both
# listings - no shortened names ("Australian PGA Champ", "GP Katar", "Qatar GP" never count) - and the series must be the same (F1 Academy is not Formula 1, Moto3 is not MotoGP).
# Tennis, snooker, darts, bowls, cycling ... are left out on purpose: several matches / courts / stages run at once, so the same event name would send people to the wrong one.
_GOLF_NAME_RE = re.compile(r"((?:[A-Z][\w'&.-]*|&)(?: (?:[A-Z][\w'&.-]*|of|de|&)){0,6}? (?:Championship|Open|Classic|Invitational|Challenge|Masters|Trophy|Pro-Am|Tournament|Cup|Series))\b")
_GOLF_GENERIC = {"the", "world", "championship", "open", "classic", "masters", "trophy", "tour", "cup", "series", "final", "finals", "grand", "tournament",
                 "invitational", "challenge", "pro", "am", "golf", "pga", "lpga", "dp", "men", "women", "international", "national", "of", "de", "and"}
_GP_BEFORE_RE = re.compile(r"(?i)\b([a-z][\w'-]+) grand prix\b")
_GP_OF_RE = re.compile(r"(?i)\bgrand prix (?:of|de|d') ?([a-z][\w'-]+)")
_MOTOR_SERIES = (("f1academy", re.compile(r"(?i)\bf1 academy\b")), ("moto3", re.compile(r"(?i)\bmoto ?3\b")), ("moto2", re.compile(r"(?i)\bmoto ?2\b")),
                 ("motogp", re.compile(r"(?i)\bmoto ?gp\b")), ("f1", re.compile(r"(?i)\bformula 1\b|\bf1\b(?! academy)")))
_GP_SKIP = {"formula", "f1", "the", "a", "motogp", "moto", "heineken", "airways"}


def _ev_norm(text):
    return " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9&']+", " ", unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower())).strip() + " "


def event_key(title, sub):
    """('golf', ' australian pga championship ') / ('motor', (' qatar grand prix ', 'f1')) for a block whose FULL event name is written out, else None"""
    text = f"{LIVE_LEAD_RE.sub('', title or '')} {sub or ''}"
    if re.search(r"(?i)\bgolf\b", text):
        for m in _GOLF_NAME_RE.finditer(text):
            name = _ev_norm(m.group(1))
            words = [w for w in name.split() if w not in _GOLF_GENERIC]
            if words and len(name.split()) >= 2:
                return "golf", name
        return None
    series = tuple(sorted(n for n, rx in _MOTOR_SERIES if rx.search(text)))
    if not series:
        return None
    for rx in (_GP_OF_RE, _GP_BEFORE_RE):                           # "Grand Prix of Valencia" and "Valencia Grand Prix" are the same full name
        m = rx.search(text)
        if m and m.group(1).lower() not in _GP_SKIP:
            return "motor", (f" {_ev_norm(m.group(1)).strip()} grand prix ", series)
    return None


def event_match(key, text):
    """the other listing carries the same FULL event name (either name may be the longer one) and, for racing, the same series"""
    kind, val = key
    other = event_key(text, "")
    if kind == "golf":
        t = _ev_norm(text)
        return val in t or bool(other and other[0] == "golf" and other[1] in val)
    name, series = val
    if not other or other[0] != "motor" or other[1][1] != series:
        return False
    return name in other[1][0] or other[1][0] in name or name in _ev_norm(text)


def add_alternatives(tv):
    try:
        import watch_channels as wc
    except Exception as e:
        print(f"  NOTE: watch_channels.py not available ({e}) - no alternatives on team events")
        return 0
    try:
        listings = wc.load_listings(sport_root=tv)
    except Exception as e:
        print(f"  Channel listings not read ({e}) - no alternatives on team events")
        return 0
    chans = [(cid, name, fam) for cid, name, fam in wc.CHANNELS if cid not in ALT_NOT_ENGLISH and not re.search(r"4K|UHD", name)]
    seen = changed = 0
    for p in tv.iter("programme"):
        try:
            if not any((c.text or "") == "Live" for c in p.findall("category")):
                continue
            title, sub = p.findtext("title") or "", p.findtext("sub-title") or ""
            d = p.find("desc")
            desc = (d.text or "") if d is not None else ""
            if "available on" in desc or "also live on" in desc:
                continue
            sides = alt_sides(title, sub)
            key = None
            if not (sides and team_sport_of(title, sub, p.get("channel", ""), desc)):
                sides, key = None, event_key(title, sub)
                if not key:
                    continue
            seen += 1
            ko = datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
            ha, aa = _tnt5_aliases(sides[0]) if sides else [], _tnt5_aliases(sides[1]) if sides else []
            women = bool(_ALT_WOMEN_RE.search(f"{title} {sub}"))
            ages = set(_ALT_AGE_RE.findall(f"{title} {sub}"))
            fams = {}
            for cid, name, fam in chans:
                if cid == p.get("channel"):
                    continue
                for s0, e0, text in listings.get(cid, []):
                    if not (s0 <= ko + timedelta(minutes=20) and e0 >= ko + timedelta(minutes=30)) or _ALT_SKIP_RE.search(text):
                        continue
                    t = _tnt5_norm(text)
                    same = event_match(key, text) if key else (any(x in t for x in ha) and any(x in t for x in aa))
                    if (same and bool(_ALT_WOMEN_RE.search(text)) == women and set(_ALT_AGE_RE.findall(text)) == ages):
                        fams.setdefault(fam, []).append(name)
                        break
            names = wc.order_names(fams)[:ALT_MAX]
            if not names:
                continue
            line = ALT_LINE.format(chs=wc.join_names(names)).replace("This match", "This event" if key else "This match", 1)
            if d is None:
                d = ET.Element("desc", {"lang": "en"})
                kids = list(p)
                pos = 1 + sum(1 for c in kids if c.tag in ("title", "sub-title"))
                p.insert(pos, d)
            d.text = f"{desc} | {line}" if desc else line
            changed += 1
        except Exception as e:
            print(f"  WARNING: alternatives for one block failed ({e})")
    print(f"Alternative channels: {seen} live team / golf / racing events looked at, {changed} given an 'also available on' line")
    return changed


def main():
    ap = argparse.ArgumentParser(description="XMLTV guide of sports TV channels in several countries.")
    ap.add_argument("--out", default=OUTPUT_NAME, help=f"output file (default {OUTPUT_NAME})")
    ap.add_argument("--no-carry", action="store_true",
                    help="don't keep channels missing from this run from the previous guide")
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
    ap.add_argument("--no-slovenia", action="store_true", help="leave out NEO's Slovenian channels (Arena, Šport TV)")
    ap.add_argument("--no-croatia", action="store_true", help="leave out the Croatian channels (MAXtv)")
    ap.add_argument("--no-canal", action="store_true", help="leave out Canal+'s guide (Eurosport 360, Canal+ PL, Infosport+)")
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
    ap.add_argument("--no-albania", action="store_true", help="leave out the SuperSport and Tring Sport channels")
    ap.add_argument("--al-channels", default=AL_DEFAULT,
                    help="IPKO channel names, comma separated (default supersport-1 ... supersport-7, tring-sport-1 ... tring-sport-7)")
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
    ap.add_argument("--no-cyprus", action="store_true", help="leave out Cyta's Cytavision Sports channels")
    ap.add_argument("--cy-keywords", default="cyta sport",
                    help="Cyta channels to take: comma-separated entries, each matching when all its "
                         "words are in the channel name (default 'cyta sport')")
    ap.add_argument("--no-nowtv", action="store_true", help="leave out Now TV (Hong Kong)")
    ap.add_argument("--no-starhub", action="store_true", help="leave out StarHub (Hub Sports, Singapore)")
    ap.add_argument("--no-sky", action="store_true", help="leave out Sky's guide (UK/Ireland; epgshare01 fills in)")
    ap.add_argument("--now-channels", default=",".join(NOW_CHANNELS),
                    help="Now TV channel numbers, comma separated (e.g. 631,638)")
    ap.add_argument("--no-epgshare", action="store_true", help="leave out everything from epgshare01.online")
    ap.add_argument("--no-bein-mena", action="store_true", help="don't read beIN's own Middle East guide (stays on epgshare BEIN1)")
    ap.add_argument("--no-skygo", action="store_true", help="don't read Sky Go's TV guide (Sky Sport NZ stays on epgshare NZ1)")
    ap.add_argument("--no-yourtv", action="store_true", help="don't read YourTV's Foxtel guide (Fox Sports + ESPN AU stay on epgshare AU1)")
    ap.add_argument("--no-astro", action="store_true", help="don't read Astro's own TV guide (the Astro channels stay on epgshare MY1)")
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
    il_yes = {}
    if not args.no_israel and YES_CHANNELS:            # Eurosport 1-2 Israel from yes (29 Oct 2026; empty - 403)
        print("Israel: reading yes TV guide (Eurosport 1-2) ...")
        il_yes = fetch_yes(il_days, args.debug)
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
        ro.update(fetch_programetv(ro_days, args.debug))
        print(f"  {sum(len(v) for v in ro.values())} programmes on {len(ro)} channel(s)")
    bg = {}
    if not args.no_bulgaria:
        bg_days = [datetime.now(SOFIA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Bulgaria: reading тв-програма.bg {bg_days[0]} to {bg_days[-1]} ...")
        bg = fetch_bulgaria(bg_days, args.bg_channels, args.debug)
        print(f"  {sum(len(v) for v in bg.values())} programmes on {len(bg)} channel(s)")
    arena, arena_ba = {}, {}
    if not args.no_arena:
        ar_days = [datetime.now(BELGRADE).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Balkans: reading Arena Sport TV page {ar_days[0]} to {ar_days[-1]} ...")
        arena = fetch_arena(ar_days, args.debug)
        print(f"  {sum(len(v) for v in arena.values())} programmes on {len(arena)} channel(s)")
        for url in ARENA_PAGES_BA:                     # Bosnia and Herzegovina feed (29 Oct 2026)
            got = fetch_arena(ar_days, args.debug, url=url, lang="bs-BA,bs;q=0.9,sr;q=0.8")
            if got:
                same = got == arena
                print(f"  Bosnia ({url}): {sum(len(v) for v in got.values())} programmes on {len(got)} channel(s)"
                      + (" - SAME as the Serbian page (probably a redirect) - not used" if same else "")
                      + (f": {', '.join(sorted(got))}" if not same else ""))
                if not same:
                    arena_ba = got
                    break
        else:
            print("  WARNING: no Bosnian Arena Sport page gave a schedule", file=sys.stderr)
        if MTS_CHANNELS:                               # (empty since 29 Oct 2026, late)
            print("Serbia: reading mts TV guide ...")
            arena.update(fetch_mts(ar_days, args.debug))
    neo = {}
    if not args.no_slovenia:                           # 29 Oct 2026
        si_days = [datetime.now(LJUBLJANA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Slovenia: reading NEO's TV guide (Arena Sport, Arena Premium, Arena Fight, Šport TV) "
              f"{si_days[0]} to {si_days[-1]} ...")
        neo = fetch_neo(si_days, args.debug)
        print(f"  {sum(len(v) for v in neo.values())} programmes on {len(neo)} channel(s), "
              f"{sum(e['live'] for v in neo.values() for e in v)} live")
    hrv = {}
    if not args.no_croatia:                            # 29 Oct 2026
        hr_days = [datetime.now(ZAGREB).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Croatia: reading MAXtv's TV guide (Arena, Sport Klub, MAX Sport, Sportska TV) "
              f"{hr_days[0]} to {hr_days[-1]} ...")
        hrv = fetch_maxtv(hr_days, args.debug)
        print(f"  {sum(len(v) for v in hrv.values())} programmes on {len(hrv)} channel(s), "
              f"{sum(e['live'] for v in hrv.values() for e in v)} live")
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
        print("Belgium: reading Telenet's full TV guide (Play Sports, Golf, DAZN, DAZN Pro League) ...")
        full = fetch_netherlands(be_days, "", args.debug, names=TELENET_CHANNELS,
                                 segment_url=TELENET_SEGMENT, headers=TELENET_HEADERS)
        for name, evs in full.items():                 # full schedule replaces the calendar's few events,
            cal = {e["start"]: e for e in be.get(name, [])}   # keeping its competition/round and LIVE
            for e in evs:
                c = cal.get(e["start"])
                if c:
                    e["live"] = True
                    e["sub"] = e["sub"] or c.get("sub", "")
            be[name] = evs
            print(f"  Telenet {name}: {len(evs)} programmes, {sum(e['live'] for e in evs)} live")
        if not full:
            print("  WARNING: Telenet's guide gave nothing - calendar events only", file=sys.stderr)
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
    cz, cz_sms = {}, {}
    if not args.no_czechia:
        cz_days = [datetime.now(PRAGUE).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Czechia: reading mujtvprogram.cz {cz_days[0]} to {cz_days[-1]} ...")
        cz = fetch_czechia(cz_days, args.cz_channels, args.debug)
        print(f"  {sum(len(v) for v in cz.values())} programmes on {len(cz)} channel(s)")
        print("Czechia: reading m.tv.sms.cz (Premier Sport 1, 3) ...")
        cz_sms = fetch_sms(cz_days, args.debug)
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
        for cid, alts in CH_FALLBACK.items():          # blue Sport 3/4: try the older live channel numbers
            if cid in [c.strip() for c in args.ch_channels.split(",")] and not swi.get(cid):
                for alt in alts:
                    got = fetch_switzerland(ch_days, alt, args.debug).get(alt)
                    print(f"  {CH_CHANNELS[cid][1]}: channel {cid} empty, channel {alt}: {len(got or [])} programmes")
                    if got:
                        swi[cid] = got
                        break
        print(f"  {sum(len(v) for v in swi.values())} programmes on {len(swi)} channel(s)")
    fra = {}
    if not args.no_france:
        fr_days = [datetime.now(PARIS).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"France: reading SFR TV guide {fr_days[0]} to {fr_days[-1]} ...")
        fra = fetch_france(fr_days, args.fr_channels, args.debug)
        print(f"  {sum(len(v) for v in fra.values())} programmes on {len(fra)} channel(s)")
    canal = {}
    if not args.no_france and not args.no_canal and CANAL_CHANNELS:
        print("France: reading Canal+'s TV guide (Eurosport 360 1-8, Canal+ Premier League, Infosport+) ...")
        canal = fetch_canal(max(args.days, 1), args.debug)
        print(f"  {sum(len(v) for v in canal.values())} programmes on {len(canal)} channel(s), "
              f"{sum(e['live'] for v in canal.values() for e in v)} live")
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
        if tld == "no":                                # V Sport 2 NO from RiksTV (29 Oct 2026)
            print("Norway: reading RiksTV guide (V Sport 2) ...")
            got = fetch_rikstv(nd_days, args.debug)
            if got:
                nordic[(prefix, zone, place, id(RIKSTV_CHANNELS))] = (RIKSTV_CHANNELS, got)
    ss = {}
    if SUPERSPORT and not args.no_supersport:
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
    cy = {}
    if not args.no_cyprus:
        cy_days = [datetime.now(NICOSIA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Cyprus: reading Cyta's TV guide {cy_days[0]} to {cy_days[-1]} ...")
        cy = fetch_cyprus(cy_days, args.cy_keywords, details=not args.no_desc, debug=args.debug)
        print(f"  {sum(len(v) for v in cy.values())} programmes on {len(cy)} channel(s)")
    now_hk = {}
    if not args.no_nowtv:
        hk_days = [datetime.now(ZoneInfo("Asia/Hong_Kong")).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Hong Kong: reading Now TV guide {hk_days[0]} to {hk_days[-1]} ...")
        now_hk = fetch_now(hk_days, args.now_channels, args.debug)
        print(f"  {sum(len(v) for v in now_hk.values())} programmes on {len(now_hk)} channel(s)")
    hub, mew = {}, {}
    if not args.no_starhub:
        sg_days = [datetime.now(ZoneInfo("Asia/Singapore")).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Singapore: reading StarHub's TV guide (Hub Sports) {sg_days[0]} to {sg_days[-1]} ...")
        hub = fetch_starhub(sg_days, args.debug)
        print(f"Singapore: reading mewatch (beIN SPORTS 4-5 SG) ...")
        mew = fetch_mewatch([datetime.now(timezone.utc).date() + timedelta(days=i) for i in range(max(args.days, 1))],
                            args.debug)
        print(f"  {sum(len(v) for v in hub.values())} programmes on {len(hub)} channel(s), "
              f"{sum(e['live'] for v in hub.values() for e in v)} live")
    sky = {}
    if not args.no_sky:
        uk_days = [datetime.now(LONDON).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"UK/Ireland: reading Sky's TV guide {uk_days[0]} to {uk_days[-1]} ...")
        sky = fetch_sky(uk_days, args.debug)
        print(f"  {sum(len(v) for v in sky.values())} programmes on {len(sky)} channel(s)")
        if sky:
            premier_fill(sky, uk_days, args.debug)            # Sky's "This is Premier Sports 2 UK Sky" blocks (26 Nov 2026)
            premier_ireland_fix(sky)                          # cut-off / run-together titles on the Irish feed
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
        if "nz" in [g.strip().lower() for g in args.epgshare.split(",")] and not args.no_skygo:   # 2 Nov 2026
            nz_days = [datetime.now(ZoneInfo(EPGSHARE["nz"]["tz"])).date() + timedelta(days=i) for i in range(max(args.days, 1))]
            print(f"New Zealand: reading Sky Go's TV guide {nz_days[0]} to {nz_days[-1]} (Sky Sport NZ) ...")
            skygo = fetch_skygo_nz(nz_days, args.debug)
            if skygo:
                eps.setdefault("nz", {}).update(skygo)       # replaces epgshare's NZ1 listing for these channels
                left = sorted({part for part in EPGSHARE["nz"]["channels"]} - set(skygo))
                print(f"  {sum(len(v) for v in skygo.values())} programmes on {len(skygo)} channel(s) from Sky Go"
                      + (f"; still on epgshare NZ1: {', '.join(left)}" if left else ""))
                if left:
                    gh_warn("Sky Go partly fell back", f"these Sky Sport NZ channels are on epgshare NZ1: {', '.join(left)}")
            else:
                print("  Sky Go gave nothing usable - Sky Sport NZ stays on epgshare NZ1")
                gh_warn("Sky Go fell back", "Sky Sport NZ is on epgshare NZ1 (Sky Go gave nothing usable)")
        if "au" in [g.strip().lower() for g in args.epgshare.split(",")] and not args.no_yourtv:   # 4 Nov 2026
            au_days = [datetime.now(ZoneInfo(EPGSHARE["au"]["tz"])).date() + timedelta(days=i) for i in range(max(args.days, 1))]
            print(f"Australia: reading YourTV's Foxtel guide {au_days[0]} to {au_days[-1]} (Fox Sports, ESPN) ...")
            yt = fetch_yourtv_au(au_days, args.debug)
            if yt:
                au_eps = eps.setdefault("au", {})
                for part, evs in yt.items():       # replaces AU1's listing; AU1 only fills the time before YourTV's first programme
                    yt_first = evs[0]["start"]
                    before = [{**e, "stop": min(e["stop"], yt_first)} for e in au_eps.get(part, []) if e["start"] < yt_first]
                    au_eps[part] = before + evs
                left = sorted(set(EPGSHARE["au"]["channels"]) - set(yt))
                print(f"  {sum(len(v) for v in yt.values())} programmes on {len(yt)} channel(s) from YourTV"
                      + (f"; still on epgshare AU1: {', '.join(left)}" if left else ""))
                if left:
                    gh_warn("YourTV partly fell back", f"these AU channels are on epgshare AU1: {', '.join(left)}")
            else:
                print("  YourTV gave nothing usable - the Australian channels stay on epgshare AU1")
                gh_warn("YourTV fell back", "Fox Sports + ESPN AU are on epgshare AU1 (YourTV gave nothing usable)")
        if "my" in [g.strip().lower() for g in args.epgshare.split(",")] and not args.no_astro:   # 5 Nov 2026
            my_days = [datetime.now(ZoneInfo(EPGSHARE["my"]["tz"])).date() + timedelta(days=i) for i in range(max(args.days, 1))]
            print(f"Malaysia: reading Astro's own TV guide {my_days[0]} to {my_days[-1]} (Premier League 1-5, Football, Grandstand, Arena, UHD, Sports Plus ...) ...")
            ast = fetch_astro_my(my_days, args.debug)
            if ast:
                for line in merge_astro_my(eps.setdefault("my", {}), ast):
                    print("  Astro " + line)
            else:
                print("  Astro gave nothing usable - the Astro channels stay on epgshare MY1")
                gh_warn("Astro fell back", "the Astro channels are on epgshare MY1 (Astro's guide gave nothing usable)")
        if "mena" in [g.strip().lower() for g in args.epgshare.split(",")] and not args.no_bein_mena:   # 2 Nov 2026
            mena_days = [datetime.now(timezone.utc).date() + timedelta(days=i) for i in range(max(args.days, 1))]
            print(f"Middle East: reading beIN's own TV guide {mena_days[0]} to {mena_days[-1]} (beIN SPORTS MENA) ...")
            bm = fetch_bein_mena(mena_days, args.debug)
            if bm:
                eps.setdefault("mena", {}).update(bm)       # replaces epgshare's BEIN1 listing for these channels
                left = sorted(set(EPGSHARE["mena"]["channels"]) - set(bm))
                print(f"  {sum(len(v) for v in bm.values())} programmes on {len(bm)} channel(s) from beIN"
                      + (f"; still on epgshare: {', '.join(left)}" if left else ""))
                unexpected = [x for x in left if x != "beINSPORTSFTA"]      # FTA never comes from beIN
                if unexpected:
                    gh_warn("beIN MENA partly fell back", f"these channels are on epgshare BEIN1: {', '.join(unexpected)}")
            else:
                print("  beIN gave nothing usable - the Middle East channels stay on epgshare BEIN1")
                gh_warn("beIN MENA fell back", "the Middle East beIN channels are on epgshare BEIN1 (beIN gave nothing usable)")
        if "turkey" in [g.strip().lower() for g in args.epgshare.split(",")]:   # 29 Oct 2026 (late)
            tr_days = [datetime.now(ZoneInfo("Europe/Istanbul")).date() + timedelta(days=i) for i in range(max(args.days, 1))]
            print("Turkey: reading Turkcell TV+ guide (S Sport 1-2, A Spor, TRT Spor - with descriptions) ...")
            tvp = fetch_tvplus(tr_days, args.debug)
            if tvp:
                eps.setdefault("turkey", {}).update(tvp)   # replaces epgshare's listing for these channels
            # (Digiturk refuses GitHub - HTTP 403, 30 Oct 2026 - so fetch_digiturk isn't called)
    if not args.no_bein:
        bn_days = [datetime.now(ZoneInfo("Asia/Singapore")).date() + timedelta(days=i - 1)
                   for i in range(max(args.days, 1) + 1)]      # from yesterday (UTC days, Asia is ahead)
        print(f"beIN SPORTS: reading beIN's guide {bn_days[0]} to {bn_days[-1]} ...")
        bein = fetch_bein(bn_days, args.bein, args.debug)
        print(f"  {sum(len(v) for g in bein.values() for v in g.values())} programmes on "
              f"{sum(len(g) for g in bein.values())} channel(s)")
    if not il and not ch1 and not gr and not nl and not ro and not bg and not arena and not sk and not be \
            and not es and not pt and not br and not al and not cz and not svk and not pl and not it and not de and not ind and not swi and not fra and not nordic and not bein and not ss and not eps and not now_hk and not sky and not cy and not hub and not mew and not canal and not hrv and not neo:
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
        force += [t for evs in arena_ba.values() for e in evs for t in (e["title"], e["sub"])]   # Bosnia (29 Oct, late)
        force += [t for evs in neo.values() for e in evs for t in (e["title"], e["sub"])]        # Slovenia (29 Oct, late)
        force += [t for evs in sk.values() for e in evs for t in (e["title"], e["sub"])]
        force += [t for evs in hrv.values() for e in evs for t in (e["title"], e["sub"])]    # Croatia (MAXtv): Latin script, so forced
        force += [e["sub"] for evs in be.values() for e in evs]
        force += [e["title"] for evs in es.values() for e in evs]
        force += [e["title"] for evs in pt.values() for e in evs]
        force += [e["title"] for evs in br.values() for e in evs]
        force += [e["title"] for evs in al.values() for e in evs]
        force += [e["title"] for evs in cz.values() for e in evs]
        force += [e["title"] for evs in svk.values() for e in evs]
        force += [e["title"] for evs in it.values() for e in evs if not e.get("no_translate")]
        force += [t for evs in de.values() for e in evs for t in (e["title"], e["sub"])]
        force += [e["title"] for evs in swi.values() for e in evs]
        force += [t for evs in nl.values() for t in dutch_to_translate(evs)]          # Ziggo (20 Nov 2026)
        force += [t for evs in fra.values() for e in evs for t in (e["title"], e["sub"])]
        force += [e["title"] for _, got in nordic.values() for evs in got.values() for e in evs]
        texts += [t for g in bein.values() for evs in g.values() for e in evs for t in (e["title"], e["sub"])]
        force += [t for evs in pl.values() for e in evs for t in (e["title"], e["sub"])]
        texts += [e["title"] for evs in now_hk.values() for e in evs]   # only Chinese text
        texts += [t for evs in cy.values() for e in evs for t in (e["title"], e["sub"])]   # only Greek text
        texts += [t for evs in sky.values() for e in evs for t in (e["title"], e["sub"])]
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
    for part, evs in il_yes.items():
        records.append({"id": f"IL.{part}", "name": next(n for p, n in YES_CHANNELS.values() if p == part),
                        "tz": ISRAEL, "place": "Israel", "filler": False, "back_to_back": True, "events": evs})
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
    for cid, evs in sky.items():
        uk = cid.startswith("UK.")
        records.append({"id": cid, "name": SKY_CHANNELS[cid][0], "tz": LONDON if uk else ZoneInfo("Europe/Dublin"),
                        "place": "UK" if uk else "Ireland", "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in cy.items():
        records.append({"id": f"CY.{cyta_part(chname)}", "name": chname, "tz": NICOSIA, "place": "Cyprus",
                        "filler": False, "back_to_back": True, "events": evs, "fix_caps": True})
    for part, evs in mew.items():
        records.append({"id": f"SG.{part}", "name": f"beIN SPORTS {part[-1]} SG", "tz": ZoneInfo("Asia/Singapore"),
                        "place": "Singapore", "filler": False, "back_to_back": True, "events": evs})
    for (kind, n), evs in hub.items():
        nm = "Sports" if kind == "S" else "Premier"
        records.append({"id": f"SG.Hub{nm}{n}", "name": f"Hub {nm} {n}", "tz": ZoneInfo("Asia/Singapore"),
                        "place": "Singapore", "filler": False, "back_to_back": True, "events": evs})
    for cid, evs in now_hk.items():
        part, chname = NOW_CHANNELS.get(cid, (f"Now{cid}", f"Now TV {cid}"))
        records.append({"id": f"HK.{part}", "name": chname, "tz": ZoneInfo("Asia/Hong_Kong"), "place": "Hong Kong",
                        "filler": False, "back_to_back": True, "events": evs})
    for group, got in eps.items():
        cfg = EPGSHARE[group]
        for part, evs in got.items():
            records.append({"id": f"{cfg['prefix']}.{part}", "name": cfg["channels"][part][0],
                            "tz": ZoneInfo(cfg["tz"]), "place": cfg["place"],
                            "filler": False, "back_to_back": True, "events": evs,
                            "backup": bool(cfg.get("backup")),
                            # Turkey's beIN channels: matches get the competition, kick-off and LIVE flag from LiveOnSat's list
                            "bein_guide": cfg["prefix"] == "TR" and part.startswith("beINSPORTS")})
    for cc, got in bein.items():
        place, zone = BEIN_COUNTRIES[cc][0], ZoneInfo(BEIN_COUNTRIES[cc][1])
        for name, evs in got.items():
            chname = f"{name} {cc.upper()}"
            part = re.sub(r"[^A-Za-z0-9]+", "", name) or "Channel"
            records.append({"id": f"{cc.upper()}.{part}", "name": chname, "tz": zone, "place": place,
                            "filler": False, "back_to_back": True, "events": evs, "bein_guide": True})
    for (prefix, zone, place, _), (table, got) in nordic.items():
        for cid, evs in got.items():
            part, chname = table.get(cid, (f"Channel{re.sub(r'[^A-Za-z0-9]+', '', cid)}",
                                           f"{place} channel {cid}"))
            records.append({"id": f"{prefix}.{part}", "name": chname, "tz": zone, "place": place,
                            "filler": False, "back_to_back": True, "events": evs})
    for part, evs in canal.items():
        records.append({"id": f"FR.{part}", "name": next(n for p, n in CANAL_CHANNELS.values() if p == part),
                        "tz": PARIS, "place": "France", "filler": False, "back_to_back": True, "events": evs})
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
        popup = bool(IT_POPUP_RE.match(chname))              # Sky Sport 251-258: "Coming up" blocks between matches (5 Nov 2026)
        records.append({"id": f"IT.{part}", "name": chname, "tz": ROME, "place": "Italy",
                        "filler": popup and not args.no_filler, "back_to_back": not popup, "events": evs})
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
    for part, evs in cz_sms.items():
        records.append({"id": f"CZ.{part}", "name": next(n for p, n in SMS_CHANNELS.values() if p == part),
                        "tz": PRAGUE, "place": "Czechia", "filler": False, "back_to_back": True, "events": evs})
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
    for part, evs in neo.items():
        name = next(n for p, n in NEO_CHANNELS.values() if p == part)
        records.append({"id": f"SI.{part}", "name": name, "tz": LJUBLJANA, "place": "Slovenia",
                        "filler": False, "back_to_back": True, "events": evs})
    for part, evs in hrv.items():
        name = next(n for p, n in MAXTV_CHANNELS.values() if p == part)
        records.append({"id": f"HR.{part}", "name": name, "tz": ZAGREB, "place": "Croatia",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in arena_ba.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", re.sub(r"(?i)\s*\b(BH|BiH)\b", "", chname)) or "Channel"
        records.append({"id": f"BA.{part}", "name": f"{chname} BiH" if not re.search(r"(?i)\b(BH|BiH)\b", chname)
                        else chname, "tz": SARAJEVO, "place": "Bosnia and Herzegovina",
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

    own = {r["id"] for r in records if not r.get("backup")}
    dropped = [r["id"] for r in records if r.get("backup") and r["id"] in own]
    records = [r for r in records if not (r.get("backup") and r["id"] in own)]
    if dropped and args.debug:
        print(f"epgshare01 backups not needed (your own source has them): {', '.join(dropped)}")
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
    astro_matchday(records)                         # Astro pop-up PL channels (28 Oct 2026)
    hr_titles(records)                              # Croatian upper-case titles (26 Nov 2026)
    starz_football(records)                         # STARZPLAY Sports 1/2 football from FotMob (26 Nov 2026)
    rush_cricket_titles(records)                    # Rush Sports Test cricket (26 Nov 2026)
    rush_fixture_titles(records)                    # Rush Sports UEFA matches: teams, red ball, description (26 Nov 2026)
    bein_fixture_titles(records)                    # beIN Malaysia "A vs B - MD5" -> live / competition / description (26 Nov 2026)
    code_titles(records)                            # beIN Indonesia "UEL 2026/27: CRY Vs RSO (L)" (26 Nov 2026)
    astro_idle_fill(records)                        # PL 3 / 4 / 5: 'No live match scheduled' between matches (5 Nov 2026)
    records.extend(divider_records())               # country dividers '### FRANCE ###' -> DIV.FRANCE (5 Nov 2026)
    collect_match_pairs(records)                    # strong fixtures -> short replays of the same match get 'vs' too (5 Nov 2026)
    tv, count, listed = build_xmltv(records, suffix, args.minutes)
    if F1_REPLAYS:
        print(f"F1 repeats no longer marked live (OpenF1 session times): {len(F1_REPLAYS)}")
    if CARRY_OVER and not args.no_carry and not suffix and os.path.exists(args.out):
        kept = carry_over(tv, listed, args.out)       # sources that failed this run
        if kept:
            count += sum(n for _, _, n in kept)
            print(f"Kept from the previous guide (no programmes this run - source failed?): "
                  f"{len(kept)} channel(s), {sum(n for _, _, n in kept)} programmes")
            for cid, name, n in kept:
                print(f"  kept {cid} ({n} programmes)")
        filled = fill_missing_days(tv, args.out)      # whole days a source lost (DStv)
        if filled:
            count += sum(n for _, n in filled)
            print(f"Filled missing days from the previous guide: {len(filled)} channel(s), "
                  f"{sum(n for _, n in filled)} programmes")
    if not suffix:
        empties = add_empty_placeholders(tv, listed)
        if empties:
            count += sum(1 for _ in tv.iter("programme") if _.get("channel") in {c for c, _n in empties})
            print(f"Placeholders for empty channels: {len(empties)}")
            for cid, name in empties:
                print(f"  placeholder {cid} ({name})")
        if IDLE_GAP_FILLER:
            idle = add_idle_gap_fillers(tv)
            if idle:
                count += sum(n for _, n in idle)
                print(f"Idle-gap fillers: {sum(n for _, n in idle)} blocks on {len(idle)} channel(s)")
    if not suffix:
        add_alternatives(tv)
    out_path = unique_path(args.out) if args.unique else args.out
    write_xml(tv, out_path)
    if run_no is not None:
        save_last_run(run_no)

    print(f"\nWrote {out_path}: {len(listed)} channels, {count} programmes")
    for cid, name in listed:
        print(f"  {cid:<32} {name}")


if __name__ == "__main__":
    main()
