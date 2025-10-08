import streamlit as st
import pandas as pd
from datetime import datetime
from textblob import TextBlob
from instagrapi import Client

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

    try:
        # ==============================
        # 2️⃣ Instagram Login with instagrapi
        # ==============================
        cl = Client()
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        st.success("✅ Logged in successfully.")

        # Get user ID
        user_id = cl.user_id_from_username(selected_user)

        # Fetch reels (IGTV / Reels are treated as media)
        medias = cl.user_medias(user_id, amount=100)  # Adjust amount as needed
        all_data = []

        # Placeholder for progress updates
        progress_text = st.empty()
        total_reels = len(medias)
        processed_reels = 0

        for media in medias:
            processed_reels += 1
            progress_text.info(f"Processing reels... {processed_reels}/{total_reels} covered")

            media_date = media.taken_at
            if START_DATE <= media_date <= END_DATE:
                reel_url = f"https://www.instagram.com/reel/{media.pk}/"
                views = media.view_count if hasattr(media, "view_count") else "N/A"
                likes = media.like_count if hasattr(media, "like_count") else "N/A"
                caption = media.caption_text if media.caption_text else ""
                
                # Comments
                comments_data = []
                comments = cl.media_comments(media.pk)
                for c in comments:
                    comments_data.append(c.text)
                
                # Include caption as first comment
                if caption:
                    comments_data.insert(0, caption)
                
                # Sentiment analysis
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
                        "Date": media_date.strftime("%Y-%m-%d"),
                        "Time": media_date.strftime("%H:%M:%S"),
                        "Likes": likes,
                        "Comment": comment,
                        "Sentiment_Label": sentiment_label,
                        "Sentiment_Score": sentiment_score
                    })

        progress_text.success(f"✅ Scraping completed! Total reels processed: {processed_reels}")

        # ==============================
        # 3️⃣ Convert to DataFrame
        # ==============================
        if all_data:
            df = pd.DataFrame(all_data)
            st.success(f"✅ Scraping completed! Total reels collected: {df['URL'].nunique()}")

            # ==============================
            # 4️⃣ Overview
            # ==============================
            st.subheader("👤 User Overview")
            st.write(f"**Username:** {selected_user}")
            st.write(f"**Date Range:** {from_date} to {to_date}")
            st.write(f"**Total Reels Collected:** {df['URL'].nunique()}")
            total_likes = df["Likes"].replace("N/A", 0).astype(int).sum()
            st.write(f"**Total Likes:** {total_likes}")

            sentiment_counts = df["Sentiment_Label"].value_counts(normalize=True) * 100
            st.write(f"**Sentiment Distribution (%):**")
            st.bar_chart(sentiment_counts)

            # ==============================
            # 5️⃣ Drill-down per Reel
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
