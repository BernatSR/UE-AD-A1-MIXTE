from ariadne import QueryType, MutationType
from graphql import GraphQLError

query = QueryType()
mutation = MutationType()


# --------- QUERIES --------- #

@query.field("allBookings")
def resolve_all_bookings(_, info):
    request = info.context["request"]
    bookings = info.context["bookings"]

    # Admin only (comme GET /bookings avant)
    if request.headers.get("X-Admin", "false").lower() != "true":
        raise GraphQLError("admin only")

    return bookings


@query.field("bookingsByUser")
def resolve_bookings_by_user(_, info, userid):
    find_user_booking = info.context["find_user_booking"]

    entry = find_user_booking(userid)
    if entry is None:
        # Comme l'API REST qui renvoyait {userid, dates: []}
        return {"userid": userid, "dates": []}

    return entry


@query.field("detailedBookingsByUser")
def resolve_detailed_bookings_by_user(_, info, userid):
    find_user_booking = info.context["find_user_booking"]
    get_movie = info.context["get_movie"]

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
                movies_detailed.append({
                    "id": movie_id,
                    "error": "movie not found"
                })
        detailed_dates.append({
            "date": d.get("date"),
            "movies": movies_detailed
        })

    return {
        "userid": userid,
        "dates": detailed_dates
    }


@query.field("statsMoviesForDate")
def resolve_stats_movies_for_date(_, info, date):
    request = info.context["request"]
    bookings = info.context["bookings"]
    validate_date_str = info.context["validate_date_str"]
    get_movie = info.context["get_movie"]

    # Admin only (comme l'endpoint REST /stats/date/.../movies)
    if request.headers.get("X-Admin", "false").lower() != "true":
        raise GraphQLError("admin only")

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
            items.append({
                "movie": info_movie,
                "count": nb
            })
        else:
            items.append({
                "movie": {"id": movie_id, "error": "movie not found"},
                "count": nb
            })

    items_sorted = sorted(items, key=lambda x: x["count"], reverse=True)

    return {
        "date": date,
        "movies": items_sorted
    }


# --------- MUTATIONS --------- #

@mutation.field("addBooking")
def resolve_add_booking(_, info, userid, date, movies):
    bookings = info.context["bookings"]
    write = info.context["write"]
    validate_date_str = info.context["validate_date_str"]
    check_schedule = info.context["check_schedule"]
    find_user_booking = info.context["find_user_booking"]
    find_date_entry = info.context["find_date_entry"]

    if not validate_date_str(date):
        raise GraphQLError("invalid date format, expected YYYYMMDD")

    if not isinstance(movies, list) or len(movies) == 0:
        raise GraphQLError("provide movie or movies as a non-empty array")

    to_add_movie = []
    for item in movies:
        if isinstance(item, str):
            to_add_movie.append(item)

    if len(to_add_movie) == 0:
        raise GraphQLError("provide movie or movies as strings")

    result = check_schedule(date, to_add_movie)
    if result is not True:
        msg = result.get("error", "schedule error")
        # On ajoute des détails si disponibles
        if "not_allowed_movies" in result:
            msg += f" (not allowed: {', '.join(result['not_allowed_movies'])})"
        raise GraphQLError(msg)

    entry = find_user_booking(userid)
    if entry is None:
        entry = {"userid": userid, "dates": []}
        bookings.append(entry)

    dentry = find_date_entry(entry, date)
    if dentry is None:
        dentry = {"date": date, "movies": []}
        entry["dates"].append(dentry)

    for mid in to_add_movie:
        if mid not in dentry["movies"]:
            dentry["movies"].append(mid)

    write()

    return {
        "message": "booking added",
        "date": date,
        "movies": dentry["movies"]
    }


@mutation.field("deleteBooking")
def resolve_delete_booking(_, info, userid, date, movieid):
    bookings = info.context["bookings"]
    write = info.context["write"]
    find_user_booking = info.context["find_user_booking"]
    find_date_entry = info.context["find_date_entry"]

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

    new_dates = []
    for d in entry.get("dates", []):
        if d.get("movies"):
            new_dates.append(d)
    entry["dates"] = new_dates

    write()

    return {
        "message": "booking deleted",
        "userid": userid,
        "date": date,
        "movie": movieid
    }
