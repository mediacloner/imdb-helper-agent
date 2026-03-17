# IMDb Navigation Guide

---

## Page Layouts — Where Things Are

### Homepage (https://www.imdb.com/)

**Top header (always visible on every IMDb page):**
- Far left: IMDb logo in a yellow box — click it to return to the homepage
- Centre: Search bar (`#suggestion-search`) with a magnifying-glass submit button (`#suggestion-search-button`)
- Far right: Sign In button, Watchlist button, IMDbPro link

**Main content (homepage only):**
- Below header: a full-width editorial carousel with featured movies/shows (Previous / Next arrows)
- Horizontal row of topic chips: Oscars, Awards Season Guide, SXSW, Women's History Month, etc.
- "Most popular movies" and "Most popular TV shows" horizontal card rails — each card has a title, year, rating, and a ribbon to add to Watchlist
- "What to Watch" section showing streaming service recommendations

**No "Menu" sidebar button on the homepage in the current UI** — top-level navigation is through the search bar and direct links in the header.

---

### Movie / TV Title Page (https://www.imdb.com/title/<tt_id>/)

**Sub-navigation bar** — just below the header, a horizontal strip of links:
- Cast & crew → opens `/fullcredits/`
- User reviews → opens `/reviews/`
- Trivia → opens `/trivia/`
- FAQ → opens `/faq/`
- "View all topics" button → expands more sub-page links
Selector: `[data-testid="hero-subnav-bar-topic-links"]`

**Hero / title block** (top of page, below sub-nav):
- Movie title, year (clickable → release info page), age rating badge (clickable → parental guide), duration
- Aggregate IMDb rating (e.g. "8.8 ★") — click it → `/ratings/` page
- "Rate" button — opens a star-rating popup (requires sign-in)
- Popularity rank badge — click it → `/chart/moviemeter/`

**Media block** (right side of hero):
- Poster thumbnail — click it to view full poster
- Trailer slot — click the play button to watch the trailer
- "35 Videos" link → `/videogallery/`
- "99+ Photos" link → photo gallery

**Action buttons** (below media block):
- "Add to Watchlist" button (`[data-testid="tm-box-wl-button"]`) — requires sign-in
- "Add to another list" button (`[data-testid="tm-box-addtolist-button"]`) — requires sign-in
- "Mark as watched" / eye checkmark button (`[data-testid="watched-button-<tt_id>"]`) — requires sign-in

**Principal credits** (below hero):
- Director name with link to their person page
- Stars: top 3 actors with links
- "See full cast and crew" → `/fullcredits/`
Selector: `[data-testid="title-pc-principal-credit"]`

**Review counts row:**
- "X User reviews" link → `/reviews/`
- "X Critic reviews" link
- Metascore badge → `/criticreviews/`
Selector: `[data-testid="reviewContent-all-reviews"]`

**Awards block:**
- "Top rated movie #N" → `/chart/top/`
- "Won X Oscars / Y nominations" → `/awards/`
Selector: `[data-testid="award_information"]`

**More to explore** (below the fold — scroll down):
- "More like this" card rail
- "Storyline" section with plot keywords and genre tags
- "Did you know" section with trivia/goofs/quotes links
- "User reviews" preview card with a "See all reviews" link
- "Details" section: original title, release date, country, language, filming locations, production companies
- "Box office" section (budget, gross) with a link to `/business/`
- "Technical specs" link → `/technical/`

---

### Advanced Title Search Page (https://www.imdb.com/search/title/)

**This is the most important filter page. Here is the exact layout:**

**Top area:**
- Three tabs: **TITLES** | NAMES | COLLABORATIONS — you are on TITLES by default
- "See results" button (`[data-testid="adv-search-get-results"]`) — always visible at top right, click it to run the search with current filters
- "Expand all" button (`[data-testid="adv-search-expand-all"]`) — expands every filter section at once

**Left side — Filter Accordion Panel:**
A vertical stack of collapsible filter sections. Each section header is a button — click it to expand or collapse that section. When collapsed, it shows "Expand X". When open, it shows "Collapse X".

Complete list of accordion sections and how to interact with each:

| Section | Accordion selector | What's inside | How to use |
|---|---|---|---|
| Title name | `[data-testid="accordion-item-titleNameAccordion"]` | Text input for title keyword | Type a title word |
| **Title type** | `[data-testid="accordion-item-titleTypeAccordion"]` | Chip buttons: Movie, TV Series, Short, TV Episode, TV Mini Series, TV Movie, TV Special, TV Short, Video Game, Video, Music Video, Podcast Series, Podcast Episode | Click one or more chips to select the type |
| **Release date** | `[data-testid="accordion-item-releaseDateAccordion"]` | Two text inputs: "from" year and "to" year | Type a year in each field, e.g. 2020 in both for a single year |
| **IMDb ratings** | `[data-testid="accordion-item-ratingsAccordion"]` | Two number inputs: min rating and max rating (1–10) | Type 7 and 10 for "7 or higher" |
| Number of votes | `[data-testid="accordion-item-numOfVotesAccordion"]` | Two number inputs: min and max votes | Type 1000 in "min" to filter out obscure titles |
| **Genre** | `[data-testid="accordion-item-genreAccordion"]` | Chip buttons, one per genre | Click a genre chip to select it; click again to deselect |
| Cast or crew | `[data-testid="accordion-item-castOrCrewAccordion"]` | Person name autocomplete input | Type an actor or director name |
| Characters | `[data-testid="accordion-item-charactersAccordion"]` | Text input | Type a character name |
| Keywords | `[data-testid="accordion-item-keywordsAccordion"]` | Text input with autocomplete | Type a keyword like "world-war-ii" |
| Runtime | `[data-testid="accordion-item-runtimeAccordion"]` | Two number inputs: min and max minutes | e.g. 90 to 120 for 90–120 min films |
| Country | `[data-testid="accordion-item-countryAccordion"]` | Country autocomplete input | Type a country name |
| Languages | `[data-testid="accordion-item-languagesAccordion"]` | Language autocomplete input | Type a language name |
| US certificates | `[data-testid="accordion-item-certsAccordion"]` | Rating chips (G, PG, PG-13, R, NC-17) | Click a rating chip |
| Color info | `[data-testid="accordion-item-colorInfoAccordion"]` | Options: Color, Black and White | Click an option |
| Sound mix | `[data-testid="accordion-item-soundMixAccordion"]` | Options: Mono, Stereo, Dolby, etc. | Click an option |
| Awards & recognition | `[data-testid="accordion-item-awardsAccordion"]` | Award group chips (Oscar winner, etc.) | Click a chip |

