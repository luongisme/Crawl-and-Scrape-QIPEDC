import os
import csv
import time
import requests
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm


BASE_URL = "https://qipedc.moet.gov.vn"
DICTIONARY_URL = f"{BASE_URL}/dictionary"

OUTPUT_DIR = "QIPEDC_TEST"
VIDEO_DIR = os.path.join(OUTPUT_DIR, "Videos")
CSV_PATH = os.path.join(OUTPUT_DIR, "metadata.csv")

os.makedirs(VIDEO_DIR, exist_ok=True)


def create_driver():
    options = Options()
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(options=options)


def crawl_first_page():
    driver = create_driver()
    videos = []

    selector = (
        "section:nth-of-type(2) "
        "> div:nth-of-type(2) "
        "> div:nth-of-type(1) "
        "> a"
    )

    try:
        driver.get(DICTIONARY_URL)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, selector)
            )
        )

        cards = driver.find_elements(
            By.CSS_SELECTOR,
            selector
        )

        print(f"Found {len(cards)} cards")

        for card in cards:
            try:
                label = card.find_element(
                    By.CSS_SELECTOR,
                    "p"
                ).text.strip()

                img = card.find_element(
                    By.CSS_SELECTOR,
                    "img"
                )

                thumbnail_url = img.get_attribute("src")

                filename = os.path.basename(
                    urlparse(thumbnail_url).path
                )

                video_id = os.path.splitext(filename)[0]

                video_url = (
                    f"{BASE_URL}/videos/{video_id}.mp4"
                )

                videos.append({
                    "video_id": video_id,
                    "label": label,
                    "video_url": video_url,
                    "thumbnail_url": thumbnail_url
                })

                print(
                    f"{label} -> {video_id}"
                )

            except Exception as e:
                print("Parse error:", e)

    finally:
        driver.quit()

    return videos


def save_metadata(videos):
    with open(
        CSV_PATH,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "VIDEO_ID",
            "LABEL",
            "VIDEO_FILE",
            "VIDEO_URL",
            "THUMBNAIL_URL"
        ])

        for item in videos:
            writer.writerow([
                item["video_id"],
                item["label"],
                item["video_id"] + ".mp4",
                item["video_url"],
                item["thumbnail_url"]
            ])

    print(f"\nMetadata saved: {CSV_PATH}")


def download_video(item):
    filename = item["video_id"] + ".mp4"

    output_path = os.path.join(
        VIDEO_DIR,
        filename
    )

    if os.path.exists(output_path):
        print(f"Skip: {filename}")
        return

    try:
        response = requests.get(
            item["video_url"],
            stream=True,
            timeout=30,
            verify=False
        )

        response.raise_for_status()

        total_size = int(
            response.headers.get(
                "content-length",
                0
            )
        )

        with open(output_path, "wb") as f:
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=filename,
                ncols=90
            ) as bar:

                for chunk in response.iter_content(
                    chunk_size=8192
                ):

                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))

        print(
            f"Downloaded: "
            f"{item['label']} -> {filename}"
        )

    except Exception as e:
        print(
            f"Failed {filename}: {e}"
        )

        if os.path.exists(output_path):
            os.remove(output_path)


def main():
    print("=== CRAWL PAGE 1 ===")

    videos = crawl_first_page()

    if not videos:
        print("No videos found.")
        return

    print(
        f"\nTotal: {len(videos)} videos"
    )

    # Quan trọng: save metadata trước
    save_metadata(videos)

    print("\n=== DOWNLOAD ===")

    for i, item in enumerate(videos, start=1):
        print(
            f"\n[{i}/{len(videos)}] "
            f"{item['label']}"
        )

        download_video(item)

        # Không spam server
        time.sleep(0.5)

    print("\n=== DONE ===")
    print(f"Check folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()