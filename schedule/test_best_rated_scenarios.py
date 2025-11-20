import grpc
from google.protobuf.empty_pb2 import Empty

import schedule_pb2
import schedule_pb2_grpc


# ---------- Helpers d'affichage ----------

def print_schedule_entry(entry, prefix="  "):
    print(f"{prefix}- date = {entry.date}, movies = {list(entry.movies)}")


def print_all_schedules(stub, title="\n=== Schedules actuels ==="):
    print(title)
    all_sched = stub.GetAllSchedules(Empty())
    if len(all_sched.schedules) == 0:
        print("  (vide)")
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


def wait_for_enter():
    input("\nAppuie sur Entrée pour lancer le scénario suivant...")


# ---------- Scénarios de tests GetBestRatedMovie ----------

def scenario_1_invalid_format(stub):
    """
    CT1 : date au mauvais format -> INVALID_ARGUMENT
    """
    print("\n=== Scénario 1 : date au mauvais format ===")
    print_all_schedules(stub)
    wait_for_enter()

    bad_date = "2025-01-01"  # format invalide
    try:
        stub.GetBestRatedMovie(schedule_pb2.DateRequest(date=bad_date))
        fail("GetBestRatedMovie aurait dû échouer (format invalide)")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            ok(f"Erreur attendue INVALID_ARGUMENT pour la date {bad_date}")
        else:
            fail(f"Code d'erreur inattendu : {e.code()} - {e.details()}")


def scenario_2_date_not_found(stub):
    """
    CT2 : date correcte mais absente du schedule -> NOT_FOUND
    """
    print("\n=== Scénario 2 : date absente du schedule ===")
    print_all_schedules(stub)
    wait_for_enter()

    test_date = "20991231"

    # On vérifie que la date n'existe pas (et on la supprime si jamais elle existe)
    try:
        stub.DeleteSchedule(schedule_pb2.DateRequest(date=test_date))
        ok(f"Ancien schedule sur {test_date} supprimé pour repartir proprement")
    except grpc.RpcError:
        pass  # pas grave si elle n'existait pas

    try:
        stub.GetBestRatedMovie(schedule_pb2.DateRequest(date=test_date))
        fail("GetBestRatedMovie aurait dû échouer (date absente)")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            ok(f"Erreur attendue NOT_FOUND pour la date {test_date}")
        else:
            fail(f"Code d'erreur inattendu : {e.code()} - {e.details()}")

    print_all_schedules(stub, "\n=== Après scénario 2 ===")


def scenario_3_date_without_movies(stub):
    """
    CT3 : date présente mais sans films -> BestRatedResponse vide + message
    """
    print("\n=== Scénario 3 : date avec 0 film programmé ===")
    print_all_schedules(stub)
    wait_for_enter()

    test_date = "20990101"

    # On supprime si déjà présent
    try:
        stub.DeleteSchedule(schedule_pb2.DateRequest(date=test_date))
    except grpc.RpcError:
        pass

    # On crée un schedule vide
    stub.CreateSchedule(
        schedule_pb2.CreateScheduleRequest(
            date=test_date,
            movies=[]
        )
    )
    ok(f"Schedule créé pour {test_date} avec 0 film")

    resp = stub.GetBestRatedMovie(schedule_pb2.DateRequest(date=test_date))
    print(f"  Réponse : date={resp.date}, rating={resp.rating}, message='{resp.message}'")

    assert_equal(resp.date, test_date, "La date dans la réponse est correcte")
    assert_equal(resp.rating, 0.0, "Rating = 0.0 quand aucun film n'est programmé")
    assert_equal(resp.message, "no movies scheduled for this date",
                 "Message explicite quand aucun film n'est programmé")

    print_all_schedules(stub, "\n=== Après scénario 3 ===")


