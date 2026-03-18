import json
import re
from typing import Any

from graph_client import GraphClient
from ollama_client import chat
from vector_store import VectorStore


# ── Social greeting sanitiser ──────────────────────────────────────────────────
# Users often prefix navigation questions with greetings like
# "Hi, how are you, I hope you are well, Im here with my family and I want to
# know how to see the directors of The Matrix".
# Passing the full text to the LLM causes it to respond conversationally,
# producing empty `steps` and therefore no video.
#
# Strategy:
#   1. Look for "I want to know / I'd like to know / can you tell me" connector
#      and extract the navigation question that follows.
#   2. If not found, iteratively strip known leading-greeting patterns.

# Social connector that bridges preamble → actual question
_SOCIAL_CONNECTOR_RE = re.compile(
    r"(?:and\s+)?i(?:'?m|\s+am)?\s*(?:just\s+)?(?:want(?:ing)?|need(?:ing)?|would\s+like)\s+to\s+"
    r"(?:know|ask|find\s+out)\s+",
    re.IGNORECASE,
)

# Leading-greeting patterns stripped one at a time from the front
_LEADING_GREETING_PATTERNS = [
    re.compile(r"^(hi+|hello+|hey+|greetings?|howdy)[,!.?\s]+", re.IGNORECASE),
    re.compile(r"^how\s+(are\s+you|r\s+u)\b[^.!?,]*[.!?,]?\s*", re.IGNORECASE),
    re.compile(r"^i\s+hope\s+you(?:'?re?|\s+are)?[\w\s]+?[.,!]\s*", re.IGNORECASE),
    re.compile(r"^hope\s+you(?:'?re?|\s+are)?[\w\s]+?[.,!]\s*", re.IGNORECASE),
    re.compile(r"^i(?:'?m|am)\s+here(?:\s+with\s+[^,]+)?[,!.\s]+", re.IGNORECASE),
    re.compile(r"^im\s+here(?:\s+with\s+[^,]+)?[,!.\s]+", re.IGNORECASE),
    re.compile(r"^please\s+(?:tell|help|show)\s+me\s+", re.IGNORECASE),
    re.compile(r"^please[,!\s]+", re.IGNORECASE),
    re.compile(r"^can\s+you\s+(?:tell|help|please|show)\s+me\s+", re.IGNORECASE),
    re.compile(r"^could\s+you\s+(?:tell|help|please|show)\s+me\s+", re.IGNORECASE),
    re.compile(r"^tell\s+me\s+", re.IGNORECASE),
    re.compile(r"^i\s+(?:just\s+)?(?:want|need|would\s+like)\s+to\s+know\s+", re.IGNORECASE),
    re.compile(r"^and\s+i\s+(?:just\s+)?(?:want|need|would\s+like)\s+to\s+know\s+", re.IGNORECASE),
]


def _clean_question(question: str) -> str:
    """Strip social pleasantries from a question, returning the navigational core.
    Falls back to the original question if nothing meaningful remains."""
    text = question.strip()

    # Strategy 1: find "I want to know ..." connector and extract what follows.
    connector_match = _SOCIAL_CONNECTOR_RE.search(text)
    if connector_match:
        after = text[connector_match.end():].strip(" ,!.\t\n")
        if len(after) > 5:
            return after[:1].upper() + after[1:]

    # Strategy 2: iteratively strip leading greeting phrases.
    changed = True
    while changed:
        changed = False
        for pat in _LEADING_GREETING_PATTERNS:
            new = pat.sub("", text, count=1).strip(" ,!.\t\n")
            if new and new != text:
                text = new
                changed = True
                break

    result = text[:1].upper() + text[1:] if text else ""
    return result or question.strip()

# Title IDs verified to exist — any other tt-ID in a generated URL will be stripped
# so the recorder clicks from search results instead of navigating to a wrong page
# Default example title used when the LLM omits sub-page URLs
_DEFAULT_EXAMPLE_ID = "tt1375666"  # Inception

# Maps description keywords → sub-page URL suffix for click steps with no URL.
# The recorder already falls back to _goto when a click fails + has a URL — this
# ensures it always has one so it actually navigates instead of getting stuck.
_SUBPAGE_URL_MAP = {
    "review":        "/reviews/",
    "trivia":        "/trivia/",
    "goof":          "/goofs/",
    "quote":         "/quotes/",
    "parental":      "/parentalguide/",
    "location":      "/locations/",
    "full cast":     "/fullcredits/",
    "full crew":     "/fullcredits/",
    "award":         "/awards/",
    "box office":    "/business/",
    "budget":        "/business/",
    "soundtrack":    "/soundtrack/",
    "technical":     "/technical/",
    "spec":          "/technical/",
    "release":       "/releaseinfo/",
    "alternate title": "/releaseinfo/#akas",
    "aka":           "/releaseinfo/#akas",
    "plot":          "/plotsummary/",
    "connection":    "/movieconnections/",
    "keyword":       "/keywords/",
    "faq":           "/faq/",
    "social":        "/externalsites/",
    "official":      "/externalsites/",
    "filming":       "/locations/",
}

