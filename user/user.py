from flask import Flask, render_template, request, jsonify, make_response
import json
from datetime import datetime
import time
import uuid


app = Flask(__name__)

PORT = 3203
HOST = '0.0.0.0'

# Ouvre fichier json -> charge en dict Python -> extrait la liste d'utilisateurs
with open('{}/data/users.json'.format("."), "r") as jsf:
   users = json.load(jsf)["users"]

def write(users):
    with open('{}/data/users.json'.format("."), 'w') as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)

def name_to_id(name: str):
    return name.strip().lower().replace(" ", "_")

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


#Route

@app.route("/", methods=['GET'])
def profil():
   return "<h1 style='color:blue'>Welcome to the User service!</h1>"

#CRUD user

#CREATE

@app.route("/users", methods=['POST'])
def add_user():

    req = request.get_json(silent=True) or {}
    if "name" not in req:
        return make_response(jsonify({"error": "missing 'name' field"}), 400)

    # Générer l'id à partir du name
    user_id = req["name"].strip().lower().replace(" ", "_")
    req["id"] = user_id
    req["last_active"] = int(time.time())
    req["is_admin"] = False

    for user in users:
        if user["id"] == user_id:
            return make_response(jsonify({"error": "user ID already exists"}), 409)

    users.append(req)
    write(users)

    return make_response(jsonify({
        "message": "user added",
        "user": req
    }), 201)



#READ

@app.route("/users", methods=['GET'])
def get_all_users():
    """Renvoie la liste complète des utilisateurs."""

    caller_id = request.headers.get("X-User-Id")

    if caller_id is None:
        return make_response(jsonify({"error": "missing X-User-Id header"}), 400)

    if not is_admin(caller_id):
        return make_response(jsonify({"error": "admin only"}), 403)

    return make_response(jsonify(users), 200)



@app.route("/users/<userid>", methods=['GET'])
def get_user(userid):
    """Renvoie un utilisateur précis selon son ID."""
    for user in users:
        if str(user["id"]) == str(userid):
            return make_response(jsonify(user), 200)
    return make_response(jsonify({"error": "user ID not found"}), 404)


@app.route("/users/<userid>/admin", methods=["GET"])
def check_user_admin(userid):
    """Route pour que les autres services puissent vérifier si un utilisateur est admin"""
    
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "user ID not found"}), 404)

    return make_response(jsonify({"is_admin": bool(user.get("is_admin", False))}), 200)


#UPDATE

@app.route("/users/<userid>", methods=['PUT'])
def update_user(userid):
    payload = request.get_json(silent=True) or {}

    # On cherche l'user
    for user in users:
        if str(user["id"]) == str(userid):

            # Met à jour seulement les champs présents dans le JSON
            if "name" in payload:
                user["name"] = payload["name"]

            user["last_active"] = int(time.time())
            write(users)

            return make_response(jsonify(user), 200)

    return make_response(jsonify({"error": "user ID not found"}), 404)


#DELETE

@app.route("/users/<userid>", methods=['DELETE'])
def del_user(userid):
   for user in users:
      if str(user["id"]) == str(userid):
         users.remove(user)
         write(users) 
         return make_response(jsonify(user),200)

   return make_response(jsonify({"error": "user ID not found"}), 404)


if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