def scenario_4_all_movies_invalid_in_movie_service(stub):
    """
    CT4 : tous les IDs de films sont inconnus du service Movie
    -> pas de film valide, message 'no valid movie info found for this date'
    """
    print("\n=== Scénario 4 : tous les films sont inconnus du service Movie ===")
    print_all_schedules(stub)
    wait_for_enter()

    test_date = "20990102"

    # On supprime si déjà présent
    try:
        stub.DeleteSchedule(schedule_pb2.DateRequest(date=test_date))
    except grpc.RpcError:
        pass

    fake_movies = ["id-inconnu-1", "id-inconnu-2"]

    stub.CreateSchedule(
        schedule_pb2.CreateScheduleRequest(
            date=test_date,
            movies=fake_movies
        )
    )
    ok(f"Schedule créé pour {test_date} avec uniquement des IDs inconnus")

    resp = stub.GetBestRatedMovie(schedule_pb2.DateRequest(date=test_date))
    print(f"  Réponse : date={resp.date}, rating={resp.rating}, message='{resp.message}'")

    assert_equal(resp.date, test_date, "La date dans la réponse est correcte")
    assert_equal(resp.rating, 0.0, "Rating = 0.0 quand aucun film n'est valide")
    assert_equal(resp.message, "no valid movie info found for this date",
                 "Message explicite quand aucun film n'est valide côté Movie")

    print_all_schedules(stub, "\n=== Après scénario 4 ===")


def scenario_5_valid_existing_data(stub):
    """
    CT5 : cas "heureux" sur une date qui existe déjà dans les données de base
    (par ex. 20151205, utilisée dans le TP).
    """
    print("\n=== Scénario 5 : cas heureux sur une date de la base (ex: 20151205) ===")
    print_all_schedules(stub)
    wait_for_enter()

    test_date = "20151205"
    try:
        best = stub.GetBestRatedMovie(schedule_pb2.DateRequest(date=test_date))
        print(
            f"  Best rated movie for {test_date}: "
            f"{best.movie.title} (id={best.movie.id}, rating={best.rating})"
        )
        ok("GetBestRatedMovie a réussi sur une date existante avec des films")
    except grpc.RpcError as e:
        fail(f"GetBestRatedMovie a échoué : {e.code()} - {e.details()}")


def scenario_6_mix_valid_and_invalid_movies(stub):
    """
    CT6 : mélange d'IDs valides et invalides.
    On vérifie que :
      - les films inconnus sont ignorés
      - on obtient quand même un film valide comme meilleur.
    ATTENTION : nécessite qu'au moins un ID choisi existe vraiment dans Movie.
    """
    print("\n=== Scénario 6 : mélange d'IDs valides et invalides ===")
    print_all_schedules(stub)
    wait_for_enter()

    test_date = "20990103"

    # ID supposé valide (utilisé dans le fichier de tests du TP)
    valid_movie_id = "a8034f44-aee4-44cf-b32c-74cf452aaaae"
    invalid_movie_id = "id-inconnu-XYZ"

    # On nettoie éventuellement l'ancienne entrée
    try:
        stub.DeleteSchedule(schedule_pb2.DateRequest(date=test_date))
    except grpc.RpcError:
        pass

    stub.CreateSchedule(
        schedule_pb2.CreateScheduleRequest(
            date=test_date,
            movies=[valid_movie_id, invalid_movie_id]
        )
    )
    ok(f"Schedule créé pour {test_date} avec un film valide et un film invalide")

    best = stub.GetBestRatedMovie(schedule_pb2.DateRequest(date=test_date))
    print(
        f"  Best rated movie for {test_date}: "
        f"{best.movie.title} (id={best.movie.id}, rating={best.rating})"
    )

    if best.movie.id == valid_movie_id:
        ok("Le meilleur film retourné est bien l'ID valide (les invalides ont été ignorés)")
    else:
        fail("Le film retourné n'est pas l'ID valide attendu (vérifier les données Movie)")

    print_all_schedules(stub, "\n=== Après scénario 6 ===")


# ---------- main ----------

def main():
    print("=== Connexion au service gRPC Schedule ===")
    channel = grpc.insecure_channel("localhost:3202")
    stub = schedule_pb2_grpc.ScheduleStub(channel)

    # Enchaînement des scénarios
    scenario_1_invalid_format(stub)
    scenario_2_date_not_found(stub)
    scenario_3_date_without_movies(stub)
    scenario_4_all_movies_invalid_in_movie_service(stub)
    scenario_5_valid_existing_data(stub)
    scenario_6_mix_valid_and_invalid_movies(stub)

    print("\n=== ✔ TOUS LES SCÉNARIOS ONT ÉTÉ EXÉCUTÉS ===")


if __name__ == "__main__":
    main()