_VERIFIED_TITLE_IDS = {
    "tt0133093", "tt0234215", "tt0242653", "tt1375666", "tt0468569",
    "tt0816692", "tt0068646", "tt0111161", "tt0110912", "tt0109830",
    "tt4154796", "tt0499549", "tt0120338", "tt0099685", "tt0137523",
    "tt0102926", "tt0108052", "tt0088247", "tt0103064", "tt0078748",
    "tt0090605", "tt0107290", "tt0076759", "tt0110357", "tt0088763",
    # TV shows
    "tt0098904", "tt0903747", "tt0944947", "tt0108778", "tt0141842",
    "tt4574334", "tt0386676", "tt0306414",
    "tt0106004", "tt0096697", "tt0106179", "tt0411008",
    "tt0412142", "tt4786824", "tt7660850",
}


_INTENT_PROMPT = """You are an assistant that maps user questions to IMDb page titles.
Given a user question, extract:
1. A keyword for the START page (default: "Ratings, Reviews").
2. A keyword for the END page the user wants to reach.

Use EXACT words from real IMDb page titles. Examples of real IMDb page titles:
- "Top 250" → top-rated movies chart
- "Most popular movies" or "most popular right now" → moviemeter (trending movies)
- "Most popular TV shows" → TV show popularity chart (NOT videogamemeter)
- "Video game meter" or "most popular video games" → videogamemeter (ONLY when question is about video games)
- "Box office" → box office chart
- "Full cast & crew" or "Full credits" → cast/crew pages
- "User reviews" → movie review pages
- "Parental guide" → age ratings, content warnings
- "Filming locations" or "Filming & production" → where movies were filmed
- "Technical specs" → technical information
- "Release info" or "Release dates" → when/where movies were released
- "Awards" → movie award nominations page
- "Awards Central" → IMDb awards hub, Emmy, Oscar, Golden Globe, Cannes winners
- "Box office" → financial data
- "Plot summary" → storyline summaries
- "Photo gallery" or "mediaindex" → movie photos
- "Video gallery" or "Trailers" → video clips and trailers
- "External sites" or "Official website" → external links
- "Soundtrack" → music listings
- "Full credits" → complete cast and crew
- "Goofs" → movie mistakes
- "Trivia" or "Did You Know" → movie trivia
- "Quotes" → famous lines
- "Movie connections" → referenced in, spoofed by
- "Keywords" → movie keywords
- "Company credits" → production companies
- "Episode guide" or "Episodes" → TV show episode listings
- "Biography" → celebrity biography and birthdate
- "Filmography" → actor or director filmography
- "Upcoming releases" or "Calendar" → release calendar
- "Celebrity news" or "News" → IMDb news and editorial
- "STARmeter" → celebrity popularity rankings
- "Born Today" → celebrity birthdays today
- "Bottom 100" → lowest-rated movies
- "Video game" or "videogamemeter" → video game chart
- "Advanced search" or "search/title" → advanced filter search
- "Find" → title search

Respond ONLY with a valid JSON object:
{
  "start_state": "<keyword from IMDb page title>",
  "end_state": "<keyword from IMDb page title>"
}
Do not include any explanation outside the JSON object."""

# Used when the graph found a valid path
_ANSWER_WITH_PATH_PROMPT = """You are a helpful assistant guiding users through the IMDb website.

Rules:
- NEVER mention internal IDs like node_id or state_ strings
- Write ONE brief sentence summarising what the user will do
  (e.g. "Search for 'The Matrix' then open its Full Cast page.")
- Do NOT repeat each step — they are shown separately
- Be concise and action-oriented."""

