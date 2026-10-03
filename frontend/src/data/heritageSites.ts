/**
 * UNESCO World Heritage Sites shown on the landing page.
 *
 * Names, countries and inscription years were checked against the UNESCO World
 * Heritage Centre pages (https://whc.unesco.org/en/list/<id>) on 2026-10-03.
 * Order is the standing one: South Africa, rest of SADC, rest of Africa, then
 * other regions (Oceania, Europe, South America, North America, Asia).
 *
 * Photos are from Wikimedia Commons under CC0, public domain or CC BY, resized
 * to 800x600 JPEG; see public/photos/heritage/CREDITS.txt. A site with no
 * `image` has no freely licensed photo we could confirm and shows a card.
 */
export type HeritageImage = {
  src: string;
  alt: string;
  author: string;
  licence: string;
  licenceUrl?: string;
  sourceUrl: string;
};

export type HeritageGroupId = "south-africa" | "sadc" | "africa" | "other";

export type HeritageSite = {
  id: string;
  name: string;
  /** Country or countries, as on the UNESCO list. */
  place: string;
  /** Year of inscription on the World Heritage List. */
  year: number;
  group: HeritageGroupId;
  /** UNESCO World Heritage Centre list number, for the source link. */
  whc: number;
  image?: HeritageImage;
};

export const HERITAGE_GROUPS: { id: HeritageGroupId; label: string }[] = [
  { id: "south-africa", label: "South Africa" },
  { id: "sadc", label: "Rest of SADC" },
  { id: "africa", label: "Rest of Africa" },
  { id: "other", label: "Beyond Africa" },
];

