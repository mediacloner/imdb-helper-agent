# IMDb Navigation Guide

## Home Page
URL: https://www.imdb.com/
Contains a universal search bar (CSS: #suggestion-search) and submit button (#suggestion-search-button).
The IMDb logo links back home. Top navigation bar has Movies, TV Shows, Awards, Celebs, News sections.

## Searching for a Movie, TV Show, or Person
1. Click the search bar (#suggestion-search) at the top of any page.
2. Type the title or person name.
3. Press Enter or click the submit button (#suggestion-search-button).
4. Results page URL pattern: https://www.imdb.com/find/?q=<search_term>&s=tt
5. On the results page, click the title link under "Titles" to open the title page.
Example: https://www.imdb.com/find/?q=The+Matrix&s=tt

## Movie / Title Pages
URL pattern: https://www.imdb.com/title/<tt_id>/
Contains: rating, plot summary, cast preview, genre tags, trailer links.
The cast section shows the top-billed actors. "Full cast & crew" link navigates to the fullcredits page.

Known movie IDs:
- The Matrix (1999): tt0133093 → https://www.imdb.com/title/tt0133093/
- The Matrix Reloaded (2003): tt0234215 → https://www.imdb.com/title/tt0234215/
- The Matrix Revolutions (2003): tt0242653 → https://www.imdb.com/title/tt0242653/
- Inception (2010): tt1375666 → https://www.imdb.com/title/tt1375666/
- The Dark Knight (2008): tt0468569 → https://www.imdb.com/title/tt0468569/
- Interstellar (2014): tt0816692 → https://www.imdb.com/title/tt0816692/
- The Godfather (1972): tt0068646 → https://www.imdb.com/title/tt0068646/
- The Shawshank Redemption (1994): tt0111161 → https://www.imdb.com/title/tt0111161/
- Pulp Fiction (1994): tt0110912 → https://www.imdb.com/title/tt0110912/
- Forrest Gump (1994): tt0109830 → https://www.imdb.com/title/tt0109830/
- Avengers: Endgame (2019): tt4154796 → https://www.imdb.com/title/tt4154796/
- Avatar (2009): tt0499549 → https://www.imdb.com/title/tt0499549/
- Titanic (1997): tt0120338 → https://www.imdb.com/title/tt0120338/
- Goodfellas (1990): tt0099685 → https://www.imdb.com/title/tt0099685/
- Fight Club (1999): tt0137523 → https://www.imdb.com/title/tt0137523/
- The Silence of the Lambs (1991): tt0102926 → https://www.imdb.com/title/tt0102926/
- Schindler's List (1993): tt0108052 → https://www.imdb.com/title/tt0108052/
- The Terminator (1984): tt0088247 → https://www.imdb.com/title/tt0088247/
- Terminator 2: Judgment Day (1991): tt0103064 → https://www.imdb.com/title/tt0103064/
- Alien (1979): tt0078748 → https://www.imdb.com/title/tt0078748/
- Aliens (1986): tt0090605 → https://www.imdb.com/title/tt0090605/
- Jurassic Park (1993): tt0107290 → https://www.imdb.com/title/tt0107290/
- Star Wars: A New Hope (1977): tt0076759 → https://www.imdb.com/title/tt0076759/
- The Lion King (1994): tt0110357 → https://www.imdb.com/title/tt0110357/
- Back to the Future (1985): tt0088763 → https://www.imdb.com/title/tt0088763/

## TV Show Pages
URL pattern: https://www.imdb.com/title/<tt_id>/
Known TV show IDs:
- Seinfeld (1989–1998): tt0098904 → https://www.imdb.com/title/tt0098904/
- Breaking Bad (2008–2013): tt0903747 → https://www.imdb.com/title/tt0903747/
- Game of Thrones (2011–2019): tt0944947 → https://www.imdb.com/title/tt0944947/
- Friends (1994–2004): tt0108778 → https://www.imdb.com/title/tt0108778/
- The Sopranos (1999–2007): tt0141842 → https://www.imdb.com/title/tt0141842/
- Stranger Things (2016–): tt4574334 → https://www.imdb.com/title/tt4574334/
- The Office US (2005–2013): tt0386676 → https://www.imdb.com/title/tt0386676/
- The Wire (2002–2008): tt0306414 → https://www.imdb.com/title/tt0306414/
- Frasier (1993–2004): tt0106004 → https://www.imdb.com/title/tt0106004/
- The Simpsons (1989–): tt0096697 → https://www.imdb.com/title/tt0096697/
- The X-Files (1993–2018): tt0106179 → https://www.imdb.com/title/tt0106179/
- Lost (2004–2010): tt0411008 → https://www.imdb.com/title/tt0411008/
- House M.D. (2004–2012): tt0412142 → https://www.imdb.com/title/tt0412142/
- The Crown (2016–): tt4786824 → https://www.imdb.com/title/tt4786824/
- Succession (2018–2023): tt7660850 → https://www.imdb.com/title/tt7660850/

## TV Show Page UI Structure
When you open a TV show page (https://www.imdb.com/title/<tt_id>/):
- Top area shows the show title, rating, year range, genre tags, and a synopsis
- Below the synopsis there is an "Episode guide" link/button — clicking it opens the full episode list
- "Full cast & crew" link leads to the fullcredits page
- A "Reviews" section and a "More like this" section appear further down

## Episode Guide Page UI Structure
After clicking "Episode guide" on a show page, you arrive at:
https://www.imdb.com/title/<tt_id>/episodes/
- At the top of the page there is a season selector showing season numbers as tabs or a dropdown: 1, 2, 3 ...
- Click the number of the season you want (e.g. click "1" for Season 1, click "2" for Season 2)
- Below the selector, the list of episodes for the selected season is shown
- Each episode card shows: episode number, title, air date, rating, and a short description

Navigation flow to reach Season 1 of a show:
1. Search for the show title in the search bar
2. Click the show title in the search results
3. On the show page, click the "Episode guide" link (visible near the top/middle of the page)
4. On the episodes page, click "1" in the season selector to filter to Season 1

## TV Show Episodes Pages
URL pattern: https://www.imdb.com/title/<tt_id>/episodes/?season=<N>
Each season has its own episodes listing. Season numbers start at 1.
Direct examples:
- Frasier Season 1: https://www.imdb.com/title/tt0106004/episodes/?season=1
- Frasier Season 2: https://www.imdb.com/title/tt0106004/episodes/?season=2
- Breaking Bad Season 1: https://www.imdb.com/title/tt0903747/episodes/?season=1
- Seinfeld Season 1: https://www.imdb.com/title/tt0098904/episodes/?season=1
- Friends Season 1: https://www.imdb.com/title/tt0108778/episodes/?season=1
- Game of Thrones Season 1: https://www.imdb.com/title/tt0944947/episodes/?season=1
- The Simpsons Season 1: https://www.imdb.com/title/tt0096697/episodes/?season=1

## Full Cast & Crew Pages
URL pattern: https://www.imdb.com/title/<tt_id>/fullcredits/
Lists every actor, director, writer, and crew member with links to their person pages.
Direct examples:
- The Matrix full cast: https://www.imdb.com/title/tt0133093/fullcredits/
- Inception full cast: https://www.imdb.com/title/tt1375666/fullcredits/
- The Dark Knight full cast: https://www.imdb.com/title/tt0468569/fullcredits/
- Seinfeld full cast: https://www.imdb.com/title/tt0098904/fullcredits/
- Breaking Bad full cast: https://www.imdb.com/title/tt0903747/fullcredits/
- Friends full cast: https://www.imdb.com/title/tt0108778/fullcredits/

## Person Pages
URL pattern: https://www.imdb.com/name/<nm_id>/
Contains filmography, biography, photos.
Known people:
- Keanu Reeves: https://www.imdb.com/name/nm0000206/
- Laurence Fishburne: https://www.imdb.com/name/nm0000401/
- Carrie-Anne Moss: https://www.imdb.com/name/nm0005251/
- Christopher Nolan: https://www.imdb.com/name/nm0634240/
- Leonardo DiCaprio: https://www.imdb.com/name/nm0000138/

## Charts and Lists
- IMDb Top 250 Movies: https://www.imdb.com/chart/top/
- IMDb Bottom 100 Movies (lowest rated): https://www.imdb.com/chart/bottom/
- Most Popular Movies: https://www.imdb.com/chart/moviemeter/
- IMDb Top 250 TV Shows: https://www.imdb.com/chart/toptv/
- Most Popular TV Shows: https://www.imdb.com/chart/tvmeter/
- Box Office (US): https://www.imdb.com/chart/boxoffice/
- Most Popular Celebrities: https://www.imdb.com/chart/starmeter/

## Browse and Search
- Browse by Genre/Interest: https://www.imdb.com/interest/all/
- Advanced Title Search: https://www.imdb.com/search/title/
- Advanced People Search: https://www.imdb.com/search/name/

## Searching by Language / Country of Origin
Use the Advanced Title Search with filter parameters:
- Spanish-language movies (newest first): https://www.imdb.com/search/title/?languages=es&sort=year,desc
- French-language movies: https://www.imdb.com/search/title/?languages=fr&sort=year,desc
- Italian-language movies: https://www.imdb.com/search/title/?languages=it&sort=year,desc
- German-language movies: https://www.imdb.com/search/title/?languages=de&sort=year,desc
- Japanese-language movies: https://www.imdb.com/search/title/?languages=ja&sort=year,desc
- Movies from Spain (country): https://www.imdb.com/search/title/?country_of_origin=es&sort=year,desc
- Movies from France: https://www.imdb.com/search/title/?country_of_origin=fr&sort=year,desc
Language codes follow ISO 639-1. Country codes follow ISO 3166-1 alpha-2.

IMPORTANT: There is NO URL like imdb.com/movies or imdb.com/genre/<language>.
Always use imdb.com/search/title/ with query parameters for language/country filtering.

## News and Events
- Movie News: https://www.imdb.com/news/movie/
- TV News: https://www.imdb.com/news/tv/
- Upcoming Releases Calendar: https://www.imdb.com/calendar
- Awards Central: https://www.imdb.com/awards-central/
- Oscars Guide: https://www.imdb.com/oscars/

## User Features (requires sign-in)
- Watchlist: https://www.imdb.com/watchlist
- Ratings history: https://www.imdb.com/user/<user_id>/ratings
- Sign in: https://www.imdb.com/registration/signin

## Navigation Menu Structure
Clicking the "Menu" button (hamburger, top-left) opens a sidebar with:
- Movies → Top 250, Most Popular, Box Office, Upcoming, Browse by Genre
- TV Shows → Top 250, Most Popular, Browse by Genre
- Watch → What to Watch, Latest Trailers
- Awards & Events → Oscars, Emmys, STARmeter Awards
- Celebs → Born Today, Most Popular, Photos
- News → Movie, TV, Celebrity news

## Common Navigation Flows

### How to view episodes of a TV show season
1. Search for the show title in the search bar
2. Click the TV series entry in search results
3. Navigate directly to the episodes page: https://www.imdb.com/title/<tt_id>/episodes/?season=<N>
Example for Frasier Season 1: https://www.imdb.com/title/tt0106004/episodes/?season=1

### How to find actors of a specific movie
1. Search for the movie title in the search bar
2. Click the movie in search results
3. On the movie page, click "Full cast & crew" link
4. Or navigate directly to: https://www.imdb.com/title/<tt_id>/fullcredits/

### How to find the Top 250 list
1. Click Menu → Movies → Top 250 Movies
2. Or navigate directly to: https://www.imdb.com/chart/top/

### How to check box office results
1. Click Menu → Movies → Box Office
2. Or navigate directly to: https://www.imdb.com/chart/boxoffice/

### How to find upcoming movies
1. Click Menu → Movies → Upcoming Releases
2. Or navigate directly to: https://www.imdb.com/calendar

### How to search for an actor or director
1. Type their name in the search bar
2. In results, select the person under "Names" section
3. Their filmography is listed on the person page

## Advanced Search URL Parameters

Base URL: https://www.imdb.com/search/title/
All filters can be combined with & in the URL.

### Title Type (title_type parameter)
- Feature films: title_type=feature
- TV Series: title_type=tv_series
- TV Mini-Series / Limited Series: title_type=tv_miniseries
- TV Movies: title_type=tv_movie
- Short Films: title_type=short
- Documentary: title_type=documentary
- TV Episode: title_type=tv_episode

Examples:
- All TV mini-series: https://www.imdb.com/search/title/?title_type=tv_miniseries
- All short films: https://www.imdb.com/search/title/?title_type=short

### Genre Filter (genres parameter)
Values: action, comedy, drama, horror, sci-fi, romance, thriller, animation, documentary, crime, adventure, fantasy, mystery, biography, history, war, western, musical, sport, family

Examples:
- Horror movies: https://www.imdb.com/search/title/?genres=horror
- War movies: https://www.imdb.com/search/title/?genres=war
- Sci-fi movies: https://www.imdb.com/search/title/?genres=sci-fi
- Documentary films: https://www.imdb.com/search/title/?genres=documentary

### Sort Order (sort parameter)
- By user rating descending (highest first): sort=user_rating,desc
- By user rating ascending: sort=user_rating,asc
- By number of votes descending: sort=num_votes,desc
- By year newest: sort=year,desc
- By year oldest: sort=year,asc
- By box office gross: sort=boxoffice_gross_us,desc
- By popularity: sort=moviemeter,asc

### Year Range (release_date parameter)
- From 1990 to 2000: release_date=1990-01-01,2000-12-31
- Before 1960 (classic films): release_date=,1960-12-31
- From 2000 onwards: release_date=2000-01-01,
- TV shows that started before 2000: release_date=,2000-12-31

### User Rating Filter (user_rating parameter)
- Highly rated (7+): user_rating=7.0,10.0
- Top rated (8+): user_rating=8.0,10.0

### Number of Votes Filter (num_votes parameter)
- Well known titles only: num_votes=1000,

### Color Filter (colors parameter)
- Black and white films ONLY: colors=black_and_white
- Color films only: colors=color

### Country of Origin (country_of_origin parameter)
Country codes (ISO 3166-1 alpha-2):
- United Kingdom: gb
- United States: us
- South Korea: kr
- Japan: jp
- France: fr
- Germany: de
- Italy: it
- Spain: es
- India: in
- Australia: au
- Brazil: br
- Mexico: mx
- Canada: ca
- Sweden: se
- Denmark: dk
- Norway: no

### Keyword Filter (keywords parameter)
- Based on true story: keywords=based-on-true-story
- Superhero: keywords=superhero
- Stephen King adaptation: keywords=stephen-king
- Marvel Cinematic Universe: keywords=marvel-cinematic-universe
- DC Extended Universe: keywords=dc-extended-universe
- World War II: keywords=world-war-ii&genres=documentary
- Based on novel: keywords=based-on-novel
- Villain protagonist: keywords=villain-protagonist

### Combining Filters — Full URL Examples
These are the most important combined examples:

Highest-rated war movies (1000+ votes, sorted by rating):
https://www.imdb.com/search/title/?genres=war&sort=user_rating,desc&num_votes=1000,

Top sci-fi movies sorted by rating and votes:
https://www.imdb.com/search/title/?genres=sci-fi&sort=user_rating,desc&num_votes=1000,

Horror movies sorted by rating:
https://www.imdb.com/search/title/?genres=horror&sort=user_rating,desc

Black and white classic films (before 1960, sorted by rating):
https://www.imdb.com/search/title/?colors=black_and_white&release_date=,1960-12-31&sort=user_rating,desc&num_votes=1000,

Classic black and white films (all years, sorted by rating):
https://www.imdb.com/search/title/?colors=black_and_white&sort=user_rating,desc&num_votes=1000,

Mini-series / limited series:
https://www.imdb.com/search/title/?title_type=tv_miniseries&sort=user_rating,desc

UK sci-fi TV series:
https://www.imdb.com/search/title/?title_type=tv_series&genres=sci-fi&country_of_origin=gb&sort=user_rating,desc

Short horror films from South Korea:
https://www.imdb.com/search/title/?title_type=short&genres=horror&country_of_origin=kr

South Korean horror films (all types):
https://www.imdb.com/search/title/?genres=horror&country_of_origin=kr&sort=user_rating,desc

WWII documentaries:
https://www.imdb.com/search/title/?genres=documentary&keywords=world-war-ii&sort=user_rating,desc

Stephen King film adaptations:
https://www.imdb.com/search/title/?keywords=stephen-king&title_type=feature&sort=user_rating,desc

Marvel Cinematic Universe movies:
https://www.imdb.com/search/title/?keywords=marvel-cinematic-universe&sort=year,asc

Movies based on novels sorted by rating:
https://www.imdb.com/search/title/?keywords=based-on-novel&sort=user_rating,desc

TV shows started before 2000 (release_date filter):
https://www.imdb.com/search/title/?title_type=tv_series&release_date=,2000-01-01&sort=user_rating,desc

IMPORTANT: IMDb advanced search does NOT have a direct filter for "number of seasons" or "still ongoing".
To find shows that started before 2000 and are still airing, use the URL above and look for shows still in production in the results.

## Finding Highest-Rated Episodes of a TV Show

To find the best-rated episode of a specific TV show (e.g. The Sopranos):
1. Search for the show in the search bar
2. Open the show page
3. Navigate to its episodes page: https://www.imdb.com/title/<tt_id>/episodes/
4. On the episodes page, each episode shows its IMDb rating
5. Browse across seasons to compare ratings

For The Sopranos (tt0141842) specifically:
- Episodes page: https://www.imdb.com/title/tt0141842/episodes/?season=1

Note: IMDb does not currently offer a direct URL to sort ALL episodes across all seasons by rating in one view.
The best approach is to check season by season.

## Multi-Person / Co-Appearance Search

To find movies where two specific people both appeared:
URL pattern: https://www.imdb.com/search/title/?role=<nm_id1>,<nm_id2>

Example — movies with both Tom Hanks (nm0000158) and Robin Wright (nm0000701):
https://www.imdb.com/search/title/?role=nm0000158,nm0000701

Known person IDs for co-appearance searches:
- Tom Hanks: nm0000158
- Robin Wright: nm0000701
- Brad Pitt: nm0000093
- Cate Blanchett: nm0000949
- Meryl Streep: nm0000658
- Robert De Niro: nm0000134
- Al Pacino: nm0000199
- Denzel Washington: nm0000243
- Julia Roberts: nm0000210
- Will Smith: nm0000226
- George Clooney: nm0000123
- Charlize Theron: nm0000234
- Tom Cruise: nm0000129
- Matt Damon: nm0000354

Navigation to find co-appearance:
1. Go to https://www.imdb.com/search/title/ (Advanced Title Search)
2. Use the People filter to enter both actor names
3. Or use the direct URL with role= parameter

## Franchise and Collection Search

For finding all movies in a franchise, use keyword search:
- Marvel Cinematic Universe: https://www.imdb.com/search/title/?keywords=marvel-cinematic-universe&sort=year,asc
- DC Extended Universe: https://www.imdb.com/search/title/?keywords=dc-extended-universe&sort=year,asc
- Star Wars franchise: https://www.imdb.com/search/title/?keywords=star-wars&title_type=feature&sort=year,asc
- James Bond franchise: https://www.imdb.com/search/title/?keywords=james-bond&title_type=feature&sort=year,asc
- Harry Potter franchise: https://www.imdb.com/search/title/?keywords=harry-potter&title_type=feature&sort=year,asc
- Lord of the Rings: https://www.imdb.com/search/title/?keywords=the-lord-of-the-rings&title_type=feature&sort=year,asc

Alternative: IMDb also maintains official franchise/series lists accessible from the franchise's main title page.

## Awards and Cross-Award Search

Award nominations and winners are tracked on:
- Awards Central overview: https://www.imdb.com/awards-central/
- Oscars (Academy Awards): https://www.imdb.com/oscars/
- BAFTA awards: https://www.imdb.com/event/ev0000123/
- Emmy awards: https://www.imdb.com/event/ev0000223/
- Golden Globe awards: https://www.imdb.com/event/ev0000292/

To find movies nominated for both an Oscar AND a BAFTA:
1. Go to https://www.imdb.com/awards-central/ for an overview
2. Use Advanced Title Search with: https://www.imdb.com/search/title/?groups=oscar_winner&sort=user_rating,desc
3. For BAFTA winners: https://www.imdb.com/search/title/?groups=bafta_winner
4. Cross-reference: look up https://www.imdb.com/event/ev0000003/ for Oscars and check BAFTA nominations for the same films

The groups parameter values:
- oscar_winner: Academy Award winners
- oscar_nominee: Academy Award nominees
- emmy_winner: Emmy winners
- golden_globe_winner: Golden Globe winners

## User Features — Mark as Watched / Check-In

To mark a movie as watched on IMDb (requires IMDb account sign-in):
1. Navigate to the movie's page: https://www.imdb.com/title/<tt_id>/
2. Look for the checkmark icon or "Mark as watched" button near the movie title
3. Click it — this adds it to your "Check-ins" list
4. Alternatively, go to your profile and Watchlist to add/remove items there

The "Mark as seen" / check-in feature:
- It appears as a small eye icon or checkmark on movie/TV show pages
- URL to your watchlist: https://www.imdb.com/watchlist
- Requires sign-in: https://www.imdb.com/registration/signin

## More Known Person IDs

Additional actors/directors for navigation:
- Keanu Reeves: nm0000206 → https://www.imdb.com/name/nm0000206/
- Laurence Fishburne: nm0000401 → https://www.imdb.com/name/nm0000401/
- Carrie-Anne Moss: nm0005251 → https://www.imdb.com/name/nm0005251/
- Christopher Nolan: nm0634240 → https://www.imdb.com/name/nm0634240/
- Leonardo DiCaprio: nm0000138 → https://www.imdb.com/name/nm0000138/
- Tom Hanks: nm0000158 → https://www.imdb.com/name/nm0000158/
- Robin Wright: nm0000701 → https://www.imdb.com/name/nm0000701/
- Meryl Streep: nm0000658 → https://www.imdb.com/name/nm0000658/
- Brad Pitt: nm0000093 → https://www.imdb.com/name/nm0000093/
- Cate Blanchett: nm0000949 → https://www.imdb.com/name/nm0000949/
- Robert De Niro: nm0000134 → https://www.imdb.com/name/nm0000134/
- Al Pacino: nm0000199 → https://www.imdb.com/name/nm0000199/
- Denzel Washington: nm0000243 → https://www.imdb.com/name/nm0000243/
- Clint Eastwood: nm0000142 → https://www.imdb.com/name/nm0000142/
- Steven Spielberg: nm0000229 → https://www.imdb.com/name/nm0000229/
- Quentin Tarantino: nm0000233 → https://www.imdb.com/name/nm0000233/
- Martin Scorsese: nm0000217 → https://www.imdb.com/name/nm0000217/
- James Cameron: nm0000116 → https://www.imdb.com/name/nm0000116/
- Tim Burton: nm0000318 → https://www.imdb.com/name/nm0000318/
- Ridley Scott: nm0000631 → https://www.imdb.com/name/nm0000631/
- Bryan Cranston: nm0186505 → https://www.imdb.com/name/nm0186505/
- Aaron Paul: nm0666739 → https://www.imdb.com/name/nm0666739/

## TV Shows with Episode Guide URLs

Known TV show episode pages (format: /title/<tt_id>/episodes/?season=<N>):
- Game of Thrones Season 1: https://www.imdb.com/title/tt0944947/episodes/?season=1
- Game of Thrones Season 2: https://www.imdb.com/title/tt0944947/episodes/?season=2
- Game of Thrones Season 3: https://www.imdb.com/title/tt0944947/episodes/?season=3
- Breaking Bad Season 1: https://www.imdb.com/title/tt0903747/episodes/?season=1
- Breaking Bad Season 2: https://www.imdb.com/title/tt0903747/episodes/?season=2
- The Sopranos Season 1: https://www.imdb.com/title/tt0141842/episodes/?season=1
- The Sopranos Season 2: https://www.imdb.com/title/tt0141842/episodes/?season=2
- Stranger Things Season 1: https://www.imdb.com/title/tt4574334/episodes/?season=1
- The Wire Season 1: https://www.imdb.com/title/tt0306414/episodes/?season=1
- The Simpsons Season 1: https://www.imdb.com/title/tt0096697/episodes/?season=1
- Friends Season 1: https://www.imdb.com/title/tt0108778/episodes/?season=1
- Lost Season 1: https://www.imdb.com/title/tt0411008/episodes/?season=1
- House M.D. Season 1: https://www.imdb.com/title/tt0412142/episodes/?season=1
- The Crown Season 1: https://www.imdb.com/title/tt4786824/episodes/?season=1
- Succession Season 1: https://www.imdb.com/title/tt7660850/episodes/?season=1

To find episode count for each season of any TV show:
1. Go to the show's episodes page: https://www.imdb.com/title/<tt_id>/episodes/
2. In the season selector at the top, each season number is listed
3. The count of episodes per season is shown in each season's listing

## Contributing and Reporting Errors
- IMDb Contribution Portal: https://contribute.imdb.com/
- To report incorrect info on a title page: navigate to the title, then click "Edit page" button (visible on most title pages)
- Alternatively use: https://contribute.imdb.com/updates
- To suggest a new title: https://contribute.imdb.com/ → click "Add a new title"
- NOTE: There is NO public "follow other users" feature on IMDb.

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
