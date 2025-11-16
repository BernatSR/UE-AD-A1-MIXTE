import json
import uuid

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


# Helpers JSON 

def load_movies():
    with open(MOVIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["movies"]


def save_movies(movies):
    with open(MOVIES_PATH, "w", encoding="utf-8") as f:
        json.dump({"movies": movies}, f, ensure_ascii=False, indent=2)


def load_actors():
    with open(ACTORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["actors"]


def save_actors(actors):
    with open(ACTORS_PATH, "w", encoding="utf-8") as f:
        json.dump({"actors": actors}, f, ensure_ascii=False, indent=2)


# Fonctions Movie

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


# Fonctions Actor

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


#  Types Ariadne

query = QueryType()
mutation = MutationType()
movie_type = ObjectType("Movie")
actor_type = ObjectType("Actor")


def require_admin(info):
    request = info.context["request"]
    is_admin = request.headers.get("X-Admin", "false").lower() == "true"
    if not is_admin:
        raise GraphQLError("admin only")


# Query resolvers 

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


# Field resolvers 

@movie_type.field("actors")
def resolve_movie_actors(movie, info):
    movie_id = movie.get("id")
    if not movie_id:
        return []
    return get_actors_for_movie(movie_id)


@actor_type.field("films")
def resolve_actor_films(actor, info):
    return get_movies_for_actor(actor)


# Mutations

@mutation.field("createMovie")
def resolve_create_movie(_, info, input):
    require_admin(info)
    title = input.get("title")
    director = input.get("director")
    rating = input.get("rating")

    if not title or not director:
        raise GraphQLError("Missing 'title' or 'director'")


type_defs = load_schema_from_path("movie.graphql")
schema = make_executable_schema(type_defs, [query, mutation])