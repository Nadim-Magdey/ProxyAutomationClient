import requests
import zipfile
import shutil
from pathlib import Path
from version import VERSION

MANIFEST_URL = "https://yourserver.com/manifest.json"
BASE_DIR = Path(__file__).parent
TMP_DIR = BASE_DIR / "update_tmp"

def check_update():
    data = requests.get(MANIFEST_URL).json()
    return data

def download(url):
    TMP_DIR.mkdir(exist_ok=True)
    zip_path = TMP_DIR / "update.zip"

    r = requests.get(url)
    with open(zip_path, "wb") as f:
        f.write(r.content)

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(TMP_DIR)

    return TMP_DIR

def replace_files(new_dir):
    for item in BASE_DIR.iterdir():
        if item.name == "update_tmp":
            continue

        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    for item in new_dir.iterdir():
        shutil.move(str(item), str(BASE_DIR))

def main():
    data = check_update()

    if data["version"] != VERSION:
        print("Updating system...")
        new_files = download(data["url"])
        replace_files(new_files)
        print("Update complete")

if __name__ == "__main__":
    main()