**Genre chip selectors** (inside the Genre accordion when expanded):
- `[data-testid="test-chip-id-Action"]` → Action
- `[data-testid="test-chip-id-Adventure"]` → Adventure
- `[data-testid="test-chip-id-Animation"]` → Animation
- `[data-testid="test-chip-id-Biography"]` → Biography
- `[data-testid="test-chip-id-Comedy"]` → Comedy
- `[data-testid="test-chip-id-Crime"]` → Crime
- `[data-testid="test-chip-id-Documentary"]` → Documentary
- `[data-testid="test-chip-id-Drama"]` → Drama
- `[data-testid="test-chip-id-Family"]` → Family
- `[data-testid="test-chip-id-Fantasy"]` → Fantasy
- `[data-testid="test-chip-id-History"]` → History
- `[data-testid="test-chip-id-Horror"]` → Horror
- `[data-testid="test-chip-id-Music"]` → Music
- `[data-testid="test-chip-id-Musical"]` → Musical
- `[data-testid="test-chip-id-Mystery"]` → Mystery
- `[data-testid="test-chip-id-Romance"]` → Romance
- `[data-testid="test-chip-id-Sci-Fi"]` → Sci-Fi
- `[data-testid="test-chip-id-Sport"]` → Sport
- `[data-testid="test-chip-id-Thriller"]` → Thriller
- `[data-testid="test-chip-id-War"]` → War
- `[data-testid="test-chip-id-Western"]` → Western

**Title type chip selectors** (inside the Title type accordion when expanded):
- `[data-testid="test-chip-id-movie"]` → Movie (feature film)
- `[data-testid="test-chip-id-tvSeries"]` → TV Series
- `[data-testid="test-chip-id-tvMiniSeries"]` → TV Mini Series
- `[data-testid="test-chip-id-tvMovie"]` → TV Movie
- `[data-testid="test-chip-id-short"]` → Short
- `[data-testid="test-chip-id-tvSpecial"]` → TV Special

**Step-by-step: how to filter documentaries released in 2020:**
1. Go to https://www.imdb.com/search/title/
2. On the left panel, find the **"Genre"** section — click its header to expand it
3. Inside the Genre section, click the **"Documentary"** chip button — it highlights when selected
4. On the left panel, find the **"Release date"** section — click its header to expand it
5. Inside the Release date section, type **2020** in the "from" field and **2020** in the "to" field
6. Click the **"See results"** button at the top right of the filter panel
Direct URL shortcut: https://www.imdb.com/search/title/?genres=documentary&release_date=2020-01-01,2020-12-31

**Step-by-step: how to filter by genre only (e.g. Horror):**
1. Go to https://www.imdb.com/search/title/
2. On the left panel, click the **"Genre"** accordion header to expand it
3. Click the **"Horror"** chip
4. Click **"See results"**
Direct URL shortcut: https://www.imdb.com/search/title/?genres=horror&sort=user_rating,desc

**Step-by-step: how to filter by title type (e.g. TV Mini-Series):**
1. Go to https://www.imdb.com/search/title/
2. On the left panel, click the **"Title type"** accordion header to expand it
3. Click the **"TV Mini Series"** chip
4. Click **"See results"**

---

### Search Results Page (https://www.imdb.com/find/?q=<term>)

**Layout:**
- Top: search bar (pre-filled with your query) with a dropdown to switch search type
- Results grouped by type:
  - **Titles** section: movies and TV shows matching the query
  - **Names** section: people (actors, directors) matching the query
  - **Companies**, **Keywords** sections (less common)

**How to identify the right result:**
- Each title result shows: thumbnail poster, title, year, type (Movie / TV Series / etc.)
- Click the title text or poster to open that title's page
- If multiple results, look at the year to distinguish (e.g. "The Ring (2002)" vs "Ring (1998)")

---

### Episodes Page (https://www.imdb.com/title/<tt_id>/episodes/)

**Layout:**
- Top: show title with a link back to the main show page
- **Season selector** — a row of numbered buttons (1, 2, 3 …) — click the season number to load that season's episodes
- Episode list: each episode shows episode number, title, air date, IMDb rating, short description
- Episode count per season is visible from the number of cards shown

