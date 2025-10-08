import streamlit as st
import pandas as pd
from datetime import datetime
from instagrapi import Client
from textblob import TextBlob

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

    START_DATE = datetime.combine(from_date, datetime.min.time())
    END_DATE = datetime.combine(to_date, datetime.max.time())

    st.info("Starting scraping... This may take a few minutes depending on number of reels.")

    # ==============================
    # 2️⃣ Login with instagrapi
    # ==============================
    try:
        client = Client()
        client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        st.success("✅ Logged in successfully.")
    except Exception as e:
        st.error(f"Login failed: {e}")
        st.stop()

    # ==============================
    # 3️⃣ Fetch Reels
    # ==============================
    try:
        user_id = client.user_id_from_username(selected_user)
        reels = client.user_medias(user_id, amount=1000)  # Fetch up to 1000 recent posts
        all_data = []

        for reel in reels:
            # Only reels
            if reel.media_type != 2:  # 2 = video (reel)
                continue

            reel_datetime = reel.taken_at
            if not (START_DATE <= reel_datetime <= END_DATE):
                continue

            reel_url = f"https://www.instagram.com/reel/{reel.code}/"
            views = reel.video_view_count or "N/A"
            likes = reel.like_count or "N/A"

            # Caption
            comments_data = []
            if reel.caption_text:
                comments_data.append(reel.caption_text)

            # Comments (limited to first 50)
            comments = client.media_comments(reel.id, amount=50)
            for c in comments:
                comments_data.append(c.text)

            for comment in comments_data:
                sentiment_score = TextBlob(comment).sentiment.polarity
                if sentiment_score > 0:
                    sentiment_label = "Positive"
                elif sentiment_score < 0:
                    sentiment_label = "Negative"
                else:
                    sentiment_label = "Neutral"

                all_data.append({
                    "URL": reel_url,
                    "Views": views,
                    "Date": reel_datetime.strftime("%Y-%m-%d"),
                    "Time": reel_datetime.strftime("%H:%M:%S"),
                    "Likes": likes,
                    "Comment": comment,
                    "Sentiment_Label": sentiment_label,
                    "Sentiment_Score": sentiment_score
                })

        # ==============================
        # 4️⃣ Convert to DataFrame
        # ==============================
        if all_data:
            df = pd.DataFrame(all_data)
            st.success(f"✅ Scraping completed! Total reels collected: {len(df)}")

            # ==============================
            # 5️⃣ Overview
            # ==============================
            st.subheader("👤 User Overview")
            st.write(f"**Username:** {selected_user}")
            st.write(f"**Date Range:** {START_DATE.date()} to {END_DATE.date()}")
            st.write(f"**Total Reels Collected:** {df['URL'].nunique()}")
            total_likes = df["Likes"].replace("N/A", 0).astype(int).sum()
            st.write(f"**Total Likes:** {total_likes}")

            sentiment_counts = df["Sentiment_Label"].value_counts(normalize=True) * 100
            st.write(f"**Sentiment Distribution (%):**")
            st.bar_chart(sentiment_counts)

            # ==============================
            # 6️⃣ Drill-down per Reel
            # ==============================
            st.subheader("🔍 Explore Reels")
            reel_urls = df["URL"].unique().tolist()
            selected_reels = st.multiselect("Select one or more Reels to explore", reel_urls)

            for url in selected_reels:
                post_df = df[df["URL"] == url]
                if not post_df.empty:
                    st.markdown(f"### [Reel Link]({url})")
                    st.write(f"**Caption:** {post_df.iloc[0]['Comment']}")
                    st.write(f"**Date:** {post_df.iloc[0]['Date']} | **Time:** {post_df.iloc[0]['Time']}")
                    st.write(f"**Views:** {post_df.iloc[0]['Views']} | **Likes:** {post_df.iloc[0]['Likes']}")

                    # Sentiment breakdown
                    comments_only = post_df[post_df["Comment"].notna()]
                    sentiment_counts_post = comments_only["Sentiment_Label"].value_counts(normalize=True) * 100
                    st.write(f"**Sentiment Split (%):**")
                    st.bar_chart(sentiment_counts_post)

                    # Show all comments
                    st.write("📝 Comments")
                    st.dataframe(comments_only[["Comment", "Sentiment_Label", "Sentiment_Score"]].reset_index(drop=True))
                    st.markdown("---")
        else:
            st.warning("No reels found in the selected date range.")

    except Exception as e:
        st.error(f"Error occurred: {e}")
