import grpc
from concurrent import futures
import json
import os
import requests

from datetime import datetime

import schedule_pb2
import schedule_pb2_grpc


DATABASE_PATH = "./databases/times.json"


def load_schedule():
    try:
        with open(DATABASE_PATH, "r", encoding="utf-8") as jsf:
            return json.load(jsf)["schedule"]
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def save_schedule(schedule_data):
    try:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        data = {"schedule": schedule_data}
        with open(DATABASE_PATH, "w", encoding="utf-8") as jsf:
            json.dump(data, jsf, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving schedule: {e}")
        raise


def validate_date_format(date_str: str) -> bool:
    if len(date_str) != 8 or not date_str.isdigit():
        return False
    # Optionnel : vérif date réelle
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return True
    except ValueError:
        return False


def get_movie(movie_id: str):
    try:
        r = requests.get(f"http://localhost:3200/movies/{movie_id}", timeout=3)
    except requests.RequestException:
        return None

    if r.status_code == 200:
        return r.json()
    return None


class ScheduleServicer(schedule_pb2_grpc.ScheduleServicer):
    def __init__(self):
        self.schedule = load_schedule()

    # ---------- READ ---------- #
    def GetAllSchedules(self, request, context):
        items = []
        for entry in self.schedule:
            item = schedule_pb2.ScheduleEntry(
                date=entry.get("date", ""),
                movies=entry.get("movies", []),
            )
            items.append(item)

        return schedule_pb2.ScheduleList(entries=items)


    def GetScheduleByDate(self, request, context):
        date = request.date

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD",
            )

        for entry in self.schedule:
            if entry.get("date") == date:
                return schedule_pb2.ScheduleEntry(
                    date=entry.get("date", ""),
                    movies=entry.get("movies", []),
                )

        context.abort(
            grpc.StatusCode.NOT_FOUND,
            f"Schedule not found for date: {date}",
        )

    # ---------- CREATE ---------- #
    def AddScheduleEntry(self, request, context):
        date = request.date
        movies = list(request.movies)

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD",
            )

        for entry in self.schedule:
            if entry.get("date") == date:
                context.abort(
                    grpc.StatusCode.ALREADY_EXISTS,
                    f"Schedule already exists for date: {date}",
                )

        if not movies:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Missing 'movies' (must be a non-empty array)",
            )

        for movie in movies:
            if not isinstance(movie, str) or len(movie.strip()) == 0:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "All movie entries must be non-empty strings",
                )

        new_entry = {"date": date, "movies": movies}
        self.schedule.append(new_entry)

        try:
            save_schedule(self.schedule)
        except Exception:
            context.abort(
                grpc.StatusCode.INTERNAL,
                "Failed to save schedule",
            )

        return schedule_pb2.ScheduleEntry(date=date, movies=movies)

    # ---------- DELETE ---------- #
    def DeleteScheduleEntry(self, request, context):
        date = request.date

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD",
            )

        for i, entry in enumerate(self.schedule):
            if entry.get("date") == date:
                deleted = self.schedule.pop(i)
                try:
                    save_schedule(self.schedule)
                except Exception:
                    context.abort(
                        grpc.StatusCode.INTERNAL,
                        "Failed to save schedule",
                    )

                return schedule_pb2.DeleteScheduleResponse(
                    message=f"Schedule deleted for date: {date}",
                    deleted_entry=schedule_pb2.ScheduleEntry(
                        date=deleted.get("date", ""),
                        movies=deleted.get("movies", []),
                    ),
                )

        context.abort(
            grpc.StatusCode.NOT_FOUND,
            f"Schedule not found for date: {date}",
        )

    # ---------- UPDATE ---------- #
    def UpdateScheduleEntry(self, request, context):
        date = request.date
        movies = list(request.movies)

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD",
            )

        for i, entry in enumerate(self.schedule):
            if entry.get("date") == date:
                if not movies:
                    context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "Missing 'movies' (must be a non-empty array)",
                    )

                for movie in movies:
                    if not isinstance(movie, str) or len(movie.strip()) == 0:
                        context.abort(
                            grpc.StatusCode.INVALID_ARGUMENT,
                            "All movie entries must be non-empty strings",
                        )

                try:
                    self.schedule[i]["movies"] = movies
                    save_schedule(self.schedule)
                except Exception:
                    context.abort(
                        grpc.StatusCode.INTERNAL,
                        "Failed to save schedule",
                    )

                return schedule_pb2.ScheduleEntry(
                    date=date,
                    movies=movies,
                )

        context.abort(
            grpc.StatusCode.NOT_FOUND,
            f"Schedule not found for date: {date}",
        )

    # ---------- ENDPOINT SUPPLEMENTAIRE : Best rated scheduled movie ---------- #
    def BestRatedScheduledMovie(self, request, context):
        date = request.date

        if not validate_date_format(date):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid date format. Use YYYYMMDD",
            )

        day_entry = None
        for entry in self.schedule:
            if entry.get("date") == date:
                day_entry = entry
                break

        if day_entry is None:
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Schedule not found for date: {date}",
            )

        movies_today = day_entry.get("movies", [])

        if len(movies_today) == 0:
            return schedule_pb2.BestRatedResponse(
                date=date,
                message="no movies scheduled for this date",
                has_movie=False,
            )

        best_movie = None
        best_rating = -1.0

        for movie_id in movies_today:
            info = get_movie(movie_id)
            if info is None:
                continue

            rating = info.get("rating")
            if rating is None:
                continue

            if rating > best_rating:
                best_rating = rating
                best_movie = info

        if best_movie is None:
            return schedule_pb2.BestRatedResponse(
                date=date,
                message="no valid rated movies for this date",
                has_movie=False,
            )

        movie_msg = schedule_pb2.Movie(
            id=str(best_movie.get("id", "")),
            title=best_movie.get("title", ""),
            director=best_movie.get("director", ""),
            rating=float(best_movie.get("rating", 0.0)),
        )

        return schedule_pb2.BestRatedResponse(
            date=date,
            has_movie=True,
            movie=movie_msg,
            rating=best_rating,
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    schedule_pb2_grpc.add_ScheduleServicer_to_server(ScheduleServicer(), server)
    server.add_insecure_port("[::]:3002")
    print("Schedule gRPC server running on port 3002")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