# Used when graph had no path — produces answer + navigation steps in ONE call
_ANSWER_AND_STEPS_PROMPT = """You are a helpful assistant guiding users through the IMDb website.
You have access to IMDb context with URL patterns, movie IDs, and navigation flows.

Your response must be a JSON object with exactly two keys:
- "answer": a concise numbered step-by-step guide for the user (markdown allowed, include real URLs)
- "steps": a JSON array of navigation steps the recorder will execute

CRITICAL RULES — read carefully before responding:
- NEVER use Inception, The Dark Knight, or any other specific movie as an example UNLESS the user explicitly asked about that movie. For generic queries (genre filters, advanced search, franchise search, etc.) always use the URL patterns from the IMDb context — do NOT substitute a specific movie example.
- For genre/filter/advanced-search queries, ALWAYS use the relevant https://www.imdb.com/search/title/?... URL from the context. Do NOT navigate to a specific movie page.
- For filter queries (genre, year, language, rating, etc.) generate exactly TWO steps: (1) navigate to https://www.imdb.com/search/title/ and (2) navigate to the final combined filter URL. Use interaction_type "navigate" for BOTH — NEVER use search_query for filter parameters. The "answer" text MUST describe the UI actions in human terms — e.g. "On the left panel, click the **Genre** accordion header to expand it, click the **Documentary** chip (it highlights when selected), click the **Release date** accordion header, type **2020** in the 'from' year field and **2020** in the 'to' year field, then click the **See results** button at the top right." NEVER say "use the genres= parameter" or "set release_date=" — always describe the physical UI interaction with the accordion controls.
- For franchise queries (Marvel, MCU, Star Wars, James Bond, etc.), use the keyword search URL pattern from context.
- For multi-actor / co-appearance queries, use the role= URL pattern from context.
- For TV episode queries (e.g. best episode of a show), use the /episodes/?season= URL pattern from context.
- For award queries (Oscar, BAFTA, Emmy, Golden Globe), use the /awards-central/ and groups= URL patterns from context.
- For Cannes / Venice / Berlin / Sundance / festival award queries: IMDb does NOT have a groups= parameter for these festivals. Navigate to https://www.imdb.com/search/title/ and use keywords= (e.g. keywords=palme-d-or, keywords=golden-lion) or describe using the Awards & recognition filter accordion.
- For "mark as watched" / check-in queries, describe the eye/checkmark icon on the title page and the watchlist URL.
- For production company / studio queries (e.g. "movies by Pixar"): use https://www.imdb.com/find/?q=<company>&s=co to find the company, then navigate to their title page, OR use https://www.imdb.com/search/title/?companies=<co_id> if the company ID is known.
- For decade / era queries ("best movies of the 1980s", "films from the 1950s"): use release_date filter URL, e.g. https://www.imdb.com/search/title/?release_date=1980-01-01,1989-12-31&sort=user_rating,desc&num_votes=1000,
- For silent film / black-and-white / era queries: combine release_date (e.g. 1920-1929) with colors=black_and_white.
- For keyword searches ("movies with keyword 'artificial intelligence'"): use https://www.imdb.com/search/title/?keywords=<keyword> with the keyword in slug form.
- For Stephen King / book adaptation queries: use https://www.imdb.com/search/title/?keywords=stephen-king or keywords=based-on-novel.
- For "director who also acted / wrote / starred": use the role= URL with the person's nm-ID. If unknown, search for the person first.
- For editorial/news content: navigate to https://www.imdb.com/news/movie/ for movie news and editorial picks.
- For "sort by release date / rating" queries: use https://www.imdb.com/search/title/?sort=year,desc (newest first — IMDb uses `year` as the release date sort field) or sort=user_rating,desc (highest rated first).
- For children's / parental guide filter queries: use https://www.imdb.com/search/title/?certificates=US:G or certificates=US:PG and describe using the US certificates accordion.
- For "reviews sorted by helpfulness": navigate to a title's /reviews/ page and use the sort dropdown — the URL param is ?sort=helpfulnessScore&dir=desc.

Rules for "answer":
- ALWAYS describe the navigation as a sequence of human actions (click, search, scroll) — not just a URL
- Each step should describe what the user sees and does: e.g. "Search for 'Frasier' in the search bar", "Click the TV series result", "Click the 'Episodes' tab", "Select Season 1 from the dropdown"
- You MAY include a direct URL at the end of the relevant step as a shortcut reference, but it must NOT replace the human description
- ONLY use URLs and IMDb title IDs (ttXXXXXXX) that are EXPLICITLY listed in the IMDb context provided
- NEVER guess or invent a title ID — describe the navigation instead
- For language/country searches, use: https://www.imdb.com/search/title/?languages=<code>&sort=year,desc
- For advanced filter searches, build the URL from the parameter patterns listed in the IMDb context

Rules for "steps":
- The steps array MUST have exactly one entry per numbered step in "answer" — they must match 1-to-1
- "description": short label matching that answer step
- "url": ONLY use URLs from the IMDb context — leave "" if unknown
- NEVER invent a title ID (ttXXXXXXX) not in the context — use a click step with "" url instead
- "action":
  - "interaction_type": "search_query" when the step is a search, "click" when clicking a button/link, "navigate" when going to a direct URL
  - "target_element_id": for search_query put the SEARCH TERM, for click put the visible label text, for navigate use null
- For search_query steps, target_element_id MUST be a real specific name (e.g. "The Matrix", "Tom Hanks") — NEVER a placeholder like "the movie title" or "the actor name"
- For the first step of any search/lookup question, use a search_query step with a real example term
- For click steps that open a sub-section of a title page (reviews, trivia, quotes, parental guide, awards, etc.) ALWAYS include the full URL from the sub-page patterns in the context — do NOT leave url empty
- Bottom 100 / lowest-rated movies chart: https://www.imdb.com/chart/bottom/ (NOT /chart/top/)
- IMDb Contribution Portal: https://contribute.imdb.com/ (for reporting errors or adding titles)
- IMDb does NOT have a "Top 10", "Top 20", "Top 50", or "Top 100" chart. The only ranked chart is "Top 250" at https://www.imdb.com/chart/top/ — always redirect "top N" queries there and explain this clearly.
- CRITICAL URL parameter rules — NEVER invent parameters:
  - Country filter: use `country_of_origin=<code>` (e.g. `country_of_origin=jp` for Japan). NEVER use `country=` or `countries=`.
  - Company/studio filter: use `companies=<co_id>` with the IMDb company ID (e.g. `companies=co0048420` for Studio Ghibli, `companies=co0017902` for Pixar). NEVER use `production_company=` or `studio=`.
  - Title type: use `title_type=feature` (NOT `featurefilm` or `movie`), `title_type=tv_miniseries` (NOT `mini_series`).
  - Year/date filter: use `release_date=YYYY-MM-DD,YYYY-MM-DD` with full ISO dates. NEVER use `year=` or short `release_date=2010,2023`.
  - Awards filter: use `groups=oscar_winners` (plural). NEVER use `oscar_winner` (singular).
  - There is NO `studio=`, `director=`, `actor=`, `genre=`, `language=`, `rating=`, `votes=`, or `type=` URL parameter.

Example — answer has 3 steps, steps array has exactly 3 entries:
{
  "answer": "1. Search for 'The Matrix' in the search bar\\n2. Click the movie result to open its page\\n3. Click 'Full cast & crew' to see all actors (https://www.imdb.com/title/tt0133093/fullcredits/)",
  "steps": [
    {"description": "Search for The Matrix", "url": "https://www.imdb.com/find/?q=The+Matrix&s=tt", "action": {"interaction_type": "search_query", "target_element_id": "The Matrix"}},
    {"description": "The Matrix movie page", "url": "https://www.imdb.com/title/tt0133093/", "action": {"interaction_type": "navigate", "target_element_id": null}},
    {"description": "Full cast & crew", "url": "https://www.imdb.com/title/tt0133093/fullcredits/", "action": {"interaction_type": "navigate", "target_element_id": null}}
  ]
}"""


