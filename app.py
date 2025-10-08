import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


# ===============================
# Backend: Scraper Function
# ===============================
def scrape_instagram_reels(username, start_date, end_date):
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME") or "bethe_shit"
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD") or "Imthebobby"
    TARGET_PROFILE = username
    START_DATE = start_date.strftime("%Y-%m-%d")
    END_DATE = end_date.strftime("%Y-%m-%d")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--headless=new")  # headless for Streamlit
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 7)

    st.info("🔐 Logging into Instagram...")
    driver.get("https://www.instagram.com/accounts/login/")
    wait.until(EC.presence_of_element_located((By.NAME, "username")))
    driver.find_element(By.NAME, "username").send_keys(INSTAGRAM_USERNAME)
    driver.find_element(By.NAME, "password").send_keys(INSTAGRAM_PASSWORD)
    driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
    time.sleep(7)

    st.info(f"📸 Opening {TARGET_PROFILE}'s Reels page...")
    driver.get(f"https://www.instagram.com/{TARGET_PROFILE}/reels/")
    time.sleep(5)

    all_data = []
    stop_scraping = False
    batches_scraped = 0
    reels_container_xpath = '/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/div[2]/div/div'

    while not stop_scraping:
        try:
            reels_container = driver.find_element(By.XPATH, reels_container_xpath)
        except Exception:
            break

        batch_elements = reels_container.find_elements(By.XPATH, './div/div')
        total_batches = len(batch_elements)
        st.write(f"📦 Batches loaded: {total_batches}")

        for batch_index in range(batches_scraped, total_batches):
            if stop_scraping:
                break

            batch = batch_elements[batch_index]
            reel_links = batch.find_elements(By.XPATH, './div/div/a')
            batch_reels = []

            for reel in reel_links:
                reel_url = reel.get_attribute("href")
                try:
                    views_text = reel.find_element(By.XPATH, ".//div[2]/div[2]/div/div[2]/div/span/span").text
                except NoSuchElementException:
                    views_text = "N/A"
                batch_reels.append((reel_url, views_text))

            for reel_url, views in batch_reels:
                driver.execute_script("window.open(arguments[0]);", reel_url)
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(3)
                try:
                    date_str = driver.find_element(By.TAG_NAME, "time").get_attribute("datetime")[:10]
                    time_str = driver.find_element(By.TAG_NAME, "time").get_attribute("datetime")[11:23]
                except NoSuchElementException:
                    date_str, time_str = "N/A", "N/A"

                if batch_index > 0 and date_str != "N/A" and date_str < START_DATE:
                    stop_scraping = True
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    break

                likes = "N/A"
                try:
                    likes = driver.find_element(By.CSS_SELECTOR, "span.html-span.xdj266r.x14z9mp.xat24cr").text
                except:
                    pass

                # caption + comments
                comments = []
                try:
                    comments_container = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.x5yr21d"))
                    )
                    caption_elem = comments_container.find_element(By.XPATH, './/div/div[1]/div/div[2]/div/span/div/span')
                    caption_text = caption_elem.text.strip()
                    comments.append(caption_text)
                except:
                    pass

                all_data.append({
                    "URL": reel_url,
                    "Views": views,
                    "Date": date_str,
                    "Time": time_str,
                    "Likes": likes,
                    "Comment": "; ".join(comments)
                })

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)

            batches_scraped += 1

        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(2)

    driver.quit()
    if all_data:
        df = pd.DataFrame(all_data)
        csv_path = f"{TARGET_PROFILE}_reels_data.csv"
        df.to_csv(csv_path, index=False)
        st.success(f"✅ Scraping completed successfully! Data saved to {csv_path}")
        return csv_path
    else:
        st.warning("⚠️ No data scraped.")
        return None


# ===============================
# Streamlit Frontend
# ===============================
st.title("📊 Instagram Reels Scraper & Sentiment Dashboard")

selected_user = st.text_input("👤 Enter Instagram Username").strip()
from_date = st.date_input("📅 From Date")
to_date = st.date_input("📅 To Date")

if st.button("📑 Get Report"):
    if not selected_user:
        st.warning("Please enter a username.")
    elif not from_date or not to_date:
        st.warning("Please select valid date range.")
    else:
        with st.spinner("🔍 Scraping data... please wait, this may take a few minutes ⏳"):
            scraped_file = scrape_instagram_reels(selected_user, from_date, to_date)

        if scraped_file:
            st.info("📂 Loading scraped data...")
            df = pd.read_csv(scraped_file)
            st.write(f"Total records: {len(df)}")
            st.dataframe(df.head())
