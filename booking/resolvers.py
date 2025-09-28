import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
import grpc

import schedule_pb2
import schedule_pb2_grpc

BOOKINGS_PATH = "./databases/bookings.json"

MOVIE_GRAPHQL_URL = "http://movie:3200/graphql"  
SCHEDULE_GRPC_ADDR = "schedule:50051"            

DATE_RX = re.compile(r"^\d{8}$")


# ---------- Utils JSON ----------
def load_bookings() -> List[Dict[str, Any]]:
    try:
        with open(BOOKINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("bookings", [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def save_bookings(bookings: List[Dict[str, Any]]) -> None:
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


def next_booking_id(bookings: List[Dict[str, Any]]) -> int:
    return (max((int(b["id"]) for b in bookings), default=0) + 1)


def fetch_movie_by_id(movie_id: str) -> Optional[Dict[str, Any]]:
    """
    Interroge le service Movie (ton schéma actuel) :
    - Query: movie_with_id(_id: ID!)
    - Champs: id, title, director, rating
    """
    query = """
    query GetMovie($id: ID!) {
      movie_with_id(_id: $id) {
        id
        title
        director
        rating
      }
    }
    """
    payload = {"query": query, "variables": {"id": str(movie_id)}}
    try:
        res = requests.post(MOVIE_GRAPHQL_URL, json=payload, timeout=4)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            return None
        return data.get("data", {}).get("movie_with_id")
    except Exception:
        return None



# ---------- Schedule (gRPC) ----------
def check_schedule_date(movie_id: str, date_ymd: str) -> bool:
    """
    Appel gRPC au service Schedule pour vérifier que le film movie_id est bien
    programmé à la date date_ymd (YYYYMMDD).
    On suppose une RPC: ValidateDate(ValidateDateRequest) returns (ValidateDateResponse)
    avec bool 'ok' et string 'reason'.
    """
    try:
        with grpc.insecure_channel(SCHEDULE_GRPC_ADDR) as channel:
            stub = schedule_pb2_grpc.ScheduleStub(channel)
            req = schedule_pb2.ValidateDateRequest(
                movie_id=str(movie_id),
                date= str(date_ymd)
            )
            resp: schedule_pb2.ValidateDateResponse = stub.ValidateDate(req, timeout=3)
            return bool(resp.ok)
    except Exception:
        return False


# ---------- Resolvers: Queries ----------
def resolve_bookings(*_) -> List[Dict[str, Any]]:
    return load_bookings()


def resolve_booking_by_id(*_, id: str) -> Optional[Dict[str, Any]]:
    bookings = load_bookings()
    return next((b for b in bookings if str(b.get("id")) == str(id)), None)


def booking_with_userid(*_, userId: str) -> List[Dict[str, Any]]:
    """
    Renvoie une liste d'objets { booking, movie } pour un userId donné.
    """
    bookings = load_bookings()
    filtered = [b for b in bookings if str(b.get("userId")) == str(userId)]
    results = []
    for b in filtered:
        mv = fetch_movie_by_id(b["movieId"])
        results.append({"booking": b, "movie": mv})
    return results


# ---------- Field resolver: Booking.movie ----------
def resolve_booking_movie(obj: Dict[str, Any], *_):
    """
    Permet de faire: booking { id movie { ... } } en résolvant le film lié.
    """
    movie_id = obj.get("movieId")
    return fetch_movie_by_id(movie_id) if movie_id else None


# ---------- Mutations ----------
def resolve_add_booking(*_, input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crée une réservation après vérifications:
    - format date
    - film existe (Movie GraphQL)
    - slot valide (Schedule gRPC)
    """
    user_id = str(input.get("userId"))
    movie_id = str(input.get("movieId"))
    date_ymd = str(input.get("date"))

    # Validations basiques
    if not validate_date_str(date_ymd):
        raise ValueError("Invalid date format: expected YYYYMMDD")

    movie = fetch_movie_by_id(movie_id)
    if not movie:
        raise ValueError("Unknown movieId")

    if not check_schedule_date(movie_id, date_ymd):
        raise ValueError("Selected date is not available for this movie in Schedule")

    bookings = load_bookings()
    new_id = next_booking_id(bookings)
    booking = {
        "id": str(new_id),
        "userId": user_id,
        "movieId": movie_id,
        "date": date_ymd
    }
    bookings.append(booking)
    save_bookings(bookings)
    return booking


def resolve_delete_booking(*_, id: str) -> bool:
    bookings = load_bookings()
    before = len(bookings)
    bookings = [b for b in bookings if str(b.get("id")) != str(id)]
    save_bookings(bookings)
    return len(bookings) < before
