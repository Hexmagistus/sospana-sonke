// Daily Spark content. Everything here is data: add or reorder freely, the tests
// check the invariants (counts, uniqueness, attribution rules, region order).
//
// JOKES: original wording written for Sospana Sonke (clean, kind, work / job-hunt /
//   African daily life). They laugh WITH people, never at a group.
// WISDOM: two kinds, and the rule is strict.
//   - "quote"   : a named person, ONLY where the attribution is well documented.
//                 `source` says where (book, speech, chapter). Ancient texts are quoted
//                 from public-domain translations; `source` notes when wording varies by
//                 translation.
//   - "proverb" : traditional sayings. Labelled "African proverb" (never given an invented
//                 author). `origin` names a language/culture only where it is well known.
//                 English renderings of non-English proverbs are our own; `native` holds
//                 the original wording where we are sure of it.
// `region` orders the wisdom list South Africa -> SADC -> Africa -> everywhere else.

export type JokeTheme = "job-hunt" | "interview" | "office" | "africa" | "tech" | "wordplay";

export interface Joke {
  id: string;
  theme: JokeTheme;
  text: string;
}

export type WisdomRegion = "ZA" | "SADC" | "AFRICA" | "WORLD";

export interface Wisdom {
  id: string;
  kind: "quote" | "proverb";
  text: string;
  /** Person for a quote. Always undefined for proverbs. */
  author?: string;
  /** Where a quote comes from (work, speech, chapter). */
  source?: string;
  /** Language or culture of a proverb, only when well established. */
  origin?: string;
  /** Original wording of a proverb, when we are certain of it. */
  native?: string;
  region: WisdomRegion;
}

export const REGION_ORDER: Record<WisdomRegion, number> = { ZA: 0, SADC: 1, AFRICA: 2, WORLD: 3 };

const j = (id: number, theme: JokeTheme, text: string): Joke => ({
  id: `j${String(id).padStart(3, "0")}`, theme, text,
});

