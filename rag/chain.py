import json
import re
from typing import Any

from graph_client import GraphClient
from ollama_client import chat
from vector_store import VectorStore

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


_INTENT_PROMPT = """You are an assistant that understands user intent on IMDb.
Given a user question, extract:
1. A keyword for the START page the user is likely on (default: "Ratings, Reviews").
2. A keyword for the END page the user wants to reach.

Use keywords that would appear in an IMDb page title. Examples:
- "Top 250" for the top movies list
- "Most popular" for popular movies
- "Box office" for box office charts
- "Full cast" for cast pages
- "User reviews" for review pages
- "Upcoming releases" for release calendar
- "Genre" for genre browsing

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
- For franchise queries (Marvel, MCU, Star Wars, James Bond, etc.), use the keyword search URL pattern from context.
- For multi-actor / co-appearance queries, use the role= URL pattern from context.
- For TV episode queries (e.g. best episode of a show), use the /episodes/?season= URL pattern from context.
- For award queries (Oscar, BAFTA, Emmy, Golden Globe), use the /awards-central/ and groups= URL patterns from context.
- For "mark as watched" / check-in queries, describe the eye/checkmark icon on the title page and the watchlist URL.

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

Example — answer has 3 steps, steps array has exactly 3 entries:
{
  "answer": "1. Search for 'The Matrix' in the search bar\\n2. Click the movie result to open its page\\n3. Click 'Full cast & crew' to see all actors (https://www.imdb.com/title/tt0133093/fullcredits/)",
  "steps": [
    {"description": "Search for The Matrix", "url": "https://www.imdb.com/find/?q=The+Matrix&s=tt", "action": {"interaction_type": "search_query", "target_element_id": "The Matrix"}},
    {"description": "The Matrix movie page", "url": "https://www.imdb.com/title/tt0133093/", "action": {"interaction_type": "navigate", "target_element_id": null}},
    {"description": "Full cast & crew", "url": "https://www.imdb.com/title/tt0133093/fullcredits/", "action": {"interaction_type": "navigate", "target_element_id": null}}
  ]
}"""


