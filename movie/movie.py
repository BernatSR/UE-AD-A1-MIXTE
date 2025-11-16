from ariadne import graphql_sync
from flask import Flask, request, jsonify, make_response

import resolvers as r  # contient schema

PORT = 3001
HOST = '0.0.0.0'
app = Flask(__name__)

schema = r.schema


@app.route("/", methods=['GET'])
def home():
    return make_response("<h1 style='color:blue'>Welcome to the Movie service!</h1>", 200)


@app.route('/graphql', methods=['POST'])
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(
        schema,
        data,
        context_value={"request": request},
        debug=True
    )
    status_code = 200 if "errors" not in result else 400
    return jsonify(result), status_code


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
