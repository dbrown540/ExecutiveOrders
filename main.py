import requests
import json
from openai import OpenAI
from bs4 import BeautifulSoup

# Initialize the OpenAI client
client = OpenAI()

def gpt(text):
    """
    Sends a prompt to the OpenAI API and returns the response content.
    Includes error handling to catch issues during the API call.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"""
You are an AI assistant responsible for analyzing newly passed executive orders. Your job is to analyze the text and separate key words by sentiment. For example, if the executive order contains the following excerpt:
" Section 1.  Purpose and Policy.  The prior administration’s immigration policies inexcusably endangered and caused enormous suffering within our Nation, including by causing the southern border to be overrun by cartels, criminal gangs, known terrorists, human traffickers, smugglers, unvetted military-age males from foreign adversaries, and illicit narcotics.  These open-border policies are responsible for the horrific and inexcusable murders of many innocent American citizens at the hands of illegal aliens."
You will determine that the words written with a negative sentiment include the following: "suffering", "cartel", "smugglers", "narcotics", "open-border", "illegal", "aliens".

Your output should be a JSON structure where the keys are either "positive" or "negative" and the values are an array of key words.

For example:

{{
    "positive": ["keyword 1", "keyword 2", "keyword 3"],
    "negative": ["keyword 1", "keyword 2", "keyword 3"]
}}

Here is the text for you to analyze:

{text}
                    """
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in GPT call: {e}")
        return None

# Settings
base_url = "https://www.whitehouse.gov/presidential-actions/"
pages = 15
sentiment_analysis = {"positive": [], "negative": []}

# Build list of White House page URLs
whitehouse_page_links = []
for i in range(1, pages + 1):
    unique_url = base_url if i == 1 else f"{base_url}page/{i}/"
    whitehouse_page_links.append(unique_url)

# Extract executive order links from each page
links_to_executive_orders = []
for wh_link in whitehouse_page_links:
    print(wh_link)
    try:
        response = requests.get(wh_link)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {wh_link}: {e}")
        continue

    soup = BeautifulSoup(response.text, 'html.parser')
    h2_tags = soup.find_all("h2", class_="wp-block-post-title")
    
    for h2_tag in h2_tags:
        a_tag = h2_tag.find("a")
        if a_tag:
            executive_order_href = a_tag.get("href")
            links_to_executive_orders.append(executive_order_href)

# Process each executive order
for i, executive_order in enumerate(links_to_executive_orders):
    print(f"Analyzing Executive order {i}/{len(links_to_executive_orders)}...")
    try:
        response = requests.get(executive_order)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching executive order {executive_order}: {e}")
        continue

    soup = BeautifulSoup(response.text, 'html.parser')
    p_tags = soup.find_all("p")

    executive_order_string = ""
    for p_tag in p_tags:
        executive_order_string += p_tag.getText()

    print("Sending request to gpt...")
    analyzed_keywords = gpt(text=executive_order_string)
    if analyzed_keywords is None:
        print("Skipping this executive order due to GPT error.")
        continue

    # Clean the GPT response before parsing JSON
    parsed_keywords = analyzed_keywords.replace("```json", "").replace("```", "")
    
    try:
        new_sentiment_analysis = json.loads(parsed_keywords)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from GPT response: {e}")
        continue

    positive_keywords = new_sentiment_analysis.get("positive", [])
    negative_keywords = new_sentiment_analysis.get("negative", [])

    # Update sentiment analysis dictionary while avoiding duplicates
    for word in positive_keywords:
        if word not in sentiment_analysis["positive"]:
            sentiment_analysis["positive"].append(word)

    for word in negative_keywords:
        if word not in sentiment_analysis["negative"]:
            sentiment_analysis["negative"].append(word)

print(sentiment_analysis)
