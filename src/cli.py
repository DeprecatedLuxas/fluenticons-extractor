import click
import os
import requests
import json
import ramda
import shutil
import re

API_URI = "https://api.figma.com/v1/"

PATTERN = re.compile('=[0-9]{2}')


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
        print(response.status_code)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return None
    except (Exception, requests.HTTPError, requests.exceptions.SSLError) as exception:
        print("Error occurred attpempting to make an api request. {0}".format(exception))
        return None

def create_size_directories(sizes, out_dir):
    if not os.path.exists(out_dir):
            os.mkdir(out_dir)

    for folder in sizes:
        if not os.path.exists(os.path.join(out_dir, folder)):
            os.mkdir(os.path.join(out_dir, folder))


def get_figma_files(token, file_key):
    data = request_figma_api(token, 'files/{0}'.format(file_key))
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
    data = request_figma_api(token, 'images/{0}?ids={1}&format=svg'.format(file_key, ids))
    print(data)
    if data is not None:
        return FigmaImages(data["images"], data["err"])

def save_image(out_dir, name, size, image_url):
    dir_out = os.path.join(out_dir, size)
    name = "{0}.svg".format(name)
    file_out = os.path.join(dir_out, name)
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        response.raw.decode_content = True
        with open(file_out, "wb") as file:
            shutil.copyfileobj(response.raw, file)
            print('Saving image {0}'.format(name))
def divide_chunks(l, n):
      
    # looping till length l
    for i in range(0, len(l), n): 
        yield l[i:i + n]

@click.command()
@click.option('--token', '--t', 'token', required=True, help='Figma API Token')
@click.option('--key', '--k', 'file_key', required=True, help='The filekey of the figma')
@click.option('--out', '--o', 'out_dir', default='./icons', help='The dir to output the files in')
def cli(token, out_dir, file_key):
    files = get_figma_files(token, file_key)

    component_ids = []
    size_map = []
    images = {}
    
    for key in files.components:

        component_ids.append(key)

        if re.findall(r'=[0-9]{2}', ramda.prop('name')(files.components[key])):
            component_size = PATTERN.findall(ramda.prop("name")(files.components[key]))[0].replace('=', '')
        else:
            continue

        size_map.append(component_size)

    chunked_component_ids = list(divide_chunks(component_ids, 100))
    
    size_map = list(dict.fromkeys(size_map))
    for chunk in chunked_component_ids:
        image_dict = get_figma_images(token, file_key, ','.join(chunk)).images
        images.update(image_dict)

    create_size_directories(size_map, out_dir)
    for key in component_ids:
        if re.findall(r'=[0-9]{2}', ramda.prop('name')(files.components[key])):
            size = PATTERN.findall(ramda.prop("name")(files.components[key]))[0].replace('=', '')
        else:
            continue
        save_image(
            out_dir,
            ramda.prop("key")(files.components[key]),
            size,
            images[key],
        )

if __name__ == "__main__":
    cli()
   