# Words to strip when extracting a film/show title from an LLM end-state description.
# Whatever remains after dropping these is treated as the subject title the user asked about.
_TITLE_DROP_WORDS = {
    "page", "movie", "film", "show", "series", "cast", "crew", "awards",
    "trivia", "reviews", "review", "credits", "full", "imdb", "title", "the",
    "and", "a", "an", "how", "find", "navigate", "go", "get", "episodes",
    "season", "information", "details", "rating", "ratings", "biography",
    "filmography", "home", "tv", "television", "their", "this", "that",
    "with", "from", "into", "some", "more", "also", "then", "list",
    "about", "using", "only", "another", "other", "same", "just",
    "specific", "release", "date", "year", "plot", "summary", "overview",
    # Common question/preposition words that must not be mistaken for title words
    "for", "are", "you", "can", "see", "not", "want", "know", "look",
    "what", "where", "which", "does", "will", "its", "all", "was", "has",
    "had", "him", "her", "his", "one", "two", "our", "out", "new", "way",
    "use", "now", "old", "any", "who", "why", "did", "but", "via", "per",
    "the", "is", "it", "be", "at", "on", "by", "or", "as", "if", "do",
    "to", "in", "of", "up", "me", "my", "we", "us", "so", "no",
    "section", "tab", "link", "button", "menu", "site", "web", "url",
}


def _extract_subject_title(end_description: str) -> str:
    """Extract the subject film/show name from an LLM-extracted end state description.

    Strips common navigation/UI terms; returns remaining words as the title candidate.
    Returns empty string for generic queries (no specific title to extract).
    """
    words = re.findall(r"[a-zA-Z']+", end_description)
    candidates = [w for w in words if w.lower() not in _TITLE_DROP_WORDS and len(w) > 2]
    return " ".join(candidates[:3]) if candidates else ""


