import requests

# Set your API details
KODI_URL = "PUT JSONRPC KODI URL HERE"
RADARR_URL = "PUT RADARR URL HERE"
RADARR_API_KEY = "PUT RADARR API KEY HERE"

def get_watched_movies_from_kodi():
    payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetMovies",
        "params": {
            "filter": {"operator": "greaterthan", "field": "playcount", "value": "0"},
            "properties": ["title", "imdbnumber", "playcount"]
        },
        "id": 1
    }
    try:
        response = requests.post(KODI_URL, json=payload, timeout=10).json()
        return response.get('result', {}).get('movies', [])
    except Exception as e:
        print(f"Error connecting to Kodi: {e}")
        return []

def update_kodi_library():
    """Triggers Kodi to clean removed files and scan for library updates."""
    print("\nUpdating Kodi Video Library...")
    
    # 1. Clean dead/deleted files from Kodi DB
    clean_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.Clean",
        "id": 1
    }
    # 2. Rescan Video Library
    scan_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.Scan",
        "id": 1
    }
    
    try:
        requests.post(KODI_URL, json=clean_payload, timeout=10)
        print("[SUCCESS] Sent 'Clean Library' command to Kodi.")
        
        requests.post(KODI_URL, json=scan_payload, timeout=10)
        print("[SUCCESS] Sent 'Scan Library' command to Kodi.")
    except Exception as e:
        print(f"[FAILED] Could not trigger Kodi library update: {e}")

def get_radarr_movies():
    headers = {"X-Api-Key": RADARR_API_KEY}
    try:
        response = requests.get(f"{RADARR_URL}/api/v3/movie", headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error connecting to Radarr: {e}")
        return []

def main():
    print("Fetching watched movies from Kodi...")
    kodi_movies = get_watched_movies_from_kodi()
    
    if not kodi_movies:
        print("No watched movies found in Kodi.")
        return

    print("Fetching library from Radarr...")
    radarr_movies = get_radarr_movies()

    # Find matches between Kodi watched list and Radarr library
    to_delete = []
    for k_movie in kodi_movies:
        imdb_id = k_movie.get('imdbnumber')
        title = k_movie.get('title')
        
        for r_movie in radarr_movies:
            if (imdb_id and r_movie.get('imdbId') == imdb_id) or (r_movie.get('title', '').lower() == title.lower()):
                to_delete.append(r_movie)
                break

    if not to_delete:
        print("No matching watched movies found in Radarr.")
        return

    # List movies identified for deletion
    print("\n" + "="*50)
    print("The following watched movies were found in Radarr:")
    print("="*50)
    for index, movie in enumerate(to_delete, start=1):
        year = movie.get('year', 'N/A')
        print(f"{index}. {movie['title']} ({year}) [ID: {movie['id']}]")
    print("="*50)

    # Prompt user for confirmation
    confirm = input(f"\nAre you sure you want to delete these {len(to_delete)} movie(s) from Radarr and disk? (y/N): ").strip().lower()
    
    if confirm == 'y':
        headers = {"X-Api-Key": RADARR_API_KEY}
        print("\nDeleting movies from Radarr...")
        deleted_any = False
        
        for movie in to_delete:
            movie_id = movie['id']
            delete_url = f"{RADARR_URL}/api/v3/movie/{movie_id}?deleteFiles=true&addImportExclusion=false"
            res = requests.delete(delete_url, headers=headers)
            
            if res.status_code == 200:
                print(f"[SUCCESS] Deleted from Radarr: {movie['title']}")
                deleted_any = True
            else:
                print(f"[FAILED] Could not delete {movie['title']}: {res.status_code}")

        # Update Kodi Library if deletions took place
        if deleted_any:
            update_kodi_library()

        print("\nProcess finished.")
    else:
        print("\nOperation cancelled. No files or entries were deleted.")

if __name__ == "__main__":
    main()