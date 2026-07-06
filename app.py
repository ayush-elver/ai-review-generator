import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
from faker import Faker
from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlparse
import random
import json
import re

st.set_page_config(
    page_title="AI Product Review Generator",
    page_icon="⭐",
    layout="centered"
)

st.title("AI Product Review Generator")

st.write("Generate AI customer reviews and download them as Excel.")

# ----------------------------
# Inputs
# ----------------------------

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
    5,
    20,
    5
)

generate = st.button("Generate Reviews")

# ----------------------------
# Main
# ----------------------------

if generate:

    if not api_key:
        st.error("Please enter Gemini API Key.")
        st.stop()

    if not product_url:
        st.error("Please enter Product URL.")
        st.stop()

    if not product_id:
        st.error("Please enter Product ID.")
        st.stop()

    try:

        # Configure Gemini
        genai.configure(api_key=api_key)

        # ----------------------------
        # Fetch webpage
        # ----------------------------

        with st.spinner("Fetching product page..."):

            headers = {
                "User-Agent": "Mozilla/5.0"
            }

            response = requests.get(
                product_url,
                headers=headers,
                timeout=20
            )

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unnecessary tags
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            content = soup.get_text(
                separator=" ",
                strip=True
            )

            content = content[:12000]

        # ----------------------------
        # Gemini
        # ----------------------------

        with st.spinner("Generating reviews..."):

            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
You are a genuine customer.

Based on the product information below, generate exactly {num_reviews} realistic reviews.

Product Information:

{content}

Rules:

- Return ONLY JSON.
- No markdown.
- No explanation.
- No extra text.

Format:

[
  {{
    "title":"Excellent Sound",
    "main_review":"Battery backup is amazing."
  }}
]
"""

            response = model.generate_content(prompt)

            response_text = ""

            try:
                response_text = response.text
            except:
                pass

            if not response_text:
                st.error("Gemini returned an empty response.")
                st.write(response)
                st.stop()

            # Debug (optional)
            with st.expander("Gemini Raw Response"):
                st.code(response_text)

            # Remove markdown
            response_text = response_text.replace("```json", "")
            response_text = response_text.replace("```", "")
            response_text = response_text.strip()

            # Extract JSON array
            match = re.search(r"\[.*\]", response_text, re.DOTALL)

            if not match:
                st.error("Gemini did not return JSON.")
                st.stop()

            json_text = match.group()

            try:
                reviews = json.loads(json_text)

            except Exception as e:
                st.error("JSON Parsing Error")
                st.code(json_text)
                st.exception(e)
                st.stop()

        # ----------------------------
        # Create dataframe
        # ----------------------------

        fake = Faker("en_IN")

        product_handle = urlparse(product_url).path.split("/")[-1]

        rows = []

        for review in reviews:

            first = fake.first_name()
            last = fake.last_name()

            rows.append({

                "title": review.get("title", ""),

                "body": review.get("main_review", ""),

                "rating": random.randint(4, 5),

                "review_date": datetime.now(
                    timezone.utc
                ).strftime("%m-%d-%Y %H:%M:%S UTC"),

                "reviewer_name": f"{first} {last}",

                "reviewer_email":
                f"{first.lower()}.{last.lower()}{random.randint(1,999)}@gmail.com",

                "product_id": product_id,

                "product_handle": product_handle,

                "reply": "",

                "picture_urls": ""

            })

        df = pd.DataFrame(rows)

        st.success(f"Generated {len(df)} Reviews")

        st.dataframe(df, use_container_width=True)

        # ----------------------------
        # Excel Download
        # ----------------------------

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                index=False
            )

        output.seek(0)

        st.download_button(
            "📥 Download Excel",
            output,
            file_name="reviews.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except requests.exceptions.RequestException as e:
        st.error(f"Website Error: {e}")

    except Exception as e:
        st.exception(e)
