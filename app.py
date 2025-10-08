import streamlit as st
import pandas as pd
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from textblob import TextBlob
import undetected_chromedriver as uc

# ==============================
# 1️⃣ Streamlit UI Inputs
# ==============================
st.title("📊 Instagram Reels Scraper & Sentiment Dashboard")

selected_user = st.text_input("Enter Instagram Username").strip()
from_date = st.date_input("From")
to_date = st.date_input("To")

INSTAGRAM_USERNAME = st.text_input("Your Instagram Username").strip()
INSTAGRAM_PASSWORD = st.text_input("Your Instagram Password", type="password")

if st.button("📑 Get Report"):
    if not selected_user or not from_date or not to_date or not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        st.warning("Please enter all required fields!")
        st.stop()

    START_DATE = str(from_date)
    END_DATE = str(to_date)
    st.info("Starting scraping... This may take a few minutes depending on number of reels.")

    # ==============================
    # 2️⃣ Selenium Setup (Streamlit Cloud compatible)
    # ==============================
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = uc.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)

    try:
        # Login
        driver.get("https://www.instagram.com/accounts/login/")
        wait.until(EC.presence_of_element_located((By.NAME, "username")))
        driver.find_element(By.NAME, "username").send_keys(INSTAGRAM_USERNAME)
        driver.find_element(By.NAME, "password").send_keys(INSTAGRAM_PASSWORD)
        driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
        time.sleep(7)
        st.success("✅ Logged in successfully.")

        # Go to user's reels page
        driver.get(f"https://www.instagram.com/{selected_user}/reels/")
        time.sleep(5)
        st.info("Scraping reels...")

        all_data = []
        stop_scraping = False
        batches_scraped = 0
        reels_container_xpath = '//div[@role="main"]//div[contains(@class,"_aabd")]'

        while not stop_scraping:
            reels_container = driver.find_elements(By.XPATH, reels_container_xpath)
            if not reels_container:
                break

            for reel_elem in reels_container[batches_scraped:]:
                reel_url = reel_elem.find_element(By.TAG_NAME, "a").get_attribute("href")
                
                # Open reel in new tab
                driver.execute_script("window.open(arguments[0]);", reel_url)
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(2)

                # Get reel datetime
                try:
                    datetime_str = driver.find_element(By.TAG_NAME, "time").get_attribute("datetime")
                    date_str = datetime_str[:10]
                    time_str = datetime_str[11:19]
                except:
                    date_str = "N/A"
                    time_str = "N/A"

                # Stop if date is earlier than START_DATE
                if date_str != "N/A" and date_str < START_DATE:
                    stop_scraping = True
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    break

                if date_str != "N/A" and START_DATE <= date_str <= END_DATE:
                    # Likes
                    try:
                        likes = driver.find_element(By.CSS_SELECTOR, "section span").text
                    except:
                        likes = "N/A"

                    # Comments
                    all_comments_data = []
                    try:
                        comments_container = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//ul[contains(@class,"_aa_")]'))
                        )
                        comment_elems = comments_container.find_elements(By.XPATH, './/li//span')
                        for comment_elem in comment_elems:
                            text = comment_elem.text.strip()
                            if text:
                                all_comments_data.append(text)
                    except:
                        pass
                else:
                    likes = "Out of range"
                    all_comments_data = []

                if not all_comments_data:
                    all_comments_data = ["No comments / Caption unavailable"]

                # Process each comment
                for comment in all_comments_data:
                    sentiment_score = TextBlob(comment).sentiment.polarity
                    if sentiment_score > 0:
                        sentiment_label = "Positive"
                    elif sentiment_score < 0:
                        sentiment_label = "Negative"
                    else:
                        sentiment_label = "Neutral"

                    all_data.append({
                        "URL": reel_url,
                        "Date": date_str,
                        "Time": time_str,
                        "Likes": likes,
                        "Comment": comment,
                        "Sentiment_Label": sentiment_label,
                        "Sentiment_Score": sentiment_score
                    })

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)

            batches_scraped += 1
            if not stop_scraping:
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)

        driver.quit()

        # ==============================
        # 3️⃣ Convert to DataFrame & Display
        # ==============================
        if all_data:
            df = pd.DataFrame(all_data)
            st.success(f"✅ Scraping completed! Total reels collected: {df['URL'].nunique()}")

            st.subheader("👤 User Overview")
            st.write(f"**Username:** {selected_user}")
            st.write(f"**Date Range:** {START_DATE} to {END_DATE}")
            st.write(f"**Total Reels Collected:** {df['URL'].nunique()}")
            try:
                total_likes = df["Likes"].replace("N/A", 0).astype(int).sum()
            except:
                total_likes = "N/A"
            st.write(f"**Total Likes:** {total_likes}")

            sentiment_counts = df["Sentiment_Label"].value_counts(normalize=True) * 100
            st.write(f"**Sentiment Distribution (%):**")
            st.bar_chart(sentiment_counts)

            # Drill-down per reel
            st.subheader("🔍 Explore Reels")
            reel_urls = df["URL"].unique().tolist()
            selected_reels = st.multiselect("Select one or more Reels to explore", reel_urls)

            for url in selected_reels:
                post_df = df[df["URL"] == url]
                if not post_df.empty:
                    st.markdown(f"### [Reel Link]({url})")
                    st.write(f"**Date:** {post_df.iloc[0]['Date']} | **Time:** {post_df.iloc[0]['Time']}")
                    st.write(f"**Likes:** {post_df.iloc[0]['Likes']}")

                    comments_only = post_df[post_df["Comment"].notna()]
                    sentiment_counts_post = comments_only["Sentiment_Label"].value_counts(normalize=True) * 100
                    st.write(f"**Sentiment Split (%):**")
                    st.bar_chart(sentiment_counts_post)

                    st.write("📝 Comments")
                    st.dataframe(comments_only[["Comment", "Sentiment_Label", "Sentiment_Score"]].reset_index(drop=True))
                    st.markdown("---")
        else:
            st.warning("No reels found in the selected date range.")

    except Exception as e:
        st.error(f"Error occurred: {e}")
        driver.quit()
