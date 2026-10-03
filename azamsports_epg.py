import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def create_azam_epg(output_filename="azam_sports_epg.xml"):
    # Root <tv> element following XMLTV DTD standard
    tv = ET.Element("tv", {
        "generator-info-name": "Azam Sports EPG Generator",
        "generator-info-url": "https://www.azamtv.com"
    })

    # Define Azam Sports Channels
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

    # Sample schedule data: (Channel ID, Start Time 'YYYYMMDDHHMMSS +ZZZZ', End Time, Title, Description, Category)
    # Timestamps are formatted in East Africa Time (EAT, UTC+3)
    schedule_data = [
        # Thursday, October 8, 2026
        ("azamsports1.tz", "20261008040000 +0300", "20261008060000 +0300", 
         "Tanzania Premier League: Mashujaa vs Polisi Tanzania", 
         "Live coverage of the Tanzania Premier League match.", "Football"),
         
        ("azamsports1.tz", "20261008061500 +0300", "20261008081500 +0300", 
         "Tanzania Premier League: Pamba vs Geita Gold", 
         "Live action from the Tanzania Premier League clash.", "Football"),
         
        ("azamsports1.tz", "20261008083000 +0300", "20261008103000 +0300", 
         "Tanzania Premier League: Namungo vs Tabora United", 
         "Catch all the excitement live as Namungo squares off against Tabora United.", "Football"),
         
        ("azamsports1.tz", "20261008110000 +0300", "20261008130000 +0300", 
         "Tanzania Premier League: Coastal Union vs Azam FC", 
         "Coastal Union faces off against Azam FC in a crucial league fixture.", "Football"),

        # Friday, October 9, 2026
        ("azamsports2.tz", "20261009040000 +0300", "20261009060000 +0300", 
         "Tanzania Premier League: Singida Big Stars vs JKT Tanzania", 
         "Singida Big Stars takes on JKT Tanzania live.", "Football"),
         
        ("azamsports2.tz", "20261009061500 +0300", "20261009081500 +0300", 
         "Tanzania Premier League: Mbeya City vs Kagera Sugar", 
         "Live coverage of Mbeya City battling Kagera Sugar.", "Football"),

        # Saturday, October 10, 2026 (Marquee Derby)
        ("azamsports4.tz", "20261010090000 +0300", "20261010110000 +0300", 
         "Tanzania Premier League: Simba SC vs Young Africans", 
         "The Kariakoo Derby! Simba SC squares off against Young Africans in the marquee fixture.", "Football"),
    ]

    # Populate programmes into XML
    for ch_id, start, stop, title_text, desc_text, category_text in schedule_data:
        prog = ET.SubElement(tv, "programme", {
            "start": start,
            "stop": stop,
            "channel": ch_id
        })

        title = ET.SubElement(prog, "title", lang="en")
        title.text = title_text

        desc = ET.SubElement(prog, "desc", lang="en")
        desc.text = desc_text

        category = ET.SubElement(prog, "category", lang="en")
        category.text = category_text
        
        cat_sub = ET.SubElement(prog, "category", lang="en")
        cat_sub.text = "Sports"

    # Write to a pretty-printed XML file
    tree = ET.ElementTree(tv)
    
    # Optional formatting for Python 3.9+
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        pass

    tree.write(output_filename, encoding="utf-8", xml_declaration=True)
    print(f"Successfully generated XMLTV EPG file: {output_filename}")

if __name__ == "__main__":
    create_azam_epg()