export const JOKES: Joke[] = [
  // ---- job hunt ----
  j(1, "job-hunt", "I wrote “detail-oriented” on my CV, then spent twenty minutes choosing between “Dear Sir/Madam” and “To whom it may concern”. The details are going very well."),
  j(2, "job-hunt", "My CV says “references available on request”. My references are my mother and a very loyal neighbour. Both are excellent and both will say yes."),
  j(3, "job-hunt", "The advert wanted an entry-level candidate with five years’ experience. I have the five years. I’m just waiting for the entry-level to arrive."),
  j(4, "job-hunt", "I set a job alert for “anything”. Turns out “anything” is a specific job: being surprised at 06:00 by forty-seven emails."),
  j(5, "job-hunt", "I updated my profile photo so I look like someone who has already been hired. It’s working. Even I believe me."),
  j(6, "job-hunt", "A cover letter is a love letter with a longer word count and no guarantee of a reply."),
  j(7, "job-hunt", "My job-search strategy has three steps: apply, wait, and refresh the inbox like it owes me money."),
  j(8, "job-hunt", "They asked for my salary expectations. I said “yes”. We both decided to move on gracefully."),
  j(9, "job-hunt", "Networking tip: say “we should grab a coffee” to everyone. My coffee budget is now my biggest expense and my best investment."),
  j(10, "job-hunt", "I sent my CV as a PDF so it can’t be edited. Unfortunately I can’t edit it either, and it still says “Objectiv”."),
  j(11, "job-hunt", "Applying for jobs is simple. Typing your whole CV into a form that has already read your CV is the philosophical part."),
  j(12, "job-hunt", "I have fourteen tabs open: three jobs, two tutorials, seven versions of my CV, and one cat video for morale. Morale is crucial."),
  j(13, "job-hunt", "I put “proficient in Excel” on my CV. In my defence, I can open it and close it with enormous confidence."),
  j(14, "job-hunt", "A rejection email said another candidate’s profile “closely matched the role”. Fair enough. I closely matched the free biscuits."),
  j(15, "job-hunt", "I treat every interview invitation like a braai invitation: say yes quickly, ask what to bring, and arrive on time."),
  j(16, "job-hunt", "Productivity hack: send one application before you check your phone. The phone can wait. It only has group chats about other group chats."),
  j(17, "job-hunt", "My career gap is not a gap. It’s a sabbatical with unreliable Wi-Fi."),
  j(18, "job-hunt", "A good CV fits on two pages. Mine fits on two pages if you use font size six and believe in yourself."),
  j(19, "job-hunt", "I asked for feedback on my application. The feedback was an automatic reply thanking me for my interest in asking for feedback."),
  j(20, "job-hunt", "Job hunting is like fishing: patience, decent bait, and a friend who keeps saying “try the other side of the lake”. The friend has never fished."),
  j(21, "job-hunt", "I named my file CV_final_FINAL_v7_really. The recruiter replied, “Thanks for the final final.” We’re now on friendly terms."),
  j(22, "job-hunt", "The advert said “fast-paced environment”. I commute by minibus taxi at rush hour. I am, technically, a professional."),
  j(23, "job-hunt", "My strengths are punctuality and teamwork. My weakness is that I say “punctuality and teamwork” in every interview."),
  j(24, "job-hunt", "Tip: save the job advert as a PDF before you apply. Adverts have a habit of vanishing the moment you get an interview, like they got shy."),
  j(25, "job-hunt", "One-way video interview: it’s like a conversation, but the other person is on holiday."),
  j(26, "job-hunt", "I’m not unemployed, I’m between opportunities. Opportunities, it seems, are on a long taxi route with many stops."),
  j(27, "job-hunt", "Fun fact: a CV gets about six seconds of attention. Mine gets six seconds and a sympathetic nod."),
  j(28, "job-hunt", "I tailored my CV so carefully for one role that it now fits that exact job and nothing else, like a very ambitious suit."),
  j(29, "job-hunt", "The best job-search tool is a friend who says, “I saw your name come up, I put in a good word.” Be that friend to someone today."),
  j(30, "job-hunt", "I keep a folder called “Wins”. It has one rejection that was very politely written. It counts."),
  // ---- interviews ----
  j(31, "interview", "Interviewer: “Tell me about a time you failed.” Me: “This sentence.” (Please laugh, I’m nervous.)"),
  j(32, "interview", "My biggest weakness is that I overthink my answer to “What’s your biggest weakness?”"),
  j(33, "interview", "When they asked if I had any questions, I asked if the office has a kettle. It was the right question. They respected my priorities."),
  j(34, "interview", "I said I’m a team player. Unrelated: I once ate the last koeksister without asking. I’m working on it."),
  j(35, "interview", "Video-interview dress code: smart on top, comfortable below. Just promise me you won’t stand up."),
  j(36, "interview", "I arrived forty-five minutes early. I was the most punctual person in the car park, and the security guard and I are now close friends."),
  j(37, "interview", "Asked why I want to work there, “it’s near a taxi rank” was honest but incomplete. I added “and your mission matters to me”. That part is true too."),
  j(38, "interview", "I work well under pressure. Ask anyone who has watched me submit an assignment at 23:58."),
  j(39, "interview", "The panel had four people. I made eye contact with each for exactly four seconds. It was a very polite staring contest."),
  j(40, "interview", "I told them my hobbies are reading and hiking. My real hobbies are scrolling and locating a charger."),
  j(41, "interview", "After the interview they said, “We’ll be in touch.” It has been three weeks. I assume they are touching grass."),
  j(42, "interview", "The best interview answer is honesty with polish. The second best is “Great question” while you think."),
  j(43, "interview", "I Googled “how to sit confidently”. Now I’m sitting extremely upright and I think I’ve stopped breathing."),
  j(44, "interview", "I thanked the receptionist, the security guard and the plant. The plant looked relieved. It had an interview too."),
  j(45, "interview", "Mock interviews are wonderful. My friend asked me five questions, and then asked me for a lift home. Both were excellent practice."),
  // ---- office ----
  j(46, "office", "Today’s meeting has been cancelled. It will be replaced by an email about the meeting being cancelled."),
  j(47, "office", "I have three thousand unread emails. I like to think of it as a very long, very quiet book."),
  j(48, "office", "Our printer works perfectly until someone is in a hurry. It can smell urgency."),
  j(49, "office", "“Let’s circle back” is corporate for “I’ll think about this when I’m feeling brave”."),
  j(50, "office", "I’m so productive today that I’ve visited the kitchen four times. It’s research. Into biscuits."),
  j(51, "office", "My to-do list has one item: “update to-do list”. I am absolutely smashing it."),
  j(52, "office", "Working-from-home update: my colleague’s dog attended the meeting, contributed, and got a warmer reaction than my idea."),
  j(53, "office", "The Wi-Fi is down, so we are trying something radical: talking to each other. Please send biscuits."),
  j(54, "office", "Spreadsheet law: if you can’t find the error, it is in the cell you were sure was fine."),
  j(55, "office", "The office thermostat is a mystery. At 09:00 it’s the Arctic. At 14:00 it’s a sauna. Everyone is certain it’s someone else’s fault."),
  j(56, "office", "I replied “Noted” to an email. I did not note it. It was simply the shortest word that closed the topic."),
  j(57, "office", "Teamwork makes the dream work, unless the dream is a group presentation. Then it is four people and one person’s slides."),
  j(58, "office", "Work password rules: twelve characters, a capital, a symbol and a haiku. My password is now the most poetic thing I’ve ever written."),
  j(59, "office", "My manager says she’s an open-door leader. I tried the door. It was a push door. The metaphor survived."),
  j(60, "office", "Lunch break: the only meeting everyone attends on time, with full participation, and no slides."),
  j(61, "office", "When a colleague says “quick call?”, please define quick. History shows it’s somewhere between twelve minutes and the next financial year."),
  j(62, "office", "A to-do list is just a wish list with better posture."),
  j(63, "office", "Office plants teach important lessons: they need light, they need water, and sometimes they just need you to stop talking near them."),
  j(64, "office", "“Reply all” is a superpower. Like most superpowers, it was handed to the wrong people."),
  j(65, "office", "IT asked if I’d tried turning it off and on again. I said I had. I had, in fact, only turned it off. Long Friday."),
  j(66, "office", "My desk plan: neat, ordered, minimal. My desk reality: three mugs, a museum of chargers, and a sticky note saying “Remember”. Remember what? Great question."),
  j(67, "office", "Fridge etiquette: label your lunch. Not for security. So that when it has become science, we know whom to congratulate."),
  j(68, "office", "The best invention at work is the lunchtime walk. It has no login, no subscription, and it still counts as a meeting if you bring someone."),
  j(69, "office", "My colleague says she can multitask. She is currently typing, talking, and looking for her glasses. They are on her head. We love her."),
  j(70, "office", "Every team needs three people: someone who plans, someone who does, and someone who brings the snacks. The third is the most senior."),
  // ---- Africa, daily life ----
  j(71, "africa", "Load-shedding taught us three things: patience, how to read by candlelight, and that the one charger that works is always at the other end of the house."),
  j(72, "africa", "I have perfected the “power’s back!” cheer. The whole street joins in. No choreographer, just collective relief."),
  j(73, "africa", "The data bundle is the new currency. “Can I borrow 200 MB?” is how you know you are truly close to someone."),
  j(74, "africa", "My family WhatsApp group has forty-three members, three languages and nineteen good-morning pictures before seven. The flowers are lovely. The bandwidth is crying."),
  j(75, "africa", "A true job-seeker’s skill: finding the one spot in the house where the network bars appear. Stand there. Do not move. Apply."),
  j(76, "africa", "“Now” means now. “Now now” means soon. “Just now” means we’ll see. Our timekeeping has more layers than the Johannesburg skyline."),
  j(77, "africa", "Minibus-taxi etiquette: pass the money forward, say “thank you, driver”, and nobody counts the change aloud. Efficiency by trust. HR departments, take notes."),
  j(78, "africa", "Braai logic: one person is in charge of the fire and eleven are in charge of advising them. It is the most democratic management structure I know."),
  j(79, "africa", "Nyama choma, braai, suya: different countries, same project plan. Gather friends, light a fire, argue gently about timing."),
  j(80, "africa", "Jollof debates are the only disagreements where everyone insists they’re right and everyone gets seconds."),
  j(81, "africa", "Mobile money: sending cash takes four seconds. Explaining to your aunt that you did not lose it takes four hours."),
  j(82, "africa", "Joburg’s robots taught me patience. Durban’s sun taught me sunscreen. Cape Town’s wind taught me to hold on to my hat and my dreams."),
  j(83, "africa", "Football logic: everyone is a coach until the penalty. Same as every Monday-morning meeting."),
  j(84, "africa", "My gran’s interview advice: “Greet everyone properly and sit up straight.” She was a career consultant all along, billed in cups of rooibos."),
  j(85, "africa", "Greeting properly takes five minutes: “How are you? How’s the family? How was the road?” The meeting hasn’t begun and we’ve already built a relationship."),
  j(86, "africa", "My aunt can spot a typo in a CV from three rooms away. She isn’t in HR. She’s just a more thorough kind of love."),
  j(87, "africa", "Pap and vleis, ugali and nyama, fufu and soup: the world’s most reliable motivational speech is “come, eat”."),
  j(88, "africa", "Kilimanjaro principle: nobody climbs it in a rush. Pole pole. Also, bring snacks."),
  j(89, "africa", "Johannesburg, Nairobi, Lagos, Harare: different cities, same side-hustle spirit and the same WhatsApp group. Both are wonderful."),
  j(90, "africa", "Africa has over fifty countries and one and a half billion strong opinions about how to cook rice. This is called diversity of thought."),
  j(91, "africa", "I asked my dad for career advice. He said, “Work hard, be kind, and stop adjusting the antenna.” I think there is a metaphor, but the TV is still fuzzy."),
  j(92, "africa", "Ubuntu in business terms: “Your success is my success, so please share the good Wi-Fi password.”"),
  j(93, "africa", "The unofficial African CV: “Skilled at fixing anything with a bit of wire, a lot of patience and a cousin.” Hire them all."),
  j(94, "africa", "Some people dream of a corner office. I dream of a corner office with reliable electricity and a fridge. We all have different goals."),
  j(95, "africa", "In my town the best career fair is the Saturday market: you meet a plumber, a coder, a baker and a poet, and one of them is the same person."),
  j(96, "africa", "“Five minutes away” is a flexible unit of measurement, like “a short walk” or “a small braai”."),
  j(97, "africa", "A good rooibos or a strong chai fixes eighty percent of problems. The other twenty percent need a second cup."),
  j(98, "africa", "Our neighbourhood has a weather forecast, a news service and a recruitment agency. It is called “the aunties over the fence”."),
  // ---- tech ----
  j(99, "tech", "My CV helper suggested I “leverage synergies”. I suggested it leverage the delete key."),
  j(100, "tech", "“Have you tried clearing your cache?” is the modern “have you tried hugging a tree?” Both are calming. Neither is guaranteed."),
  j(101, "tech", "A software update at 09:00 on Monday is the computer’s way of saying, “let’s take it slow today”."),
  j(102, "tech", "Autocorrect turned “Kind regards” into “King regards”. The recruiter replied, “Your Majesty.” I am still waiting for the royal job offer."),
  j(103, "tech", "Our Wi-Fi password is WelcomeGuest2019. Some of us haven’t left 2019 either."),
  j(104, "tech", "I told my computer it was fast. It froze. Compliments, apparently, need processing time."),
  j(105, "tech", "The cloud is just someone else’s computer, and sometimes that someone is having a day."),
  j(106, "tech", "Two-factor authentication: because one password was not enough to forget."),
  j(107, "tech", "Backing up your files is like flossing: everyone agrees, almost nobody does, and the day you need it you wish you had."),
  j(108, "tech", "The mute button is the most powerful button in modern history. It protects family secrets and lunchtime crunching."),
  j(109, "tech", "“You’re on mute” is the national anthem of remote work."),
  j(110, "tech", "A weak signal is just the internet asking, “Are you sure you want to apply today?” Yes. Walk to the window."),
  j(111, "tech", "I’m ninety percent sure I’m good with computers. The other ten percent is me typing “how to copy and paste” into a search bar."),
  j(112, "tech", "Screen-share etiquette: close the tab with the forty-seven job adverts. Or leave it open. We all know the feeling."),
  // ---- wordplay ----
  j(113, "wordplay", "Why did the CV go to therapy? It had too many unresolved gaps."),
  j(114, "wordplay", "Why did the spreadsheet bring a ladder? To reach the next level of cells."),
  j(115, "wordplay", "A job interview is speed dating where both sides pretend to love the same snacks."),
  j(116, "wordplay", "Motivational poster for the office: “Be the colleague your Wi-Fi thinks you are: reliable and mostly connected.”"),
  j(117, "wordplay", "A good manager is like a good sieve: lets the important things through and keeps the unnecessary meetings out."),
  j(118, "wordplay", "Laptop battery at three percent: the original deadline."),
  j(119, "wordplay", "Ambition is what gets you up in the morning. Coffee is what gets ambition to arrive."),
  j(120, "wordplay", "I have years of experience in waiting for replies. Please consider it a transferable skill."),
  j(121, "wordplay", "The electrician got the job. He made a great connection and nobody was shocked."),
  j(122, "wordplay", "What is a farmer’s favourite interview question? “Where do you see yourself growing in five years?”"),
  j(123, "wordplay", "Why did the baker get promoted? She really knew how to rise to the occasion."),
  j(124, "wordplay", "Why did the pilot pass the interview? His answers were a little high, but he landed every question."),
];

