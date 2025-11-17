import json
import os
import requests
from concurrent import futures

import grpc
from google.protobuf import empty_pb2

import schedule_pb2
import schedule_pb2_grpc

PORT = 3202
DATABASE_PATH = "./data/times.json"



def load_schedule():
    try:
        with open(DATABASE_PATH, "r", encoding="utf-8") as jsf:
            return json.load(jsf)["schedule"]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_schedule(schedule_data):
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    data = {"schedule": schedule_data}
    with open(DATABASE_PATH, "w", encoding="utf-8") as jsf:
        json.dump(data, jsf, indent=2)


def validate_date_format(date: str) -> bool:
    return len(date) == 8 and date.isdigit()


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
            "http://localhost:3001/graphql", 
            json={"query": query, "variables": {"id": movie_id}},
            timeout=3,
        )
    except requests.RequestException:
        return None

    if r.status_code != 200:
        return None

    payload = r.json()
    return payload.get("data", {}).get("movie")



# Implémentation du service gRPC

class ScheduleServicer(schedule_pb2_grpc.ScheduleServicer):
    def __init__(self):
        self.schedule = load_schedule()

    # GET /showmovies
    def GetAllSchedules(self, request, context):
        entries = [
            schedule_pb2.ScheduleEntry(
                date=e["date"],
                movies=e.get("movies", [])
            )
            for e in self.schedule
        ]
        return schedule_pb2.ListSchedulesResponse(schedules=entries)

    # GET /showmovies/<date>
    def GetScheduleByDate(self, request, context):
        date = request.date

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD"
            )

        for e in self.schedule:
            if e.get("date") == date:
                return schedule_pb2.ScheduleEntry(
                    date=e["date"],
                    movies=e.get("movies", [])
                )

        context.abort(
            grpc.StatusCode.NOT_FOUND,
            f"Schedule not found for date: {date}"
        )

    # POST /showmovies/<date>
    def CreateSchedule(self, request, context):
        date = request.date
        movies = list(request.movies)

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD"
            )

        for e in self.schedule:
            if e.get("date") == date:
                context.abort(
                    grpc.StatusCode.ALREADY_EXISTS,
                    f"Schedule already exists for date: {date}"
                )

        if not isinstance(movies, list):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Movies must be an array"
            )

        for movie in movies:
            if not isinstance(movie, str) or len(movie.strip()) == 0:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "All movie entries must be non-empty strings"
                )

        new_entry = {"date": date, "movies": movies}
        self.schedule.append(new_entry)
        try:
            save_schedule(self.schedule)
        except Exception:
            context.abort(
                grpc.StatusCode.INTERNAL,
                "Failed to save schedule"
            )

        return schedule_pb2.ScheduleEntry(
            date=date,
            movies=movies
        )

    # PUT /showmovies/<date>
    def UpdateSchedule(self, request, context):
        date = request.date
        movies = list(request.movies)

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD"
            )

        if not isinstance(movies, list):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Movies must be an array"
            )

        for movie in movies:
            if not isinstance(movie, str) or len(movie.strip()) == 0:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "All movie entries must be non-empty strings"
                )

        for i, e in enumerate(self.schedule):
            if e.get("date") == date:
                self.schedule[i]["movies"] = movies
                try:
                    save_schedule(self.schedule)
                except Exception:
                    context.abort(
                        grpc.StatusCode.INTERNAL,
                        "Failed to save schedule"
                    )

                return schedule_pb2.ScheduleEntry(
                    date=date,
                    movies=movies
                )

        context.abort(
            grpc.StatusCode.NOT_FOUND,
            f"Schedule not found for date: {date}"
        )

    # DELETE /showmovies/<date>
    def DeleteSchedule(self, request, context):
        date = request.date

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD"
            )

        for i, e in enumerate(self.schedule):
            if e.get("date") == date:
                deleted = self.schedule.pop(i)
                try:
                    save_schedule(self.schedule)
                except Exception:
                    context.abort(
                        grpc.StatusCode.INTERNAL,
                        "Failed to save schedule"
                    )

                deleted_msg = schedule_pb2.ScheduleEntry(
                    date=deleted["date"],
                    movies=deleted.get("movies", [])
                )
                return schedule_pb2.DeleteScheduleResponse(
                    success=True,
                    message=f"Schedule deleted for date: {date}",
                    deleted_entry=deleted_msg
                )

        context.abort(
            grpc.StatusCode.NOT_FOUND,
            f"Schedule not found for date: {date}"
        )

    # GET /showmovies/<date>/best-rated
    def GetBestRatedMovie(self, request, context):
        date = request.date

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD"
            )

        day_entry = None
        for e in self.schedule:
            if e.get("date") == date:
                day_entry = e
                break

        if day_entry is None:
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Schedule not found for date: {date}"
            )

        movies_today = day_entry.get("movies", [])

        if len(movies_today) == 0:
            return schedule_pb2.BestRatedResponse(
                date=date,
                movie=schedule_pb2.Movie(),  # vide
                rating=0.0,
                message="no movies scheduled for this date"
            )

        best_movie_json = None
        best_rating = -1.0

        for movie_id in movies_today:
            info = get_movie(movie_id)
            if info is None:
                continue

            rating = info.get("rating")
            try:
                rating_val = float(rating)
            except (TypeError, ValueError):
                continue

            if rating_val > best_rating:
                best_rating = rating_val
                best_movie_json = info

        if best_movie_json is None:
            return schedule_pb2.BestRatedResponse(
                date=date,
                movie=schedule_pb2.Movie(),
                rating=0.0,
                message="no valid movie info found for this date"
            )

        movie_msg = schedule_pb2.Movie(
            id=str(best_movie_json.get("id", "")),
            title=str(best_movie_json.get("title", "")),
            rating=float(best_movie_json.get("rating", 0.0)),
            director=str(best_movie_json.get("director", ""))
        )

        return schedule_pb2.BestRatedResponse(
            date=date,
            movie=movie_msg,
            rating=best_rating,
            message=""
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    schedule_pb2_grpc.add_ScheduleServicer_to_server(ScheduleServicer(), server)
    server.add_insecure_port(f"[::]:{PORT}")
    server.start()
    print(f"gRPC Schedule server running on port {PORT}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
