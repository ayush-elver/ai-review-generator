import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import re
import pandas as pd
import random
from faker import Faker
from datetime import datetime, timezone
from io import BytesIO

st.set_page_config(page_title="AI Review Generator", page_icon="⭐", layout="centered")

st.title("⭐ AI Product Review Generator")

st.write("Generate realistic customer reviews from a product page and download them as Excel.")

# -----------------------------
# User Inputs
# -----------------------------
api_key = st.text_input("Gemini API Key", type="password")

product_url = st.text_input(
    "Product URL",
    placeholder="https://example.com/products/product-name"
)

product_id = st.text_input(
    "Product ID",
    placeholder="9077778350338"
)

num_reviews = st.slider(
    "Number of Reviews",
    min_value=5,
    max_value=20,
    value=5
)

generate = st.button("Generate Reviews")

if generate:

    if not api_key:
        st.error("Please enter your Gemini API Key.")
        st.stop()

    if not product_url:
        st.error("Please enter Product URL.")
        st.stop()

    if not product_id:
        st.error("Please enter Product ID.")
        st.stop()

    try:

        with st.spinner("Fetching product page..."):

            html = requests.get(product_url, timeout=20).text

            soup = BeautifulSoup(html, "html.parser")

            content = soup.get_text(separator=" ", strip=True)

            content = content[:10000]

        with st.spinner("Generating AI reviews..."):

            genai.configure(api_key=api_key)

            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
You are a real customer who purchased this product.

Product Information:
{content}

Generate {num_reviews} realistic customer reviews.

Rules:
- Title should be under 4 words.
- Main review should be under 15 words.
- Rating should feel genuine.

Return ONLY a valid JSON array.

Example:

[
 {{
   "title":"Excellent Sound",
   "main_review":"Battery backup is amazing and audio quality is excellent."
 }}
]
"""

            response = model.generate_content(prompt)

            response_text = response.text

            clean_json = re.sub(
                r"^```json\\s*|\\s*```$",
                "",
                response_text.strip(),
                flags=re.DOTALL
            )

            reviews = json.loads(clean_json)

        fake = Faker("en_IN")

        records = []

        for review in reviews:

            first_name = fake.first_name()

            last_name = fake.last_name()

            records.append({
                "title": review.get("title", ""),
                "body": review.get("main_review", ""),
                "rating": random.randint(4, 5),
                "review_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "reviewer_name": f"{first_name} {last_name}",
                "reviewer_email": f"{first_name.lower()}.{last_name.lower()}{random.randint(1,999)}@gmail.com",
                "product_id": product_id,
                "product_handle": "",
                "reply": "",
                "picture_urls": ""
            })

        df = pd.DataFrame(records)

        st.success(f"Generated {len(df)} reviews.")

        st.dataframe(df)

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        st.download_button(
            label="📥 Download Reviews Excel",
            data=output,
            file_name="reviews.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(str(e))

