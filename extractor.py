__author__ = "Lucas Nørgård"
__version__ = "0.1.0"
__license__ = "MIT"


import os
import requests
import json
import shutil
import re
import concurrent.futures
import time
import argparse

SAVED = 0
API_URI = "https://api.figma.com/v1/"

PATTERN_SIZE = re.compile("=[0-9]{2}")
PATTERN_THEME = re.compile("=(Filled|Regular)")
PATTERN_WIDTH = re.compile('width="[0-9]+"')
PATTERN_HEIGHT = re.compile('height="[0-9]+"')


class FigmaFile:
    def __init__(self, name, document, components, last_modified, thumbnail_url, schema_version, styles):
        self.name = name
        self.last_modified = last_modified
        self.thumbnail_url = thumbnail_url
        self.document = document
        self.components = components
        self.schema_version = schema_version
        self.styles = styles


class FigmaImages:
    def __init__(self, images, err):
        self.err = err
        self.images = images


def request_figma_api(token, endpoint):
    headers = {"X-Figma-Token": "{0}".format(token), "Content-Type": "application/json"}
    try:
        response = requests.get("{0}{1}".format(API_URI, endpoint), headers=headers)

        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return None
    except (Exception, requests.HTTPError, requests.exceptions.SSLError) as exception:
        print("Error occurred attpempting to make an api request. {0}".format(exception))
        return None


def create_directories(sizes, out_dir):
    filled_path = os.path.join(out_dir, "filled")
    regular_path = os.path.join(out_dir, "regular")
    print("Creating directories")

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    if not os.path.exists(os.path.join(out_dir, "filed")):
        os.mkdir(os.path.join(out_dir, "filled"))

    if not os.path.exists(os.path.join(out_dir, "regular")):
        os.mkdir(os.path.join(out_dir, "regular"))

    for folder in sizes:
        if not os.path.exists(os.path.join(filled_path, folder)):
            os.mkdir(os.path.join(filled_path, folder))
        if not os.path.exists(os.path.join(regular_path, folder)):
            os.mkdir(os.path.join(regular_path, folder))


def get_figma_files(token, file_key):
    data = request_figma_api(token, "files/{0}".format(file_key))
    if data is not None:
        return FigmaFile(
            data["name"],
            data["document"],
            data["components"],
            data["lastModified"],
            data["thumbnailUrl"],
            data["schemaVersion"],
            data["styles"],
        )


def get_figma_images(token, file_key, ids):
    time.sleep(3)
    data = request_figma_api(token, "images/{0}?ids={1}&format=svg".format(file_key, ids))
    if data is not None:
        return FigmaImages(data["images"], data["err"])


def divide_chunks(l, n):

    # looping till length l
    for i in range(0, len(l), n):
        yield l[i : i + n]


def get_and_save_image(chunk):
    global SAVED
    image_dict = get_figma_images(TOKEN, FILE_KEY, ",".join(chunk)).images
    for key in chunk:

        theme = PATTERN_THEME.findall(files.components[key].get("name"))[0].lower()

        size = PATTERN_SIZE.findall(files.components[key].get("name"))[0].replace("=", "")
        dir_out = os.path.join(OUT_DIR, "{0}/{1}".format(theme, size))

        name = "{0}.svg".format(files.components[key].get("key"))
        file_out = os.path.join(dir_out, name)
        time.sleep(3)

        response = requests.get(image_dict[key])

        text = response.text
        if SCALE != "none":

            if (re.findall(r"width=\"[0-9]+\"", response.text)) and (re.findall(r"height=\"[0-9]+\"", response.text)):

                text = PATTERN_HEIGHT.sub(f'height="{SCALE}"', text)
                text = PATTERN_WIDTH.sub(f'width="{SCALE}"', text)
            else:
                print(f'{name} didn\'t have a height and width specified')
                continue
        if response.status_code == 200:

            with open(file_out, "w") as file:
                file.write(text)

                print(f"Saving image {name} with size {size} and theme {theme}")
                SAVED += 1


def main(args):
    global TOKEN
    global FILE_KEY
    global OUT_DIR
    global SIZE
    global SCALE
    global files
    global component_ids

    TOKEN = args.token
    FILE_KEY = args.key
    OUT_DIR = args.out
    SIZE = args.size
    SCALE = args.scale
    firstTimer = time.perf_counter()
    files = get_figma_files(TOKEN, FILE_KEY)
    component_ids = []
    size_map = []

    for key in files.components:
        if re.findall(r"=[0-9]{2}", files.components[key].get("name")):
            component_size = PATTERN_SIZE.findall(files.components[key].get("name"))[0].replace("=", "")
            if SIZE != "all":

                if component_size == SIZE:
                    size_map.append(component_size)
                    component_ids.append(key)
                else:
                    continue
            else:
                size_map.append(component_size)
                component_ids.append(key)
        else:
            continue
    # Splitted up because of the uri to long response code.
    chunked_component_ids = list(divide_chunks(component_ids, 100))
    size_map = list(dict.fromkeys(size_map))
    create_directories(size_map, OUT_DIR)

    with concurrent.futures.ThreadPoolExecutor() as executor:

        executor.map(get_and_save_image, chunked_component_ids)

    secondTimer = time.perf_counter()

    print(f"Finished in {secondTimer-firstTimer} seconds")
    print(f"Saved {SAVED} images")


if __name__ == "__main__":
    extractor_parser = argparse.ArgumentParser(description="List the content of a folder")
    extractor_parser.add_argument("-token", "--token", required=True)
    extractor_parser.add_argument("-key", "--key", required=True)
    extractor_parser.add_argument("-out", "--out", default="./icons")
    extractor_parser.add_argument("-size", "--size", default="all")
    extractor_parser.add_argument("-scale", "--scale", default="none")
    extractor_parser.add_argument(
        "--version", action="version", version="%(prog)s (version {version})".format(version=__version__)
    )
    args = extractor_parser.parse_args()
    main(args)