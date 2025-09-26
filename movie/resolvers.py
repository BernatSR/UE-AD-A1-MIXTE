import json
import requests

def check_admin_user(user_id):
    """Check if a user is admin by calling the user service"""
    try:
        response = requests.get(f"http://localhost:3203/users/{user_id}/admin", timeout=5)
        if response.status_code == 200:
            return response.json().get("is_admin", False)
        elif response.status_code == 404:
            raise Exception(f"User with ID {user_id} not found")
        else:
            raise Exception("Failed to verify user admin status")
    except requests.exceptions.RequestException:
        raise Exception("Unable to connect to user service")

def movie_with_id(_,info,_id):
    with open('{}/data/movies.json'.format("."), "r") as file:
        movies = json.load(file)
        for movie in movies['movies']:
            if movie['id'] == _id:
                return movie
            
def update_movie_rate(_,info,_id,_rate,_user_id):
    # Check if user is admin
    if not check_admin_user(_user_id):
        raise Exception("Access denied: Only admin users can update movie ratings")
    
    newmovies = {}
    newmovie = {}
    with open('{}/data/movies.json'.format("."), "r") as rfile:
        movies = json.load(rfile)
        for movie in movies['movies']:
            if movie['id'] == _id:
                movie['rating'] = _rate
                newmovie = movie
                newmovies = movies
                break
        else:
            raise Exception(f"Movie with ID {_id} not found")
    
    with open('{}/data/movies.json'.format("."), "w") as wfile:
        json.dump(newmovies, wfile, indent=2)
    return newmovie


def resolve_actors_in_movie(movie, info):
    with open('{}/data/actors.json'.format("."), "r") as file:
        actors = json.load(file)
        result = [actor for actor in actors['actors'] if movie['id'] in actor['films']]
        return result

def all_movies(_, info):
    with open('{}/data/movies.json'.format("."), "r") as file:
        movies = json.load(file)
        return movies['movies']

def add_movie(_, info, _id, _title, _director, _rating, _user_id):
    # Check if user is admin
    if not check_admin_user(_user_id):
        raise Exception("Access denied: Only admin users can add movies")
    
    new_movie = {
        "id": _id,
        "title": _title,
        "director": _director,
        "rating": _rating
    }
    
    with open('{}/data/movies.json'.format("."), "r") as rfile:
        movies = json.load(rfile)
        
    # Check if movie with this ID already exists
    for movie in movies['movies']:
        if movie['id'] == _id:
            raise Exception(f"Movie with ID {_id} already exists")
    
    movies['movies'].append(new_movie)
    
    with open('{}/data/movies.json'.format("."), "w") as wfile:
        json.dump(movies, wfile, indent=2)
    
    return new_movie

def delete_movie(_, info, _id, _user_id):
    # Check if user is admin
    if not check_admin_user(_user_id):
        raise Exception("Access denied: Only admin users can delete movies")
    
    with open('{}/data/movies.json'.format("."), "r") as rfile:
        movies = json.load(rfile)
    
    original_count = len(movies['movies'])
    movies['movies'] = [movie for movie in movies['movies'] if movie['id'] != _id]
    
    if len(movies['movies']) == original_count:
        raise Exception(f"Movie with ID {_id} not found")
    
    with open('{}/data/movies.json'.format("."), "w") as wfile:
        json.dump(movies, wfile, indent=2)
    
    return f"Movie with ID {_id} deleted successfully"
    
