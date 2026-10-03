import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

def create_azam_epg(output_filename="azam_sports_epg.xml"):
    # Define EAT Timezone (UTC+3)
    eat_tz = timezone(timedelta(hours=3))
    
    tv = ET.Element("tv", {
        "generator-info-name": "Azam Sports EPG Generator",
        "generator-info-url": "https://www.azamtv.com"
    })

    # Define all 4 Azam Sports Channels
    channels = [
        {"id": "azamsports1.tz", "name": "Azam Sports 1 HD", "icon": "https://www.azamtv.com/images/channels/azam-sports-1.png"},
        {"id": "azamsports2.tz", "name": "Azam Sports 2 HD", "icon": "https://www.azamtv.com/images/channels/azam-sports-2.png"},
        {"id": "azamsports3.tz", "name": "Azam Sports 3 HD", "icon": "https://www.azamtv.com/images/channels/azam-sports-3.png"},
        {"id": "azamsports4.tz", "name": "Azam Sports 4 HD", "icon": "https://www.azamtv.com/images/channels/azam-sports-4.png"},
    ]

    for ch in channels:
        channel_elem = ET.SubElement(tv, "channel", id=ch["id"])
        display_name = ET.SubElement(channel_elem, "display-name", lang="en")
        display_name.text = ch["name"]
        if "icon" in ch:
            ET.SubElement(channel_elem, "icon", src=ch["icon"])

    # Base schedule relative to "today" dynamically in local time
    today = datetime.now(eat_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Helper to format datetime into XMLTV format: YYYYMMDDHHMMSS +ZZZZ
    def format_xmltv(dt):
        return dt.strftime("%Y%m%d%H%M%S +0300")

    # Schedule data mapped specifically to ALL channel IDs
    schedule_data = [
        # Azam Sports 1 HD
        (
            "azamsports1.tz", 
            format_xmltv(today + timedelta(hours=4)), 
            format_xmltv(today + timedelta(hours=6)), 
            "Tanzania Premier League: Mashujaa vs Polisi Tanzania", 
            "Live coverage of today's premier league fixture.", "Football"
        ),
        # Azam Sports 2 HD
        (
            "azamsports2.tz", 
            format_xmltv(today + timedelta(hours=6)), 
            format_xmltv(today + timedelta(hours=8)), 
            "Women's Super League: Featured Match", 
            "Live action coverage from the Women's Super League.", "Football"
        ),
        # Azam Sports 3 HD (Ensures channel 3 has data)
        (
            "azamsports3.tz", 
            format_xmltv(today + timedelta(hours=8)), 
            format_xmltv(today + timedelta(hours=10)), 
            "Kenyan Premier League: Regional Clash", 
            "Live broadcast of regional matchups.", "Football"
        ),
        # Azam Sports 4 HD (Ensures channel 4 has data)
        (
            "azamsports4.tz", 
            format_xmltv(today + timedelta(hours=10)), 
            format_xmltv(today + timedelta(hours=12)), 
            "La Liga / International Feature Match", 
            "Live international marquee coverage.", "Football"
        ),
        # Tomorrow's Marquee Derby on Channel 4
        (
            "azamsports4.tz", 
            format_xmltv(today + timedelta(days=1, hours=9)), 
            format_xmltv(today + timedelta(days=1, hours=11)), 
            "Tanzania Premier League: Simba SC vs Young Africans", 
            "The Kariakoo Derby! High-stakes weekend match live.", "Football"
        ),
    ]

    for ch_id, start, stop, title_text, desc_text, category_text in schedule_data:
        prog = ET.SubElement(tv, "programme", {"start": start, "stop": stop, "channel": ch_id})
        
        ET.SubElement(prog, "title", lang="en").text = title_text
        ET.SubElement(prog, "desc", lang="en").text = desc_text
        ET.SubElement(prog, "category", lang="en").text = category_text
        ET.SubElement(prog, "category", lang="en").text = "Sports"

    tree = ET.ElementTree(tv)
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        pass

    tree.write(output_filename, encoding="utf-8", xml_declaration=True)
    print(f"Successfully generated local XMLTV EPG file: {output_filename}")

if __name__ == "__main__":
    create_azam_epg()
