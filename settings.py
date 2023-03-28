
def get_anki_mp3_directory() -> str:
    """
    Get the path to Anki media - this is where we will save mp3 files
    :return: the path to the location where Anki looks for mp3 files (and other media)
    For example, on a mac, this might be:
    /Users/{username}/Library/Application Support/Anki2/User 1/collection.media
    """
    raise Exception("set your Anki output directory")
    

def get_deepl_api_key() -> (str, bool):
    raise Exception("get a deepl api key and add it here. Return True for free key, False for a paid key.")
    # return "YOUR API KEY", True  # True if it is a free key, False if it is a paid key