class QueryChain:
    def __init__(self, vector_store: VectorStore, graph_client: GraphClient) -> None:
        self._vector_store = vector_store
        self._graph_client = graph_client

    def run(self, question: str) -> dict[str, Any]:
        # Strip social pleasantries before any LLM call so the model focuses on
        # the navigation intent rather than responding conversationally.
        nav_question = _clean_question(question)

        # 1. Extract intent (LLM call #1)
        intent_raw = chat(
            [{"role": "system", "content": _INTENT_PROMPT},
             {"role": "user", "content": f"User question: {nav_question}"}],
            response_format="json",
        )
        try:
            intent_raw = re.sub(r"<think>.*?</think>", "", intent_raw, flags=re.DOTALL).strip()
            intent = json.loads(intent_raw)
            start_description = intent.get("start_state", "")
            end_description = intent.get("end_state", "")
        except (json.JSONDecodeError, AttributeError):
            start_description = ""
            end_description = nav_question

        # 2. Query graph for a path
        steps: list[dict[str, Any]] = []
        if start_description and end_description:
            steps = self._graph_client.find_path(start_description, end_description)

        # Detect graph miss: no steps, generic search fallback, or path doesn't relate to intent
        graph_miss = not steps or (
            len(steps) == 1
            and "find" in steps[0].get("node_id", "").lower()
            and steps[0].get("synthetic") is not True
        )

        # Miss if all steps have null interaction_type — means no real edge traversal (no path found,
        # just a destination node returned by _search_fallback or a single-node match)
        if not graph_miss and steps and all(
            s.get("action", {}).get("interaction_type") is None for s in steps
        ):
            graph_miss = True

        # Also a miss if the last step's description doesn't match the end intent at all
        if not graph_miss and end_description and steps:
            last_desc = steps[-1].get("description", "").lower()
            intent_words = [w for w in end_description.lower().split() if len(w) > 3]
            if intent_words and not any(w in last_desc for w in intent_words):
                graph_miss = True

        # Graph hit but path passes through podcast / video-game nodes.
        # The fuzzy matcher picks podcast_series or videogamemeter nodes when
        # queries contain words like "keyword", "type", "popular", "series".
        # Check EVERY step (not just the last) so partial paths are caught.
        if not graph_miss and steps:
            _WRONG_TYPE_MARKERS = ("podcast", "videogame", "video_game", "videogamemeter")
            for step in steps:
                step_blob = step.get("url", "").lower() + " " + step.get("description", "").lower()
                if any(m in step_blob for m in _WRONG_TYPE_MARKERS):
                    graph_miss = True
                    break

        # Detect when the graph path visits a specific title that is NOT what the user
        # asked about — regardless of whether the path went through a /chart/ hub or a
        # direct edge.  This covers both:
        #   • home → /chart/top/ → Inception → trivia   (hub detour)
        #   • home → Inception → trivia                 (direct wrong-title path)
        #
        # Strategy — ADAPT the path instead of a full graph miss:
        #   1. Extract the subject title the user asked about (from end_description).
        #   2. Check whether that subject appears anywhere in the path steps.
        #   3. If not → path is using the wrong example title → build an adapted path:
        #        search for subject → click first result → reuse sub-page click steps
        #      Sub-page steps (e.g. /trivia, /awards) are converted to click-by-text so
        #      they work on any title page the recorder lands on after the search.
        # Guard: don't adapt for chart/ranking queries — the chart path IS the answer.
        if not graph_miss and steps:
            # Try end_description first (LLM-extracted intent); fall back to the cleaned
            # question itself.  The LLM often outputs a generic end state like "trivia page"
            # without including the title name, so the question is the more reliable source.
            subject = _extract_subject_title(end_description) or _extract_subject_title(nav_question)
            if subject:
                has_title_page = any(
                    re.search(r"/title/tt\d+", step.get("url", "") or "")
                    for step in steps
                )
                if has_title_page:
                    _CHART_GUARD_WORDS = (
                        "top 250", "top rated", "highest rated", "chart", "ranking",
                        "best movie", "best film", "best tv", "top tv",
                    )
                    q_wants_chart = any(kw in question.lower() for kw in _CHART_GUARD_WORDS)
                    if not q_wants_chart:
                        # Check if subject words appear in any step description or URL
                        subject_words = [w for w in subject.lower().split() if len(w) > 2]
                        subject_in_path = any(
                            any(
                                w in (s.get("description", "") or "").lower()
                                or w in (s.get("url", "") or "").lower()
                                for w in subject_words
                            )
                            for s in steps
                        )
                        if not subject_in_path:
                            # Path uses a different title — adapt it.
                            # Map sub-page path segments to visible IMDb link text so the
                            # recorder can click by text on any title page.
                            _SUBPAGE_LABELS: dict[str, str] = {
                                "fullcredits": "Full Cast & Crew",
                                "trivia": "Trivia",
                                "awards": "Awards",
                                "reviews": "User Reviews",
                                "ratings": "Ratings",
                                "plotsummary": "Plot Summary",
                                "soundtrack": "Soundtrack",
                                "goofs": "Goofs",
                                "quotes": "Quotes",
                                "parentalguide": "Parents Guide",
                                "episodes": "Episodes",
                                "releaseinfo": "Release Info",
                                "companycredits": "Company Credits",
                                "technical": "Technical Specs",
                                "keywords": "Keywords",
                            }
                            # Find the first title-specific step index
                            title_start = next(
                                (i for i, s in enumerate(steps)
                                 if re.search(r"/title/tt\d+", s.get("url", "") or "")),
                                None,
                            )
                            post_title: list[dict[str, Any]] = []
                            for s in steps[title_start:] if title_start is not None else []:
                                url = s.get("url", "") or ""
                                sub_match = re.search(r"/title/tt\d+/([^/?#]+)", url)
                                if sub_match:
                                    # Sub-page → click-by-text (works on any title page)
                                    sub_path = sub_match.group(1).lower()
                                    label = _SUBPAGE_LABELS.get(sub_path, sub_path.title())
                                    post_title.append({
                                        "description": f"Click {label}",
                                        "url": "",
                                        "action": {
                                            "interaction_type": "click",
                                            "target_element_id": label,
                                        },
                                        "node_id": "",
                                        "synthetic": True,
                                    })
                                elif re.search(r"/title/tt\d+/?$", url):
                                    # Bare title page — covered by click_result_step, skip
                                    continue
                                else:
                                    post_title.append(dict(s))
                            search_step: dict[str, Any] = {
                                "description": f"Search for {subject} on IMDb",
                                "url": (
                                    "https://www.imdb.com/find/?q="
                                    + subject.replace(" ", "+")
                                    + "&s=tt"
                                ),
                                "action": {
                                    "interaction_type": "search_query",
                                    "target_element_id": subject,
                                },
                                "node_id": "",
                                "synthetic": True,
                            }
                            # Explicit step to land on the title page from /find/.
                            # Without this, the recorder consumes the first post_title
                            # click step to auto-navigate away from /find/, leaving
                            # the actual sub-page interaction unexecuted.
                            # Friendly target — _click_first_find_result handles the
                            # actual selector logic when the recorder sees /find/ in the URL.
                            click_result_step: dict[str, Any] = {
                                "description": f"Click on {subject} in search results",
                                "url": "",
                                "action": {
                                    "interaction_type": "click",
                                    "target_element_id": f"{subject} search result",
                                },
                                "node_id": "",
                                "synthetic": True,
                            }
                            # Replace steps[0] with a clean home navigate step.
                            # The original steps[0] carries the graph edge action
                            # (e.g. "click Top 250 Movies") which would fire before
                            # the search, sending the recorder to the wrong page.
                            home_step: dict[str, Any] = {
                                "description": "IMDb home page",
                                "url": "https://www.imdb.com/",
                                "action": {
                                    "interaction_type": "navigate",
                                    "target_element_id": None,
                                },
                                "node_id": steps[0].get("node_id", ""),
                                "synthetic": True,
                            }
                            steps = [home_step, search_step, click_result_step] + post_title

        # Graph hit but ALL steps have null interaction_type — partial null check.
        # Already caught if ALL are null above; also miss if MOST are null (≥ 60%),
        # which indicates the graph returned a disconnected node list rather than
        # a real traversal path.
        if not graph_miss and steps and len(steps) > 2:
            null_count = sum(
                1 for s in steps
                if s.get("action", {}).get("interaction_type") is None
            )
            if null_count / len(steps) >= 0.6:
                graph_miss = True

        # Graph hit but path is too long (> 10 steps) — very long indirect paths
        # are almost always caused by the fuzzy matcher anchoring on a generic
        # keyword in an unrelated node.  Cap at 10 to force a cleaner LLM answer.
        if not graph_miss and len(steps) > 10:
            graph_miss = True

        # Force miss for queries the graph cannot answer — language/country, advanced
        # parametric filters, franchise collections, multi-actor co-appearance,
        # cross-award searches, and account-level features.
        # IMPORTANT: keep this list NARROW — only force-miss when the graph truly cannot
        # produce a useful path. Over-broad keywords block valid graph paths.
        _FORCE_MISS_KEYWORDS = {
            # ── Language / nationality filters ───────────────────────────────────────
            # Graph has no language= or country_of_origin= filter nodes
            "spanish", "french film", "italian film", "german film",
            "japanese film", "korean film", "chinese film", "portuguese",
            "russian film", "arabic film", "hindi", "turkish film",
            "swedish film", "danish film", "norwegian film", "polish film", "dutch film",
            "bollywood", "south korea", "united kingdom", "british film",
            "from spain", "from france", "from brazil", "from mexico",
            "from italy", "from germany", "from japan", "from korea",
            "in spanish", "in french", "in italian", "in portuguese",
            "in japanese", "in korean", "in hindi", "in arabic",
            "neo-realist", "italian cinema", "french cinema", "german cinema",
            # ── Franchise / collection searches ──────────────────────────────────────
            "marvel cinematic", "mcu film", "dc extended", "dceu",
            "james bond film", "harry potter film", "lord of the rings film",
            "star wars film",
            # ── Keyword-based searches (use keywords= URL param) ─────────────────────
            "stephen king", "based on novel", "based on book", "film adaptation",
            "all adaptations", "novels on imdb", "book adaptation",
            # ── Multi-actor / co-appearance ───────────────────────────────────────────
            "co-star", "co-appear", "appeared together", "starring both",
            "films with both", "movies with both actors", "same two actors",
            # ── Director who also acted (use role= URL param) ─────────────────────────
            "director also appears", "director who also acted", "directed and starred",
            "directed by.*actor", "director.*also act", "wrote, directed, and starred",
            "same person wrote", "wrote directed starred",
            # ── Cross-award multi-criteria ─────────────────────────────────────────────
            "oscar and bafta", "oscar & bafta", "bafta and oscar",
            "emmy and golden", "multiple award winner", "multiple award nominee",
            "cross-award", "won both oscar",
            # ── Non-IMDb-group festival awards (no groups= param for these) ────────────
            "cannes", "palme d'or", "palme dor", "venice film festival",
            "berlin film festival", "sundance", "golden lion", "silver bear",
            # ── Production company / studio search ───────────────────────────────────
            "produced by a specific", "production company", "movies produced by",
            "films produced by", "movies from studio", "films from studio",
            "studio behind", "made by pixar", "made by a24", "made by marvel",
            # ── Mark as watched / personal account features ───────────────────────────
            "mark as watched", "mark as seen", "check-in", "checkin",
            "watched list", "seen list", "add to watched",
            # ── Ongoing / status queries ──────────────────────────────────────────────
            "still ongoing", "still airing", "still running",
            # ── Generic person lookup (use search steps, not graph path) ─────────────
            "find an actor", "find a director", "find an actress", "find a writer",
            "find a person", "search for an actor", "search for a director",
            "look up a person", "look up someone", "find someone on imdb",
            "find a tv show", "search for a tv show", "find a show",
            # ── Generic "how to search" — no specific graph destination ───────────────
            "how do i search", "search for a movie", "search for a tv show",
            "find out what year", "what year a movie",
            "birthday of a celebrity", "celebrities born on",
            # ── Decade / era searches (need release_date filter URL) ──────────────────
            "decade", "1920s", "1930s", "1940s", "1950s", "1960s", "1970s",
            "1980s", "1990s", "2000s", "2010s", "2020s",
            "from the 50s", "from the 60s", "from the 70s", "from the 80s",
            "from the 90s", "best of each decade",
            # ── Silent / vintage / era-specific films ─────────────────────────────────
            "silent film", "silent era", "black and white film",
            # ── Genre/type/style filters (need parametric URL, graph has no specific node) ─
            # Graph has only a generic Genre browse page — specific queries need filter URLs
            "horror", "war movie", "war film", "sci-fi", "science fiction",
            "documentary", "animation genre", "thriller genre",
            "black and white", "black & white", "b&w", "monochrome",
            "mini-series", "miniseries", "limited series",
            "short film", "short horror", "films under 30",
            "only tv movies", "only feature films", "only theatrical",
            "animated movie", "animated film", "g rating", "rated g",
            "suitable for children", "suitable for young", "appropriate for kids",
            "children under", "parental guide rating",
            # ── Actor/director + genre combos (need parametric search URL) ────────────
            "movies starring", "films starring", "movies featuring", "films featuring",
            "tv shows starring", "shows starring", "series starring",
            "directed by a specific", "movies directed by", "films directed by",
            # ── Genre browsing (needs accordion UI interaction, not just /search/title/) ─
            "browse by genre", "browse movies by genre", "browse films by genre",
            "filter by genre", "search by genre", "find movies by genre",
            # ── Biographical / keyword genre searches ─────────────────────────────────
            "biopic", "biographical film", "biographical movie", "based on a true story",
            "about musicians", "about athletes", "about politicians", "about scientists",
            # ── Bottom 100 / worst-rated (LLM confuses with Top 250) ─────────────────
            "bottom 100", "lowest-rated movies", "worst rated movies", "lowest rated movies",
            # ── Keyword-based search queries ──────────────────────────────────────────
            "search by keyword", "filter by keyword", "movies with keyword",
            "keyword search", "by keyword",
            # ── Sort / order queries (not a graph state, needs search URL with sort=) ──
            "sort by release date", "sort by rating", "newest first", "oldest first",
            "sorted by", "order by release", "most recent first",
            # ── Remake searches ────────────────────────────────────────────────────────
            "foreign language remake", "language remake", "remake of",
            "american remake", "original and the remake",
            # ── Editorial / news content ──────────────────────────────────────────────
            "editorial pick", "featured article", "editorial content",
            "imdb editorial", "browse articles", "imdb news article",
            # ── User review sorting ────────────────────────────────────────────────────
            "reviews sorted by helpfulness", "sort reviews by", "most helpful review",
            "sorted by helpfulness", "helpful review sort",
            # ── Actor least-known / obscure filmography ───────────────────────────────
            "least-known film", "lowest-rated film of", "least known movie of",
            "obscure film of an actor", "actor's worst film",
            # ── Streaming availability — no graph nodes ──────────────────────────────
            "available to stream", "streaming on", "watch on ",
            "amazon prime", "netflix", "disney+", "hulu", "streaming service",
            "where to watch", "connect my imdb account to amazon",
            "link imdb to amazon", "imdb to amazon prime",
            # ── Rating actions (not navigation) ──────────────────────────────────────
            "how do i rate", "rate a movie", "rate this movie", "give a rating",
            "submit a rating", "rating a title",
            # ── Episode/season COUNT queries (not navigation) ─────────────────────────
            "episode count", "how many episodes in", "episodes per season",
            "seasons and episodes count", "number of episodes in",
            # ── Social / follow features ──────────────────────────────────────────────
            "follow other users", "follow user", "follow list",
            # ── Account sign-in / login (not a navigable IMDb page path) ─────────────
            "sign in", "log in", "login", "sign into my", "sign into imdb",
            "imdb account", "create an account", "register account",
            "connect my imdb", "link my imdb",
        }
        q_lower = nav_question.lower()
        if not graph_miss and any(kw in q_lower for kw in _FORCE_MISS_KEYWORDS):
            graph_miss = True

        # 3. Retrieve IMDb context chunks (use cleaned question for better embedding match)
        rag_chunks = self._vector_store.search(nav_question, k=8)
        context_text = "\n\n".join(c["text"] for c in rag_chunks) if rag_chunks else ""

        if not graph_miss:
            # Graph hit: short summary only (LLM call #2)
            path_text = self._format_path_for_llm(steps)
            answer = chat(
                [{"role": "system", "content": _ANSWER_WITH_PATH_PROMPT},
                 {"role": "user", "content": f"User question: {nav_question}\n\nNavigation path:\n{path_text}"}],
            ).strip()
        else:
            # Graph miss: combined answer + steps in ONE call (LLM call #2)
            combined_raw = chat(
                [{"role": "system", "content": _ANSWER_AND_STEPS_PROMPT},
                 {"role": "user", "content": f"IMDb context:\n{context_text}\n\nUser question: {nav_question}"}],
                response_format="json",
            )
            combined = self._parse_json_object(combined_raw)
            answer = combined.get("answer", "")
            steps = self._build_steps(combined.get("steps", []))
            # Fallback: if the LLM returned an answer but no parseable steps,
            # generate a minimal search step so the recorder at least visits IMDb
            # and shows the search bar rather than producing no video at all.
            if not steps and answer:
                steps = self._build_steps([{
                    "description": "Search on IMDb",
                    "url": "https://www.imdb.com/search/title/",
                    "action": {"interaction_type": "navigate", "target_element_id": None},
                }])

        start_node_id = steps[0].get("node_id", "") if steps else ""
        end_node_id = steps[-1].get("node_id", "") if steps else ""

        return {
            "answer": answer,
            "steps": steps,
            "start_node_id": start_node_id,
            "end_node_id": end_node_id,
            "intent": {
                "start_state": start_description,
                "end_state": end_description,
            },
            "graph_miss": graph_miss,
            "synthetic_steps": graph_miss and len(steps) > 0,
        }

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, AttributeError):
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, AttributeError):
                pass
        return {}

    def _build_steps(self, raw_steps: list) -> list[dict[str, Any]]:
        if not isinstance(raw_steps, list):
            return []
        steps = []
        for i, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            url = item.get("url", "") or ""

            # Replace generic placeholder tokens so the recorder can navigate to real pages.
            # tt placeholders → Inception (tt1375666); nm placeholders → Bryan Cranston (nm0186505)
            url = re.sub(r"<(tt_id|movie_id|title_id|tt\w*id\w*)>", "tt1375666", url, flags=re.IGNORECASE)
            url = re.sub(r"<(nm_id|actor_id|person_id|nm\w*id\w*)>", "nm0186505", url, flags=re.IGNORECASE)
            action = item.get("action") or {}
            itype = action.get("interaction_type")
            target = action.get("target_element_id") or ""
            description = item.get("description", f"Step {i + 1}")

            # Strip any title URL where the tt-ID is not in our verified list
            tt_match = re.search(r"/title/(tt\d+)", url)
            url_scrubbed = tt_match and tt_match.group(1) not in _VERIFIED_TITLE_IDS
            if url_scrubbed:
                url = ""
                # Convert navigate→click so recorder finds the link by visible text
                if itype == "navigate" and not target:
                    itype = "click"
                    # Use a cleaned-up version of the description as the click target
                    target = re.sub(
                        r"\s*(movie page|tv show page|title page|series page)\s*$",
                        "", description, flags=re.IGNORECASE
                    ).strip()

            # contribute.imdb.com deep paths 404 — land on the portal home instead
            if url and "contribute.imdb.com" in url and len(url) > len("https://contribute.imdb.com/"):
                url = "https://contribute.imdb.com/"

            # Correct Bottom 100 chart hallucination: LLM sometimes uses /chart/top/
            # for questions about lowest-rated / worst movies
            if url and "/chart/top/" in url:
                desc_lower = description.lower()
                if any(kw in desc_lower for kw in ("bottom", "worst", "lowest")):
                    url = "https://www.imdb.com/chart/bottom/"

            # For click steps that navigate to a title sub-page but have no URL,
            # infer the URL from the description so the recorder can _goto as fallback.
            # GUARD: skip this inference for filter/search/browse steps — injecting
            # the Inception example URL onto a "filter by genre" step causes the
            # recorder to visit Inception's subpage instead of a search results page.
            _SUBPAGE_FILTER_INDICATORS = {
                "filter", "search", "find", "sort", "browse", "decade", "genre",
                "year", "rating", "language", "type", "documentary", "animated",
                "animated film", "release date", "newest", "oldest", "popular",
                "chart", "list", "all movies", "all films", "oscar", "bafta",
                "emmy", "grammy", "festival", "cannes", "palme", "silent film",
                "1920", "1930", "1940", "1950", "select", "apply", "results",
            }
            if itype == "click" and not url:
                desc_lower = description.lower()
                is_filter_step = any(ind in desc_lower for ind in _SUBPAGE_FILTER_INDICATORS)
                if not is_filter_step:
                    for kw, path_suffix in _SUBPAGE_URL_MAP.items():
                        if kw in desc_lower:
                            url = f"https://www.imdb.com/title/{_DEFAULT_EXAMPLE_ID}{path_suffix}"
                            break

            steps.append({
                "node_id": f"synthetic_{i}",
                "url": url,
                "description": description,
                "action": {
                    "interaction_type": itype,
                    "target_element_id": target or None,
                },
                "synthetic": True,
            })
        return steps

    def _format_path_for_llm(self, steps: list[dict[str, Any]]) -> str:
        if not steps:
            return "No navigation path found in the graph for this query."
        lines = []
        for i, step in enumerate(steps):
            description = step.get("description", "Unknown state")
            url = step.get("url", "")
            action = step.get("action", {})
            interaction = (action or {}).get("interaction_type", "")
            element = (action or {}).get("target_element_id", "")
            line = f"Step {i + 1}: {description}"
            if url:
                line += f" ({url})"
            if interaction and element and not element.startswith("state_"):
                line += f" — {interaction} on '{element}'"
            lines.append(line)
        return "\n".join(lines)