export const HERITAGE_SITES: HeritageSite[] = [
  {
    id: "robben-island", name: "Robben Island", place: "South Africa", year: 1999, group: "south-africa", whc: 916,
    image: {
      src: "/photos/heritage/robben-island.jpg",
      alt: "Robben Island from the air, with Table Mountain and the Cape Town coast across the water",
      author: "South African Tourism from South Africa", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Robben_Island_-_Cape_Town,_South_Africa_(3883849594).jpg",
    },
  },
  {
    id: "isimangaliso", name: "iSimangaliso Wetland Park", place: "South Africa · Mozambique", year: 1999, group: "south-africa", whc: 914,
    image: {
      src: "/photos/heritage/isimangaliso.jpg",
      alt: "A greater kudu bull standing in tall grass in iSimangaliso Wetland Park, KwaZulu-Natal",
      author: "Fyre Mael", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Kudu_Bull_-_iSimangaliso_Wetland_Park,_KwaZulu-Natal,_South_Africa_(32272328472).jpg",
    },
  },
  {
    id: "drakensberg", name: "uKhahlamba / Drakensberg Park", place: "South Africa · Lesotho", year: 2000, group: "south-africa", whc: 985,
    image: {
      src: "/photos/heritage/drakensberg.jpg",
      alt: "A stony river bed below the basalt cliffs of the Drakensberg Amphitheatre",
      author: "Bothar", licence: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Amphitheatre_Drakensberg.jpg",
    },
  },
  {
    id: "mapungubwe", name: "Mapungubwe Cultural Landscape", place: "South Africa", year: 2003, group: "south-africa", whc: 1099,
    image: {
      src: "/photos/heritage/mapungubwe.jpg",
      alt: "A flat-topped sandstone outcrop with sparse trees in the Mapungubwe landscape, Limpopo",
      author: "South African Tourism from South Africa", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Mapungubwe,_Limpopo,_South_Africa_(20535429052).jpg",
    },
  },
  {
    id: "cradle", name: "Cradle of Humankind (Fossil Hominid Sites)", place: "South Africa", year: 1999, group: "south-africa", whc: 915,
    image: {
      src: "/photos/heritage/cradle.jpg",
      alt: "Aerial view of the Maropeng visitor centre in the Cradle of Humankind, Gauteng",
      author: "South African Tourism from South Africa", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Cradle_of_Humankind,_Maropeng,_Gauteng,_South_Africa_(20311531989).jpg",
    },
  },
  {
    id: "victoria-falls", name: "Mosi-oa-Tunya / Victoria Falls", place: "Zambia · Zimbabwe", year: 1989, group: "sadc", whc: 509,
    image: {
      src: "/photos/heritage/victoria-falls.jpg",
      alt: "Water pouring over the lip of Victoria Falls on the Zimbabwe–Zambia border",
      author: "ninara from Helsinki, Finland", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:The_Smoke_that_Thunders,_Victoria_Falls,_Zimbabwe_(14532921781).jpg",
    },
  },
  {
    id: "okavango", name: "Okavango Delta", place: "Botswana", year: 2014, group: "sadc", whc: 1432,
    image: {
      src: "/photos/heritage/okavango.jpg",
      alt: "A warm sky reflected in the still water of the Okavango Delta",
      author: "Richardk85", licence: "CC0",
      licenceUrl: "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Okavango-delta-sunrise-april-2025.jpg",
    },
  },
  {
    id: "tsodilo", name: "Tsodilo", place: "Botswana", year: 2001, group: "sadc", whc: 1021,
  },
  {
    id: "khami", name: "Khami Ruins National Monument", place: "Zimbabwe", year: 1986, group: "sadc", whc: 365,
    image: {
      src: "/photos/heritage/khami.jpg",
      alt: "A path beside an old stone terrace wall at the Khami ruins, Zimbabwe",
      author: "Ulamm", licence: "Public domain",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Khami_ruins_(ZW).jpg",
    },
  },
  {
    id: "great-zimbabwe", name: "Great Zimbabwe National Monument", place: "Zimbabwe", year: 1986, group: "sadc", whc: 364,
    image: {
      src: "/photos/heritage/great-zimbabwe.jpg",
      alt: "A dry-stone granite wall at Great Zimbabwe",
      author: "Fanny Schertzer", licence: "CC BY 3.0",
      licenceUrl: "https://creativecommons.org/licenses/by/3.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Great_inclosure_-_Great_Zimbabwe_(14).jpg",
    },
  },
  {
    id: "lake-malawi", name: "Lake Malawi National Park", place: "Malawi", year: 1984, group: "sadc", whc: 289,
    image: {
      src: "/photos/heritage/lake-malawi.jpg",
      alt: "A sandy beach with small huts on the shore of Lake Malawi, hills across the water",
      author: "Kevin Walsh from Oxford, England", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Lake_malawi_national_park.jpg",
    },
  },
  {
    id: "ngorongoro", name: "Ngorongoro Conservation Area", place: "Tanzania", year: 1979, group: "sadc", whc: 39,
    image: {
      src: "/photos/heritage/ngorongoro.jpg",
      alt: "Green grassland and a small lake on the floor of Ngorongoro Crater, Tanzania",
      author: "William Warby from London, England", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Ngorongoro_Crater.jpg",
    },
  },
  {
    id: "kilimanjaro", name: "Kilimanjaro National Park", place: "Tanzania", year: 1987, group: "sadc", whc: 403,
    image: {
      src: "/photos/heritage/kilimanjaro.jpg",
      alt: "Elephants crossing the plain with snow-capped Mount Kilimanjaro in the distance, seen from Amboseli in Kenya",
      author: "Ninaras", licence: "CC BY 4.0",
      licenceUrl: "https://creativecommons.org/licenses/by/4.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Amboseli_National_Park_and_Mt._Kilimanjaro.jpg",
    },
  },
  {
    id: "zanzibar", name: "Stone Town of Zanzibar", place: "Tanzania", year: 2000, group: "sadc", whc: 173,
    image: {
      src: "/photos/heritage/zanzibar.jpg",
      alt: "Boats at anchor in front of the waterfront buildings of Stone Town, Zanzibar",
      author: "Dr. Ondřej Havelka (cestovatel)", licence: "CC BY 4.0",
      licenceUrl: "https://creativecommons.org/licenses/by/4.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Harbour_at_the_picturesque_Stone_Town.jpg",
    },
  },
  {
    id: "lalibela", name: "Rock-Hewn Churches, Lalibela", place: "Ethiopia", year: 1978, group: "africa", whc: 18,
    image: {
      src: "/photos/heritage/lalibela.jpg",
      alt: "The Church of Saint George at Lalibela, cut down into the rock in the shape of a cross",
      author: "Sailko", licence: "CC BY 3.0",
      licenceUrl: "https://creativecommons.org/licenses/by/3.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Lalibela,_san_giorgio,_esterno_24.jpg",
    },
  },
  {
    id: "giza", name: "Memphis and its Necropolis, the Pyramid Fields from Giza to Dahshur", place: "Egypt", year: 1979, group: "africa", whc: 86,
    image: {
      src: "/photos/heritage/giza.jpg",
      alt: "The three pyramids of Giza rising from the desert sand",
      author: "Walkerssk", licence: "CC0",
      licenceUrl: "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Pyramids_in_Giza_-_Egypt.jpg",
    },
  },
  {
    id: "timbuktu", name: "Timbuktu", place: "Mali", year: 1988, group: "africa", whc: 119,
    image: {
      src: "/photos/heritage/timbuktu.jpg",
      alt: "A sandy street between mud-brick walls in Timbuktu, Mali",
      author: "upyernoz from Haverford, USA", licence: "CC BY 2.0",
      licenceUrl: "https://creativecommons.org/licenses/by/2.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Timbuktu_Street_(6916743).jpg",
    },
  },
  {
    id: "great-barrier-reef", name: "Great Barrier Reef", place: "Australia", year: 1981, group: "other", whc: 154,
  },
  {
    id: "acropolis", name: "Acropolis, Athens", place: "Greece", year: 1987, group: "other", whc: 404,
    image: {
      src: "/photos/heritage/acropolis.jpg",
      alt: "Doric columns of the Parthenon on the Acropolis in Athens against a blue sky",
      author: "Jebulon", licence: "CC0",
      licenceUrl: "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Parthenon_east_side_Acropolis_Athens,_Greece.jpg",
    },
  },
  {
    id: "machu-picchu", name: "Historic Sanctuary of Machu Picchu", place: "Peru", year: 1983, group: "other", whc: 274,
    image: {
      src: "/photos/heritage/machu-picchu.jpg",
      alt: "Stone walls and terraces of Machu Picchu with Andean peaks behind",
      author: "Tomas Sobek tomas_nz", licence: "CC0",
      licenceUrl: "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Ruins_of_Machu_Picchu_(Unsplash).jpg",
    },
  },
  {
    id: "grand-canyon", name: "Grand Canyon National Park", place: "United States", year: 1979, group: "other", whc: 75,
    image: {
      src: "/photos/heritage/grand-canyon.jpg",
      alt: "Layered red and tan rock walls of the Grand Canyon, with snow and pines on the rim",
      author: "Mx. Granger", licence: "CC0",
      licenceUrl: "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Grand_Canyon_layers.jpg",
    },
  },
  {
    id: "taj-mahal", name: "Taj Mahal", place: "India", year: 1983, group: "other", whc: 252,
    image: {
      src: "/photos/heritage/taj-mahal.jpg",
      alt: "The Taj Mahal and its long reflecting pool in Agra, India",
      author: "Almbauer", licence: "CC0",
      licenceUrl: "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Taj_Mahal_2018.jpg",
    },
  },
  {
    id: "angkor", name: "Angkor", place: "Cambodia", year: 1992, group: "other", whc: 668,
    image: {
      src: "/photos/heritage/angkor.jpg",
      alt: "The towers of Angkor Wat in silhouette, reflected in water, Cambodia",
      author: "Martaapue", licence: "CC0",
      licenceUrl: "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Angkor_Wat_in_Cambodia.jpg",
    },
  },
  {
    id: "petra", name: "Petra", place: "Jordan", year: 1985, group: "other", whc: 326,
    image: {
      src: "/photos/heritage/petra.jpg",
      alt: "Al-Khazneh, the Treasury, carved into the red sandstone cliff at Petra, Jordan",
      author: "Vyacheslav Argenberg", licence: "CC BY 4.0",
      licenceUrl: "https://creativecommons.org/licenses/by/4.0",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Al-Khazneh_(The_Treasury)_2,_Petra,_Jordan.jpg",
    },
  },
];
