from flask import Flask, request, jsonify
import requests
import json
import re
from datetime import datetime

# Ariadne (GraphQL)
from ariadne import graphql_sync, make_executable_schema, load_schema_from_path
from ariadne.constants import PLAYGROUND_HTML
from resolvers import query, mutation  # à remplir dans resolvers.py

app = Flask(__name__)

PORT = 3201
HOST = "0.0.0.0"

# -------------------------------------------------------------------
# Données et utilitaires
# -------------------------------------------------------------------

with open("./databases/bookings.json", "r", encoding="utf-8") as jsf:
    bookings = json.load(jsf)["bookings"]

DATE_RX = re.compile(r"^\d{8}$")


def write():
    """Sauvegarde le fichier bookings.json"""
    with open("./databases/bookings.json", "w", encoding="utf-8") as f:
        json.dump({"bookings": bookings}, f, ensure_ascii=False, indent=2)


def validate_date_str(date_str: str) -> bool:
    """Vérifie format YYYYMMDD et que la date est valide"""
    if not DATE_RX.match(date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return True
    except ValueError:
        return False


def check_schedule(date_str, movie_ids):
    """
    Vérifie auprès du service Schedule si les films sont bien programmés
    pour la date donnée.
    Renvoie True si tout va bien, sinon un dict d'erreur (à gérer dans les resolvers).
    """
    try:
        r = requests.get(f"http://localhost:3202/showmovies/{date_str}", timeout=3)
    except requests.RequestException:
        return {"error": "schedule service unreachable", "status": 503}

    if r.status_code != 200:
        return {"error": "date not found in schedule", "status": 404}

    # Réponse du service schedule pour les films du jour
    day = r.json()
    # Liste des films à cette date
    allowed_movies = day.get("movies", [])
    not_allowed = [m for m in movie_ids if m not in allowed_movies]

    if not_allowed:
        return {
            "error": "some movies are not scheduled for this date",
            "date": date_str,
            "not_allowed_movies": not_allowed,
            "status": 409,
        }

    return True


def find_user_booking(userid: str):
    """Retourne l'entrée de réservation d'un user ou None"""
    for booking in bookings:
        if booking.get("userid") == userid:
            return booking
    return None


def find_date_entry(user_entry, date_str: str):
    """Retourne l'entrée d'une date pour ce user ou None"""
    for date_entry in user_entry.get("dates", []):
        if date_entry.get("date") == date_str:
            return date_entry
    return None


def get_movie(movie_id: str):
    """Va chercher un film dans le service Movie ou None"""
    try:
        r = requests.get(f"http://localhost:3200/movies/{movie_id}", timeout=3)
    except requests.RequestException:
        # Service movie down, timeout, etc.
        return None

    if r.status_code == 200:
        return r.json()
    else:
        return None


# -------------------------------------------------------------------
# GraphQL : schéma + resolvers
# -------------------------------------------------------------------

# booking.graphql doit être dans le même dossier que ce fichier
type_defs = load_schema_from_path("./booking.graphql")

# query et mutation viennent de resolvers.py
schema = make_executable_schema(type_defs, query, mutation)


# -------------------------------------------------------------------
# Routes HTTP : accueil + endpoint GraphQL
# -------------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return "<h1 style='color:blue'>Welcome to the Booking service (GraphQL)!</h1>"


# Playground (interface GraphQL dans le navigateur)
@app.route("/graphql", methods=["GET"])
def graphql_playground():
    return PLAYGROUND_HTML, 200


# Endpoint GraphQL
@app.route("/graphql", methods=["POST"])
def graphql_server():
    data = request.get_json()

    # Tout ce dont les resolvers peuvent avoir besoin est passé dans le context
    success, result = graphql_sync(
        schema,
        data,
        context_value={
            "request": request,
            "bookings": bookings,
            "write": write,
            "validate_date_str": validate_date_str,
            "check_schedule": check_schedule,
            "find_user_booking": find_user_booking,
            "find_date_entry": find_date_entry,
            "get_movie": get_movie,
        },
        debug=True,
    )

    status_code = 200 if success else 400
    return jsonify(result), status_code


# -------------------------------------------------------------------
# Lancement de l'application
# -------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Booking GraphQL server running on port {PORT}")
    app.run(host=HOST, port=PORT)