**Navigation to reach Season 1:**
1. Search for the show name in the search bar
2. Click the TV series result
3. On the show page, click the "Episode guide" link (visible in the middle of the page near the title info)
4. On the episodes page, click "1" in the season selector

---

### Person Page (https://www.imdb.com/name/<nm_id>/)

**Layout:**
- Top: person's name, photo, profession tags, born info
- "Bio" link → `/bio` page with full biography
- "Awards" link → `/awards` page
- **Filmography** section (below the fold — scroll down): grouped by role (Actor, Director, Producer, Writer)
  - Each entry: title, year, character name / role
  - Click a title to open that title's page

---

### Chart Pages

**IMDb Top 250 (https://www.imdb.com/chart/top/):**
- Ranked list of 250 movies, each with: rank number, poster, title, year, rating, votes
- Click a title to open it
- "Filter" button at top lets you filter by genre/year/rating

**Bottom 100 — lowest rated movies (https://www.imdb.com/chart/bottom/):**
- Same layout as Top 250 but sorted worst-first

**Most Popular Movies (https://www.imdb.com/chart/moviemeter/):**
- Popularity ranking, updated weekly

---

## Searching for a Movie, TV Show, or Person

1. Click the search bar (`#suggestion-search`) at the top of any page
2. Type the title or person name
3. Press Enter or click the submit button (`#suggestion-search-button`)
4. Results page URL: https://www.imdb.com/find/?q=<search_term>&s=tt
5. On the results page, click the title link under "Titles" to open the title page

Example: https://www.imdb.com/find/?q=The+Matrix&s=tt

---

## Movie / TV Title Pages — Sub-Pages

URL pattern: https://www.imdb.com/title/<tt_id>/

**Sub-page links — accessible from the horizontal sub-navigation bar near the top:**
- Cast & crew (`[data-testid="hero-subnav-bar-topic-links"]` first link) → `/fullcredits/`
- User reviews → `/reviews/`
- Trivia → `/trivia/`
- FAQ → `/faq/`

**Or scroll down and look for:**
- "Full cast & crew" in the principal credits block
- "See all reviews" in the reviews preview section
- Sub-page links in "Did you know" block: trivia, goofs, quotes

Known movie IDs:
- The Matrix (1999): tt0133093 → https://www.imdb.com/title/tt0133093/
- The Matrix Reloaded (2003): tt0234215
- The Matrix Revolutions (2003): tt0242653
- Inception (2010): tt1375666 → https://www.imdb.com/title/tt1375666/
- The Dark Knight (2008): tt0468569
- Interstellar (2014): tt0816692
- The Godfather (1972): tt0068646
- The Shawshank Redemption (1994): tt0111161
- Pulp Fiction (1994): tt0110912
- Forrest Gump (1994): tt0109830
- Avengers: Endgame (2019): tt4154796
- Avatar (2009): tt0499549
- Titanic (1997): tt0120338
- Goodfellas (1990): tt0099685
- Fight Club (1999): tt0137523
- The Silence of the Lambs (1991): tt0102926
- Schindler's List (1993): tt0108052
- The Terminator (1984): tt0088247
- Terminator 2: Judgment Day (1991): tt0103064
- Alien (1979): tt0078748
- Aliens (1986): tt0090605
- Jurassic Park (1993): tt0107290
- Star Wars: A New Hope (1977): tt0076759
- The Lion King (1994): tt0110357
- Back to the Future (1985): tt0088763

---

## TV Show Pages

URL pattern: https://www.imdb.com/title/<tt_id>/

Known TV show IDs:
- Seinfeld (1989–1998): tt0098904
- Breaking Bad (2008–2013): tt0903747
- Game of Thrones (2011–2019): tt0944947
- Friends (1994–2004): tt0108778
- The Sopranos (1999–2007): tt0141842
- Stranger Things (2016–): tt4574334
- The Office US (2005–2013): tt0386676
- The Wire (2002–2008): tt0306414
- Frasier (1993–2004): tt0106004
- The Simpsons (1989–): tt0096697
- The X-Files (1993–2018): tt0106179
- Lost (2004–2010): tt0411008
- House M.D. (2004–2012): tt0412142
- The Crown (2016–): tt4786824
- Succession (2018–2023): tt7660850

**TV Show Page UI Structure:**
- Top: show title, year range, rating, genre tags, synopsis
- "Episode guide" link/button — click it to open the full episode list (→ `/episodes/`)
- "Full cast & crew" link → `/fullcredits/`
- Season selector on the episodes page: numbered buttons 1, 2, 3 … — click a number to see that season

**Navigation flow to reach Season 1 of a show:**
1. Search for the show title in the search bar
2. Click the TV series entry in search results
3. On the show page, click the "Episode guide" link (visible near the middle of the page)
4. On the episodes page, click "1" in the season selector

---

## TV Show Episodes Pages

URL pattern: https://www.imdb.com/title/<tt_id>/episodes/?season=<N>

Direct examples:
- Frasier Season 1: https://www.imdb.com/title/tt0106004/episodes/?season=1
- Frasier Season 2: https://www.imdb.com/title/tt0106004/episodes/?season=2
- Breaking Bad Season 1: https://www.imdb.com/title/tt0903747/episodes/?season=1
- Seinfeld Season 1: https://www.imdb.com/title/tt0098904/episodes/?season=1
- Friends Season 1: https://www.imdb.com/title/tt0108778/episodes/?season=1
- Game of Thrones Season 1: https://www.imdb.com/title/tt0944947/episodes/?season=1
- The Simpsons Season 1: https://www.imdb.com/title/tt0096697/episodes/?season=1
- The Sopranos Season 1: https://www.imdb.com/title/tt0141842/episodes/?season=1
- Game of Thrones Season 2: https://www.imdb.com/title/tt0944947/episodes/?season=2
- Game of Thrones Season 3: https://www.imdb.com/title/tt0944947/episodes/?season=3
- Breaking Bad Season 2: https://www.imdb.com/title/tt0903747/episodes/?season=2
- Stranger Things Season 1: https://www.imdb.com/title/tt4574334/episodes/?season=1
- The Wire Season 1: https://www.imdb.com/title/tt0306414/episodes/?season=1
- Lost Season 1: https://www.imdb.com/title/tt0411008/episodes/?season=1
- House M.D. Season 1: https://www.imdb.com/title/tt0412142/episodes/?season=1
- The Crown Season 1: https://www.imdb.com/title/tt4786824/episodes/?season=1
- Succession Season 1: https://www.imdb.com/title/tt7660850/episodes/?season=1

---

## Full Cast & Crew Pages

URL pattern: https://www.imdb.com/title/<tt_id>/fullcredits/

**How to reach it:**
- From a title page: click "Cast & crew" in the sub-navigation bar at the top, OR click "See full cast and crew" in the principal credits block, OR click "Full cast & crew" in the "More to explore" section
- Direct URL: https://www.imdb.com/title/<tt_id>/fullcredits/

Direct examples:
- The Matrix: https://www.imdb.com/title/tt0133093/fullcredits/
- Inception: https://www.imdb.com/title/tt1375666/fullcredits/
- The Dark Knight: https://www.imdb.com/title/tt0468569/fullcredits/
- Seinfeld: https://www.imdb.com/title/tt0098904/fullcredits/
- Breaking Bad: https://www.imdb.com/title/tt0903747/fullcredits/
- Friends: https://www.imdb.com/title/tt0108778/fullcredits/

---

## Person Pages

URL pattern: https://www.imdb.com/name/<nm_id>/

**How to navigate to a person page:**
1. Type the person's name in the search bar
2. On the results page, look under the "Names" section
3. Click the person's name

**Person page layout:**
- Top: name, photo, born info, job title (Actor, Director, etc.)
- Links to: Bio (`/bio`), Awards (`/awards`), Known for section
- **Filmography** (scroll down): grouped by Actor / Director / Producer / Writer
  - Each title shows: movie/show title, year, character name, rating
  - Click a title to open that title's page

Known people:
- Keanu Reeves: nm0000206 → https://www.imdb.com/name/nm0000206/
- Christopher Nolan: nm0634240 → https://www.imdb.com/name/nm0634240/
- Leonardo DiCaprio: nm0000138 → https://www.imdb.com/name/nm0000138/
- Tom Hanks: nm0000158 → https://www.imdb.com/name/nm0000158/
- Brad Pitt: nm0000093 → https://www.imdb.com/name/nm0000093/
- Robin Wright: nm0000701
- Meryl Streep: nm0000658
- Robert De Niro: nm0000134
- Al Pacino: nm0000199
- Denzel Washington: nm0000243
- Clint Eastwood: nm0000142
- Steven Spielberg: nm0000229
- Quentin Tarantino: nm0000233
- Martin Scorsese: nm0000217
- James Cameron: nm0000116
- Tim Burton: nm0000318
- Ridley Scott: nm0000631
- Bryan Cranston: nm0186505
- Aaron Paul: nm0666739

---

## Charts and Lists

- IMDb Top 250 Movies: https://www.imdb.com/chart/top/
- IMDb Bottom 100 Movies (LOWEST rated — NOT top): https://www.imdb.com/chart/bottom/
- Most Popular Movies: https://www.imdb.com/chart/moviemeter/
- IMDb Top 250 TV Shows: https://www.imdb.com/chart/toptv/
- Most Popular TV Shows: https://www.imdb.com/chart/tvmeter/
- Box Office (US): https://www.imdb.com/chart/boxoffice/
- Most Popular Celebrities: https://www.imdb.com/chart/starmeter/

---

## Advanced Search — Filter URL Reference

Base URL: https://www.imdb.com/search/title/
All filters are combinable with & in the URL.

### Genre (genres parameter)
IMPORTANT: Use hyphens where needed — `sci-fi` and `film-noir` use hyphens. All others are plain words.
Values: action, adventure, animation, biography, comedy, crime, documentary, drama, family, fantasy, film-noir, history, horror, music, musical, mystery, romance, sci-fi, sport, thriller, war, western

### Title Type (title_type parameter)
IMPORTANT: Use `tv_miniseries` (not `mini_series`). Use `feature` (not `featurefilm` or `movie`).
- Feature films: title_type=feature   ← NOT `featurefilm`, NOT `movie`
- TV Series: title_type=tv_series
- TV Mini-Series / Limited Series: title_type=tv_miniseries
- TV Movies: title_type=tv_movie
- Short Films: title_type=short
- TV Episodes: title_type=tv_episode
- Multiple types (ORed): title_type=feature,tv_movie

### Year Range (release_date parameter)
IMPORTANT: Always use full ISO dates (YYYY-MM-DD). NEVER use `year=` or short formats like `release_date=2010,2023`.
- Single year 2020: release_date=2020-01-01,2020-12-31
- From 1990 to 2000: release_date=1990-01-01,2000-12-31
- Before 1960: release_date=,1960-12-31
- From 2000 onwards: release_date=2000-01-01,
- 1940s (decade): release_date=1940-01-01,1949-12-31
- WRONG (do not use): release_date=2010,2023 or year=2010,2023

### User Rating (user_rating parameter)
IMPORTANT: Use `user_rating=`, NOT `rating=`.
- Highly rated (7+): user_rating=7.0,10.0
- Top rated (8+): user_rating=8.0,10.0
- Format: min,max (open-ended: user_rating=7.5, means 7.5 and above)

### Number of Votes (num_votes parameter)
IMPORTANT: Use `num_votes=`, NOT `votes=`.
- Well-known titles only: num_votes=1000,
- Very well-known: num_votes=10000,

### Color (colors parameter)
- Black and white: colors=black_and_white
- Color only: colors=color

### Sort Order (sort parameter)
Format: sort=<field>,<asc|desc>
Confirmed values from actual IMDb URLs:
- Highest rated first: sort=user_rating,desc
- Newest first: sort=year,desc  (IMDb uses `year` for release date sort)
- Oldest first: sort=year,asc
- Most popular: sort=moviemeter,asc
- Most votes: sort=num_votes,desc
- Alphabetical: sort=alpha,asc
- US box office: sort=boxoffice_gross_us,desc

### Language (languages parameter — ISO 639-1 code)
IMPORTANT: Use `languages=`, NOT `language=`.
Use `primary_language=` to match only the PRIMARY language (more precise).
- Spanish: languages=es
- French: languages=fr
- Italian: languages=it
- German: languages=de
- Japanese: languages=ja
- Hindi/Bollywood: languages=hi
- Korean: languages=ko
- Exclude English: languages=!en
- Example (primary Japanese): https://www.imdb.com/search/title/?primary_language=ja&title_type=feature

### Country of Origin (country_of_origin parameter — ISO 3166-1 alpha-2)
IMPORTANT: Use `country_of_origin=`, NOT `country=` or `countries=`. Never use `country=`.
- UK: gb | US: us | France: fr | Germany: de | Italy: it | Spain: es
- India: in | Japan: jp | South Korea: kr | Australia: au | Brazil: br
- Multiple (comma-separated, ORed): country_of_origin=fr,it
- Example: Japanese films → https://www.imdb.com/search/title/?country_of_origin=jp&sort=user_rating,desc

### Content Rating / Certificate (certificates parameter)
IMPORTANT: Use `certificates=`, NOT `content_rating=`. Values are lowercase: `us:g` not `US:G`.
- G-rated: certificates=us:g
- PG-rated: certificates=us:pg
- PG-13: certificates=us:pg_13
- R-rated: certificates=us:r
- NC-17: certificates=us:nc_17
- Multiple (ORed): certificates=us:g,us:pg
- UK ratings: certificates=gb:u, certificates=gb:pg, certificates=gb:12, certificates=gb:15, certificates=gb:18

### Keywords (keywords parameter)
IMPORTANT: Use `keywords=`, NOT `keyword=`. Values use hyphens (slug format).
- WWII: keywords=world-war-ii
- Superhero: keywords=superhero
- MCU: keywords=marvel-cinematic-universe
- James Bond: keywords=james-bond
- Harry Potter: keywords=harry-potter
- AI / artificial intelligence: keywords=artificial-intelligence
- Based on novel: keywords=based-on-novel
- Stephen King: keywords=stephen-king
- Musician biopic: keywords=musician
- Palme d'Or (Cannes): keywords=palme-d-or
- Golden Lion (Venice): keywords=golden-lion
- Multiple (ANDed): keywords=based-on-novel,time-travel

### Awards (groups parameter)
IMPORTANT: Values are PLURAL (e.g. `oscar_winners` not `oscar_winner`).
BAFTA has no confirmed `groups=` value — use keywords=bafta instead.
- Oscar winners: groups=oscar_winners
- Oscar nominees: groups=oscar_nominees
- Oscar Best Picture winners: groups=oscar_best_picture_winners
- Oscar Best Director winners: groups=oscar_best_director_winners
- Emmy winners: groups=emmy_winners
- Emmy nominees: groups=emmy_nominees
- Golden Globe winners: groups=golden_globe_winners
- Golden Globe nominees: groups=golden_globe_nominees
- Razzie winners (worst films): groups=razzie_winners
- National Film Registry: groups=national_film_registry
- IMDb Top 250: groups=top_250
- IMDb Bottom 100: groups=bottom_100

### Person / Role (role parameter)
IMPORTANT: Use `role=`, NOT `person=`. Takes nm-IDs.
- Single person: role=nm0000158 (Tom Hanks)
- Multiple persons (all must appear, ANDed): role=nm0000158,nm0000212
- Example (Tom Hanks + Meg Ryan films): https://www.imdb.com/search/title/?role=nm0000158,nm0000212

### Combined URL Examples
Documentaries released in 2020:
https://www.imdb.com/search/title/?genres=documentary&release_date=2020-01-01,2020-12-31

Highest-rated war movies (1000+ votes):
https://www.imdb.com/search/title/?genres=war&sort=user_rating,desc&num_votes=1000,

Horror movies from the 1980s:
https://www.imdb.com/search/title/?genres=horror&release_date=1980-01-01,1989-12-31&sort=user_rating,desc

Black and white classic films (pre-1960):
https://www.imdb.com/search/title/?colors=black_and_white&release_date=,1960-12-31&sort=user_rating,desc&num_votes=1000,

Sci-fi highly-rated (NOTE: sci-fi with hyphen, as IMDb uses it):
https://www.imdb.com/search/title/?genres=sci-fi&sort=user_rating,desc&num_votes=1000,

Mini-series / limited series (NOTE: tv_miniseries, as IMDb uses it):
https://www.imdb.com/search/title/?title_type=tv_miniseries&sort=user_rating,desc

Spanish-language movies (newest):
https://www.imdb.com/search/title/?languages=es&sort=year,desc

Korean horror:
https://www.imdb.com/search/title/?genres=horror&country_of_origin=kr&sort=user_rating,desc

MCU movies:
https://www.imdb.com/search/title/?keywords=marvel-cinematic-universe&sort=year,asc

WWII documentaries:
https://www.imdb.com/search/title/?genres=documentary&keywords=world-war-ii&sort=user_rating,desc

Musician biopics:
https://www.imdb.com/search/title/?genres=biography&keywords=musician&sort=user_rating,desc

Movies with both Tom Hanks and Robin Wright:
https://www.imdb.com/search/title/?role=nm0000158,nm0000701

Oscar winners sorted by rating (NOTE: oscar_winners plural):
https://www.imdb.com/search/title/?groups=oscar_winners&sort=user_rating,desc

G-rated animated films:
https://www.imdb.com/search/title/?genres=animation&certificates=us:g&title_type=feature&sort=user_rating,desc

Studio Ghibli films (Japan, animation):
https://www.imdb.com/search/title/?companies=co0048420&sort=user_rating,desc

Japanese animated films (country + genre):
https://www.imdb.com/search/title/?genres=animation&country_of_origin=jp&title_type=feature&sort=user_rating,desc

Best films from the 1980s:
https://www.imdb.com/search/title/?release_date=1980-01-01,1989-12-31&sort=user_rating,desc&num_votes=10000,

Silent films (1920s, black and white):
https://www.imdb.com/search/title/?release_date=1920-01-01,1929-12-31&colors=black_and_white&sort=user_rating,desc&num_votes=100,

Feature films only (no shorts or TV):
https://www.imdb.com/search/title/?title_type=feature&sort=user_rating,desc&num_votes=1000,

IMPORTANT: IMDb does NOT have URLs like imdb.com/movies or imdb.com/genre/<name>.
Always use imdb.com/search/title/ with query parameters for filtering.
NEVER use find/?q= to search for a language or genre.
NEVER invent parameters: no `country=`, `production_company=`, `studio=`, `director=`, `actor=`, `genre=`, `language=`, `rating=`, `votes=`, `type=`.

---

## Searching by Language / Country

Use Advanced Title Search with filter parameters:
- Spanish: https://www.imdb.com/search/title/?languages=es&sort=year,desc
- French: https://www.imdb.com/search/title/?languages=fr&sort=year,desc
- Hindi/Bollywood: https://www.imdb.com/search/title/?languages=hi&sort=user_rating,desc
- Korean: https://www.imdb.com/search/title/?languages=ko&sort=user_rating,desc
- Japanese: https://www.imdb.com/search/title/?languages=ja&sort=year,desc
- Italian: https://www.imdb.com/search/title/?languages=it&sort=year,desc
- German: https://www.imdb.com/search/title/?languages=de&sort=year,desc

---

## News and Events

- Movie News: https://www.imdb.com/news/movie/
- TV News: https://www.imdb.com/news/tv/
- Upcoming Releases Calendar: https://www.imdb.com/calendar
- Awards Central: https://www.imdb.com/awards-central/
- Oscars Guide: https://www.imdb.com/oscars/

---

## User Features (requires sign-in)

**Watchlist:**
- URL: https://www.imdb.com/watchlist
- On any title page: click "Add to Watchlist" button (`[data-testid="tm-box-wl-button"]`)
- Or click the ribbon icon on poster thumbnails

**Mark as Watched:**
- On a title page: click the eye/checkmark "Mark as watched" button (`[data-testid="watched-button-<tt_id>"]`) near the Watchlist button
- Requires sign-in: https://www.imdb.com/registration/signin

**Rating a title:**
- On a title page: click the "Rate" button in the rating bar (opens a star popup)
- Requires sign-in

---

## Title Sub-Page URL Patterns

For any movie or TV show with known ID (e.g. tt1375666 for Inception):
- User reviews:       https://www.imdb.com/title/tt1375666/reviews/
- Trivia:             https://www.imdb.com/title/tt1375666/trivia/
- Goofs:              https://www.imdb.com/title/tt1375666/goofs/
- Quotes:             https://www.imdb.com/title/tt1375666/quotes/
- Parental guide:     https://www.imdb.com/title/tt1375666/parentalguide/
- Filming locations:  https://www.imdb.com/title/tt1375666/locations/
- Full cast & crew:   https://www.imdb.com/title/tt1375666/fullcredits/
- Awards:             https://www.imdb.com/title/tt1375666/awards/
- Box office/Budget:  https://www.imdb.com/title/tt1375666/business/
- Soundtrack:         https://www.imdb.com/title/tt1375666/soundtrack/
- Technical specs:    https://www.imdb.com/title/tt1375666/technical/
- Release info/dates: https://www.imdb.com/title/tt1375666/releaseinfo/
- Plot summary:       https://www.imdb.com/title/tt1375666/plotsummary/
- Connections:        https://www.imdb.com/title/tt1375666/movieconnections/
- Keywords:           https://www.imdb.com/title/tt1375666/keywords/
- FAQ:                https://www.imdb.com/title/tt1375666/faq/
- Alternate titles:   https://www.imdb.com/title/tt1375666/releaseinfo/#akas
- Social media links: https://www.imdb.com/title/tt1375666/externalsites/

---

## Common Navigation Flows

### Find documentaries from 2020 (filter page workflow)
1. Go to https://www.imdb.com/search/title/
2. On the left filter panel, click the **"Genre"** accordion header to expand it
3. Click the **"Documentary"** chip — it will highlight
4. Click the **"Release date"** accordion header to expand it
5. Type **2020** in the "from" year field and **2020** in the "to" year field
6. Click the **"See results"** button (top right of the filter panel)
Direct URL: https://www.imdb.com/search/title/?genres=documentary&release_date=2020-01-01,2020-12-31

### Find horror movies (quick filter)
1. Go to https://www.imdb.com/search/title/
2. Expand **"Genre"** accordion, click **"Horror"** chip
3. Click **"See results"**
Direct URL: https://www.imdb.com/search/title/?genres=horror&sort=user_rating,desc

### View episodes of a TV show season
1. Search for the show title in the search bar
2. Click the TV series entry in search results
3. On the show page, click the **"Episode guide"** link
4. Click the season number in the season selector
Direct example for Breaking Bad Season 1: https://www.imdb.com/title/tt0903747/episodes/?season=1

### Find actors of a specific movie
1. Search for the movie title in the search bar
2. Click the movie in search results
3. In the sub-navigation bar at the top, click **"Cast & crew"**
4. Or navigate directly: https://www.imdb.com/title/<tt_id>/fullcredits/

### Find the Top 250 list
1. Navigate to: https://www.imdb.com/chart/top/
The list shows 250 movies ranked by weighted average rating.

### Check box office results
- Navigate to: https://www.imdb.com/chart/boxoffice/
- Or on a title page, scroll to the "Box office" section and click the link to `/business/`

### Find upcoming movies / release calendar
- Navigate to: https://www.imdb.com/calendar

### Look up an actor or director
1. Type their name in the search bar
2. In results, click the person's name under the "Names" section
3. Their filmography is on the person page (scroll down)

### Find movies with two specific actors
URL pattern: https://www.imdb.com/search/title/?role=<nm_id1>,<nm_id2>
Example (Tom Hanks + Brad Pitt): https://www.imdb.com/search/title/?role=nm0000158,nm0000093

### Find franchise / collection movies
- MCU: https://www.imdb.com/search/title/?keywords=marvel-cinematic-universe&sort=year,asc
- Star Wars: https://www.imdb.com/search/title/?keywords=star-wars&title_type=feature&sort=year,asc
- James Bond: https://www.imdb.com/search/title/?keywords=james-bond&title_type=feature&sort=year,asc
- Harry Potter: https://www.imdb.com/search/title/?keywords=harry-potter&title_type=feature&sort=year,asc
- Lord of the Rings: https://www.imdb.com/search/title/?keywords=the-lord-of-the-rings&title_type=feature&sort=year,asc

### Find highest-rated episodes of a TV show
1. Search for the show
2. Open the show page
3. Click "Episode guide"
4. Browse each season — episode ratings are shown on each card
(IMDb does not offer a single view sorted by rating across all seasons)

### Awards and cross-award search
- Awards Central: https://www.imdb.com/awards-central/
- Oscar winners: https://www.imdb.com/search/title/?groups=oscar_winners&sort=user_rating,desc
- Oscar nominees: https://www.imdb.com/search/title/?groups=oscar_nominees&sort=user_rating,desc
- Emmy winners: https://www.imdb.com/search/title/?groups=emmy_winners
- Golden Globe winners: https://www.imdb.com/search/title/?groups=golden_globe_winners
- BAFTA: no confirmed groups= value — use keywords=bafta instead

### Find movies by production company / studio
IMPORTANT: There is NO `production_company=` URL parameter on IMDb. NEVER use it.
The correct parameter is `companies=<co_id>` where the co_id is IMDb's internal company ID.
1. Search the company: https://www.imdb.com/find/?q=Pixar&s=co
2. Click the company name under "Companies" in the results
3. On the company page, browse or click "Full list of titles"
Known company IDs and their filter URLs:
- Pixar (co0017902): https://www.imdb.com/search/title/?companies=co0017902
- A24 (co0390568): https://www.imdb.com/search/title/?companies=co0390568
- Marvel Studios (co0051941): https://www.imdb.com/search/title/?companies=co0051941
- Studio Ghibli (co0048420): https://www.imdb.com/search/title/?companies=co0048420
- Warner Bros. (co0026840): https://www.imdb.com/search/title/?companies=co0026840
- Universal Pictures (co0005073): https://www.imdb.com/search/title/?companies=co0005073
Note: For companies NOT listed above, search via https://www.imdb.com/find/?q=<company>&s=co first.

### Find movies from a specific decade
URL pattern: `release_date=<YYYY>-01-01,<YYYY>-12-31` (set to decade start/end)
- 1950s best: https://www.imdb.com/search/title/?release_date=1950-01-01,1959-12-31&sort=user_rating,desc&num_votes=1000,
- 1960s best: https://www.imdb.com/search/title/?release_date=1960-01-01,1969-12-31&sort=user_rating,desc&num_votes=1000,
- 1970s best: https://www.imdb.com/search/title/?release_date=1970-01-01,1979-12-31&sort=user_rating,desc&num_votes=1000,
- 1980s best: https://www.imdb.com/search/title/?release_date=1980-01-01,1989-12-31&sort=user_rating,desc&num_votes=1000,
- 1990s best: https://www.imdb.com/search/title/?release_date=1990-01-01,1999-12-31&sort=user_rating,desc&num_votes=1000,
- 2000s best: https://www.imdb.com/search/title/?release_date=2000-01-01,2009-12-31&sort=user_rating,desc&num_votes=1000,
For "best movies of each decade", navigate separately to each decade URL above — IMDb has no single "per-decade" view.

### Find silent / black-and-white / vintage films
- Silent films (1920s): https://www.imdb.com/search/title/?release_date=1920-01-01,1929-12-31&colors=black_and_white&sort=user_rating,desc&num_votes=100,
- Black-and-white only (any year): https://www.imdb.com/search/title/?colors=black_and_white&sort=user_rating,desc&num_votes=1000,
- Pre-1960 classics: https://www.imdb.com/search/title/?release_date=,1960-12-31&colors=black_and_white&sort=user_rating,desc&num_votes=1000,
- Italian neo-realist (1940s–1950s): https://www.imdb.com/search/title/?country_of_origin=it&release_date=1940-01-01,1959-12-31&sort=user_rating,desc&num_votes=100,

### Find movies by keyword
URL: https://www.imdb.com/search/title/?keywords=<slug>
Keyword slugs (use hyphens):
- artificial-intelligence, time-travel, superhero, based-on-novel, world-war-ii
- stephen-king, harry-potter, james-bond, marvel-cinematic-universe, palme-d-or
- golden-lion (Venice), silver-bear (Berlin), foreign-language-film

### Sort search results
- Newest first: https://www.imdb.com/search/title/?sort=year,desc
- Highest rated first: https://www.imdb.com/search/title/?sort=user_rating,desc
- Most popular first: https://www.imdb.com/search/title/?sort=moviemeter,asc
- Combine with filters: ?genres=drama&sort=year,desc

### Find movies suitable for children (parental guide / rating filter)
URL: https://www.imdb.com/search/title/?certificates=US:G (G-rated)
- G-rated animated: https://www.imdb.com/search/title/?genres=animation&certificates=US:G&sort=user_rating,desc
- PG-rated family: https://www.imdb.com/search/title/?genres=family&certificates=US:PG&sort=user_rating,desc
UI: On the Advanced Search page, expand the **"US certificates"** accordion and click the **G** or **PG** chip.
To see the parental guide for a specific film: navigate to https://www.imdb.com/title/<tt_id>/parentalguide/

### Find Cannes / Venice / Berlin / Sundance award winners
IMDb does NOT have a `groups=` parameter for non-US festival awards. Use keyword search:
- Palme d'Or winners: https://www.imdb.com/search/title/?keywords=palme-d-or&sort=year,desc
- Golden Lion (Venice): https://www.imdb.com/search/title/?keywords=golden-lion&sort=year,desc
- Silver Bear (Berlin): https://www.imdb.com/search/title/?keywords=silver-bear&sort=year,desc
- Sundance Grand Jury: https://www.imdb.com/search/title/?keywords=sundance-film-festival&sort=year,desc
Or navigate to Awards Central: https://www.imdb.com/awards-central/ and search for the specific festival.

### Sort user reviews by helpfulness
1. Navigate to a title's reviews page: https://www.imdb.com/title/<tt_id>/reviews/
2. On the reviews page, use the **Sort** dropdown (top right of review list)
3. Select **"Helpfulness"** — this sorts reviews by the number of "helpful" votes
Direct URL parameter: https://www.imdb.com/title/<tt_id>/reviews/?sort=helpfulnessScore&dir=desc

### Find director who also acted (role= filter)
URL: https://www.imdb.com/search/title/?role=<nm_id> — returns titles where that person had any role
To find films where the same person directed AND acted: search for the person, open their filmography,
or use: https://www.imdb.com/search/title/?role=<nm_id>&sort=user_rating,desc (filter by their nm_id)
Known examples: Quentin Tarantino (nm0000233), Clint Eastwood (nm0000142), Mel Gibson (nm0000154)

### Browse editorial picks and featured articles
- Movie news & editorial: https://www.imdb.com/news/movie/
- TV news: https://www.imdb.com/news/tv/
- Homepage editorial carousel: visit https://www.imdb.com/ — the large carousel at the top shows IMDb's current featured picks (Previous/Next arrows to browse)
- Topic chips on homepage: "Oscars", "Awards Season Guide", etc. — click to see curated editorial content

### Sign in to IMDb account
IMDb uses Amazon login. There is no separate IMDb sign-in page.
URL: https://www.imdb.com/registration/signin
This redirects to Amazon's login page. Use your Amazon email and password.
After sign-in, features like Watchlist, ratings, and "Mark as watched" become available.

### Contribute or report an error
- IMDb Contribution Portal: https://contribute.imdb.com/
- On any title page: click the "Edit page" button to report incorrect info
- Add a new title: https://contribute.imdb.com/ → "Add a new title"
- NOTE: There is NO public "follow other users" feature on IMDb.
