"""United States employers added from index lists and ATS slug probes.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, the employer's own
board names a post, and at least half of the located roles are in the United States.
Analog Devices, Ciena, Equifax, and Equinix are the exception added later:
the unfiltered Workday board is global, and the stored URL is that board's own
United States filter, which lists the roles named in the note. Allegion's own
board is already mostly in the United States, so it is stored without a filter.
Everyone else from the same lists is a blank row. Intel, Revvity, and Viatris
are large groups whose own Workday board has no United States filter. Those
rows are `global_group` and the note contains `careers_scope=global`.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 usa-employers'
LINKS = {
    'A. O. Smith': ('https://www.aosmith.com/about-us/careers.html', 'PRIVATE', 'static'),
    'AES Corporation': ('https://www.aes.com/about-us/careers', 'PRIVATE', 'static'),
    'AbbVie': ('https://careers.smartrecruiters.com/abbvie', 'PRIVATE', 'smartrecruiters'),
    'Abbott Laboratories': ('https://www.abbott.com/en-us/careers', 'PRIVATE', 'static'),
    'AdventHealth': ('https://jobs.adventhealth.com/', 'HOSPITAL', 'static'),
    'Aflac': ('https://careers.aflac.com', 'PRIVATE', 'static'),
    'Albemarle Corporation': ('https://albemarle.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Alexandria Real Estate Equities': ('https://www.are.com/careers', 'PRIVATE', 'static'),
    'Align Technology': ('https://jobs.aligntech.com', 'PRIVATE', 'static'),
    'Allegion': ('https://allegion.wd5.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Alliant Energy': ('https://www.alliantenergy.com/careers', 'PRIVATE', 'static'),
    'Altria': ('https://www.altria.com/people-and-careers/careers?src=topnav', 'PRIVATE', 'static'),
    'Ameren': ('https://ameren.wd1.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'American Electric Power': ('https://www.aep.com/careers/', 'PRIVATE', 'static'),
    'American International Group': ('https://www.aig.com/home/careers', 'PRIVATE', 'static'),
    'Ametek': ('https://www.ametek.com/careers', 'PRIVATE', 'static'),
    'Amgen': ('https://amgen.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Analog Devices': ('https://analogdevices.wd1.myworkdayjobs.com/External?locationCountry=bc33aa3152ec42d4995f4791a106ed09', 'PRIVATE', 'workday'),
    'Apollo Global Management': ('https://www.apollo.com/careers', 'PRIVATE', 'static'),
    'Archer Daniels Midland': ('https://www.adm.com/en-us/culture-and-careers/', 'PRIVATE', 'static'),
    'Arista Networks': ('https://careers.smartrecruiters.com/aristanetworks', 'PRIVATE', 'smartrecruiters'),
    'Arthur J. Gallagher & Co': ('https://jobs.ajg.com/ajg-home', 'PRIVATE', 'static'),
    'Atmos Energy': ('https://www.atmosenergy.com/careers/working-atmos-energy/', 'PRIVATE', 'static'),
    'Avery Dennison': ('https://careers.smartrecruiters.com/averydennison', 'PRIVATE', 'smartrecruiters'),
    'Axon Enterprise': ('https://job-boards.greenhouse.io/axon', 'PRIVATE', 'greenhouse'),
    'Baker Hughes': ('https://careers.bakerhughes.com', 'PRIVATE', 'static'),
    'Baxter International': ('https://jobs.baxter.com/en', 'PRIVATE', 'static'),
    'Biogen': ('https://www.biogen.com/careers.html', 'PRIVATE', 'static'),
    'Boston Scientific': ('https://www.bostonscientific.com/en-US/careers.html', 'PRIVATE', 'static'),
    'Brex': ('https://www.brex.com/careers', 'PRIVATE', 'static'),
    'Bristol Myers Squibb': ('https://careers.bms.com', 'PRIVATE', 'static'),
    'Brown & Brown': ('https://careers.smartrecruiters.com/brownbrown', 'PRIVATE', 'smartrecruiters'),
    'Brown–Forman': ('https://careers.brown-forman.com/', 'PRIVATE', 'static'),
    'CF Industries': ('https://cfindustries.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Carnival Corporation': ('https://www.carnivalcorp.com/careers/', 'PRIVATE', 'static'),
    'Cencora': ('https://careers.smartrecruiters.com/cencora', 'PRIVATE', 'smartrecruiters'),
    'CenterPoint Energy': ('https://careers.centerpointenergy.com/', 'PRIVATE', 'static'),
    'Church & Dwight': ('https://www.churchdwight.com/careers/', 'PRIVATE', 'static'),
    'Ciena': ('https://ciena.wd5.myworkdayjobs.com/Careers?Location_Country=bc33aa3152ec42d4995f4791a106ed09', 'PRIVATE', 'workday'),
    'Cincinnati Financial': ('https://www.cinfin.com/cincinnati-insurance-careers', 'PRIVATE', 'static'),
    'Cintas': ('https://www.cintas.com/careers/', 'PRIVATE', 'static'),
    'City of San Antonio': ('https://careers.smartrecruiters.com/cityofsanantonio', 'MUNI', 'smartrecruiters'),
    'Clorox': ('https://www.thecloroxcompany.com/careers/', 'PRIVATE', 'static'),
    'Coherent Corp': ('https://www.coherent.com/peopleandculture', 'PRIVATE', 'static'),
    'Colgate-Palmolive': ('https://jobs.colgate.com/go/View-All-Jobs/8506400/', 'PRIVATE', 'icims'),
    'Comfort Systems USA': ('https://comfortsystemsusa.com/careers/', 'PRIVATE', 'static'),
    'Community Health Systems': ('https://www.chs.net/careers/', 'HOSPITAL', 'static'),
    'Confluent': ('https://jobs.ashbyhq.com/confluent', 'PRIVATE', 'static'),
    'Copart': ('https://www.copart.com/careers', 'PRIVATE', 'static'),
    'Corpay': ('https://www.corpay.com/careers', 'PRIVATE', 'static'),
    'CrowdStrike': ('https://www.crowdstrike.com/en-us/careers/', 'PRIVATE', 'static'),
    'Crown Castle': ('https://www.crowncastle.com/careers/', 'PRIVATE', 'static'),
    'D. R. Horton': ('https://www.drhorton.com/careers', 'PRIVATE', 'static'),
    'DTE Energy': ('https://www.dteenergy.com/us/en/residential/about-dte/careers/careers.html', 'PRIVATE', 'static'),
    'Darden Restaurants': ('https://www.darden.com/careers/', 'PRIVATE', 'static'),
    'Deere & Company': ('https://www.deere.com/en-us/our-company/careers', 'PRIVATE', 'static'),
    'Dell Technologies': ('https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers', 'PRIVATE', 'static'),
    'Delta Air Lines': ('https://www.delta.com/us/en/careers/overview', 'PRIVATE', 'static'),
    'Devon Energy': ('https://devonenergy.wd5.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Dollar General': ('https://careers.dollargeneral.com/', 'PRIVATE', 'static'),
    'Dominion Energy': ('https://careers.dominionenergy.com/', 'PRIVATE', 'static'),
    "Domino's": ('https://careers.smartrecruiters.com/dominos', 'PRIVATE', 'smartrecruiters'),
    'Dow Inc': ('https://corporate.dow.com/en-us/careers.html', 'PRIVATE', 'static'),
    'Duke University Health System': ('https://www.dukehealth.org/about-duke-health/job-opportunities', 'HOSPITAL', 'static'),
    'EOG Resources': ('https://careers.eogresources.com/process_jobsearch.asp', 'PRIVATE', 'static'),
    'EQT Corporation': ('https://www.eqt.com/careers', 'PRIVATE', 'static'),
    'Edison International': ('https://www.edisoncareers.com', 'PRIVATE', 'static'),
    'Edwards Lifesciences': ('https://www.edwards.com/careers', 'PRIVATE', 'static'),
    'Elevance Health': ('https://careers.elevancehealth.com/', 'PRIVATE', 'static'),
    'Emcor': ('https://emcorgroup.com/careers', 'PRIVATE', 'static'),
    'Entergy': ('https://jobs.entergy.com', 'PRIVATE', 'static'),
    'Equifax': ('https://equifax.wd5.myworkdayjobs.com/External?locationCountry=bc33aa3152ec42d4995f4791a106ed09', 'PRIVATE', 'workday'),
    'Equinix': ('https://equinix.wd1.myworkdayjobs.com/External?Location_Country=bc33aa3152ec42d4995f4791a106ed09', 'PRIVATE', 'workday'),
    'Evergy': ('https://www.evergy.com/careers/careers-and-internships', 'PRIVATE', 'static'),
    'Eversource Energy': ('https://www.eversource.com/residential/about/careers.html', 'PRIVATE', 'static'),
    'Exelon': ('https://jobs.exeloncorp.com/careers-home/', 'PRIVATE', 'static'),
    'Expedia Group': ('https://careers.expediagroup.com/', 'PRIVATE', 'static'),
    'Expeditors International': ('https://careers.smartrecruiters.com/expeditors', 'PRIVATE', 'smartrecruiters'),
    'Extra Space Storage': ('https://careers.extraspace.com/', 'PRIVATE', 'static'),
    'FactSet': ('https://www.factset.com/careers', 'PRIVATE', 'static'),
    'Ferguson Enterprises': ('https://www.ferguson.com/content/corporate-information/careers/', 'PRIVATE', 'static'),
    'Fidelity National Information Services': ('https://www.fisglobal.com/careers', 'PRIVATE', 'static'),
    'Figma': ('https://www.figma.com/careers/', 'PRIVATE', 'static'),
    'First Solar': ('https://www.firstsolar.com/Careers', 'PRIVATE', 'static'),
    'FirstEnergy': ('https://www.firstenergycorp.com/careers.html', 'PRIVATE', 'static'),
    'Fortive': ('https://careers.fortive.com/', 'PRIVATE', 'static'),
    'Freeport-McMoRan': ('https://www.fcx.com/careers', 'PRIVATE', 'static'),
    'GE Vernova': ('https://careers.gevernova.com', 'PRIVATE', 'static'),
    'Gen Digital': ('https://jobs.ashbyhq.com/gen-digital', 'PRIVATE', 'static'),
    'Generac': ('https://generac.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Gilead Sciences': ('https://www.gilead.com/careers', 'PRIVATE', 'static'),
    'GoDaddy': ('https://careers.godaddy/jobs/search', 'PRIVATE', 'static'),
    'Hasbro': ('https://job-boards.greenhouse.io/hasbro', 'PRIVATE', 'greenhouse'),
    'Henry Schein': ('https://careers.smartrecruiters.com/henryschein', 'PRIVATE', 'smartrecruiters'),
    'Host Hotels & Resorts': ('https://www.hosthotels.com/Our-Company/Careers', 'PRIVATE', 'static'),
    'Hubbell Incorporated': ('https://careers.hubbell.com/go/All-Jobs/9100800/', 'PRIVATE', 'icims'),
    'Humana': ('https://www.humana.com/about/careers.html', 'PRIVATE', 'static'),
    'Huntington Ingalls Industries': ('https://www.hii.com/careers', 'PRIVATE', 'static'),
    'IDEX Corporation': ('https://idexcorp.com/careers', 'PRIVATE', 'static'),
    'Idexx Laboratories': ('https://www.idexx.com/en/about-idexx/idexx-stories/idexx-education-supports-continuous-learning-at-every-stage-of-a-veterinary-career/', 'PRIVATE', 'static'),
    'Illumina, Inc': ('https://www.illumina.com/company/careers.html', 'PRIVATE', 'static'),
    'Incyte': ('https://careers.incyte.com/jobs', 'PRIVATE', 'static'),
    'Intel': ('https://intel.wd1.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Interactive Brokers': ('https://www.interactivebrokers.com/en/general/about/careers-splash.php?menu=B', 'PRIVATE', 'static'),
    'Intuitive Surgical': ('https://careers.smartrecruiters.com/intuitive', 'PRIVATE', 'smartrecruiters'),
    'Invesco': ('https://careers.invesco.com/', 'PRIVATE', 'static'),
    'Invitation Homes': ('https://careers.invitationhomes.com/', 'PRIVATE', 'static'),
    'Jabil': ('https://careers.jabil.com/jobs.html?_gl=1%2A76lc07%2A_gcl_aw%2AR0NMLjE3NTM5NzU5MzAuRUFJYUlRb2JDaE1JNTl2czM3RG1qZ01WN1ItdEJoMjJqZ0Q0RUFBWUFTQUFFZ0xrRVBEX0J3RQ..%2A_gcl_au%2AMTEwOTcwNDk0OC4xNzU2MjI4NTIy', 'PRIVATE', 'static'),
    'KLA Corporation': ('https://www.kla.com/careers', 'PRIVATE', 'static'),
    'Kenvue': ('https://careers.smartrecruiters.com/kenvue', 'PRIVATE', 'smartrecruiters'),
    'Keurig Dr Pepper': ('https://careers.keurigdrpepper.com/en/search-jobs?acm=ALL&alrpm=ALL&ascf=%5B%7B%22key%22%3A%22ALL%22%2C%22value%22%3A%22%22%7D%5D&country=United+States', 'PRIVATE', 'static'),
    'Kinder Morgan': ('https://careers.kindermorgan.com/careers-home/', 'PRIVATE', 'static'),
    'Kraft Heinz': ('https://careers.kraftheinzcompany.com', 'PRIVATE', 'static'),
    'Labcorp': ('https://labcorp.wd1.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Lam Research': ('https://www.lamresearch.com/careers/careers-overview/', 'PRIVATE', 'static'),
    'Leidos': ('https://leidos.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Lennox International': ('https://www.lennox.com/careers/', 'PRIVATE', 'static'),
    'Live Nation Entertainment': ('https://careers.smartrecruiters.com/livenationentertainment', 'PRIVATE', 'smartrecruiters'),
    'Lockheed Martin': ('https://lockheedmartin.com/en-us/careers/life-at-lm.html', 'PRIVATE', 'static'),
    'M&T Bank': ('https://www.mtb.com/careers', 'PRIVATE', 'static'),
    'MSCI': ('https://careers.msci.com/', 'PRIVATE', 'static'),
    'Marriott International': ('https://careers.marriott.com/', 'PRIVATE', 'static'),
    'Martin Marietta Materials': ('https://www.martinmarietta.com/careers', 'PRIVATE', 'static'),
    'McCormick & Company': ('https://careers.mccormick.com/', 'PRIVATE', 'static'),
    'McKesson Corporation': ('https://careers.mckesson.com/en', 'PRIVATE', 'static'),
    'Meta Platforms': ('https://www.metacareers.com/', 'PRIVATE', 'static'),
    'Microchip Technology': ('https://careers.smartrecruiters.com/microchip', 'PRIVATE', 'smartrecruiters'),
    'Moderna': ('https://www.modernatx.com/careers/life-at-moderna', 'PRIVATE', 'static'),
    'Mondelez International': ('https://www.mondelezinternational.com/united-states/early-careers/', 'PRIVATE', 'static'),
    'Motorola Solutions': ('https://motorolasolutions.wd5.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'News Corp': ('https://careers.newscorp.com', 'PRIVATE', 'static'),
    'NiSource': ('https://www.nisource.com/careers', 'PRIVATE', 'static'),
    'Norfolk Southern': ('https://www.norfolksouthern.com/en/careers/find-your-future', 'PRIVATE', 'static'),
    'Northwestern Medicine': ('https://careers.smartrecruiters.com/northwesternmedicine', 'HOSPITAL', 'smartrecruiters'),
    'Norwegian Cruise Line Holdings': ('https://careers.smartrecruiters.com/norwegiancruiseline', 'PRIVATE', 'smartrecruiters'),
    'Nucor': ('https://nucor.com/careers/', 'PRIVATE', 'static'),
    'Oneok': ('https://www.oneok.com/careers', 'PRIVATE', 'static'),
    'OpenAI': ('https://jobs.ashbyhq.com/openai', 'PRIVATE', 'static'),
    'Otis Worldwide': ('https://www.otis.com/en/us/careers', 'PRIVATE', 'static'),
    'PPG Industries': ('https://www.ppg.com/en-US/about-ppg/careers-at-ppg', 'PRIVATE', 'static'),
    'PPL Corporation': ('https://www.pplweb.com/careers/why-ppl/', 'PRIVATE', 'static'),
    'Paychex': ('https://careers.paychex.com/careers', 'PRIVATE', 'static'),
    'Penn Medicine': ('https://careers.smartrecruiters.com/pennmedicine', 'HOSPITAL', 'smartrecruiters'),
    'PepsiCo': ('https://www.pepsico.com/en/careers', 'PRIVATE', 'static'),
    'Philip Morris International': ('https://www.pmi.com/careers/overview', 'PRIVATE', 'static'),
    'Phillips 66': ('https://www.phillips66.com/careers/', 'PRIVATE', 'static'),
    'Plaid': ('https://jobs.ashbyhq.com/plaid', 'PRIVATE', 'static'),
    'Principal Financial Group': ('https://careers.principal.com/careers-home', 'PRIVATE', 'static'),
    'Prudential Financial': ('https://www.prudential.com/careers', 'PRIVATE', 'static'),
    'Public Service Enterprise Group': ('https://landing.pseg.com/careers', 'PRIVATE', 'static'),
    'Quest Diagnostics': ('https://careers.questdiagnostics.com/', 'PRIVATE', 'static'),
    'Regeneron Pharmaceuticals': ('https://regeneron.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Regions Financial Corporation': ('https://www.regions.com/careers', 'PRIVATE', 'static'),
    'Republic Services': ('https://www.republicservices.com/about/careers.html', 'PRIVATE', 'static'),
    'ResMed': ('https://careers.smartrecruiters.com/resmed', 'PRIVATE', 'smartrecruiters'),
    'Revvity': ('https://revvity.wd103.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Rockwell Automation': ('https://www.rockwellautomation.com/en-us/careers.html', 'PRIVATE', 'static'),
    'Royal Caribbean Group': ('https://careers.royalcaribbeangroup.com/', 'PRIVATE', 'static'),
    'SBA Communications': ('https://www.sbasite.com/company/careers/', 'PRIVATE', 'static'),
    'Seagate Technology': ('https://www.seagate.com/careers/', 'PRIVATE', 'static'),
    'Sherwin-Williams': ('https://careers.sherwin-williams.com/us/en/recruiting-scam-awareness-alert.html', 'PRIVATE', 'static'),
    'Simon Property Group': ('https://careers.simon.com/campus-recruiting', 'PRIVATE', 'static'),
    'Skyworks Solutions': ('https://www.skyworksinc.com/Careers', 'PRIVATE', 'static'),
    'SoFi': ('https://www.sofi.com/careers/', 'PRIVATE', 'static'),
    'Solventum': ('https://www.solventum.com/en-us/home/our-company/careers/', 'PRIVATE', 'static'),
    'Starbucks': ('https://careers.starbucks.com/discover-opportunities/international-careers/', 'PRIVATE', 'static'),
    'Stryker Corporation': ('https://careers.stryker.com/', 'PRIVATE', 'static'),
    'Supermicro': ('https://www.supermicro.com/en/jobs', 'PRIVATE', 'static'),
    'Synopsys': ('https://careers.synopsys.com', 'PRIVATE', 'static'),
    'Sysco': ('https://www.sysco.com/jobs', 'PRIVATE', 'static'),
    'T. Rowe Price': ('https://www.troweprice.com/en/us/careers', 'PRIVATE', 'static'),
    'Teledyne Technologies': ('https://www.teledyne.com/careers', 'PRIVATE', 'static'),
    'Teradyne': ('https://jobs.teradyne.com/teradyne', 'PRIVATE', 'static'),
    'Texas Instruments': ('https://careers.ti.com/en/sites/CX', 'PRIVATE', 'static'),
    'Textron': ('https://careers.textron.com', 'PRIVATE', 'static'),
    'The Coca-Cola Company': ('https://www.coca-colacompany.com/careers', 'PRIVATE', 'static'),
    'The Cooper Companies': ('https://www.coopercos.com/careers/', 'PRIVATE', 'static'),
    'The Hershey Company': ('https://careers.thehersheycompany.com/', 'PRIVATE', 'static'),
    'The Home Depot': ('https://careers.homedepot.com/job-search-results/', 'PRIVATE', 'static'),
    'The Travelers Companies': ('https://travelers.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Trimble Inc': ('https://www.trimble.com/en/careers', 'PRIVATE', 'static'),
    'Truist Financial': ('https://truist.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Tyler Technologies': ('https://www.tylertech.com/careers', 'PRIVATE', 'static'),
    'UDR, Inc': ('https://www.udr.com/careers/', 'PRIVATE', 'static'),
    'Ulta Beauty': ('https://careers.ulta.com/careers/', 'PRIVATE', 'static'),
    'Union Pacific Corporation': ('https://www.up.com/careers', 'PRIVATE', 'static'),
    'United Parcel Service': ('https://www.ups.com/careers', 'PRIVATE', 'static'),
    'Veeva Systems': ('https://careers.veeva.com', 'PRIVATE', 'static'),
    'Verisign': ('https://job-boards.greenhouse.io/verisign', 'PRIVATE', 'greenhouse'),
    'Verisk Analytics': ('https://www.verisk.com/company/careers/', 'PRIVATE', 'static'),
    'Vertiv': ('https://www.vertiv.com/en-us/about/career-center/', 'PRIVATE', 'static'),
    'Viatris': ('https://viatris.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Vici Properties': ('https://viciproperties.com/careers/', 'PRIVATE', 'static'),
    'Vistra Corp': ('https://vistracorp.com/careers/', 'PRIVATE', 'static'),
    'Vulcan Materials Company': ('https://www.vulcanmaterials.com/careers', 'PRIVATE', 'static'),
    'W. R. Berkley Corporation': ('https://www.berkley.com/about-us/careers', 'PRIVATE', 'static'),
    'W. W. Grainger': ('https://www.grainger.com/careers', 'PRIVATE', 'static'),
    'Wabtec': ('https://careers.smartrecruiters.com/wabtec', 'PRIVATE', 'smartrecruiters'),
    'Western Digital': ('https://careers.smartrecruiters.com/westerndigital', 'PRIVATE', 'smartrecruiters'),
    'Weyerhaeuser': ('https://www.weyerhaeuser.com/careers/', 'PRIVATE', 'static'),
    'Williams Companies': ('https://williams.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Williams-Sonoma, Inc': ('https://www.williams-sonoma.com/customer-service/careers/?cm_src=OLDLINK&cm_type=fnav', 'PRIVATE', 'static'),
    'Workday, Inc': ('https://www.workday.com/en-us/company/careers/overview.html', 'PRIVATE', 'static'),
    'Xcel Energy': ('https://xcelenergy.wd1.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Zebra Technologies': ('https://www.zebra.com/us/en/about-zebra/careers.html', 'PRIVATE', 'static'),
    'Zoetis': ('https://www.zoetis.com/join-us', 'PRIVATE', 'static'),
}
BLANK_KINDS = {
    'COLLEGE': 6,
    'DEPT': 16,
    'HOSPITAL': 7,
    'MUNI': 26,
    'NGO': 10,
    'PRIVATE': 230,
    'UNI': 41,
}
LINKED_TOTAL = 534


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_usa_employers_follow_the_direct_link_rule():
    rows = _rows()
    added = [row for row in rows if row["relevance_note"].startswith(NOTE)]
    assert len(added) == len(LINKS) + sum(BLANK_KINDS.values())
    found = {}
    blank_kinds = {kind: 0 for kind in BLANK_KINDS}
    names = []
    for row in added:
        names.append(row["company_name"].casefold())
        assert row["country"] == 'United States'
        assert row["jse_code"] == ""
        assert row["official_website"] == ""
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert ":443" not in row["careers_url"]
        if row["company_name"] in LINKS:
            url, kind, ats = LINKS[row["company_name"]]
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
            blank_kinds[row["source_type"]] += 1
    assert found == {name: LINKS[name][0] for name in LINKS}
    assert blank_kinds == BLANK_KINDS
    assert len(names) == len(set(names))


def test_usa_employer_link_count():
    count = 0
    for row in _rows():
        if row["country"] == 'United States' and row["active"] == "true" and row["careers_url"].strip():
            count += 1
    assert count == LINKED_TOTAL
