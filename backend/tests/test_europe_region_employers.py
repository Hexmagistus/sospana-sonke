"""European employers added from national indexes, universities, and ATS boards.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, the employer's own
board names a post, and at least half of the located roles are in that country.
Fugro and Thales are the exception added later: the stored URL is that board's
own country filter, which lists the roles named in the note. Zealand Pharma,
Valmet, Jungheinrich, and Galderma are large groups whose own board has no
country filter. Those rows are `global_group` and the note contains
`careers_scope=global`. Everyone else from the same lists is a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 europe-employers'
LINKS = {
    'ASM International': ('Netherlands', 'https://www.asm.com/careers', 'PRIVATE', 'static'),
    'ASML Holding': ('Netherlands', 'https://www.asml.com/en/careers', 'PRIVATE', 'static'),
    'Aalberts': ('Netherlands', 'https://aalberts.com/careers', 'PRIVATE', 'static'),
    'Accor': ('France', 'https://group.accor.com/en/group/people-at-our-heart/career-growth-and-development', 'PRIVATE', 'static'),
    'Addtech': ('Sweden', 'https://www.addtech.com/this-is-addtech/career', 'PRIVATE', 'static'),
    'Adecco': ('Switzerland', 'https://careers.adeccogroup.com/en', 'PRIVATE', 'static'),
    'Adesso SE': ('Germany', 'https://www.adesso.de/de/jobs-karriere/karriere-adesso-group.jsp', 'PRIVATE', 'static'),
    'Aegon': ('Netherlands', 'https://www.aegon.com/careers', 'PRIVATE', 'static'),
    'Ahold Delhaize': ('Netherlands', 'https://aholddelhaize.com/careers/', 'PRIVATE', 'static'),
    'Air Liquide': ('France', 'https://www.airliquide.com/join-us/careers-air-liquide', 'PRIVATE', 'static'),
    'AkzoNobel': ('Netherlands', 'https://www.akzonobel.com/en/careers', 'PRIVATE', 'static'),
    'Alfa Laval': ('Sweden', 'https://www.alfalaval.com/careers/', 'PRIVATE', 'static'),
    'Alior Bank': ('Poland', 'https://www.aliorbank.pl/careers', 'PRIVATE', 'static'),
    'Alzchem Group': ('Germany', 'https://www.alzchem.com/de/karriere/', 'PRIVATE', 'static'),
    'Amadeus FiRe AG': ('Germany', 'https://karriere.amadeus-fire.de', 'PRIVATE', 'static'),
    'Ambu': ('Denmark', 'https://www.ambu.com/corporate-info/careers/life-at-ambu', 'PRIVATE', 'static'),
    'Amplifon': ('Italy', 'https://corporate.amplifon.com/en/careers/Amp-Up-Your-Career', 'PRIVATE', 'static'),
    'Amrize AG': ('Switzerland', 'https://www.amrize.com/us/en/careers.html', 'PRIVATE', 'static'),
    'Arcadis': ('Netherlands', 'https://careers.arcadis.com/', 'PRIVATE', 'static'),
    'Assa Abloy': ('Sweden', 'https://www.assaabloy.com/de/de/career', 'PRIVATE', 'static'),
    'Aurubis': ('Germany', 'https://www.aurubis.com/en/career', 'PRIVATE', 'static'),
    'Avolta': ('Switzerland', 'https://www.avoltaworld.com/en/careers', 'PRIVATE', 'static'),
    'Banca Mediolanum': ('Italy', 'https://www.bancamediolanum.it/corporate/careers', 'PRIVATE', 'static'),
    'Banca Monte dei Paschi di Siena': ('Italy', 'https://www.gruppomps.it/lavora-con-noi/index.html', 'PRIVATE', 'static'),
    'Bechtle': ('Germany', 'https://www.bechtle.com/karriere', 'PRIVATE', 'static'),
    'Beiersdorf': ('Germany', 'https://www.beiersdorf.com/career/overview', 'PRIVATE', 'static'),
    'Boliden': ('Sweden', 'https://www.boliden.com/career/', 'PRIVATE', 'static'),
    'Boskalis': ('Netherlands', 'https://careers.smartrecruiters.com/boskalis', 'PRIVATE', 'smartrecruiters'),
    'Bureau Veritas': ('France', 'https://group.bureauveritas.com/careers/leave-your-mark', 'PRIVATE', 'static'),
    'Buzzi': ('Italy', 'https://www.buzzi.com/career-opportunities', 'PRIVATE', 'static'),
    'Campari': ('Italy', 'https://www.camparigroup.com/careers', 'PRIVATE', 'static'),
    'Cancom SE': ('Germany', 'https://karriere.cancom.de/', 'PRIVATE', 'static'),
    'Capgemini': ('France', 'https://www.capgemini.com/careers/', 'PRIVATE', 'static'),
    'Carlsberg Group': ('Denmark', 'https://careers.carlsberg.com/', 'PRIVATE', 'static'),
    'Clariant': ('Switzerland', 'https://www.clariant.com/en/Careers', 'PRIVATE', 'static'),
    'Continental': ('Germany', 'https://www.continental.com/en/career/', 'PRIVATE', 'static'),
    'DNB Bank': ('Norway', 'https://www.dnb.no/careers', 'PRIVATE', 'static'),
    'Daimler Truck': ('Germany', 'https://www.daimlertruck.com/en/career', 'PRIVATE', 'static'),
    'Danone': ('France', 'https://www.danone.com/fr/carrieres.html', 'PRIVATE', 'static'),
    'Danske Bank': ('Denmark', 'https://danskebank.com/careers', 'PRIVATE', 'static'),
    'Dassault Systèmes': ('France', 'https://www.3ds.com/careers', 'PRIVATE', 'static'),
    'Demant': ('Denmark', 'https://www.demant.com/jobs-and-career', 'PRIVATE', 'static'),
    'Deutsche Börse': ('Germany', 'https://careers.deutsche-boerse.com', 'PRIVATE', 'static'),
    'Deutsche Euroshop': ('Germany', 'https://www.deutsche-euroshop.de/Konzern/Karriere', 'PRIVATE', 'static'),
    'Deutsche Telekom': ('Germany', 'https://careers.telekom.com/en', 'PRIVATE', 'static'),
    'Deutz AG': ('Germany', 'https://career.deutz.com/go/Alle-Jobs/5026601', 'PRIVATE', 'icims'),
    'Diasorin': ('Italy', 'https://int.diasorin.com/en/careers', 'PRIVATE', 'static'),
    'Dürr AG': ('Germany', 'https://www.durr-group.com/en/career', 'PRIVATE', 'static'),
    'Elisa': ('Finland', 'https://elisa.com/corporate/careers/', 'PRIVATE', 'static'),
    'Elmos Semiconductor SE': ('Germany', 'https://www.elmos.com/karriere.html', 'PRIVATE', 'static'),
    'Ems-Chemie': ('Switzerland', 'https://www.ems-group.com/en/career/the-start-at-ems/', 'PRIVATE', 'static'),
    'Encavis': ('Germany', 'https://www.encavis.com/de/karriere', 'PRIVATE', 'static'),
    'Energiekontor AG': ('Germany', 'https://www.energiekontor.de/karriere.html', 'PRIVATE', 'static'),
    'Engie': ('France', 'https://jobs.engie.com/', 'PRIVATE', 'static'),
    'Eni': ('Italy', 'https://www.eni.com/it-IT/carriere.html', 'PRIVATE', 'static'),
    'Essity': ('Sweden', 'https://www.essity.com/careers', 'PRIVATE', 'static'),
    'Euronext': ('France', 'https://www.euronext.com/en/about/careers', 'PRIVATE', 'static'),
    'Evotec': ('Germany', 'https://careers.evotec.com/en', 'PRIVATE', 'static'),
    'FLSmidth & Co.': ('Denmark', 'https://fls.com/en/company/careers', 'PRIVATE', 'static'),
    'FinecoBank': ('Italy', 'https://about.finecobank.com/it/careers/', 'PRIVATE', 'static'),
    'Flow traders': ('Netherlands', 'https://www.flowtraders.com/careers/', 'PRIVATE', 'static'),
    'Flughafen Zürich': ('Switzerland', 'https://www.flughafen-zuerich.ch/en/company/jobs/careers/job-vacancies', 'PRIVATE', 'static'),
    'Fluidra': ('Spain', 'https://www.fluidra.com/careers', 'PRIVATE', 'static'),
    'Fortum': ('Finland', 'https://www.fortum.com/careers', 'PRIVATE', 'static'),
    'Fraport': ('Germany', 'https://www.jobs-fraport.com/', 'PRIVATE', 'static'),
    'Fresenius Medical Care': ('Germany', 'https://jobs.freseniusmedicalcare.com', 'PRIVATE', 'static'),
    'Fuchs Petrolub': ('Germany', 'https://jobs.fuchs.com/', 'PRIVATE', 'static'),
    'Fugro': ('Netherlands', 'https://fugro.wd3.myworkdayjobs.com/Careers?locationCountry=9696868b09c64d52a62ee13b052383cc', 'PRIVATE', 'workday'),
    'GEA Group': ('Germany', 'https://www.gea.com/en/careers/', 'PRIVATE', 'static'),
    'GFT Technologies SE': ('Germany', 'https://jobs.gft.com/', 'PRIVATE', 'static'),
    'GN Store Nord': ('Denmark', 'https://www.gn.com/Working-with-us', 'PRIVATE', 'static'),
    'Galderma': ('Switzerland', 'https://galderma.wd3.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Galenica': ('Switzerland', 'https://jobs.galenica.com/de/', 'PRIVATE', 'static'),
    'Gerresheimer': ('Germany', 'https://careers.smartrecruiters.com/gerresheimer', 'PRIVATE', 'smartrecruiters'),
    'Givaudan SA': ('Switzerland', 'https://www.givaudan.com/careers', 'PRIVATE', 'static'),
    'Grenke AG': ('Germany', 'https://www.grenke.com/de/karriere/', 'PRIVATE', 'static'),
    'Grifols': ('Spain', 'https://www.grifols.com/en/careers', 'PRIVATE', 'static'),
    'Heidelberg Materials': ('Germany', 'https://career.heidelbergmaterials.com/jobcategory/digital', 'PRIVATE', 'static'),
    'Hensoldt': ('Germany', 'https://jobs.hensoldt.net/', 'PRIVATE', 'static'),
    'Hiab': ('Finland', 'https://www.hiabgroup.com/en/career/', 'PRIVATE', 'static'),
    'Hochtief': ('Germany', 'https://www.hochtief.com/careers', 'PRIVATE', 'static'),
    'Holcim Limited': ('Switzerland', 'https://www.holcim.com/careers', 'PRIVATE', 'static'),
    'Hornbach Holding AG': ('Germany', 'https://www.hornbach-holding.de/careers', 'PRIVATE', 'static'),
    'Huhtamäki': ('Finland', 'https://www.huhtamaki.com/en/careers/', 'PRIVATE', 'static'),
    'Hypoport SE': ('Germany', 'https://karriere.hypoport.de/?ref=28', 'PRIVATE', 'static'),
    'ING Group': ('Netherlands', 'https://careers.ing.com/en/search-jobs', 'PRIVATE', 'static'),
    'Infineon Technologies': ('Germany', 'https://www.infineon.com/careers', 'PRIVATE', 'static'),
    'Italgas': ('Italy', 'https://www.italgas.it/people/lavorare-in-italgas/crescita-e-formazione/', 'PRIVATE', 'static'),
    'Jenoptik': ('Germany', 'https://careers.jenoptik.com/?locale=en_US', 'PRIVATE', 'static'),
    'Jungheinrich': ('Germany', 'https://job-boards.greenhouse.io/jungheinrich', 'PRIVATE', 'greenhouse'),
    'Kemira': ('Finland', 'https://www.kemira.com/careers/', 'PRIVATE', 'static'),
    'Kering': ('France', 'https://www.kering.com/en/talent/job-offers/', 'PRIVATE', 'static'),
    'Kesko': ('Finland', 'https://www.kesko.fi/careers', 'PRIVATE', 'static'),
    'Klöckner & Co SE': ('Germany', 'https://www.kloeckner.com/en/career/', 'PRIVATE', 'static'),
    'Knorr-Bremse': ('Germany', 'https://careers.knorr-bremse.com/?locale=en_US', 'PRIVATE', 'static'),
    'Kongsberg Gruppen': ('Norway', 'https://www.kongsberg.com/careers/vacancies/', 'PRIVATE', 'static'),
    'Kontron AG': ('Germany', 'https://www.kontron.com/en/group/careers', 'PRIVATE', 'static'),
    'LEG Immobilien': ('Germany', 'https://karriere.leg-wohnen.de/', 'PRIVATE', 'static'),
    'Legrand': ('France', 'https://www.legrand.com/en/working-at-legrand/all-brand-ambassadors/discover-our-jobs', 'PRIVATE', 'static'),
    'Logista': ('Spain', 'https://www.logistajoinus.com/', 'PRIVATE', 'static'),
    'Logitech International SA': ('Switzerland', 'https://www.logitech.com/en-us/careers', 'PRIVATE', 'static'),
    'MTU Aero Engines': ('Germany', 'https://www.mtu.de/careers/', 'PRIVATE', 'static'),
    'Mandatum': ('Finland', 'https://www.mandatum.fi/en/group/about-the-company/careers', 'PRIVATE', 'static'),
    'Medios': ('Germany', 'https://career.medios.group/', 'PRIVATE', 'static'),
    'Mowi': ('Norway', 'https://mowi.com/careers/', 'PRIVATE', 'static'),
    'Munich Re': ('Germany', 'https://careers.munichre.com/en/munichre', 'PRIVATE', 'static'),
    'Nemetschek': ('Germany', 'https://www.nemetschek.com/en/company/career', 'PRIVATE', 'static'),
    'Neste': ('Finland', 'https://www.neste.com/about-neste/people-and-careers/work-with-us', 'PRIVATE', 'static'),
    'Nokian Tyres': ('Finland', 'https://company.nokiantyres.com/careers/', 'PRIVATE', 'static'),
    'Nordea': ('Finland', 'https://www.nordea.com/en/careers', 'PRIVATE', 'static'),
    'Nordex': ('Germany', 'https://www.nordex-online.com/en/career/', 'PRIVATE', 'static'),
    'Norsk Hydro': ('Norway', 'https://www.hydro.com/en/global/careers/', 'PRIVATE', 'static'),
    'Novartis International AG': ('Switzerland', 'https://www.novartis.com/careers', 'PRIVATE', 'static'),
    'Orange': ('France', 'https://www.orange.com/careers', 'PRIVATE', 'static'),
    'Orange Polska': ('Poland', 'https://salony.orange.pl/careers', 'PRIVATE', 'static'),
    'Orkla': ('Norway', 'https://careers.orkla.com/', 'PRIVATE', 'static'),
    'Outokumpu': ('Finland', 'https://www.outokumpu.com/en/careers', 'PRIVATE', 'static'),
    'PNE AG': ('Germany', 'https://www.pnegroup.com/karriere/arbeiten-bei-pne/', 'PRIVATE', 'static'),
    'PSP Swiss Property': ('Switzerland', 'https://www.psp.info/karriere-jobs/unsere-leistungen', 'PRIVATE', 'static'),
    'Pepco': ('Poland', 'https://careers.pepco.eu/Poland/', 'PRIVATE', 'static'),
    'Pernod Ricard': ('France', 'https://www.pernod-ricard.com/en/careers', 'PRIVATE', 'static'),
    'ProCredit': ('Germany', 'https://www.procredit-holding.com/vacancies/', 'PRIVATE', 'static'),
    'Prysmian': ('Italy', 'https://www.prysmian.com/en/people-and-careers', 'PRIVATE', 'static'),
    'Publicis': ('France', 'https://www.publicisgroupe.com/fr/le-groupe/carrieres/presentation', 'PRIVATE', 'static'),
    'Puma': ('Germany', 'https://about.puma.com/en/careers', 'PRIVATE', 'static'),
    'RTL Group': ('Germany', 'https://www.rtl.de/tools/website-erstellen', 'PRIVATE', 'static'),
    'Randstad': ('Netherlands', 'https://www.randstad.com/jobs/', 'PRIVATE', 'static'),
    'Recordati': ('Italy', 'https://careers.recordati.com/', 'PRIVATE', 'static'),
    'Rheinmetall': ('Germany', 'https://www.rheinmetall.com/de/karriere/uebersicht-karriere', 'PRIVATE', 'static'),
    'Royal Unibrew': ('Denmark', 'https://www.royalunibrew.com/careers', 'PRIVATE', 'static'),
    'SBM Offshore': ('Netherlands', 'https://www.sbmoffshore.com/careers/', 'PRIVATE', 'static'),
    'Saab': ('Sweden', 'https://www.saab.com/career', 'PRIVATE', 'static'),
    'Sacyr': ('Spain', 'https://sacyr.com/es/empleo', 'PRIVATE', 'static'),
    'Saint-Gobain': ('France', 'https://careers.smartrecruiters.com/saintgobain', 'PRIVATE', 'smartrecruiters'),
    'SalMar': ('Norway', 'https://www.salmar.no/en/career/', 'PRIVATE', 'static'),
    'Salzgitter AG': ('Germany', 'https://www.salzgitter-ag.com/de/jobs-karriere.html', 'PRIVATE', 'static'),
    'Sandoz': ('Switzerland', 'https://www.sandoz.com/careers/', 'PRIVATE', 'static'),
    'Sandvik': ('Sweden', 'https://www.home.sandvik/en/careers/', 'PRIVATE', 'static'),
    'Schneider Electric': ('France', 'https://www.se.com/ww/en/about-us/careers/overview/', 'PRIVATE', 'static'),
    'Schott Pharma AG & Co. KGaA': ('Germany', 'https://www.schott.com/en-gb/careers', 'PRIVATE', 'static'),
    'Scout24': ('Germany', 'https://www.scout24.com/en/career/jobs', 'PRIVATE', 'static'),
    'Secunet Security Networks': ('Germany', 'https://www.secunet.com/ueber-uns/karriere', 'PRIVATE', 'static'),
    'Siemens Energy': ('Germany', 'https://jobs.siemens-energy.com/en_US/jobs', 'PRIVATE', 'static'),
    'Siemens Healthineers': ('Germany', 'https://www.siemens-healthineers.com/careers', 'PRIVATE', 'static'),
    'Sika AG': ('Switzerland', 'https://www.sika.com/en/career.html', 'PRIVATE', 'static'),
    'Siltronic': ('Germany', 'https://www.siltronic.com/en/career.html', 'PRIVATE', 'static'),
    'Sonova': ('Switzerland', 'https://www.sonova.com/careers/', 'PRIVATE', 'static'),
    'Swatch': ('Switzerland', 'https://www.swatchgroup.com/en/careers-swatch-group', 'PRIVATE', 'static'),
    'Swedbank': ('Sweden', 'https://www.swedbank.ee/about/careers/work/career', 'PRIVATE', 'static'),
    'Swissquote': ('Switzerland', 'https://careers.smartrecruiters.com/swissquote', 'PRIVATE', 'smartrecruiters'),
    'Symrise': ('Germany', 'https://www.symrise.com/your-career/', 'PRIVATE', 'static'),
    'Südzucker AG': ('Germany', 'https://www.suedzuckergroup.com/en/careers/what-we-offer', 'PRIVATE', 'static'),
    'Süss Microtec SE': ('Germany', 'https://career.suss.com/en/jobs', 'PRIVATE', 'static'),
    'TeamViewer': ('Germany', 'https://careers.teamviewer.com/jobs', 'PRIVATE', 'static'),
    'Tele2': ('Sweden', 'https://www.tele2.com/join-us/job-openings-sweden/', 'PRIVATE', 'static'),
    'Telenor': ('Norway', 'https://www.telenor.com/career/', 'PRIVATE', 'static'),
    'Telia Company': ('Sweden', 'https://www.teliacompany.com/en/careers', 'PRIVATE', 'static'),
    'Terna': ('Italy', 'https://www.terna.it/en/careers', 'PRIVATE', 'static'),
    'Thales': ('France', 'https://thales.wd3.myworkdayjobs.com/Careers?locationCountry=54c5b6971ffb4bf0b116fe7651ec789a', 'PRIVATE', 'workday'),
    'ThyssenKrupp': ('Germany', 'https://www.thyssenkrupp.com/de/karriere', 'PRIVATE', 'static'),
    'Traton': ('Germany', 'https://traton.com/en/career.html', 'PRIVATE', 'static'),
    'UBS Group AG': ('Switzerland', 'https://www.ubs.com/global/en/careers.html', 'PRIVATE', 'static'),
    'Unibail-Rodamco-Westfield': ('France', 'https://www.urw.com/join-us', 'PRIVATE', 'static'),
    'United Internet': ('Germany', 'https://www.united-internet.de/jobs-karriere/', 'PRIVATE', 'static'),
    'Universal Music Group': ('Netherlands', 'https://www.universalmusic.com/careers/', 'PRIVATE', 'static'),
    'Valmet': ('Finland', 'https://valmet.wd103.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Vattenfall': ('Sweden', 'https://careers.vattenfall.com/', 'SOE', 'static'),
    'Vinci': ('France', 'https://jobs.vinci.com/fr', 'PRIVATE', 'static'),
    'Volvo': ('Sweden', 'https://www.volvogroup.com/en/careers.html', 'PRIVATE', 'static'),
    'Vonovia': ('Germany', 'https://www.vonovia.com/karriere', 'PRIVATE', 'static'),
    'Wacker Chemie': ('Germany', 'https://www.wacker.com/careers', 'PRIVATE', 'static'),
    'Wacker Neuson SE': ('Germany', 'https://wackerneusongroup.com/karriere/wacker-neuson-als-arbeitgeber', 'PRIVATE', 'static'),
    'Wärtsilä': ('Finland', 'https://www.wartsila.com/careers', 'PRIVATE', 'static'),
    'Wüstenrot & Württembergische AG': ('Germany', 'https://www.ww-ag.com/de/karriere', 'PRIVATE', 'static'),
    'Yara International': ('Norway', 'https://www.yara.no/karriere/', 'PRIVATE', 'static'),
    'Zealand Pharma': ('Denmark', 'https://zealandpharma.wd3.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Zurich Insurance Group AG': ('Switzerland', 'https://www.zurich.com/careers', 'PRIVATE', 'static'),
}
BLANK = {
    ('Denmark', 'HOSPITAL'): 1,
    ('Denmark', 'MUNI'): 1,
    ('Denmark', 'NGO'): 1,
    ('Denmark', 'PRIVATE'): 13,
    ('Denmark', 'SOE'): 1,
    ('Denmark', 'UNI'): 6,
    ('Finland', 'HOSPITAL'): 1,
    ('Finland', 'NGO'): 1,
    ('Finland', 'PRIVATE'): 10,
    ('Finland', 'UNI'): 12,
    ('France', 'DEPT'): 2,
    ('France', 'HOSPITAL'): 2,
    ('France', 'MUNI'): 3,
    ('France', 'NGO'): 2,
    ('France', 'PRIVATE'): 16,
    ('France', 'SOE'): 4,
    ('France', 'UNI'): 68,
    ('Germany', 'DEPT'): 3,
    ('Germany', 'HOSPITAL'): 3,
    ('Germany', 'MUNI'): 4,
    ('Germany', 'NGO'): 2,
    ('Germany', 'PRIVATE'): 76,
    ('Germany', 'SOE'): 2,
    ('Germany', 'UNI'): 79,
    ('Iceland', 'HOSPITAL'): 1,
    ('Iceland', 'MUNI'): 1,
    ('Iceland', 'PRIVATE'): 3,
    ('Iceland', 'UNI'): 6,
    ('Ireland', 'HOSPITAL'): 1,
    ('Ireland', 'PRIVATE'): 1,
    ('Ireland', 'SOE'): 2,
    ('Ireland', 'UNI'): 7,
    ('Italy', 'HOSPITAL'): 1,
    ('Italy', 'MUNI'): 2,
    ('Italy', 'NGO'): 1,
    ('Italy', 'PRIVATE'): 22,
    ('Italy', 'SOE'): 1,
    ('Italy', 'UNI'): 88,
    ('Netherlands', 'DEPT'): 1,
    ('Netherlands', 'HOSPITAL'): 7,
    ('Netherlands', 'MUNI'): 2,
    ('Netherlands', 'NGO'): 1,
    ('Netherlands', 'PRIVATE'): 24,
    ('Netherlands', 'SOE'): 1,
    ('Netherlands', 'UNI'): 29,
    ('Norway', 'HOSPITAL'): 1,
    ('Norway', 'MUNI'): 1,
    ('Norway', 'NGO'): 1,
    ('Norway', 'PRIVATE'): 15,
    ('Norway', 'UNI'): 31,
    ('Poland', 'HOSPITAL'): 1,
    ('Poland', 'MUNI'): 2,
    ('Poland', 'NGO'): 1,
    ('Poland', 'PRIVATE'): 24,
    ('Poland', 'SOE'): 1,
    ('Poland', 'UNI'): 20,
    ('Spain', 'HOSPITAL'): 2,
    ('Spain', 'MUNI'): 2,
    ('Spain', 'NGO'): 1,
    ('Spain', 'PRIVATE'): 24,
    ('Spain', 'SOE'): 1,
    ('Spain', 'UNI'): 93,
    ('Sweden', 'HOSPITAL'): 1,
    ('Sweden', 'MUNI'): 1,
    ('Sweden', 'NGO'): 1,
    ('Sweden', 'PRIVATE'): 14,
    ('Sweden', 'UNI'): 10,
    ('Switzerland', 'HOSPITAL'): 2,
    ('Switzerland', 'MUNI'): 2,
    ('Switzerland', 'NGO'): 1,
    ('Switzerland', 'PRIVATE'): 24,
    ('Switzerland', 'SOE'): 1,
    ('Switzerland', 'UNI'): 11,
}
LINKED_TOTAL = {
    'Germany': 77,
    'France': 32,
    'Netherlands': 22,
    'Ireland': 6,
    'Norway': 15,
    'Sweden': 18,
    'Denmark': 14,
    'Finland': 17,
    'Iceland': 5,
    'Spain': 11,
    'Italy': 18,
    'Switzerland': 25,
    'Poland': 8,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_europe_region_employers_follow_the_direct_link_rule():
    rows = _rows()
    added = [row for row in rows if row["relevance_note"].startswith(NOTE)]
    assert len(added) == len(LINKS) + sum(BLANK.values())
    found = {}
    blank = {key: 0 for key in BLANK}
    names = []
    for row in added:
        names.append((row["company_name"].casefold(), row["country"].casefold()))
        assert row["jse_code"] == ""
        assert row["official_website"] == ""
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert ":443" not in row["careers_url"]
        if row["company_name"] in LINKS:
            country, url, kind, ats = LINKS[row["company_name"]]
            assert row["country"] == country
            assert row["careers_url"] == url
            assert row["source_type"] == kind
            assert row["active"] == "true"
            if "careers_scope=global" in row["relevance_note"]:
                assert row["careers_status"] == "global_group"
            else:
                assert row["careers_status"] == "green_verified"
            assert row["scraping_status"] == "pending"
            assert row["careers_url"].startswith("https://")
            assert detect_ats(row["careers_url"])[0] == ats
            found[row["company_name"]] = row["careers_url"]
        else:
            assert row["careers_url"] == ""
            assert row["active"] == "false"
            assert row["careers_status"] == "grey_none_verified"
            assert row["scraping_status"] == "no_url"
            blank[(row["country"], row["source_type"])] += 1
    assert found == {name: LINKS[name][1] for name in LINKS}
    assert blank == BLANK
    assert len(names) == len(set(names))


def test_europe_region_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
