# Low-data channels

Fetched 2026-10-13. Prices are what those pages printed that day. They exclude a shortcode: this repository does not contain one, and the callbacks stay off until the values in `render.yaml` are set on the Frankfurt service.

The USSD callback is `POST /api/v1/ussd`. It answers `404` with `USSD is off. No shortcode is configured.` until `USSD_ENABLED` is true and `USSD_CALLBACK_SECRET` is set. The secret is the `X-Ussd-Secret` header, or the `secret` query parameter. The access log redacts a query parameter whose name contains `secret`. Africa's Talking posts `sessionId`, `serviceCode`, `phoneNumber` and `text`. It does not document a custom header, so the callback URL can carry `?secret=` once the owner has the value from the provider.

The menu is: categories (job, internship, learnership, bursary, graduate programme), the nine South African provinces, the latest stored learnerships, the latest stored bursaries, and a request to save the caller's number for SMS. A result is at most three stored South African titles that are still open and not past a stored closing date. Saving a number writes `sms_alerts`. No SMS is sent. The reply says so.

WhatsApp is `GET /api/v1/whatsapp` and `POST /api/v1/whatsapp`. Both answer `404` with `WhatsApp is off. No phone number is configured.` until `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_APP_SECRET` are all set. The POST checks `X-Hub-Signature-256`. A text message gets the same menu. A reply is posted to `https://graph.facebook.com/v21.0/{phone-number-id}/messages` only when those values are set.

## Africa's Talking

Account: <https://africastalking.com/>. Pricing page fetched: <https://africastalking.com/pricing>. SMS page fetched: <https://africastalking.com/sms/bulksms>. Help article, 27 May 2025: <https://help.africastalking.com/en/articles/1163556-how-much-is-a-dedicated-ussd-code>. That article says USSD is available in South Africa and then prints Kenya and Uganda figures. It says to email info@africastalking.com and ussd@africastalking.com. It does not print a rand figure.

On the pricing page, the block that names MTN, Vodacom, Cell C and Telkom in rand:

- Shared code: setup free, monthly maintenance ZAR 1,000, compulsory deposit USD 100. Post-paid session (the code owner pays) ZAR 0.50 per 20 seconds on all of those networks. Pre-paid session (the person pays from airtime) ZAR 0.25 per 20 seconds, and Africa's Talking also charges a session amount in that same table.
- Dedicated code, raised on those four networks, same USD 100 deposit: setup ZAR 5,000, monthly maintenance ZAR 5,000. Post-paid ZAR 0.50 per 20 seconds. Pre-paid ZAR 0.25 per 20 seconds.

The SMS page's South Africa rows:

- Outgoing SMS ZAR 0.24.
- Dedicated long code: setup ZAR 1,500, monthly maintenance ZAR 700, outgoing SMS ZAR 0.24, incoming SMS ZAR 0.70.

The same pricing page lists Africa's Talking's own WhatsApp fees, which are their charge and not Meta's rate card: setup USD 85, monthly maintenance USD 50. South Africa per message: marketing USD 0.053, utility USD 0.013, authentication USD 0.013, service USD 0.002.

The code the network assigns is whatever Africa's Talking returns after the application. Do not put a guessed code in the seed, the menu, or the environment.

## Vodacom Messaging

PDF fetched: <https://www.vodacommessaging.co.za/products/pdf/USSD%20API.pdf>. It says the figures are exclusive of VAT.

- Session cost 5c per session.
- Dedicated code R2000 per month per string.
- Once-off activation R500 per string.
- USSD is only for messaging-account holders. The PDF says a minimum spend of R165 per month on SMS.
- End-user wording on that PDF: "Vodacom, CellC & Telkom: R0.18c per 20 seconds. MTN: R0.187c per 20 seconds."

The tariffs page <https://www.vodacommessaging.co.za/tariffs_ussd.asp>, fetched the same day, shows USSD API R2 000.00 and R0.05c, and says messaging accounts have a minimum of 500 SMS at R155 per month. Those two Vodacom pages do not match each other. Confirm the live figure with sales@vodacommessaging.co.za before paying.

## WhatsApp Business Cloud API

Meta's pricing page <https://developers.facebook.com/docs/whatsapp/pricing> refused this session's fetch (HTTP 403). Do not use a guessed per-message rate. The owner reads that page while creating the app, then sets the four environment values above. The phone number id comes from that app. A business number is required. The Cloud API is documented at <https://developers.facebook.com/docs/whatsapp/cloud-api>.

## Praekelt and Turn.io

