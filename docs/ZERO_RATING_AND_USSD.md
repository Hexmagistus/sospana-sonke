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

## What the owner still has to do

1. Open an Africa's Talking account, or a Vodacom Messaging account, and let them assign the code. Put only that callback secret in `USSD_CALLBACK_SECRET`, then set `USSD_ENABLED` to true.
2. Create a Meta app, add WhatsApp, and set the four WhatsApp values. Point the callback at `https://sospana-sonke-api-fra.onrender.com/api/v1/whatsapp`.
3. Buy SMS credit on the same account before any alert can leave. The menu stores the number and does not send.
