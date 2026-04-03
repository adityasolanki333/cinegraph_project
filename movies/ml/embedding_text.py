"""
Shared embedding text builder for Pinecone vector search.
Used by both the bulk ingestion script and the runtime PineconeService
to ensure identical embedding distribution.
"""


def build_enriched_text(movie_data: dict) -> str:
    """
    Build enriched text for embedding from movie metadata.

    Accepts a dict with keys: title, overview, genres, director, cast,
    release_date (or release_year), keywords, tagline.

    Both `keywords` and `tagline` are treated as thematic signals and
    merged under the "Themes" label.
    """
    title = str(movie_data.get("title", "") or "")
    overview = str(movie_data.get("overview", "") or "")
    genres = str(movie_data.get("genres", "") or "")
    director = str(movie_data.get("director", "") or "")
    cast = str(movie_data.get("cast", "") or "")[:120]

    release_date = str(movie_data.get("release_date", "") or "")
    release_year = str(movie_data.get("release_year", "") or "")
    if not release_year and release_date and len(release_date) >= 4:
        release_year = release_date[:4]

    keywords = str(movie_data.get("keywords", "") or "")
    tagline = str(movie_data.get("tagline", "") or "")
    themes_parts = [t for t in [keywords, tagline] if t]
    themes = ", ".join(themes_parts)

    parts = [f"Title: {title}."]
    if release_year:
        parts.append(f"Year: {release_year}.")
    if overview:
        parts.append(f"Overview: {overview}")
    if genres:
        parts.append(f"Genres: {genres}.")
    if themes:
        parts.append(f"Themes: {themes}.")
    if director:
        parts.append(f"Director: {director}.")
    if cast:
        parts.append(f"Cast: {cast}.")

    return " ".join(parts).strip()
