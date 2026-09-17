import pandas as pd
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup as bs
from collections import defaultdict
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import sys

urllib3.disable_warnings(InsecureRequestWarning)


def volby_vysledky(obvod_url: str, soubor_s_vysledky: str):

    # stránka se seznamem všech obcí
    odpoved_html = volby_stahni_vysledky(obvod_url)
    if odpoved_html is None:
        sys.exit()

    # pro každou obec zjisti link pod kterým jsou výsledky voleb
    urls = {}

    # zjisti vsechny url linky jednotlivych obci
    for a in odpoved_html.find_all("a"):
        href = a.get("href")
        if "vyber" in href and a.text != "X":
            kod_obce = a.text
            full_url = urljoin(obvod_url, href)
            urls[kod_obce] = full_url

    volby_vysledky = volby_zpracuj_obce(urls)  # defaultdict(list)

    volby_uloz_vysledky(volby_vysledky, soubor_s_vysledky)


def volby_zpracuj_obce(urls: list) -> defaultdict:

    volby_vysledky = defaultdict(list)

    # zpracuj postupne vsechny vysledky obci
    for kod_obce, url_obce in urls.items():
        # pro každou obec stáhni výsledky voleb
        odpoved_html_obec = volby_stahni_vysledky(url_obce)

        volby_vysledky["code"].append(kod_obce)
        nazev_obce = odpoved_html_obec.select_one(
            "#publikace > h3:nth-child(4)"
        ).text.strip()
        nazev_obce = nazev_obce[6:]
        volby_vysledky["location"].append(nazev_obce)

        volici_v_seznamu = odpoved_html_obec.select_one(
            'td.cislo[data-rel="L1"][headers="sa2"]'
        ).get_text()
        volby_vysledky["registered"].append(volici_v_seznamu)

        vydane_obalky = odpoved_html_obec.select_one(
            'td.cislo[data-rel="L1"][headers="sa3"]'
        ).get_text()
        volby_vysledky["envelopes"].append(vydane_obalky)

        platne_hlasy = odpoved_html_obec.select_one(
            'td.cislo[data-rel="L1"][headers="sa6"]'
        ).get_text()
        volby_vysledky["valid"].append(platne_hlasy)

        # rows = odpoved_html_obec.find_all("tr")
        rows = odpoved_html_obec.select("tr")
        for row in rows:
            strana = row.select_one('td.overflow_name[headers="t1sa1 t1sb2"]')
            hlasy = row.select_one('td.cislo[headers="t1sa2 t1sb3"]')
            if strana is not None and hlasy is not None:
                volby_vysledky[strana.text.replace(" ", "")].append(hlasy.text)

            strana = row.select_one('td.overflow_name[headers="t2sa1 t2sb2"]')
            hlasy = row.select_one('td.cislo[headers="t2sa2 t2sb3"]')
            if strana is not None and hlasy is not None:
                volby_vysledky[strana.text.replace(" ", "")].append(hlasy.text)

    return volby_vysledky


def volby_uloz_vysledky(volby_vysledky: defaultdict, soubor_s_vysledky: str):
    # vytvoreni dataframu z vysledku pro ulozeni do csv
    df = pd.DataFrame(volby_vysledky)

    # Odstraneni mezer v cislech - poctech hlasu
    for column in df.columns:
        if column not in ["code", "location"]:
            df[column] = df[column].str.replace(r"\s+", "", regex=True)

    # uloy do souboru csv
    df.to_csv(soubor_s_vysledky, index=False, encoding="utf-8-sig")


def volby_stahni_vysledky(obvod: str) -> bs.BeautifulSoup:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Opera/100.0"
    }
    try:
        # odeslání požadavku GET
        odpoved = requests.get(obvod, headers=headers, verify=False)
    except Exception as exc:
        print("Request error :", exc)
        return None

    if odpoved.ok:
        return bs(odpoved.text, features="html.parser")
    else:
        return None


if __name__ == "__main__":
    url = "https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=2&xnumnuts=2105"
    volby_vysledky(url, "vysledky_kutna_hora.csv")