class QueryChain:
    def __init__(self, vector_store: VectorStore, graph_client: GraphClient) -> None:
        self._vector_store = vector_store
        self._graph_client = graph_client

    def run(self, question: str) -> dict[str, Any]:
        # 1. Extract intent (LLM call #1)
        intent_raw = chat(
            [{"role": "system", "content": _INTENT_PROMPT},
             {"role": "user", "content": f"User question: {question}"}],
            response_format="json",
        )
        try:
            intent_raw = re.sub(r"<think>.*?</think>", "", intent_raw, flags=re.DOTALL).strip()
            intent = json.loads(intent_raw)
            start_description = intent.get("start_state", "")
            end_description = intent.get("end_state", "")
        except (json.JSONDecodeError, AttributeError):
            start_description = ""
            end_description = question

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

        # Miss if the question asks about a SPECIFIC title/person but the path goes through a
        # DIFFERENT one (e.g. user asks about Titanic but graph returns an Inception path).
        # For generic "how do I find X" questions with no specific title, allow paths through
        # known titles — they demonstrate the navigation pattern as a valid example.
        if not graph_miss and steps:
            q_lower = question.lower()
            _SPECIFIC_TITLES = ["inception", "the matrix", "dark knight", "godfather", "shawshank",
                                 "breaking bad", "game of thrones", "frasier", "tt1375666", "tt0133093"]
            q_has_specific_title = any(t in q_lower for t in _SPECIFIC_TITLES)
            if q_has_specific_title:
                # User named a specific title — path must not go through a different known title
                for title in _SPECIFIC_TITLES:
                    if title not in q_lower:
                        for step in steps:
                            if title in step.get("description", "").lower() or title in step.get("url", "").lower():
                                graph_miss = True
                                break
                    if graph_miss:
                        break
            # else: generic question — a path through Inception/Matrix is a valid example, keep it

        # Force miss for queries the graph cannot answer — language/country, advanced filters,
        # franchise/collection, cross-award, multi-actor co-appearance, show-specific episode rankings,
        # genre filters, colour filters, keyword searches, and "mark as watched" user features
        _FORCE_MISS_KEYWORDS = {
            # Language / nationality
            "spanish", "french", "italian", "german", "japanese", "korean",
            "chinese", "portuguese", "russian", "arabic", "hindi", "turkish",
            "swedish", "danish", "norwegian", "polish", "dutch",
            "mexico", "spain", "france", "italy", "germany", "brazil",
            "south korea", "united kingdom", "british", "uk ",
            # Genre filter queries
            "horror", "war movie", "war film", "sci-fi", "science fiction",
            "documentary", "mini-series", "miniseries", "limited series",
            "short film", "short horror",
            # Colour / visual style filters
            "black and white", "black & white", "b&w", "monochrome",
            # Advanced multi-criteria / combined filters
            "highest rated", "top rated", "sorted by rating", "sort by rating",
            "best rated", "most voted", "filter by", "search filter",
            # Franchise / collection
            "franchise", "marvel", "mcu", "dc extended", "dceu",
            "star wars", "james bond", "harry potter", "lord of the rings",
            "stephen king", "based on novel", "based on book",
            # Multi-actor / co-appearance
            "both ", "co-star", "co-appear", "appeared together", "movies with both",
            "films with both", "starring both",
            # Cross-award searches
            "oscar and bafta", "oscar & bafta", "bafta and oscar",
            "emmy and", "golden globe and", "award winner", "award nominee",
            "cross-award", "multiple award",
            # Show-specific episode ranking
            "highest rated episode", "best episode", "top episode",
            "sopranos episode", "breaking bad episode", "game of thrones episode",
            # Mark as watched / user account features
            "mark as watched", "mark as seen", "check-in", "checkin",
            "watched list", "seen list", "add to watched",
            # World War / historical keyword searches
            "world war ii", "wwii", "world war 2", "ww2",
            # Ongoing / season count queries
            "still ongoing", "still airing", "still running", "number of seasons",
            "how many seasons",
            # Generic person/search queries — graph only has specific movie paths,
            # so "how do I find/look up an actor/director/writer" must use search steps
            "look up an actor", "look up actor", "look up a director", "look up director",
            "find an actor", "find a director", "find an actress", "find a writer",
            "find a person", "search for an actor", "search for a director",
            "look up a person", "look up someone", "find someone on imdb",
            "look up a tv show", "find a tv show", "search for a tv show",
            "look up a show", "find a show",
            # Generic navigation questions that need general search instructions
            "how do i find a", "how do i look up", "how to find a", "how to look up",
            # Generic search questions — graph only has specific paths, not "how to search"
            "how do i search", "search for a movie", "search for a tv",
            "find out what year", "what year a movie",
            "date of birth of", "birthday of a", "celebrity born",
            "filmography of", "career filmography", "sorted from first", "chronological",
            # Charts the graph doesn't know
            "bottom 100", "worst 100", "lowest rated movies", "lowest-rated movies",
            # Contribution / reporting — no graph path
            "report an error", "report error", "incorrect information", "wrong information",
            "contribute", "suggest a new title", "add a new title", "submit a title",
            # Social / follow features that don't exist on IMDb public pages
            "follow other users", "follow user", "follow list",
        }
        q_lower = question.lower()
        if not graph_miss and any(kw in q_lower for kw in _FORCE_MISS_KEYWORDS):
            graph_miss = True

        # 3. Retrieve IMDb context chunks
        rag_chunks = self._vector_store.search(question, k=8)
        context_text = "\n\n".join(c["text"] for c in rag_chunks) if rag_chunks else ""

        if not graph_miss:
            # Graph hit: short summary only (LLM call #2)
            path_text = self._format_path_for_llm(steps)
            answer = chat(
                [{"role": "system", "content": _ANSWER_WITH_PATH_PROMPT},
                 {"role": "user", "content": f"User question: {question}\n\nNavigation path:\n{path_text}"}],
            ).strip()
        else:
            # Graph miss: combined answer + steps in ONE call (LLM call #2)
            combined_raw = chat(
                [{"role": "system", "content": _ANSWER_AND_STEPS_PROMPT},
                 {"role": "user", "content": f"IMDb context:\n{context_text}\n\nUser question: {question}"}],
                response_format="json",
            )
            combined = self._parse_json_object(combined_raw)
            answer = combined.get("answer", "")
            steps = self._build_steps(combined.get("steps", []))

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

            # Replace generic movie/title placeholder tokens with a real example movie (Inception)
            # so the recorder can navigate to an actual page instead of skipping the step.
            url = re.sub(r"<(tt_id|movie_id|title_id|tt\w*id\w*)>", "tt1375666", url, flags=re.IGNORECASE)
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

            # Correct Bottom 100 chart hallucination: LLM sometimes uses /chart/top/
            # for questions about lowest-rated / worst movies
            if url and "/chart/top/" in url:
                desc_lower = description.lower()
                if any(kw in desc_lower for kw in ("bottom", "worst", "lowest")):
                    url = "https://www.imdb.com/chart/bottom/"

            # For click steps that navigate to a title sub-page but have no URL,
            # infer the URL from the description so the recorder can _goto as fallback
            if itype == "click" and not url:
                desc_lower = description.lower()
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
