"""Asia-Pacific employers added from market indexes, universities, and ATS boards.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, the employer's own
board names a post, and at least half of the located roles are in that country.
Trend Micro is the exception added later: the stored URL is that board's own
Japan filter, which lists the roles named in the note. Alcoa stores its
Australia filter. Charter Hall, Life360, Perpetual, Bridgestone, Sumitomo
Heavy Industries, Terumo, and LG Electronics are large groups whose own board
has no country filter. Those rows are `global_group` and the note contains
`careers_scope=global`. Everyone else from the same lists is a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 apac-employers'
LINKS = {
    '99 Speed Mart Retail Holdings Berhad': ('Malaysia', 'https://99speedmart.com.my/careers/', 'PRIVATE', 'static'),
    'AGC Inc.': ('Japan', 'https://www.agc.com/careers/index.html', 'PRIVATE', 'static'),
    'APA Group': ('Australia', 'https://www.apa.com.au/careers', 'PRIVATE', 'static'),
    'Adani Energy Solutions': ('India', 'https://careers.adani.com/', 'PRIVATE', 'static'),
    'Advantest': ('Japan', 'https://www.advantest.com/en/about/career-na/', 'PRIVATE', 'static'),
    'Ajinomoto': ('Japan', 'https://www.ajinomoto.co.jp/company/jp/recruit/', 'PRIVATE', 'static'),
    'Alcoa': ('Australia', 'https://alcoa.wd5.myworkdayjobs.com/Careers?Location_Country=d903bb3fedad45039383f6de334ad4db', 'PRIVATE', 'workday'),
    'Arvida Group Limited': ('New Zealand', 'https://careers.smartrecruiters.com/arvida', 'PRIVATE', 'smartrecruiters'),
    'Asahi Group Holdings': ('Japan', 'https://www.asahigroup-holdings.com/careers/', 'PRIVATE', 'static'),
    'Astellas Pharma': ('Japan', 'https://www.astellas.com/jp/careers', 'PRIVATE', 'static'),
    'Aurizon': ('Australia', 'https://www.aurizon.com.au/careers/working-at-aurizon', 'PRIVATE', 'static'),
    'Austal': ('Australia', 'https://www.austaljobs.com/', 'PRIVATE', 'static'),
    'Axis Bank': ('India', 'https://www.axis.bank.in/careers', 'PRIVATE', 'static'),
    'Bajaj Auto': ('India', 'https://www.bajajauto.com/careers/why-us', 'PRIVATE', 'static'),
    'Bajaj Holdings': ('India', 'https://www.bajajgroup.org/careers', 'PRIVATE', 'static'),
    'Bandai Namco Holdings': ('Japan', 'https://www.bandainamco.co.jp/recruit/', 'PRIVATE', 'static'),
    'Bank of Baroda': ('India', 'https://bankofbaroda.bank.in/career', 'PRIVATE', 'static'),
    'Bank of Queensland': ('Australia', 'https://www.boq.com.au/about-us/careers/', 'PRIVATE', 'static'),
    'Bank of the Philippine Islands': ('Philippines', 'https://www.bpi.com.ph/about-bpi/careers', 'PRIVATE', 'static'),
    'Banpu': ('Thailand', 'https://www.banpu.com/career/', 'PRIVATE', 'static'),
    'Baycurrent': ('Japan', 'https://www.baycurrent.co.jp/careers/', 'PRIVATE', 'static'),
    'Bharat Petroleum': ('India', 'https://www.bharatpetroleum.in/careers/careers', 'PRIVATE', 'static'),
    'Breville Group': ('Australia', 'https://brevillegroup.com/careers/', 'PRIVATE', 'static'),
    'Bridgestone': ('Japan', 'https://bridgestone.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Britannia Industries': ('India', 'https://www.britannia.co.in/careers', 'PRIVATE', 'static'),
    'Canara Bank': ('India', 'https://www.canarabank.bank.in/pages/career', 'PRIVATE', 'static'),
    'Capstone Copper': ('Australia', 'https://capstonecopper.com/careers/', 'PRIVATE', 'static'),
    'Celltrion': ('South Korea', 'https://www.celltrion.com/en-us/careers/recruit/process', 'PRIVATE', 'static'),
    'Central Pattana': ('Thailand', 'https://www.centralpattana.co.th/en/careers', 'PRIVATE', 'static'),
    'Charter Hall': ('Australia', 'https://charterhall.wd3.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Chiba Bank': ('Japan', 'https://www.chibabank.co.jp/recruit', 'PRIVATE', 'static'),
    'Chorus Limited': ('New Zealand', 'https://company.chorus.co.nz/careers', 'PRIVATE', 'static'),
    'Chubu Electric Power': ('Japan', 'https://www.chuden.co.jp/recruit/', 'PRIVATE', 'static'),
    'Chugai Pharmaceutical': ('Japan', 'https://www.chugai-pharm.co.jp/recruit/', 'PRIVATE', 'static'),
    'City Developments Limited': ('Singapore', 'https://www.cdl.com.sg/careers', 'PRIVATE', 'static'),
    'Coal India': ('India', 'https://www.coalindia.in/employee-corner/career-cil/', 'PRIVATE', 'static'),
    'Computershare': ('Australia', 'https://www.computershare.com/corporate/careers/join-our-team', 'PRIVATE', 'static'),
    'Comsys Holdings': ('Japan', 'https://www.comsys-hd.co.jp/recruit.html', 'PRIVATE', 'static'),
    'Contact Energy Limited': ('New Zealand', 'https://careers.smartrecruiters.com/contactenergy', 'PRIVATE', 'smartrecruiters'),
    'Corporate Travel Management': ('Australia', 'https://au.travelctm.com/careers/', 'PRIVATE', 'static'),
    'Credit Saison': ('Japan', 'https://www.saisoncard.co.jp/recruit/', 'PRIVATE', 'static'),
    'CyberAgent': ('Japan', 'https://www.cyberagent.co.jp/techinfo/careers/', 'PRIVATE', 'static'),
    'DMart': ('India', 'https://www.dmartindia.com/careers', 'PRIVATE', 'static'),
    'Daewoo E&C': ('South Korea', 'https://www.daewooenc.com/careers', 'PRIVATE', 'static'),
    'Dai Nippon Printing': ('Japan', 'https://www.dnp.co.jp/recruit/', 'PRIVATE', 'static'),
    'Dai-ichi Life': ('Japan', 'https://www.daiichilife-group.com/recruit/', 'PRIVATE', 'static'),
    'Daikin Industries': ('Japan', 'https://www.daikin.co.jp/recruit', 'PRIVATE', 'static'),
    'Daiwa Securities Group': ('Japan', 'https://www.daiwa-grp.jp/recruit/', 'PRIVATE', 'static'),
    'Denka': ('Japan', 'https://www.denka.co.jp/rec/', 'PRIVATE', 'static'),
    'Dentsu': ('Japan', 'https://www.dentsu.co.jp/careers/', 'PRIVATE', 'static'),
    'Doosan Robotics': ('South Korea', 'https://jobs.doosan.com/', 'PRIVATE', 'static'),
    'Dowa Holdings': ('Japan', 'https://hd.dowa.co.jp/ja/recruit.html', 'PRIVATE', 'static'),
    'Downer Group': ('Australia', 'https://downergroup.com/life-at-downer/downer-benefits/your-career/', 'PRIVATE', 'static'),
    'Droneshield': ('Australia', 'https://www.droneshield.com/careers', 'PRIVATE', 'static'),
    'Endeavour Group': ('Australia', 'https://www.endeavourgroup.com.au/careers', 'PRIVATE', 'static'),
    'Eneos Holdings': ('Japan', 'https://www.hd.eneos.co.jp/recruit/', 'PRIVATE', 'static'),
    'Evolution Mining': ('Australia', 'https://evolutionmining.com/careers/', 'PRIVATE', 'static'),
    'Fast Retailing': ('Japan', 'https://www.fastretailing.com/employment/en/', 'PRIVATE', 'static'),
    'Fisher & Paykel Healthcare Corporation Limited': ('New Zealand', 'https://careers.fphcare.com', 'PRIVATE', 'static'),
    'Fletcher Building Limited': ('New Zealand', 'https://fletcherbuilding.com/careers', 'PRIVATE', 'static'),
    'Fuji Electric': ('Japan', 'https://www.fujielectric.co.jp/recruit/', 'PRIVATE', 'static'),
    'Fujikura': ('Japan', 'https://www.fujikura.co.jp/recruit/', 'PRIVATE', 'static'),
    'Furukawa Electric': ('Japan', 'https://www.furukawaelectric.com/saiyou/recruit/', 'PRIVATE', 'static'),
    'GPT Group': ('Australia', 'https://www.gpt.com.au/about-us/careers', 'PRIVATE', 'static'),
    'Gamuda Berhad': ('Malaysia', 'https://careers.gamuda.com.my/', 'PRIVATE', 'static'),
    'Global Power Synergy': ('Thailand', 'https://www.gpscgroup.com/th/career', 'PRIVATE', 'static'),
    'Griffith University': ('Australia', 'https://careers.smartrecruiters.com/griffithuniversity', 'UNI', 'smartrecruiters'),
    'Gulf Development': ('Thailand', 'https://www.gulf.co.th/en/careers/life-at-gulf', 'PRIVATE', 'static'),
    'Hankook': ('South Korea', 'https://www.hankookandcompany.com/en/career.do', 'PRIVATE', 'static'),
    'Hanon Systems': ('South Korea', 'https://www.hanonsystems.com/kr/recruit', 'PRIVATE', 'static'),
    'Hanwha': ('South Korea', 'https://www.hanwha.com/careers.do', 'PRIVATE', 'static'),
    'Hanwha Aerospace': ('South Korea', 'https://www.hanwhaaerospace.com/eng/careers/recruit.do', 'PRIVATE', 'static'),
    'Hanwha Solutions': ('South Korea', 'https://www.hanwhasolutions.com/careers', 'PRIVATE', 'static'),
    'Hanwha Systems': ('South Korea', 'https://www.hanwhasystems.com/kr/recruit/recruit4.do', 'PRIVATE', 'static'),
    'Harvey Norman': ('Australia', 'https://www.harveynorman.com.au/careers', 'PRIVATE', 'static'),
    'Haseko Corp.': ('Japan', 'https://www.haseko.co.jp/hc/recruit/', 'PRIVATE', 'static'),
    'Heartland Group Holdings Limited': ('New Zealand', 'https://www.heartland.co.nz/about-us/careers', 'PRIVATE', 'static'),
    'Hindustan Zinc': ('India', 'https://www.hzlindia.com/careers/our-culture', 'PRIVATE', 'static'),
    'Hitachi': ('Japan', 'https://careers.hitachi.com/', 'PRIVATE', 'static'),
    'Hoya Corporation': ('Japan', 'https://www.hoya.com/recruit/', 'PRIVATE', 'static'),
    'Hyosung TNC': ('South Korea', 'https://www.hyosungtnc.com/kr/recruit', 'PRIVATE', 'static'),
    'Hyundai Steel': ('South Korea', 'https://www.hyundai-steel.com/careers', 'PRIVATE', 'static'),
    'Hyundai WIA': ('South Korea', 'https://en.hyundai-wia.com/careers', 'PRIVATE', 'static'),
    'Idemitsu Kosan': ('Japan', 'https://www.idemitsu.com/jp/recruit/index.html', 'PRIVATE', 'static'),
    'Indian Oil Corporation': ('India', 'https://www.iocl.com/careers', 'PRIVATE', 'static'),
    'Inpex': ('Japan', 'https://www.inpex-recruit.com/womens_career/', 'PRIVATE', 'static'),
    'International Container Terminal Services': ('Philippines', 'https://www.ictsi.com/our-people/current-vacancies', 'PRIVATE', 'static'),
    'J. Front Retailing': ('Japan', 'https://www.j-front-retailing.com/recruit/', 'PRIVATE', 'static'),
    'JFE Holdings': ('Japan', 'https://www.jfe-holdings.co.jp/recruitment/', 'PRIVATE', 'static'),
    'JGC Corporation': ('Japan', 'https://www.jgc.com/jp/recruit/', 'PRIVATE', 'static'),
    'Japan Exchange Group': ('Japan', 'https://www.jpx.co.jp/corporate/about-jpx/recruit/index.html', 'PRIVATE', 'static'),
    'Japan Post Holdings': ('Japan', 'https://www.post.japanpost.jp/employment/', 'PRIVATE', 'static'),
    'Kakao': ('South Korea', 'https://careers.kakao.com/index', 'PRIVATE', 'static'),
    'Kanadevia': ('Japan', 'https://www.kanadevia.com/employ/', 'PRIVATE', 'static'),
    'Kasikornbank': ('Thailand', 'https://www.kasikornbank.com/careers', 'PRIVATE', 'static'),
    'Keisei Electric Railway': ('Japan', 'https://www.keiseiline.jp/keiseijobs/', 'PRIVATE', 'static'),
    'Keppel Corporation': ('Singapore', 'https://www.keppel.com/careers/', 'PRIVATE', 'static'),
    'Keyence': ('Japan', 'https://www.keyence.com/ss/careers/', 'PRIVATE', 'static'),
    'Kia': ('South Korea', 'https://www.kia.com/us/en/careers', 'PRIVATE', 'static'),
    'Kioxia Holdings': ('Japan', 'https://www.kioxia.com/en-jp/job.html', 'PRIVATE', 'static'),
    'Kirin Holdings': ('Japan', 'https://www.kirinholdings.com/en/careers/', 'PRIVATE', 'static'),
    'Kiwi Property Group Limited': ('New Zealand', 'https://www.kiwiproperty.com/about-us/careers-and-culture', 'PRIVATE', 'static'),
    'Komatsu': ('Japan', 'https://www.komatsu.jp/ja/recruit', 'PRIVATE', 'static'),
    'Konica Minolta Holdings': ('Japan', 'https://www.konicaminolta.com/jp-ja/recruit/index.html', 'PRIVATE', 'static'),
    'Kotak Mahindra Bank': ('India', 'https://www.kotak.bank.in/en/about-us/careers.html', 'PRIVATE', 'static'),
    'Kubota': ('Japan', 'https://www.kubota.com/corporate/careers/index.html', 'PRIVATE', 'static'),
    'Kumho Petrochemical': ('South Korea', 'https://www.kkpc.com/kor/recruit/aboutJob/', 'PRIVATE', 'static'),
    'Kuraray': ('Japan', 'https://www.kuraray.com/global-en/recruit/', 'PRIVATE', 'static'),
    'LG CNS': ('South Korea', 'https://www.lgcns.com/en/careers/who-we-are', 'PRIVATE', 'static'),
    'LG Chem': ('South Korea', 'https://www.lgchem.com/career/index', 'PRIVATE', 'static'),
    'LG Display': ('South Korea', 'https://www.lgdisplay.com/kor/company/employ/job-application/interview', 'PRIVATE', 'static'),
    'LG Electronics': ('South Korea', 'https://job-boards.greenhouse.io/lgelectronics', 'PRIVATE', 'greenhouse'),
    'LG Energy Solution': ('South Korea', 'https://www.lgensol.com/kr/career/career-talent', 'PRIVATE', 'static'),
    'Land and Houses': ('Thailand', 'https://www.lh.co.th/th/careers', 'PRIVATE', 'static'),
    'Larsen & Toubro': ('India', 'https://www.larsentoubro.com/careers', 'PRIVATE', 'static'),
    'Lasertec': ('Japan', 'https://lasertec-saiyo.jp', 'PRIVATE', 'static'),
    'Life360': ('Australia', 'https://job-boards.greenhouse.io/life360', 'PRIVATE', 'greenhouse'),
    'Lotte Wellfood': ('South Korea', 'https://careers.lottewellfood.com/go/ALL-JOBS/507650/', 'PRIVATE', 'icims'),
    'Macquarie Group': ('Australia', 'https://recruitment.macquarie.com/en_US/careers', 'PRIVATE', 'static'),
    'Mahindra & Mahindra': ('India', 'https://www.mahindra.com/career', 'PRIVATE', 'static'),
    'Manawa Energy Limited': ('New Zealand', 'https://www.manawaenergy.co.nz/careers', 'PRIVATE', 'static'),
    'Marubeni': ('Japan', 'https://www.marubeni.com/jp/recruit/', 'PRIVATE', 'static'),
    'Marui Group': ('Japan', 'https://www.0101maruigroup.co.jp/recruit/', 'PRIVATE', 'static'),
    'Maruti Suzuki': ('India', 'https://www.marutisuzuki.com/corporate/careers', 'PRIVATE', 'static'),
    'Meiji Holdings': ('Japan', 'https://www.meiji.com/new-graduate/', 'PRIVATE', 'static'),
    'Meralco': ('Philippines', 'https://company.meralco.com.ph/career-opportunities/overview', 'PRIVATE', 'static'),
    'Meridian Energy Limited': ('New Zealand', 'https://www.meridianenergy.co.nz/careers', 'PRIVATE', 'static'),
    'MinebeaMitsumi': ('Japan', 'https://www.minebeamitsumi.com/corp/recruit/', 'PRIVATE', 'static'),
    'Minor International': ('Thailand', 'https://www.minor.com/en/careers', 'PRIVATE', 'static'),
    'Mirvac': ('Australia', 'https://www.mirvac.com/careers/our-culture', 'PRIVATE', 'static'),
    'Mitsubishi Electric': ('Japan', 'https://www.mitsubishielectric.com/en/careers/', 'PRIVATE', 'static'),
    'Mitsubishi Estate': ('Japan', 'https://www.mec.co.jp/saiyou/', 'PRIVATE', 'static'),
    'Mitsubishi Heavy Industries': ('Japan', 'https://www.mhi.com/recruit/', 'PRIVATE', 'static'),
    'Mitsubishi Materials': ('Japan', 'https://www.mmc.co.jp/corporate/ja/recruit/', 'PRIVATE', 'static'),
    'Mitsubishi UFJ Financial Group': ('Japan', 'https://www.mufg.jp/careers/index.html?link_id=gnavi_careers', 'PRIVATE', 'static'),
    'Mitsui & Co.': ('Japan', 'https://career.mitsui.com/', 'PRIVATE', 'static'),
    'Mitsui Fudosan': ('Japan', 'https://www.mitsuifudosan.co.jp/corporate/recruit/', 'PRIVATE', 'static'),
    'Monde Nissin': ('Philippines', 'https://mondenissin.com/careers-and-opportunities/', 'PRIVATE', 'static'),
    'Murata Manufacturing': ('Japan', 'https://corporate.murata.com/careers', 'PRIVATE', 'static'),
    'NRW Holdings': ('Australia', 'https://nrw.com.au/people-careers/', 'PRIVATE', 'static'),
    'NSK Ltd.': ('Japan', 'https://www.nsk.com/company/career/', 'PRIVATE', 'static'),
    'NextDC': ('Australia', 'https://careers.smartrecruiters.com/nextdc', 'PRIVATE', 'smartrecruiters'),
    'Nichirei': ('Japan', 'https://www.nichirei.co.jp/saiyo/recruit/', 'PRIVATE', 'static'),
    'Nippon Express': ('Japan', 'https://www.nipponexpress.com/careers/', 'PRIVATE', 'static'),
    'Nippon Express Holdings': ('Japan', 'https://www.nipponexpress-holdings.com/ja/recruit/', 'PRIVATE', 'static'),
    'Nippon Steel': ('Japan', 'https://www.nipponsteel.com/recruit/', 'PRIVATE', 'static'),
    'Nippon Yusen': ('Japan', 'https://www.nyk.com/recruit/', 'PRIVATE', 'static'),
    'Nissan': ('Japan', 'https://www.nissanmotor.jobs/', 'PRIVATE', 'static'),
    'Nisshin Seifun Group': ('Japan', 'https://www.nisshin-recruit.com/', 'PRIVATE', 'static'),
    'Nissui': ('Japan', 'https://www.nissui.co.jp/recruit/index.html', 'PRIVATE', 'static'),
    'Nomura Holdings': ('Japan', 'https://www.nomura.com/careers/', 'PRIVATE', 'static'),
    'Nomura Research Institute': ('Japan', 'https://www.nri.com/jp/career.html', 'PRIVATE', 'static'),
    'Northern Star Resources': ('Australia', 'https://careers.nsrltd.com/', 'PRIVATE', 'static'),
    'Obayashi Corp.': ('Japan', 'https://www.obayashi.co.jp/recruit/', 'PRIVATE', 'static'),
    'Odakyu Electric Railway': ('Japan', 'https://www.odakyu.jp/recruit/', 'PRIVATE', 'static'),
    'Oil and Natural Gas Corporation': ('India', 'https://ongcindia.com/web/eng/career/why-work-with-ongc', 'PRIVATE', 'static'),
    'Olympus': ('Japan', 'https://www.olympus-global.com/recruit/', 'PRIVATE', 'static'),
    'Otsuka Holdings': ('Japan', 'https://www.otsuka.com/jp/company/recruit/', 'PRIVATE', 'static'),
    'Perpetual': ('Australia', 'https://perpetual.wd3.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Rakuten': ('Japan', 'https://corp.rakuten.co.jp/careers/', 'PRIVATE', 'static'),
    'Ramsay Health Care': ('Australia', 'https://www.ramsayhealth.com/en/people-and-careers/', 'PRIVATE', 'static'),
    'Ratch Group': ('Thailand', 'https://www.ratch.co.th/en/careers', 'PRIVATE', 'static'),
    'Recruit Holdings': ('Japan', 'https://recruit-holdings.com/ja/about/careers/', 'PRIVATE', 'static'),
    'Reece Group': ('Australia', 'https://careers.reece.com/us', 'PRIVATE', 'static'),
    'Ricoh': ('Japan', 'https://jp.ricoh.com/jobs', 'PRIVATE', 'static'),
    'SK Innovation': ('South Korea', 'https://www.skinnovation.com/recruit/org_culture', 'PRIVATE', 'static'),
    'SK Telecom': ('South Korea', 'https://careers.sktelecom.com', 'PRIVATE', 'static'),
    'Samsung Biologics': ('South Korea', 'https://samsungbiologics.com/careers/value', 'PRIVATE', 'static'),
    'Samsung C&T': ('South Korea', 'https://www.samsungcnt.com/about-us/careers.do', 'PRIVATE', 'static'),
    'Samsung Electronics': ('South Korea', 'https://www.samsung.com/us/careers/', 'PRIVATE', 'static'),
    'Samsung Heavy Industries': ('South Korea', 'https://www.samsungshi.com/careers', 'PRIVATE', 'static'),
    'Samsung SDI': ('South Korea', 'https://www.samsungsdi.co.kr/career/index.html', 'PRIVATE', 'static'),
    'San Miguel Corporation': ('Philippines', 'https://www.sanmiguel.com.ph/careers', 'PRIVATE', 'static'),
    'Sandfire Resources': ('Australia', 'https://www.sandfire.com.au/careers/', 'PRIVATE', 'static'),
    'Sapporo Holdings': ('Japan', 'https://www.sapporobreweries.com/employment/', 'PRIVATE', 'static'),
    'Seah Steel Holdings': ('South Korea', 'https://www.seahsteel.co.kr/careers', 'PRIVATE', 'static'),
    'Seatrium Limited': ('Singapore', 'https://seatrium.wd3.myworkdayjobs.com/SeatriumCareers', 'PRIVATE', 'workday'),
    'Secom': ('Japan', 'https://www.secom.co.jp/recruit/portal/?link=header', 'PRIVATE', 'static'),
    'Sekisui House': ('Japan', 'https://www.sekisuihouse.co.jp/recruit/', 'PRIVATE', 'static'),
    'Shinsegae': ('South Korea', 'https://www.shinsegae.com/careers', 'PRIVATE', 'static'),
    'Shionogi': ('Japan', 'https://www.shionogi.com/jp/ja/recruit.html', 'PRIVATE', 'static'),
    'Shiseido': ('Japan', 'https://corp.shiseido.com/en/careers/', 'PRIVATE', 'static'),
    'Shizuoka Bank': ('Japan', 'https://www.shizuokabank.co.jp/recruitment/index.html', 'PRIVATE', 'static'),
    'Shizuoka Financial Group': ('Japan', 'https://www.shizuoka-fg.co.jp/recruitment/', 'PRIVATE', 'static'),
    'Shree Cement': ('India', 'https://www.shreecement.com/careers', 'PRIVATE', 'static'),
    'Shriram Finance': ('India', 'https://www.shriramfinance.in/careers', 'PRIVATE', 'static'),
    'Singtel': ('Singapore', 'https://groupcareers.singtel.com', 'PRIVATE', 'static'),
    'SoftBank': ('Japan', 'https://group.softbank/about/careers', 'PRIVATE', 'static'),
    'SoftBank Group': ('Japan', 'https://group.softbank/about/careers', 'PRIVATE', 'static'),
    'Sojitz': ('Japan', 'https://www.sojitz.com/jp/recruit/', 'PRIVATE', 'static'),
    'Sompo Holdings': ('Japan', 'https://www.sompo-hd.com/recruit/', 'PRIVATE', 'static'),
    'Subaru': ('Japan', 'https://www.subaru.co.jp/recruit/', 'PRIVATE', 'static'),
    'Sumitomo Chemical': ('Japan', 'https://www.sumitomo-chem.co.jp/recruit/', 'PRIVATE', 'static'),
    'Sumitomo Electric Industries': ('Japan', 'https://sumitomoelectric.com/careers', 'PRIVATE', 'static'),
    'Sumitomo Heavy Industries': ('Japan', 'https://sumitomoheavyindustries.wd103.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Sumitomo Metal Mining': ('Japan', 'https://www.smm.co.jp/r_info/saiyo/', 'PRIVATE', 'static'),
    'Sumitomo Realty & Development': ('Japan', 'https://www.sumitomo-rd.co.jp/recruit/', 'PRIVATE', 'static'),
    'Suncorp': ('Australia', 'https://www.suncorpgroup.com.au/careers', 'PRIVATE', 'static'),
    'Super Retail Group': ('Australia', 'https://superretailgroup.com.au/careers/', 'PRIVATE', 'static'),
    'TPG Telecom': ('Australia', 'https://www.tpgtelecom.com.au/careers', 'PRIVATE', 'static'),
    'TRUE Corporation': ('Thailand', 'https://www.true.th/careers', 'PRIVATE', 'static'),
    'Taihan Cable & Solution': ('South Korea', 'https://www.taihan.com/company/jobs', 'PRIVATE', 'static'),
    'Taisei': ('Japan', 'https://www.taisei.co.jp/saiyo/', 'PRIVATE', 'static'),
    'Tata Consumer Products': ('India', 'https://www.tataconsumer.com/people/careers-for-professionals', 'PRIVATE', 'static'),
    'Tata Steel': ('India', 'https://www.tatasteel.com/careers/', 'PRIVATE', 'static'),
    'Teijin': ('Japan', 'https://www.teijin.com/recruit/', 'PRIVATE', 'static'),
    'Terumo': ('Japan', 'https://terumo.wd3.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Thai Life Insurance': ('Thailand', 'https://careers.thailife.com', 'PRIVATE', 'static'),
    'Thai Oil': ('Thailand', 'https://careers.thaioilgroup.com/', 'PRIVATE', 'static'),
    'Thai Union Group': ('Thailand', 'https://www.thaiunion.com/careers', 'PRIVATE', 'static'),
    'The Lottery Corporation': ('Australia', 'https://www.thelotterycorporation.com/work-with-us/tech-careers', 'PRIVATE', 'static'),
    'The a2 Milk Company Limited': ('New Zealand', 'https://careers.thea2milkcompany.com', 'PRIVATE', 'static'),
    'Tobu Railway': ('Japan', 'https://www.tobu.co.jp/recruit/', 'PRIVATE', 'static'),
    'Tokio Marine Holdings': ('Japan', 'https://www.tokiomarinehd.com/careers/', 'PRIVATE', 'static'),
    'Tokyo Electron': ('Japan', 'https://www.tel.com/careers/', 'PRIVATE', 'static'),
    'Tokyo Gas': ('Japan', 'https://www.tokyo-gas.co.jp/recruit/index.html', 'PRIVATE', 'static'),
    'Tokyo Tatemono': ('Japan', 'https://tatemono.com/recruit/', 'PRIVATE', 'static'),
    'Tokyu': ('Japan', 'https://www.tokyu.co.jp/company/recruit/', 'PRIVATE', 'static'),
    'Tokyu Land': ('Japan', 'https://www.tokyu-land.co.jp/recruit/', 'PRIVATE', 'static'),
    'Toppan Printing': ('Japan', 'https://www.holdings.toppan.com/ja/recruit/', 'PRIVATE', 'static'),
    'Toto Ltd.': ('Japan', 'https://jp.toto.com/career/', 'PRIVATE', 'static'),
    'Transurban': ('Australia', 'https://careers.transurban.com', 'PRIVATE', 'static'),
    'Treasury Wine Estates': ('Australia', 'https://www.tweglobal.com/life-at-twe', 'PRIVATE', 'static'),
    'Trend Micro': ('Japan', 'https://trendmicro.wd3.myworkdayjobs.com/External?locationCountry=8b705da2becf43cfaccc091da0988ab2', 'PRIVATE', 'workday'),
    'UOL Group': ('Singapore', 'https://www.uol.com.sg/our-people/careers/', 'PRIVATE', 'static'),
    'UltraTech Cement': ('India', 'https://www.ultratechcement.com/corporate/career/overview', 'PRIVATE', 'static'),
    'United Overseas Bank': ('Singapore', 'https://www.uobgroup.com/careers/index.page', 'PRIVATE', 'static'),
    'Universal Robina': ('Philippines', 'https://www.urc.com.ph/careers', 'PRIVATE', 'static'),
    'Vector Limited': ('New Zealand', 'https://vector.co.nz/about-us/careers', 'PRIVATE', 'static'),
    'Wesfarmers': ('Australia', 'https://www.wesfarmers.com.au/util/careers/working-at-wesfarmers', 'PRIVATE', 'static'),
    'Westpac': ('Australia', 'https://www.westpac.com.au/about-westpac/careers/?wbc-vnty=www.westpac.com.au%2Fcareers', 'PRIVATE', 'static'),
    'Whitehaven Coal': ('Australia', 'https://whitehavencoal.com.au/people-careers/graduates-students/', 'PRIVATE', 'static'),
    'Wilmar International': ('Singapore', 'https://www.wilmar-international.com/careers', 'PRIVATE', 'static'),
    'Wisetech Global': ('Australia', 'https://www.wisetechglobal.com/careers/join-us/', 'PRIVATE', 'static'),
    'Yamaha Motor Company': ('Japan', 'https://global.yamaha-motor.com/jp/recruit/', 'PRIVATE', 'static'),
    'Yamato Holdings': ('Japan', 'https://www.yamato-hd.co.jp/recruit/', 'PRIVATE', 'static'),
    'Yancoal Australia': ('Australia', 'https://careers.yancoal.com.au/go/Career-Opportunities/7877410/', 'PRIVATE', 'icims'),
    'Yaskawa Electric Corporation': ('Japan', 'https://www.yaskawa.co.jp/jobs', 'PRIVATE', 'static'),
    'Yokogawa Electric': ('Japan', 'https://www.yokogawa.com/about/careers/', 'PRIVATE', 'static'),
    'Yokohama Rubber': ('Japan', 'https://www.y-yokohama.com/global/profile/notification/202512/', 'PRIVATE', 'static'),
}
BLANK = {
    ('Australia', 'HOSPITAL'): 1,
    ('Australia', 'NGO'): 1,
    ('Australia', 'PRIVATE'): 75,
    ('Australia', 'UNI'): 39,
    ('India', 'DEPT'): 1,
    ('India', 'HOSPITAL'): 1,
    ('India', 'MUNI'): 1,
    ('India', 'PRIVATE'): 67,
    ('India', 'UNI'): 51,
    ('Indonesia', 'HOSPITAL'): 1,
    ('Indonesia', 'MUNI'): 1,
    ('Indonesia', 'PRIVATE'): 43,
    ('Indonesia', 'UNI'): 2,
    ('Japan', 'HOSPITAL'): 1,
    ('Japan', 'MUNI'): 1,
    ('Japan', 'NGO'): 1,
    ('Japan', 'PRIVATE'): 106,
    ('Japan', 'UNI'): 86,
    ('Malaysia', 'DEPT'): 1,
    ('Malaysia', 'MUNI'): 1,
    ('Malaysia', 'PRIVATE'): 24,
    ('Malaysia', 'UNI'): 1,
    ('New Zealand', 'HOSPITAL'): 1,
    ('New Zealand', 'MUNI'): 1,
    ('New Zealand', 'PRIVATE'): 37,
    ('New Zealand', 'UNI'): 7,
    ('Philippines', 'HOSPITAL'): 1,
    ('Philippines', 'MUNI'): 1,
    ('Philippines', 'PRIVATE'): 22,
    ('Philippines', 'UNI'): 2,
    ('Singapore', 'DEPT'): 1,
    ('Singapore', 'HOSPITAL'): 1,
    ('Singapore', 'PRIVATE'): 22,
    ('Singapore', 'SOE'): 1,
    ('Singapore', 'UNI'): 24,
    ('South Korea', 'HOSPITAL'): 1,
    ('South Korea', 'MUNI'): 1,
    ('South Korea', 'NGO'): 1,
    ('South Korea', 'PRIVATE'): 100,
    ('South Korea', 'UNI'): 44,
    ('Thailand', 'HOSPITAL'): 1,
    ('Thailand', 'MUNI'): 1,
    ('Thailand', 'PRIVATE'): 37,
    ('Thailand', 'UNI'): 2,
    ('Vietnam', 'HOSPITAL'): 1,
    ('Vietnam', 'MUNI'): 1,
    ('Vietnam', 'PRIVATE'): 3,
    ('Vietnam', 'SOE'): 2,
    ('Vietnam', 'UNI'): 1,
}
LINKED_TOTAL = {
    'India': 49,
    'Singapore': 16,
    'Australia': 68,
    'New Zealand': 20,
    'Japan': 116,
    'South Korea': 36,
    'Indonesia': 9,
    'Malaysia': 5,
    'Thailand': 14,
    'Vietnam': 1,
    'Philippines': 11,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_apac_employers_follow_the_direct_link_rule():
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


def test_apac_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
