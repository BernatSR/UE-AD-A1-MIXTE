from flask import Flask, request, jsonify, make_response
import json
from datetime import datetime

app = Flask(__name__)

PORT = 3203
HOST = "0.0.0.0"


with open("./databases/users.json", "r", encoding="utf-8") as jsf:
    users = json.load(jsf)["users"]


def write(users_list):
    with open("./databases/users.json", "w", encoding="utf-8") as f:
        json.dump({"users": users_list}, f, ensure_ascii=False, indent=2)


def now_iso():
    return datetime.utcnow().isoformat()


def find_user(userid):
    for user in users:
        if str(user.get("id")) == str(userid):
            return user
    return None


def is_admin(userid):
    user = find_user(userid)
    if user is None:
        return False
    # On retourne la valeur du champ is_admin s'il existe, sinon False
    return bool(user.get("is_admin", False))



# Routes


@app.route("/", methods=["GET"])
def profil():
    """Page d'accueil simple du service."""
    return "<h1 style='color:blue'>Welcome to the User service!</h1>"

# CREATE

@app.route("/adduser/<userid>", methods=["POST"])
def add_user(userid):

    req = request.get_json(silent=True)
    if req is None:
        req = {}

    # On injecte l'id et la date d'activité
    req["id"] = str(userid)
    req["last_active"] = now_iso()

    if find_user(userid) is not None:
        return make_response(jsonify({"error": "user ID already exists"}), 409)

    users.append(req)
    write(users)

    return make_response(jsonify({"message": "user added"}), 200)



# READ

@app.route("/users", methods=["GET"])
def get_all_users():
    """Renvoie la liste complète des utilisateurs
    Accessible uniquement si l'appelant est admin"""
    # On récupère l'id de celui qui fait la demande
    caller_id = request.headers.get("X-User-Id")

    # Si aucun header fourni
    if caller_id is None:
        return make_response(jsonify({"error": "missing X-User-Id header"}), 400)

    # On vérifie s'il est admin
    if not is_admin(caller_id):
        return make_response(jsonify({"error": "admin only"}), 403)

    return make_response(jsonify(users), 200)


@app.route("/users/<userid>", methods=["GET"])
def get_user(userid):
    """Renvoie un utilisateur précis selon son ID"""
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "user ID not found"}), 404)

    return make_response(jsonify(user), 200)


@app.route("/users/<userid>/admin", methods=["GET"])
def check_user_admin(userid):
    """Route pour que les autres services puissent vérifier si un utilisateur est admin"""
    
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "user ID not found"}), 404)

    return make_response(jsonify({"is_admin": bool(user.get("is_admin", False))}), 200)


# UPDATE

@app.route("/users/<userid>/<name>", methods=["PUT"])
def update_user_name(userid, name):
    """ Met à jour le nom d'un utilisateur et la date last_active """
    user = find_user(userid)

    if user is None:
        return make_response(jsonify({"error": "user ID not found"}), 404)

    user["name"] = name
    user["last_active"] = now_iso()
    write(users)

    return make_response(jsonify(user), 200)

#DELETE

@app.route("/users/<userid>", methods=["DELETE"])
def del_user(userid):
    user = find_user(userid)

    if user is None:
        return make_response(jsonify({"error": "user ID not found"}), 404)

    users.remove(user)
    write(users)

    return make_response(jsonify(user), 200)


if __name__ == "__main__":
    print(f"Server running in port {PORT}")
    app.run(host=HOST, port=PORT)