Turn.io is the messaging product associated with Praekelt. This session did not fetch a public South African price list from them. Ask them for a quote rather than copying a third-party figure. Product page: <https://www.turn.io/>.

## Zero-rating: what to do, and what does not fit

Fetched 2026-10-13. Sospana Sonke is on Vercel (`sospana-sonke.vercel.app`). It is not a `.gov.za` site. Nothing in this repository shows a SARS public-benefit registration. The notes below are the published rules. They are not a claim that this site qualifies.

### ICASA, which covers MTN, Vodacom, Telkom and Cell C together

Government Gazette 50612, General Notice 2450 of 2024 (2 May 2024): <https://www.icasa.org.za/uploads/files/50612-2-5-ICASA.pdf>

GCIS write-up of that notice: <https://www.gcis.gov.za/guidelines/website/zero-rating>

Eligible applicants in those pages are public benefit organisations registered with SARS, and government departments on a `.gov.za` name. The application goes to ICASA, not to each network:

- Email: zeroratingapplications@icasa.org.za
- Or Licensing and Compliance Division, Block B, Eco Point Office Park, 350 Witch-Hazel Avenue, Eco Park, Centurion, or Private Bag X10, Highveld Park, 0169

A PBO must attach SARS proof. The motivation is at most 300 words. The site needs a static IPv4 and IPv6 address hosted in South Africa. The notice says a Cloudflare-type address will not be onboarded. Commercial content is not zero-rated. Embedded content and links to other sites are not covered. Video must not be above 480p. Fair use on the GCIS page is 300 MB a day and 2 GB a month per device.

Action: do not send that application for the current Vercel site. It is not `.gov.za`, a PBO registration is not on file here, and the host is not a static South African address. If the owner later registers a PBO with SARS and moves the public pages to a South African host with a static address, send the application to the email above and wait for ICASA to pass the name to the licence holders. The GCIS page says operators then have 14 working days, and it also records that a GCIS submission was answered about nine months later.

This session did not find a separate MTN, Telkom or Cell C form for a private website. Telkom's page <https://group.telkom.co.za/about-us/zero-rated-portal.html> is a list of sites they already zero-rated (health and education). It is not an application form. The 2020 COVID education-and-health directions at <https://www.gov.za/sites/default/files/gcis_document/202006/43411gon651.pdf> are the old process.

### Vodacom ConnectU

Page fetched: <https://www.vodacom.co.za/vodacom/shopping/v/connectu>

It says jobseekers get free access to selected job sites, and it names JOBJACK, Careers24, PNet, Job Mail, Giraffe, Career Junction, SA Learnerships, bursaries-southafrica.co.za and internships-southafrica.co.za. The same page says schools, universities, colleges, hospitals and clinics can request to have their websites zero-rated. It does not say a private job platform can, and it does not print an application form. The in-network address it gives is <http://connectu.vodacom.co.za/>.

Action: write to Vodacom from that page and ask whether a free job-discovery site can be added the way those job boards were. Do not describe the current site as already accepted.

### Moya, and data-free products that are not ICASA zero-rating

MoyaApp, fetched at <https://www.moya.app/>: text chat keeps working when the person is out of data, on MTN, Vodacom, Cell C and Telkom. The page says attachments such as voice notes, photos, videos and documents need data or Wi-Fi. That is a messenger. It does not zero-rate `sospana-sonke.vercel.app`. A separate biNu application page was not fetched. Do not treat Moya as a filed zero-rating.

Datafree, fetched at <https://www.datafree.co/>: a company pays so its own site or app opens without the visitor's data, across South African networks. The page does not print a price. Action: ask them for a quote if the owner wants the visitor's data bill paid by Sospana Sonke. That is a contract, not an ICASA application.

## What the owner still has to do

1. Open an Africa's Talking account, or a Vodacom Messaging account, and let them assign the code. Put only that callback secret in `USSD_CALLBACK_SECRET`, then set `USSD_ENABLED` to true.
2. Create a Meta app, add WhatsApp, and set the four WhatsApp values. Point the callback at `https://sospana-sonke-api-fra.onrender.com/api/v1/whatsapp`.
3. Buy SMS credit on the same account before any alert can leave. The menu stores the number and does not send.
4. Do not file the ICASA zero-rating application for the current Vercel site. It does not meet the published rules (SARS public-benefit proof or a `.gov.za` name, and a static South African address). Revisit only after both of those are true.
5. Ask Vodacom, from <https://www.vodacom.co.za/vodacom/shopping/v/connectu>, whether a free job site can be added beside the job boards they already list. Ask Datafree for a price if the owner wants to pay the visitor's data. Neither of those is done by this repository.