const w = (
  id: number,
  region: WisdomRegion,
  kind: "quote" | "proverb",
  text: string,
  extra: Partial<Wisdom> = {},
): Wisdom => ({ id: `w${String(id).padStart(3, "0")}`, region, kind, text, ...extra });

const q = (id: number, region: WisdomRegion, text: string, author: string, source: string): Wisdom =>
  w(id, region, "quote", text, { author, source });

const p = (id: number, region: WisdomRegion, text: string, origin?: string, native?: string): Wisdom =>
  w(id, region, "proverb", text, { ...(origin ? { origin } : {}), ...(native ? { native } : {}) });

// Order: South Africa, then SADC, then the rest of Africa, then everywhere else.
export const WISDOM: Wisdom[] = [
  // ======== South Africa ========
  p(1, "ZA", "A person is a person through other people.", "Nguni (Zulu, Ndebele, Xhosa)", "Umuntu ngumuntu ngabantu."),
  p(2, "ZA", "A person is a person because of people.", "Sesotho and Setswana", "Motho ke motho ka batho."),
  p(3, "ZA", "A leader is a leader through the people.", "Setswana", "Kgosi ke kgosi ka batho."),
  p(4, "ZA", "A child that does not cry dies on its mother’s back. Ask for what you need.", "Zulu", "Ingane engakhali ifela embelekweni."),
  p(5, "ZA", "The way is asked of those who have already walked it.", "Zulu", "Indlela ibuzwa kwabaphambili."),
  p(6, "ZA", "The bull is still among the calves: potential hides in the young.", "Zulu", "Inkunzi isematholeni."),
  p(7, "ZA", "You do not throw away the baby sling because one baby has died. Keep what is useful, even after a loss.", "Zulu", "Akulahlwa mbeleko ngokufelwa."),
  p(8, "ZA", "A mother holds the knife by its blade. Care often costs the carer.", "Setswana", "Mmangwana o tshwara thipa ka bogaleng."),
  q(9, "ZA", "I learned that courage was not the absence of fear, but the triumph over it.", "Nelson Mandela", "Long Walk to Freedom (1994)"),
  q(10, "ZA", "After climbing a great hill, one only finds that there are many more hills to climb.", "Nelson Mandela", "Long Walk to Freedom (1994)"),
  q(11, "ZA", "Education is the most powerful weapon which you can use to change the world.", "Nelson Mandela", "Speech at the launch of the Mindset Network, Johannesburg, 16 July 2003"),
  q(12, "ZA", "For to be free is not merely to cast off one’s chains, but to live in a way that respects and enhances the freedom of others.", "Nelson Mandela", "Long Walk to Freedom (1994)"),
  q(13, "ZA", "It is better to lead from behind and to put others in front.", "Nelson Mandela", "Long Walk to Freedom (1994)"),
  q(14, "ZA", "Sometimes it falls upon a generation to be great. You can be that great generation.", "Nelson Mandela", "Make Poverty History rally, Trafalgar Square, 3 February 2005"),
  q(15, "ZA", "Overcoming poverty is not a gesture of charity. It is an act of justice. It is the protection of a fundamental human right, the right to dignity and a decent life.", "Nelson Mandela", "Make Poverty History rally, Trafalgar Square, 3 February 2005"),
  q(16, "ZA", "A person with ubuntu is open and available to others, affirming of others, does not feel threatened that others are able and good.", "Desmond Tutu", "No Future Without Forgiveness (1999)"),
  // ======== SADC ========
  p(17, "SADC", "One finger cannot crush a louse.", "Shona", "Chara chimwe hachitswanyi inda."),
  p(18, "SADC", "One man cannot surround an anthill. Some jobs need many hands.", "Shona", "Rume rimwe harikombi churu."),
  p(19, "SADC", "A small bowl goes to where another once came from. What you give comes back around.", "Shona", "Kandiro kanoenda kunobva kamwe."),
  p(20, "SADC", "A single bracelet does not jingle.", "Congolese"),
  // ======== Africa ========
  q(21, "AFRICA", "In the course of history, there comes a time when humanity is called to shift to a new level of consciousness, to reach a higher moral ground. A time when we have to shed our fear and give hope to each other.", "Wangari Maathai", "Nobel Lecture, Oslo, 10 December 2004"),
  q(22, "AFRICA", "We are called to assist the Earth to heal her wounds and in the process heal our own.", "Wangari Maathai", "Nobel Lecture, Oslo, 10 December 2004"),
  q(23, "AFRICA", "Among the Igbo the art of conversation is regarded very highly, and proverbs are the palm-oil with which words are eaten.", "Chinua Achebe", "Things Fall Apart (1958)"),
  q(24, "AFRICA", "As the elders said, if a child washed his hands he could eat with kings.", "Chinua Achebe", "Things Fall Apart (1958)"),
  q(25, "AFRICA", "We come together because it is good for kinsmen to do so.", "Chinua Achebe", "Things Fall Apart (1958)"),
  p(26, "AFRICA", "Hurry, hurry has no blessing.", "Swahili", "Haraka haraka haina baraka."),
  p(27, "AFRICA", "Slowly, slowly is the way to travel.", "Swahili", "Pole pole ndio mwendo."),
  p(28, "AFRICA", "Little by little fills the measure.", "Swahili", "Haba na haba hujaza kibaba."),
  p(29, "AFRICA", "The patient one eats ripe fruit.", "Swahili", "Mvumilivu hula mbivu."),
  p(30, "AFRICA", "One finger cannot crush a louse.", "Swahili", "Kidole kimoja hakivunji chawa."),
  p(31, "AFRICA", "Whoever is not taught by their mother will be taught by the world.", "Swahili", "Asiyefunzwa na mamaye hufunzwa na ulimwengu."),
  p(32, "AFRICA", "Spilled water cannot be gathered up again.", "Swahili", "Maji yakimwagika hayazoleki."),
  p(33, "AFRICA", "Intelligence is wealth.", "Swahili", "Akili ni mali."),
  p(34, "AFRICA", "If you do not seal the crack, you will rebuild the wall.", "Swahili", "Usipoziba ufa utajenga ukuta."),
  p(35, "AFRICA", "One who keeps choosing the perfect hoe is not a farmer.", "Swahili", "Mchagua jembe si mkulima."),
  p(36, "AFRICA", "Patience draws out good fortune.", "Swahili", "Subira huvuta heri."),
  p(37, "AFRICA", "To live long is to see much.", "Swahili", "Kuishi kwingi ni kuona mengi."),
  p(38, "AFRICA", "If you want what is under the bed, you must bend down.", "Swahili", "Ukitaka cha mvunguni sharti uiname."),
  p(39, "AFRICA", "One who wants everything loses everything.", "Swahili", "Mtaka yote hukosa yote."),
  p(40, "AFRICA", "A promise is a debt.", "Swahili", "Ahadi ni deni."),
  p(41, "AFRICA", "Dip by dip, you finish the gourd of honey.", "Swahili", "Chovya chovya humaliza buyu la asali."),
  p(42, "AFRICA", "Where there is a will, there is a way.", "Swahili", "Penye nia pana njia."),
  p(43, "AFRICA", "Better to stub your toe than to trip your tongue.", "Swahili", "Heri kujikwaa kidole kuliko kujikwaa ulimi."),
  p(44, "AFRICA", "To ask is not ignorance.", "Swahili", "Kuuliza si ujinga."),
  p(45, "AFRICA", "The sign of rain is clouds. Prepare when you see them.", "Swahili", "Dalili ya mvua ni mawingu."),
  p(46, "AFRICA", "Do not abandon your own mat for a passing prayer rug.", "Swahili", "Usiache mbachao kwa msala upitao."),
  p(47, "AFRICA", "Visitor, come, so that the host may prosper.", "Swahili", "Mgeni njoo, mwenyeji apone."),
  p(48, "AFRICA", "Chip by chip, the log is finished.", "Swahili", "Bandu bandu huisha gogo."),
  p(49, "AFRICA", "A stick far away does not kill the snake. Use the help that is close.", "Swahili", "Fimbo ya mbali haiui nyoka."),
  p(50, "AFRICA", "Running on the floor ends at the wall: speed alone has its limits.", "Swahili", "Mbio za sakafuni huishia ukingoni."),
  p(51, "AFRICA", "It is not wrong to go back for what you forgot.", "Akan (Sankofa)", "Se wo were fi na wosankɔfa a yenkyi."),
  p(52, "AFRICA", "Wisdom is like a baobab tree; no one individual can embrace it.", "Akan"),
  p(53, "AFRICA", "The person who has not travelled widely thinks his mother is the only cook."),
  p(54, "AFRICA", "The child who is not taught will sell the family house.", "Yoruba"),
  p(55, "AFRICA", "It is with joined hands that we beat our chests with pride.", "Yoruba"),
  p(56, "AFRICA", "Let the kite perch and let the eagle perch. Live and let live.", "Igbo", "Egbe bere, ugo bere."),
  p(57, "AFRICA", "No matter how hot your anger is, it cannot cook yams.", "Igbo"),
  p(58, "AFRICA", "When a person says yes, their chi says yes too.", "Igbo", "Onye kwe, chi ya ekwe."),
  p(59, "AFRICA", "Seeing is better than hearing.", "Hausa", "Gani ya kori ji."),
  p(60, "AFRICA", "However long the night, the dawn will break.", "Hausa"),
  p(61, "AFRICA", "When spider webs unite, they can tie up a lion.", "Ethiopian"),
  p(62, "AFRICA", "He who learns, teaches.", "Ethiopian"),
  p(63, "AFRICA", "Little by little, an egg will walk.", "Ethiopian"),
  p(64, "AFRICA", "A person is a person’s medicine.", "Wolof", "Nit, nitay garabam."),
  p(65, "AFRICA", "Rain does not fall on one roof alone.", "Cameroonian"),
  p(66, "AFRICA", "Knowledge is like a garden: if it is not cultivated, it cannot be harvested.", "Guinean"),
  p(67, "AFRICA", "He who does not know one thing knows another.", "Kenyan"),
  p(68, "AFRICA", "A man who uses force is afraid of reasoning.", "Kikuyu"),
  p(69, "AFRICA", "Smooth seas do not make skilful sailors."),
  p(70, "AFRICA", "It takes a village to raise a child."),
  p(71, "AFRICA", "Cross the river in a crowd and the crocodile will not eat you."),
  p(72, "AFRICA", "When you pray, move your feet."),
  p(73, "AFRICA", "Do not look where you fell, but where you slipped."),
  p(74, "AFRICA", "Two ants do not fail to pull one grasshopper."),
  p(75, "AFRICA", "The sun does not forget a village just because it is small."),
  p(76, "AFRICA", "However full the river, it still wants to grow."),
  p(77, "AFRICA", "To get lost is to learn the way."),
  p(78, "AFRICA", "The one who asks questions does not lose his way."),
  p(79, "AFRICA", "When the music changes, so does the dance."),
  p(80, "AFRICA", "He who is being carried does not realise how far the town is."),
  p(81, "AFRICA", "The ruins of a nation begin in the homes of its people."),
  p(82, "AFRICA", "Until the lions have their own historians, the history of the hunt will always glorify the hunter."),
  // ======== Everywhere else ========
  q(83, "WORLD", "It is not that we have a short time to live, but that we waste a lot of it.", "Seneca", "On the Shortness of Life, 1 (translation varies)"),
  q(84, "WORLD", "We suffer more often in imagination than in reality.", "Seneca", "Letters to Lucilius, 13"),
  q(85, "WORLD", "If one does not know to which port one is sailing, no wind is favourable.", "Seneca", "Letters to Lucilius, 71 (translation varies)"),
  q(86, "WORLD", "Associate with those who will make a better person of you.", "Seneca", "Letters to Lucilius, 7 (translation varies)"),
  q(87, "WORLD", "Sometimes even to live is an act of courage.", "Seneca", "Letters to Lucilius, 78"),
  q(88, "WORLD", "While we are postponing, life speeds by.", "Seneca", "Letters to Lucilius, 1"),
  q(89, "WORLD", "Wherever there is a human being, there is an opportunity for kindness.", "Seneca", "On the Happy Life, 24 (translation varies)"),
  q(90, "WORLD", "In the morning when thou risest unwillingly, let this thought be present: I am rising to the work of a human being.", "Marcus Aurelius", "Meditations, 5.1 (G. Long translation)"),
  q(91, "WORLD", "No longer talk at all about the kind of man that a good man ought to be, but be such.", "Marcus Aurelius", "Meditations, 10.16 (G. Long translation)"),
  q(92, "WORLD", "The best way of avenging thyself is not to become like the wrong-doer.", "Marcus Aurelius", "Meditations, 6.6 (G. Long translation)"),
  q(93, "WORLD", "Such as are thy habitual thoughts, such also will be the character of thy mind; for the soul is dyed by the thoughts.", "Marcus Aurelius", "Meditations, 5.16 (G. Long translation)"),
  q(94, "WORLD", "Is it not pleasant to learn with a constant perseverance and application?", "Confucius", "Analects, 1.1 (J. Legge translation)"),
  q(95, "WORLD", "Is it not delightful to have friends coming from distant quarters?", "Confucius", "Analects, 1.1 (J. Legge translation)"),
  q(96, "WORLD", "Learning without thought is labour lost; thought without learning is perilous.", "Confucius", "Analects, 2.15 (J. Legge translation)"),
  q(97, "WORLD", "When you know a thing, to hold that you know it; and when you do not know a thing, to allow that you do not know it: this is knowledge.", "Confucius", "Analects, 2.17 (J. Legge translation)"),
  q(98, "WORLD", "I am not concerned that I have no place, I am concerned how I may fit myself for one.", "Confucius", "Analects, 4.14 (J. Legge translation)"),
  q(99, "WORLD", "What you do not want done to yourself, do not do to others.", "Confucius", "Analects, 15.24 (J. Legge translation)"),
  q(100, "WORLD", "When I walk along with two others, they may serve me as my teachers.", "Confucius", "Analects, 7.21 (J. Legge translation)"),
  q(101, "WORLD", "To go beyond is as wrong as to fall short.", "Confucius", "Analects, 11.16 (J. Legge translation)"),
  q(102, "WORLD", "A journey of a thousand miles begins with a single step.", "Lao Tzu", "Tao Te Ching, 64 (translation varies)"),
  q(103, "WORLD", "He who knows others is wise; he who knows himself is enlightened.", "Lao Tzu", "Tao Te Ching, 33 (translation varies)"),
  q(104, "WORLD", "The best of people is like water; it benefits all things and does not compete with them.", "Lao Tzu", "Tao Te Ching, 8 (translation varies)"),
  q(105, "WORLD", "He who is content is rich.", "Lao Tzu", "Tao Te Ching, 33 (translation varies)"),
  q(106, "WORLD", "Men are disturbed, not by things, but by the principles and notions which they form concerning things.", "Epictetus", "Enchiridion, 5 (E. Carter translation)"),
  q(107, "WORLD", "The unexamined life is not worth living.", "Socrates", "Plato, Apology, 38a"),
  q(108, "WORLD", "I am a human being; nothing human is alien to me.", "Terence", "Heauton Timorumenos (163 BC)"),
  q(109, "WORLD", "Fortune favours the bold.", "Virgil", "Aeneid, 10.284"),
  q(110, "WORLD", "If you have a garden and a library, you have everything you need.", "Cicero", "Letters to Friends, 9.4"),
  q(111, "WORLD", "Seize the day, trusting as little as possible in tomorrow.", "Horace", "Odes, 1.11 (translation varies)"),
  q(112, "WORLD", "Slow and steady wins the race.", "Aesop", "The Tortoise and the Hare (traditional fable)"),
  q(113, "WORLD", "Well done is better than well said.", "Benjamin Franklin", "Poor Richard’s Almanack (1737)"),
  q(114, "WORLD", "Better three hours too soon than a minute too late.", "William Shakespeare", "The Merry Wives of Windsor, 2.2"),
  q(115, "WORLD", "There is nothing either good or bad, but thinking makes it so.", "William Shakespeare", "Hamlet, 2.2"),
  q(116, "WORLD", "Though she be but little, she is fierce.", "William Shakespeare", "A Midsummer Night’s Dream, 3.2"),
  q(117, "WORLD", "Whatsoever thy hand findeth to do, do it with thy might.", "Ecclesiastes", "Ecclesiastes 9:10 (King James Version)"),
  q(118, "WORLD", "Iron sharpeneth iron; so a man sharpeneth the countenance of his friend.", "Proverbs", "Proverbs 27:17 (King James Version)"),
  q(119, "WORLD", "Great works are performed, not by strength, but perseverance.", "Samuel Johnson", "Rasselas (1759), chapter 13"),
  q(120, "WORLD", "If one advances confidently in the direction of his dreams, and endeavors to live the life which he has imagined, he will meet with a success unexpected in common hours.", "Henry David Thoreau", "Walden (1854)"),
  q(121, "WORLD", "Nothing great was ever achieved without enthusiasm.", "Ralph Waldo Emerson", "Circles (1841)"),
  q(122, "WORLD", "The beginning is the most important part of any work.", "Plato", "Republic, 377a (translation varies)"),
];
