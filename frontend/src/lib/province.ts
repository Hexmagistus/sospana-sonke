/** Map a free-text job location to one of South Africa's nine provinces (or null if unclear). */
export const PROVINCES: { code: string; name: string }[] = [
  { code: "GP", name: "Gauteng" },
  { code: "KZN", name: "KwaZulu-Natal" },
  { code: "WC", name: "Western Cape" },
  { code: "EC", name: "Eastern Cape" },
  { code: "LP", name: "Limpopo" },
  { code: "MP", name: "Mpumalanga" },
  { code: "NW", name: "North West" },
  { code: "FS", name: "Free State" },
  { code: "NC", name: "Northern Cape" },
];

const NAMES: [RegExp, string][] = [
  [/\bgauteng\b|,\s*gp\b|^gp$/i, "GP"],
  [/kwa\s*zulu|\bkzn\b/i, "KZN"],
  [/western cape|,\s*wc\b/i, "WC"],
  [/eastern cape|,\s*ec\b|^ec$/i, "EC"],
  [/limpopo|,\s*lp\b/i, "LP"],
  [/mpumalanga|,\s*mp\b/i, "MP"],
  [/north west|,\s*nw\b/i, "NW"],
  [/free state|,\s*fs\b/i, "FS"],
  [/northern cape|,\s*nc\b/i, "NC"],
];

const PLACES: Record<string, string[]> = {
  GP: ["johannesburg", "jhb", "pretoria", "sandton", "sunninghill", "centurion", "midrand", "glenvista", "boksburg", "bedfordview", "randburg", "vanderbijlpark", "germiston", "kempton park", "isando", "bryanston", "edenvale", "krugersdorp", "modderfontein", "roodepoort", "randfontein", "evaton", "vereeniging", "scientia", "ga-rankuwa", "soweto", "vosloorus", "springs", "silverton", "rayton", "roodekop", "wadeville", "carletonville", "norwood", "rosebank", "waterfall", "benoni", "akasia", "montana", "unitas", "milpark", "olivedale", "mulbarton", "sunward park", "femina", "pretoria east", "groenkloof", "south deep", "midvaal", "yaldwyn", "bartlett", "east rand", "on nicol", "linmed", "moot", "n17 hospital", "ga-rankuwa"],
  KZN: ["durban", "pietermaritzburg", "westville", "kokstad", "newcastle", "pinetown", "kwadukuza", "richards bay", "port edward", "umhlanga", "mobeni", "ladysmith", "empangeni", "stanger", "ethekwini", "margate", "cornubia", "umbogintwini", "abaqulusi", "st anne's", "park square", "parklands hospital", "kingsway"],
  WC: ["cape town", "stellenbosch", "pinelands", "kuilsrivier", "kuilsriver", "george", "worcester", "hermanus", "malmesbury", "vredendal", "paarl", "blaauwberg", "st helena bay", "montague gardens", "velddrif", "knysna", "somerset west", "claremont", "mossel bay", "saldanha", "oudtshoorn", "vredenburg", "brackenfell", "belville", "bellville", "simon's town", "moorreesburg", "century city", "riviersonderend", "beaufort west", "bonnievale", "clanwilliam", "franschoek", "gansbaai", "wellington", "swellendam", "kraaifontein", "plettenberg", "ceres", "constantia", "rosmead", "atlantis", "stikland", "tokai", "maitland", "n1city", "chris barnard", "garden route", "duivenhoks", "west coast", "overberg", "uct "],
  EC: ["port elizabeth", "gqeberha", "makhanda", "east london", "queenstown", "butterworth", "mthatha", "zwelitsha", "king william", "mdantsane", "aliwal north", "burgersdorp", "jeffrey's bay", "amathole", "joe gqabi", "nelson mandela bay", "sarah baartman", "mnquma", "greenacres", "cape road"],
  LP: ["polokwane", "pholoso", "ellisras", "thohoyandou", "burgersfort", "lephalale", "lebowakgomo", "dwaalboom", "thabazimbi", "groblersdal", "giyani", "mokopane", "louis trichardt", "marble hall", "tzaneen", "modimolle", "musina"],
  MP: ["secunda", "witbank", "emalahleni", "nelspruit", "mbombela", "standerton", "bushbuckridge", "barberton", "kriel", "ermelo", "piet retief", "middelburg", "kamaqhekeza", "steve tshwete", "govan mbeki"],
  NW: ["rustenburg", "klerksdorp", "vryburg", "potchefstroom", "sannieshof", "mafikeng", "mahikeng", "mmabatho", "sun city", "brits", "zeerust", "wolmaransstad", "orkney", "delareyville", "northam", "ferncrest"],
  FS: ["bloemfontein", "welkom", "bethlehem", "sasolburg", "kroonstad", "ladybrand", "frankfort", "phuthaditjhaba", "qwa qwa", "parys", "senekal", "harrismith", "pelonomi", "vaalpark", "kroon hospital"],
  NC: ["kimberley", "kuruman", "upington", "springbok", "kathu", "hotazel", "alkantpan", "colesberg", "colesburg", "port nolloth", "de aar", "hartswater", "prieska", "siyathemba", "sol plaatjie"],
};

/** Province code for a location string, or null when it names none, several, or a place abroad. */
export function provinceOf(location: string | null | undefined): string | null {
  if (!location) return null;
  const loc = location.toLowerCase();
  if (/multiple|remote|zambia/.test(loc)) return null;
  const hits = new Set<string>();
  for (const [re, code] of NAMES) if (re.test(location)) hits.add(code);
  if (hits.size === 1) return [...hits][0];
  if (hits.size > 1) return null;
  for (const [code, places] of Object.entries(PLACES)) {
    if (places.some((p) => loc.includes(p))) hits.add(code);
  }
  return hits.size === 1 ? [...hits][0] : null;
}
