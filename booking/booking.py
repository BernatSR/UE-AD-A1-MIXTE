from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType, MutationType
from flask import Flask, request, jsonify, make_response

import resolvers as r

PORT = 3001
HOST = '0.0.0.0'
app = Flask(__name__)

# -- Ariadne bindings
type_defs = load_schema_from_path('booking.graphql')

query = QueryType()
mutation = MutationType()
booking = ObjectType('Booking')

# Query fields
query.set_field('bookings', r.resolve_bookings)
query.set_field('booking', r.resolve_booking_by_id)
query.set_field('booking_with_userid', r.booking_with_userid)

# Field resolvers on types
booking.set_field('movie', r.resolve_booking_movie)

# Mutations
mutation.set_field('addBooking', r.resolve_add_booking)
mutation.set_field('deleteBooking', r.resolve_delete_booking)

schema = make_executable_schema(type_defs, query, mutation, booking)

# root message
@app.route("/", methods=['GET'])
def home():
    return make_response("<h1 style='color:blue'>Welcome to the Booking service!</h1>", 200)

# graphql entry point
@app.route('/graphql', methods=['POST'])
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(
        schema,
        data,
        context_value=None,
        debug=app.debug
    )
    status_code = 200 if success else 400
    return jsonify(result), status_code

if __name__ == "__main__":
    print(f"Server running on port {PORT}")
    app.run(host=HOST, port=PORT)
