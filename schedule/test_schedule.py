import grpc
from google.protobuf.empty_pb2 import Empty

import schedule_pb2
import schedule_pb2_grpc


def print_schedule_entry(entry, prefix="  "):
    print(f"{prefix}- date = {entry.date}, movies = {list(entry.movies)}")


def print_all_schedules(stub, title="\n=== Current Schedules ==="):
    print(title)
    all_sched = stub.GetAllSchedules(Empty())
    if len(all_sched.schedules) == 0:
        print("  (empty)")
    else:
        for e in all_sched.schedules:
            print_schedule_entry(e)
    print("-----------------------------------")


def ok(msg):
    print(f"  ✔ {msg}")


def fail(msg):
    print(f"  ✘ {msg}")


def assert_equal(a, b, msg):
    if a == b:
        ok(msg)
    else:
        fail(f"{msg} — obtenu {a}, attendu {b}")


def main():
    print("=== Connecting to gRPC Schedule service ===")
    channel = grpc.insecure_channel("localhost:3202")
    stub = schedule_pb2_grpc.ScheduleStub(channel)

    test_date = "20151210"
    initial_movies = [
        "a8034f44-aee4-44cf-b32c-74cf452aaaae",
        "720d006c-3a57-4b6a-b18f-9b713b073f3c",
    ]
    updated_movies = [
        "39ab85e5-5e8e-4dc5-afea-65dc368bd7ab"
    ]

    # -------- 1. GET ALL --------
    print_all_schedules(stub, "\n=== 1. Initial schedules ===")
    all1 = stub.GetAllSchedules(Empty())

    if any(e.date == test_date for e in all1.schedules):
        fail("Test date already existed before test")
    else:
        ok("Test date correctly absent before test")

    # -------- 2. CREATE SCHEDULE --------
    print("\n=== 2. CreateSchedule ===")
    created = stub.CreateSchedule(
        schedule_pb2.CreateScheduleRequest(
            date=test_date,
            movies=initial_movies
        )
    )
    print("Created schedule:")
    print_schedule_entry(created)
    assert_equal(created.date, test_date, "Created schedule has correct date")
    assert_equal(list(created.movies), initial_movies, "Created movies match")

    print_all_schedules(stub, "\n=== After Create ===")

    # -------- 3. GET BY DATE --------
    print("\n=== 3. GetScheduleByDate ===")
    got = stub.GetScheduleByDate(schedule_pb2.DateRequest(date=test_date))
    print("Fetched schedule:")
    print_schedule_entry(got)
    assert_equal(list(got.movies), initial_movies, "Fetched movies match created")
    print_all_schedules(stub, "\n=== After GetByDate ===")

    # -------- 4. UPDATE --------
    print("\n=== 4. UpdateSchedule ===")
    updated = stub.UpdateSchedule(
        schedule_pb2.UpdateScheduleRequest(
            date=test_date,
            movies=updated_movies
        )
    )
    print("Updated schedule:")
    print_schedule_entry(updated)
    assert_equal(list(updated.movies), updated_movies, "Updated movies stored")
    print_all_schedules(stub, "\n=== After Update ===")

    # -------- 5. GET BEST RATED --------
    print("\n=== 5. GetBestRatedMovie ===")
    try:
        test_date2="20151205"
        best = stub.GetBestRatedMovie(schedule_pb2.DateRequest(date=test_date2))
        print(
            f"  Best rated movie for {test_date2}: "
            f"{best.movie.title} (id={best.movie.id}, rating={best.rating})"
        )
        ok("BestRatedMovie executed successfully")
    except grpc.RpcError as e:
        fail(f"GetBestRatedMovie failed: {e.code()} - {e.details()}")
    print_all_schedules(stub, "\n=== After BestRatedMovie ===")

    # -------- 6. DELETE --------
    print("\n=== 6. DeleteSchedule ===")
    deleted = stub.DeleteSchedule(schedule_pb2.DateRequest(date=test_date))
    print(f"Success: {deleted.success}, message: {deleted.message}")
    print("Deleted entry:")
    print_schedule_entry(deleted.deleted_entry)

    print_all_schedules(stub, "\n=== After Delete ===")

    # -------- 7. VERIFY REMOVAL --------
    print("\n=== 7. Verify deletion ===")
    try:
        stub.GetScheduleByDate(schedule_pb2.DateRequest(date=test_date))
        fail("Schedule still exists after delete")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            ok("Schedule correctly deleted")
        else:
            fail(f"Unexpected error after delete: {e.code()}")

    print_all_schedules(stub, "\n=== Final schedules ===")

    print("\n=== ✔ ALL TESTS COMPLETED ===")


if __name__ == "__main__":
    main()
