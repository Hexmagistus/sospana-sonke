# How to use Sospana Sonke

Screen recording of the live site, [https://sospana-sonke.vercel.app](https://sospana-sonke.vercel.app), made on 9 October 2026.

| | |
|---|---|
| File | `docs/tutorial/sospana-sonke-how-to-use.mp4` |
| Duration | 2:14 (134.2 seconds) |
| Picture | 1280×720, H.264, 25 fps |
| Sound | AAC, instrumental jazz only |
| Size | 4.5 MB |

There is no voiceover. Each step has a gold title bar and a navy caption. The opening and closing cards fill the frame.

A throwaway candidate account was registered on the live site for the signed-in steps, then deleted with `POST /api/v1/account/delete` (HTTP 204). A later sign-in with the same email returned HTTP 401. No admin account was used. Nothing was sent to an employer, the CV builder’s Analyse button was not clicked, and no donation was paid.

## Music

The bed is an original instrumental loop, synthesised by `docs/tutorial/jazz-bed.py` (NumPy: sine partials, a noise brush, and a short delay). It uses no samples and no third-party recording. The melody is a sparse original pentatonic line, not a copied tune.

- **Source:** `docs/tutorial/jazz-bed.py`
- **Licence:** [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/). The composition and the generated recording are dedicated to the public domain. Anyone may reuse them, including commercially, with no attribution required.
- **Feel:** 92 BPM, 16 bars (about 42.7 seconds), repeated for the length of the picture. Chords, two bars each and then repeated: Cmaj7, Am7, Dm7, G7, Em7, A7, Dm7, G7. Walking bass, soft piano on beats 2 and 4, swung brush noise, and the sparse melody.
- **Mix:** the loop is loudness-normalised to about −18 LUFS (measured integrated loudness −18.1 LUFS), then a 2.0 second fade-in and a 3.0 second fade-out. No speech sits under it.

Regenerate the loop with `python docs/tutorial/jazz-bed.py jazz-bed.wav` (needs NumPy). The video already contains the mixed result.

## Storyboard

Times are the on-screen beats. The file runs a couple of seconds past the closing card while the browser finishes.

| Time | Title | What is on screen |
|---|---|---|
| 0:00–0:04 | How to use Sospana Sonke | Title card. Caption: a free employer directory; you apply on each employer’s own careers page. |
| 0:04–0:16 | Home page | Hero “Where talent meets opportunity”, then How it works: create a profile, find openings, review and apply on the employer’s site, keep a record. Caption: countries appear when an employer has a direct careers link. The site does not promise a job. |
| 0:16–0:23 | Sign in | Email and password form, before an account exists. Caption: Google sign-in shows when it is configured. A code is asked only if you use an authenticator. |
| 0:23–0:31 | Create an account | Free registration. Privacy policy and terms are accepted. The three preference questions are left unanswered, so they stay off. |
| 0:31–0:47 | Employer directory | South Africa opens first. Search finds Absa. Kenya is chosen in the country picker, then Private. The country stays selected when the category changes. |
| 0:47–0:55 | Colleges and SETAs | TVET and other colleges, plus South Africa’s Sector Education and Training Authorities. AGRISETA is on screen. |
| 0:55–1:03 | NGOs and non-profits | Charities, non-profits, and United Nations agencies. African Capacity Building Foundation is on screen. Apply on each one’s own page. |
| 1:03–1:10 | Government | Departments, municipalities, and state-owned entities in South Africa. You still apply on their own page. |
| 1:10–1:19 | Direct careers link | View jobs opens Absa’s own Workday board (`absa.wd3.myworkdayjobs.com/Absa`). The search box is visible. Nothing is filled in or sent. |
| 1:19–1:27 | Preferences and the daily email | Three choices, each saved on its own: tagging No, preferred post “Don’t consider me for posts right now”, alerts No. Caption: the once-a-day openings email needs a yes on alerts and a verified email. This account is set to no. |
| 1:27–1:36 | CV builder | One sample advert is pasted. Analyse is visible and is not clicked, so no job analysis is created. Nothing is sent. |
| 1:36–1:46 | Career Agent | “Employers in my field” lists real employers from the directory. They are not scored. The agent does not invent listings. |
| 1:46–1:53 | Application tracker | Empty state, “No applications yet”. Nothing is sent for you. |
| 1:53–2:01 | Donate | R20 is selected. Cash send shows “coming soon”. No payment is submitted. |
| 2:01–2:07 | Sign in again | Sign out, then the same email and password on the sign-in form. |
| 2:07–2:12 | Apply on the employer’s page | Closing card. Browse the directory, open a direct careers link, and apply there yourself. |

## What this video does not claim

- Job matching was removed. The Career Agent searches the directory and vacancies the scanner has already read.
- The daily email (“Your daily updates”) goes out once a day at 08:00 SAST only when alerts are yes, the email is verified, and the person has not unsubscribed. It lists vacancies first seen in the last 24 hours, with a posting date no older than three days, that are not closed.
- SETAs in the Colleges and SETAs list are South African.
- A careers link opens the employer’s site in a new tab. Sospana Sonke does not submit the application.
