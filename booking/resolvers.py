import json
import re
import os
from datetime import datetime
from typing import List, Dict

import requests
import grpc

from schedule import schedule_pb2
from schedule import schedule_pb2_grpc

from ariadne import (
    QueryType,
    MutationType,
    load_schema_from_path,
    make_executable_schema,
)
from graphql import GraphQLError

BOOKINGS_PATH = "./data/bookings.json"
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
DATE_RX = re.compile(r"^\d{8}$")


if USE_MONGO and _mongo_db is not None:
    try:
        bookings: List[Dict] = list(_mongo_db.bookings.find({}, {"_id": 0}))
    except Exception:
        bookings = []
else:
    with open(BOOKINGS_PATH, "r", encoding="utf-8") as jsf:
        bookings = json.load(jsf)["bookings"]


def write():
    if USE_MONGO and _mongo_db is not None:
        try:
            _mongo_db.bookings.delete_many({})
            if bookings:
                _mongo_db.bookings.insert_many([b.copy() for b in bookings])
            return
        except Exception:
            pass
    with open(BOOKINGS_PATH, "w", encoding="utf-8") as f:
        json.dump({"bookings": bookings}, f, ensure_ascii=False, indent=2)


def validate_date_str(date_str: str) -> bool:
    if not DATE_RX.match(date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return True
    except ValueError:
        return False


def require_admin(info):
    request = info.context["request"]
    if request.headers.get("X-Admin", "false").lower() != "true":
        raise GraphQLError("admin only")


def get_movie(movie_id: str):
    query = """
    query($id: ID!) {
      movie(id: $id) {
        id
        title
        director
        rating
      }
    }
    """
    try:
        r = requests.post(
            os.environ.get("MOVIE_URL", "http://localhost:3001/graphql"),
            json={"query": query, "variables": {"id": movie_id}},
            timeout=3,
        )
    except requests.RequestException:
        return None

    if r.status_code != 200:
        return None

    payload = r.json()
    return payload.get("data", {}).get("movie")


# **********  version gRPC de check_schedule **********

def check_schedule(date_str, movie_ids):
    try:
        with grpc.insecure_channel(os.environ.get("SCHEDULE_ADDR", "localhost:3202")) as channel:
            stub = schedule_pb2_grpc.ScheduleStub(channel)
            resp = stub.GetScheduleByDate(
                schedule_pb2.DateRequest(date=date_str)
            )
    except grpc.RpcError as e:
        code = e.code()
        if code == grpc.StatusCode.INVALID_ARGUMENT:
            raise GraphQLError("invalid date format, expected YYYYMMDD")
        if code == grpc.StatusCode.NOT_FOUND:
            raise GraphQLError("date not found in schedule")
        raise GraphQLError("schedule service unreachable")

    allowed_movies = list(resp.movies)
    not_allowed = [m for m in movie_ids if m not in allowed_movies]

    if not_allowed:
        raise GraphQLError(
            f"some movies are not scheduled for this date: {not_allowed}"
        )


def find_user_booking(userid: str):
    for booking in bookings:
        if booking["userid"] == userid:
            return booking
    return None


def find_date_entry(user_entry, date_str: str):
    for date_entry in user_entry["dates"]:
        if date_entry["date"] == date_str:
            return date_entry
    return None


# ----- Types Ariadne -----

query = QueryType()
mutation = MutationType()


@query.field("bookings")
def resolve_bookings(_, info):
    require_admin(info)
    return bookings


@query.field("booking")
def resolve_booking(_, info, userid):
    entry = find_user_booking(userid)
    if entry is None:
        return {"userid": userid, "dates": []}
    return entry


@query.field("bookingDetails")
def resolve_booking_details(_, info, userid):
    entry = find_user_booking(userid)
    if entry is None:
        return {"userid": userid, "dates": []}

    detailed_dates = []

    for d in entry.get("dates", []):
        movies_detailed = []
        for movie_id in d.get("movies", []):
            info_movie = get_movie(movie_id)
            if info_movie:
                movies_detailed.append(info_movie)
            else:
                movies_detailed.append({"id": movie_id, "error": "movie not found"})
        detailed_dates.append({"date": d["date"], "movies": movies_detailed})

    return {"userid": userid, "dates": detailed_dates}


@query.field("statsMoviesForDate")
def resolve_stats_movies_for_date(_, info, date):
    require_admin(info)

    if not validate_date_str(date):
        raise GraphQLError("invalid date format, expected YYYYMMDD")

    counts = {}
    for booking in bookings:
        for d in booking.get("dates", []):
            if d.get("date") == date:
                for movie_id in d.get("movies", []):
                    counts[movie_id] = counts.get(movie_id, 0) + 1

    items = []
    for movie_id, nb in counts.items():
        info_movie = get_movie(movie_id)
        if info_movie is not None:
            movie_obj = info_movie
        else:
            movie_obj = {"id": movie_id, "error": "movie not found"}
        items.append({"movie": movie_obj, "count": nb})

    items_sorted = sorted(items, key=lambda x: x["count"], reverse=True)

    return {"date": date, "movies": items_sorted}


@mutation.field("addBooking")
def resolve_add_booking(_, info, userid, date, movies):
    if not validate_date_str(date):
        raise GraphQLError("invalid date format, expected YYYYMMDD")

    to_add = [m for m in movies if isinstance(m, str) and m.strip()]

    if len(to_add) == 0:
        raise GraphQLError("provide movie or movies in argument 'movies'")

    # Vérification auprès de Schedule (maintenant en gRPC)
    check_schedule(date, to_add)

    # Vérifier que les films existent bien dans Movie
    for movie_id in to_add:
        info_movie = get_movie(movie_id)
        if info_movie is None:
            raise GraphQLError(f"movie id '{movie_id}' does not exist in Movie service")

    entry = find_user_booking(userid)
    if entry is None:
        entry = {"userid": userid, "dates": []}
        bookings.append(entry)

    dentry = find_date_entry(entry, date)
    if dentry is None:
        dentry = {"date": date, "movies": []}
        entry["dates"].append(dentry)

    for movie_id in to_add:
        if movie_id not in dentry["movies"]:
            dentry["movies"].append(movie_id)

    write()

    return {
        "message": "booking added",
        "userid": userid,
        "date": date,
        "movies": dentry["movies"],
    }


@mutation.field("deleteBooking")
def resolve_delete_booking(_, info, userid, date, movieid):
    entry = find_user_booking(userid)
    if entry is None:
        raise GraphQLError("user has no bookings")

    date_entry = find_date_entry(entry, date)
    if date_entry is None:
        raise GraphQLError("no bookings for this date")

    try:
        date_entry["movies"].remove(movieid)
    except ValueError:
        raise GraphQLError("movie not booked on this date")

    new_dates = [d for d in entry["dates"] if len(d.get("movies", [])) > 0]
    entry["dates"] = new_dates

    write()

    return {
        "message": "booking deleted",
        "userid": userid,
        "date": date,
        "movie": movieid,
    }


type_defs = load_schema_from_path("booking.graphql")
schema = make_executable_schema(type_defs, [query, mutation])
