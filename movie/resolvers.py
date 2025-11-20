import json
import uuid
import os
import requests
from typing import List, Dict

from ariadne import (
    QueryType,
    MutationType,
    ObjectType,
    load_schema_from_path,
    make_executable_schema,
)
from graphql import GraphQLError

MOVIES_PATH = "./data/movies.json"
ACTORS_PATH = "./data/actors.json"

USE_MONGO = os.environ.get("USE_MONGO", "false").lower() == "true"
MONGO_URL = os.environ.get("MONGO_URL", "")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "appdb")
_mongo_db = None
if USE_MONGO:
    try:
        from pymongo import MongoClient
        _mongo_db = MongoClient(MONGO_URL)[MONGO_DB_NAME]
    except Exception:
        _mongo_db = None


# ---------- Helpers JSON ----------

def load_movies() -> List[Dict]:
    if USE_MONGO and _mongo_db is not None:
        try:
            return list(_mongo_db.movies.find({}, {"_id": 0}))
        except Exception:
            return []
    with open(MOVIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["movies"]


def save_movies(movies: List[Dict]):
    if USE_MONGO and _mongo_db is not None:
        try:
            _mongo_db.movies.delete_many({})
            if movies:
                _mongo_db.movies.insert_many([m.copy() for m in movies])
            return
        except Exception:
            pass
    with open(MOVIES_PATH, "w", encoding="utf-8") as f:
        json.dump({"movies": movies}, f, ensure_ascii=False, indent=2)


def load_actors() -> List[Dict]:
    if USE_MONGO and _mongo_db is not None:
        try:
            return list(_mongo_db.actors.find({}, {"_id": 0}))
        except Exception:
            return []
    with open(ACTORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["actors"]


def save_actors(actors: List[Dict]):
    if USE_MONGO and _mongo_db is not None:
        try:
            _mongo_db.actors.delete_many({})
            if actors:
                _mongo_db.actors.insert_many([a.copy() for a in actors])
            return
        except Exception:
            pass
    with open(ACTORS_PATH, "w", encoding="utf-8") as f:
        json.dump({"actors": actors}, f, ensure_ascii=False, indent=2)


# ---------- Fonctions Movie ----------

def filter_movies(movie_id=None, title=None, director=None):
    movies = load_movies()
    result = movies

    if movie_id:
        result = [m for m in result if str(m.get("id")) == str(movie_id)]

    if title:
        t = title.strip().lower()
        result = [m for m in result if str(m.get("title", "")).lower() == t]

    if director:
        d = director.strip().lower()
        result = [m for m in result if str(m.get("director", "")).lower() == d]

    return result


def get_movie_by_id(movie_id):
    movies = load_movies()
    for m in movies:
        if str(m.get("id")) == str(movie_id):
            return m
    return None


def create_movie(title, director, rating=None):
    movies = load_movies()
    new_movie = {
        "id": str(uuid.uuid4()),
        "title": title,
        "director": director,
        "rating": float(rating) if rating is not None else 0.0,
    }
    movies.append(new_movie)
    save_movies(movies)
    return new_movie


def update_movie(movie_id, title=None, director=None, rating=None):
    movies = load_movies()
    for m in movies:
        if str(m.get("id")) == str(movie_id):
            if title is not None:
                m["title"] = title
            if director is not None:
                m["director"] = director
            if rating is not None:
                m["rating"] = float(rating)
            save_movies(movies)
            return m
    return None


def update_movie_rating(movie_id, rating):
    movies = load_movies()
    for m in movies:
        if str(m.get("id")) == str(movie_id):
            m["rating"] = float(rating)
            save_movies(movies)
            return m
    return None


def delete_movie(movie_id):
    movies = load_movies()
    for m in movies:
        if str(m.get("id")) == str(movie_id):
            movies.remove(m)
            save_movies(movies)
            return m
    return None


def is_movie_referenced(movie_id):
    actors = load_actors()
    return any(movie_id in a.get("films", []) for a in actors)


# ---------- Fonctions Actor ----------

def get_all_actors():
    return load_actors()


def get_actor_by_id(actor_id):
    actors = load_actors()
    for a in actors:
        if str(a.get("id")) == str(actor_id):
            return a
    return None


def get_actors_for_movie(movie_id):
    actors = load_actors()
    return [a for a in actors if movie_id in a.get("films", [])]


def get_movies_for_actor(actor):
    movie_ids = actor.get("films", [])
    if not movie_ids:
        return []
    movies = load_movies()
    movie_map = {m["id"]: m for m in movies}
    return [movie_map[mid] for mid in movie_ids if mid in movie_map]


# ---------- Types Ariadne ----------

query = QueryType()
mutation = MutationType()
movie_type = ObjectType("Movie")
actor_type = ObjectType("Actor")


def require_admin(info):
    request = info.context["request"]
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise GraphQLError("missing X-User-Id header")
    base = os.environ.get("USER_URL", "http://localhost:3203")
    try:
        resp = requests.get(f"{base}/users/{user_id}/admin", timeout=3)
    except requests.RequestException:
        raise GraphQLError("user service unreachable")
    if resp.status_code != 200:
        raise GraphQLError("admin check failed")
    data = resp.json()
    if not bool(data.get("is_admin")):
        raise GraphQLError("admin only")
    
def movie_already_exists(title, director):
    movies = load_movies()
    t = title.strip().lower()
    d = director.strip().lower()
    for m in movies:
        if (
            str(m.get("title", "")).strip().lower() == t
            and str(m.get("director", "")).strip().lower() == d
        ):
            return True
    return False



# ---------- Query resolvers ----------

@query.field("movies")
def resolve_movies(_, info, id=None, title=None, director=None):
    return filter_movies(movie_id=id, title=title, director=director)


@query.field("movie")
def resolve_movie(_, info, id):
    return get_movie_by_id(id)


@query.field("actors")
def resolve_actors(_, info):
    return get_all_actors()


@query.field("actor")
def resolve_actor(_, info, id):
    return get_actor_by_id(id)


@query.field("moviesByActor")
def resolve_movies_by_actor(_, info, actorId):
    actor = get_actor_by_id(actorId)
    if actor is None:
        return []
    return get_movies_for_actor(actor)


@query.field("actorsByMovie")
def resolve_actors_by_movie(_, info, movieId):
    return get_actors_for_movie(movieId)


@query.field("topRatedMovies")
def resolve_top_rated_movies(_, info, limit):
    movies = load_movies()
    movies_sorted = sorted(
        movies,
        key=lambda m: m.get("rating", 0.0),
        reverse=True,
    )
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return []
    return movies_sorted[:n]


# ---------- Field resolvers ----------

@movie_type.field("actors")
def resolve_movie_actors(movie, info):
    movie_id = movie.get("id")
    if not movie_id:
        return []
    actors = get_actors_for_movie(movie_id)
    if actors is None:
        return []
    return actors


@actor_type.field("films")
def resolve_actor_films(actor, info):
    movies = get_movies_for_actor(actor)
    if movies is None:
        return []
    return movies


# ---------- Mutations ----------

@mutation.field("createMovie")
def resolve_create_movie(_, info, input):
    require_admin(info)
    title = input.get("title")
    director = input.get("director")
    rating = input.get("rating")

    if not title or not director:
        raise GraphQLError("Missing 'title' or 'director'")

    if movie_already_exists(title, director):
        raise GraphQLError("movie with same title and director already exists")

    return create_movie(title=title, director=director, rating=rating)



@mutation.field("updateMovie")
def resolve_update_movie(_, info, id, input):
    require_admin(info)
    title = input.get("title")
    director = input.get("director")
    rating = input.get("rating")

    updated = update_movie(id, title=title, director=director, rating=rating)
    if updated is None:
        raise GraphQLError("movie ID not found")
    return updated


@mutation.field("updateMovieRating")
def resolve_update_movie_rating(_, info, id, rating):
    require_admin(info)
    updated = update_movie_rating(id, rating)
    if updated is None:
        raise GraphQLError("movie ID not found")
    return updated


@mutation.field("deleteMovie")
def resolve_delete_movie(_, info, id):
    require_admin(info)
    deleted = delete_movie(id)
    if deleted is None:
        raise GraphQLError("movie ID not found")
    return deleted


@mutation.field("deleteMovieSafe")
def resolve_delete_movie_safe(_, info, id):
    require_admin(info)

    if is_movie_referenced(id):
        raise GraphQLError("cannot delete movie: still referenced by actors")

    deleted = delete_movie(id)
    if deleted is None:
        raise GraphQLError("movie ID not found")
    return deleted


@mutation.field("addFilmToActor")
def resolve_add_film_to_actor(_, info, actorId, movieId):
    require_admin(info)

    actors = load_actors()
    movies = load_movies()

    movie = next((m for m in movies if m["id"] == movieId), None)
    if movie is None:
        raise GraphQLError("movie ID not found")

    actor = next((a for a in actors if a["id"] == actorId), None)
    if actor is None:
        raise GraphQLError("actor ID not found")

    films = actor.get("films", [])
    if movieId not in films:
        films.append(movieId)
    actor["films"] = films

    save_actors(actors)
    return actor


@mutation.field("removeFilmFromActor")
def resolve_remove_film_from_actor(_, info, actorId, movieId):
    require_admin(info)

    actors = load_actors()
    movies = load_movies()

    movie = next((m for m in movies if m["id"] == movieId), None)
    if movie is None:
        raise GraphQLError("movie ID not found")

    actor = next((a for a in actors if a["id"] == actorId), None)
    if actor is None:
        raise GraphQLError("actor ID not found")

    films = actor.get("films", [])

    if movieId not in films:
        raise GraphQLError("actor is not associated with this movie")

    films.remove(movieId)
    actor["films"] = films

    save_actors(actors)
    return actor


@mutation.field("createActor")
def resolve_create_actor(_, info, id, firstname, lastname, birthyear, films):
    require_admin(info)

    actors = load_actors()
    movies = load_movies()

    if any(a["id"] == id for a in actors):
        raise GraphQLError("actor ID already exists")

    for film_id in films:
        if not any(m["id"] == film_id for m in movies):
            raise GraphQLError(f"movie '{film_id}' does not exist")

    new_actor = {
        "id": id,
        "firstname": firstname,
        "lastname": lastname,
        "birthyear": int(birthyear),
        "films": films,
    }

    actors.append(new_actor)
    save_actors(actors)
    return new_actor


@mutation.field("deleteActor")
def resolve_delete_actor(_, info, id):
    require_admin(info)

    actors = load_actors()

    actor = next((a for a in actors if a["id"] == id), None)
    if actor is None:
        raise GraphQLError("actor ID not found")

    if actor.get("films", []):
        raise GraphQLError("cannot delete actor: films are still associated")

    actors.remove(actor)
    save_actors(actors)
    return actor


# ---------- Schéma ----------

type_defs = load_schema_from_path("movie.graphql")
schema = make_executable_schema(
    type_defs,
    [query, mutation, movie_type, actor_type],
)
